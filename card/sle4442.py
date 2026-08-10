from helpers.config import *
from smartcard.scard import *
from helpers.utils import *
from helpers.exceptions import *

# Card interface class
class SLE4442Interface:
    def __init__(self, log_callback=None, write_chunk_size=DEFAULT_WRITE_CHUNK_SIZE,
                 read_chunk_size=DEFAULT_READ_CHUNK_SIZE):
        """Initialize SLE4442 interface

        Args:
            log_callback: Optional callback function for logging
            write_chunk_size: Size of chunks for write operations (default: 16 bytes)
                             Some readers may support larger values for better performance
            read_chunk_size: Size of chunks for read operations (default: 32 bytes)
                             Le is a single APDU byte (max 255), and some readers cap
                             the response per-transaction regardless of Le, so reads
                             are looped in chunks of this size.
        """
        self.hcontext = None
        self.hcard = None
        self.protocol = None
        self.reader = None
        self.log_callback = log_callback
        self.log_apdus = False
        self.is_omnikey = False  # Track if reader is OMNIKEY
        self.write_chunk_size = write_chunk_size  # Configurable write chunk size
        self.read_chunk_size = read_chunk_size    # Configurable read chunk size

    def establish(self):
        """Establish PC/SC context"""
        hresult, hcontext = SCardEstablishContext(SCARD_SCOPE_USER)
        if hresult != SCARD_S_SUCCESS:
            raise RuntimeError("Failed to establish context: " + SCardGetErrorMessage(hresult))
        self.hcontext = hcontext

    def list_readers(self):
        """List available smart card readers"""
        if self.hcontext is None:
            self.establish()
        hresult, readers = SCardListReaders(self.hcontext, [])
        if hresult != SCARD_S_SUCCESS:
            raise RuntimeError("Failed to list readers: " + SCardGetErrorMessage(hresult))
        return readers

    def connect(self, reader_name):
        """Connect to a specific reader"""
        hresult, hcard, dwActiveProtocol = SCardConnect(
            self.hcontext, reader_name, SCARD_SHARE_SHARED,
            SCARD_PROTOCOL_T0 | SCARD_PROTOCOL_T1
        )
        if hresult != SCARD_S_SUCCESS:
            raise RuntimeError("Unable to connect: " + SCardGetErrorMessage(hresult))

        self.hcard = hcard
        self.protocol = dwActiveProtocol
        self.reader = reader_name

        # Detect reader type
        self.is_omnikey = self._detect_omnikey_reader(reader_name)
        if self.log_callback:
            reader_type = "OMNIKEY" if self.is_omnikey else "Standard"
            self.log_callback(f"Detected reader type: {reader_type}")

        # Select wrapper for SLE
        hresult, resp = SCardTransmit(self.hcard, self.protocol, SELECT)
        if hresult != SCARD_S_SUCCESS:
            raise RuntimeError("SELECT failed: " + SCardGetErrorMessage(hresult))
        return resp

    def _detect_omnikey_reader(self, reader_name):
        """Detect if reader is an OMNIKEY device"""
        reader_name_lower = reader_name.lower()
        omnikey_identifiers = [
            'omnikey',
            'hid global',
            'hid omnikey',
        ]
        return any(identifier in reader_name_lower for identifier in omnikey_identifiers)

    def disconnect(self, release_context=True):
        """Disconnect from reader and optionally release context

        Args:
            release_context: If True, release the PC/SC context (default: True)
                           Set to False to keep context for reconnecting to another reader
        """
        if self.hcard:
            hresult = SCardDisconnect(self.hcard, SCARD_UNPOWER_CARD)
            if hresult != SCARD_S_SUCCESS:
                raise RuntimeError("Failed to disconnect: " + SCardGetErrorMessage(hresult))
            self.hcard = None
        if release_context and self.hcontext:
            hresult = SCardReleaseContext(self.hcontext)
            if hresult != SCARD_S_SUCCESS:
                raise RuntimeError("Failed to release context: " + SCardGetErrorMessage(hresult))
            self.hcontext = None
        self.is_omnikey = False

    def transmit(self, apdu):
        """Transmit APDU and handle response"""
        if not self.hcard:
            raise RuntimeError("Not connected")

        # Log sent APDU
        if self.log_apdus and self.log_callback:
            self.log_callback(f">> APDU: {format_apdu(apdu)}")

        hresult, resp = SCardTransmit(self.hcard, self.protocol, apdu)
        if hresult != SCARD_S_SUCCESS:
            raise RuntimeError("Transmit failed: " + SCardGetErrorMessage(hresult))

        # Log received response
        if self.log_apdus and self.log_callback:
            self.log_callback(f"<< RESP: {format_apdu(resp)} ({len(resp)} bytes)")

        # Check for INS not supported error (6D 00)
        if len(resp) >= 2 and resp[-2] == 0x6D and resp[-1] == 0x00:
            raise INSNotSupportedError(
                f"INS Not Supported (6D 00)\n"
                f"APDU: {format_apdu(apdu)}\n\n"
                f"This reader does not support this command.\n"
                f"Try using 'Tools → Send Raw APDU' for reader-specific commands."
            )

        # Check for command not allowed (69 86) - reader level
        elif len(resp) >= 2 and resp[-2] == 0x69 and resp[-1] == 0x86:
            raise CommandNotAllowedError(
                f"Command Not Allowed (69 86)\n"
                f"APDU: {format_apdu(apdu)}\n\n"
                f"The reader/card rejected this command due to security restrictions.\n\n"
                f"Possible reasons:\n"
                f"• Card needs to be unlocked with correct PSC (PIN)\n"
                f"• Operation requires authentication\n"
                f"• Card is permanently blocked (error counter = 0)\n"
                f"• Write-protected memory area\n\n"
                f"Try:\n"
                f"1. Check security memory to see error counter\n"
                f"2. Unlock card with correct PSC\n"
                f"3. Check protection bits for write operations"
            )

        # Check for security not satisfied (69 82) - card level
        elif len(resp) >= 2 and resp[-2] == 0x69 and resp[-1] == 0x82:
            raise SecurityNotSatisfiedError(
                f"Security Condition Not Satisfied (69 82)\n"
                f"APDU: {format_apdu(apdu)}\n\n"
                f"The card security requirements are not met.\n\n"
                f"Possible reasons:\n"
                f"• Card needs to be unlocked with correct PSC (PIN)\n"
                f"• Authentication required before this operation\n"
                f"• Security conditions not satisfied\n\n"
                f"Try:\n"
                f"1. Unlock card with correct PSC\n"
                f"2. Check security memory status"
            )

        # Check for wrong PIN (63 Cx) - wrong PIN with retries remaining
        elif len(resp) >= 2 and resp[-2] == 0x63 and resp[-1] & 0xF0 == 0xC0:
            retries = resp[-1] & 0x0F
            raise WrongPINError(
                f"Wrong PIN (63 C{retries:X})\n"
                f"APDU: {format_apdu(apdu)}\n\n"
                f"Incorrect PSC (PIN) provided.\n\n"
                f"Remaining attempts: {retries}\n"
                f"{'⚠️ WARNING: Card will be permanently blocked at 0 attempts!' if retries <= 2 else ''}\n\n"
                f"Try:\n"
                f"1. Verify you have the correct PSC\n"
                f"2. Check security memory to see error counter\n"
                f"3. Be careful - limited attempts remaining!"
            )

        return resp

    def _check_response(self, resp, operation="Operation"):
        """Check response status words"""
        if len(resp) < 2:
            raise RuntimeError(f"{operation} failed: Short response")

        sw1, sw2 = resp[-2], resp[-1]
        if sw1 != 0x90:
            raise RuntimeError(f"{operation} failed: SW1={sw1:02X}, SW2={sw2:02X}")

        return bytes(resp[:-2])

    # High-level operations
    def read(self, addr=0, length=MAIN_MEM_SIZE):
        """Read data from card memory (chunked)

        Le is a single APDU byte, so it can never exceed 255 - requesting
        MAIN_MEM_SIZE (256) in a single transaction overflows it. On top of
        that, some readers ignore Le for this pseudo-APDU and return more
        bytes than requested per transaction. To handle both cases, reads
        are issued in chunks (self.read_chunk_size), and every byte the
        reader actually returns is kept (nothing is discarded) - so the
        result may be longer than `length` if the reader over-delivers.
        The address is advanced by however many bytes were actually
        received each time, and the loop stops once at least `length`
        bytes have been collected.
        """
        if length <= 0:
            return b''

        if addr < 0 or addr + length > MAIN_MEM_SIZE:
            raise ValueError(f"Read would exceed memory size")

        data = bytearray()
        current_addr = addr
        remaining = length

        while remaining > 0:
            # Le must fit in a single byte (max 255)
            le = min(remaining, self.read_chunk_size, 0xFF)

            apdu = READ_APDU + [current_addr, le]
            resp = self.transmit(apdu)
            chunk = self._check_response(resp, f"Read at address {current_addr:02X}")

            if not chunk:
                raise RuntimeError(
                    f"Read at address {current_addr:02X} returned no data "
                    f"(expected up to {le} bytes)"
                )

            if len(chunk) > le and self.log_callback:
                self.log_callback(
                    f"Read at address {current_addr:02X}: reader returned "
                    f"{len(chunk)} bytes for a {le}-byte request - keeping all of them"
                )

            data.extend(chunk)
            current_addr += len(chunk)
            remaining -= len(chunk)

        return bytes(data)

    def write(self, addr, data):
        """Write data to card memory (with reader-specific APDU support)"""
        if not isinstance(data, (bytes, bytearray)):
            raise ValueError("Data must be bytes or bytearray")

        if addr < 0 or addr >= MAIN_MEM_SIZE:
            raise ValueError(f"Invalid address: {addr}")

        if addr + len(data) > MAIN_MEM_SIZE:
            raise ValueError(f"Write would exceed memory size")

        # Choose APDU based on reader type
        if self.is_omnikey:
            if self.log_callback:
                self.log_callback("Using OMNIKEY write command (FF D6)")
            write_apdu_base = OMNIKEY_WRITE_APDU
        else:
            if self.log_callback:
                self.log_callback("Using standard write command (FF D0)")
            write_apdu_base = WRITE_APDU

        # Write in chunks (configurable size, default 16 bytes)
        # SLE4442 supports byte-by-byte writes, but chunking improves performance
        # Some readers may support larger chunks (32, 64, or even 256 bytes)
        bytes_written = 0

        for i in range(0, len(data), self.write_chunk_size):
            chunk = data[i:i + self.write_chunk_size]
            current_addr = addr + i

            apdu = write_apdu_base + [current_addr, len(chunk)] + list(chunk)
            resp = self.transmit(apdu)
            self._check_response(resp, f"Write at address {current_addr:02X}")

            bytes_written += len(chunk)

        if self.log_callback:
            self.log_callback(
                f"Wrote {bytes_written} bytes in {(len(data) + self.write_chunk_size - 1) // self.write_chunk_size} chunks")

        return bytes_written

    def read_protection_bits(self):
        """Read protection bits (32 bits)

        Returns 4 bytes representing protection status of first 32 bytes of memory.

        Bit mapping (LSB-first):
            - Byte 0, bit 0 (LSB) = protection for address 0x00
            - Byte 0, bit 1       = protection for address 0x01
            - ...
            - Byte 0, bit 7       = protection for address 0x07
            - Byte 1, bit 0       = protection for address 0x08
            - ...
            - Byte 3, bit 7       = protection for address 0x1F (31)

        Protection bit values:
            - 1 = byte is writable (not protected)
            - 0 = byte is write-protected (cannot be written)

        Note: Protection bits themselves can be written to protect memory,
              but once set to 0 (protected), they cannot be changed back to 1.
        """
        apdu = OMNIKEY_READ_PROT_APDU if self.is_omnikey else READ_PROT_APDU
        resp = self.transmit(apdu)
        return self._check_response(resp, "Read protection")

    def read_security(self):
        """Read security memory (4 bytes)

        Returns 4 bytes:
            - Byte 0: Error counter (7 = unlocked, 0 = permanently blocked)
            - Bytes 1-3: PSC (Programmable Security Code / PIN)

        Error counter values:
            - 7: Card is unlocked (correct PSC provided)
            - 6-1: Number of remaining unlock attempts
            - 0: Card permanently blocked (no more attempts)

        Note: Some readers (notably OMNIKEY) may not support this command.
              In that case, an INSNotSupportedError will be raised.
        """
        apdu = OMNIKEY_READ_SEC_APDU if self.is_omnikey else READ_SEC_APDU
        resp = self.transmit(apdu)
        return self._check_response(resp, "Read security")

    def is_byte_protected(self, address):
        """Check if a specific byte is write-protected

        Args:
            address: Memory address (0-31) to check

        Returns:
            True if byte is write-protected (bit = 0)
            False if byte is writable (bit = 1)

        Raises:
            ValueError: If address is outside protected range (0-31)
        """
        if address < 0 or address >= PROT_BITS:
            raise ValueError(f"Address {address} is outside protected range (0-{PROT_BITS - 1})")

        prot = self.read_protection_bits()

        # Calculate byte and bit position
        byte_index = address // 8
        bit_position = address % 8

        # Extract bit (LSB-first)
        bit_value = (prot[byte_index] >> bit_position) & 1

        # Return True if protected (bit = 0), False if writable (bit = 1)
        return bit_value == 0

    def unlock_with_pin_bytes(self, pin_bytes: bytes):
        """Unlock card with 3-byte PSC

        Returns:
            "unlocked" - PSC correct, card unlocked (error counter = 7)
            "wrong" - PSC incorrect, error counter decremented
            "blocked" - Card permanently blocked (error counter = 0)

        Note: On some readers (OMNIKEY), reading security memory may not be supported.
              In that case, the method relies solely on APDU response codes.
        """
        if len(pin_bytes) != PSC_LENGTH:
            raise ValueError(f"PSC must be exactly {PSC_LENGTH} bytes")

        apdu = UNLOCK_APDU + list(pin_bytes)
        resp = self.transmit(apdu)

        if len(resp) < 2:
            raise RuntimeError("Invalid unlock response")

        # Check for standard success response
        if resp[-2] == 0x90 and resp[-1] == 0x00:
            # Try to verify by reading security memory (may not work on all readers)
            try:
                sec = self.read_security()
                error_counter = sec[0]
                if error_counter == 7:
                    return "unlocked"
                elif error_counter == 0:
                    return "blocked"
                else:
                    # Shouldn't happen - 90 00 but counter not 7
                    return "wrong"
            except INSNotSupportedError:
                # Reader doesn't support read security (e.g., OMNIKEY)
                # Trust the 90 00 response
                if self.log_callback:
                    self.log_callback("Note: Reader doesn't support reading security memory, trusting APDU response")
                return "unlocked"

        # Check for wrong PIN with retries remaining (63 Cx)
        elif resp[-2] == 0x63 and resp[-1] & 0xF0 == 0xC0:
            retries = resp[-1] & 0x0F
            if retries == 0:
                return "blocked"
            else:
                return "wrong"

        # For any other response, try to read security memory to get actual state
        else:
            try:
                sec = self.read_security()
                error_counter = sec[0]
                if error_counter == 7:
                    return "unlocked"
                elif error_counter == 0:
                    return "blocked"
                else:
                    return "wrong"
            except INSNotSupportedError:
                # Can't determine state, assume wrong PIN
                return "wrong"

    def change_pin(self, new_pin_bytes: bytes, old_pin_bytes: bytes = None):
        """Change PSC to new 3-byte value

        Args:
            new_pin_bytes: New 3-byte PSC
            old_pin_bytes: Old 3-byte PSC (required for OMNIKEY readers)

        For OMNIKEY readers:
            - Requires old PIN, card doesn't need to be unlocked first
            - Uses FF 21 command with authentication

        For standard readers:
            - Card MUST be unlocked with current PSC first
            - Uses FF D2 command to write security memory
        """
        if len(new_pin_bytes) != PSC_LENGTH:
            raise ValueError(f"New PSC must be exactly {PSC_LENGTH} bytes")

        # Use OMNIKEY-specific change PIN command if available and old PIN provided
        if self.is_omnikey and old_pin_bytes is not None:
            if len(old_pin_bytes) != PSC_LENGTH:
                raise ValueError(f"Old PSC must be exactly {PSC_LENGTH} bytes")

            if self.log_callback:
                self.log_callback("Using OMNIKEY change PIN command (FF 21)")

            # OMNIKEY APDU: FF 21 00 00 06 [old PSC 3 bytes] [new PSC 3 bytes]
            # This command authenticates with old PSC, no unlock required
            apdu = OMNIKEY_CHANGE_PIN_APDU + list(old_pin_bytes) + list(new_pin_bytes)
            resp = self.transmit(apdu)
            self._check_response(resp, "Change PIN (OMNIKEY)")

            # Note: Cannot verify by reading security memory on OMNIKEY
            # The command either succeeds (90 00) or fails with error
            if self.log_callback:
                self.log_callback("Note: OMNIKEY readers don't support reading security memory for verification")

        else:
            # Standard change PIN command (requires card to be already unlocked)
            if self.log_callback:
                self.log_callback("Using standard change PIN command (FF D2)")

            # Verify card is unlocked before attempting PIN change
            # (only possible on readers that support read_security)
            try:
                sec = self.read_security()
                error_counter = sec[0]
                if error_counter != 7:
                    raise SecurityNotSatisfiedError(
                        f"Card must be unlocked before changing PIN.\n"
                        f"Current error counter: {error_counter} (should be 7)\n\n"
                        f"Please unlock the card with the current PSC first."
                    )
            except INSNotSupportedError:
                # Reader doesn't support read_security
                # Proceed anyway and let the write command fail if not unlocked
                if self.log_callback:
                    self.log_callback("Warning: Cannot verify unlock state - reader doesn't support read_security")

            apdu = WRITE_SEC_APDU + list(new_pin_bytes)
            resp = self.transmit(apdu)
            self._check_response(resp, "Change PIN")

        return True

    def get_reader_info(self):
        """Get reader information"""
        return {
            'name': self.reader,
            'type': 'OMNIKEY' if self.is_omnikey else 'Standard',
            'is_omnikey': self.is_omnikey,
            'write_apdu': format_apdu(OMNIKEY_WRITE_APDU) if self.is_omnikey else format_apdu(WRITE_APDU)
        }
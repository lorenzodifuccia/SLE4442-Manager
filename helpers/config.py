# ACS APDUs
SELECT = [0xFF, 0xA4, 0x00, 0x00, 0x01, 0x06]
READ_APDU = [0xFF, 0xB0, 0x00]                   # + addr + length
UNLOCK_APDU = [0xFF, 0x20, 0x00, 0x00, 0x03]     # + 3 bytes PSC
WRITE_APDU = [0xFF, 0xD0, 0x00]                  # + addr + length + data

READ_PROT_APDU = [0xFF, 0xB2, 0x00, 0x00, 0x04]  # read protection 32 bits
READ_SEC_APDU = [0xFF, 0xB2, 0x01, 0x00, 0x04]   # read security memory
WRITE_SEC_APDU = [0xFF, 0xD2, 0x01, 0x00, 0x03]  # + 3 bytes new PSC

# OMNIKEY APDUs
# https://www.hidglobal.com/sites/default/files/documentlibrary/plt-03099_a.5_-_omnikey_sw_dev_guide_0.pdf
OMNIKEY_WRITE_APDU = [0xFF, 0xD6, 0x00]          # + addr + length + data
OMNIKEY_CHANGE_PIN_APDU = [0xFF, 0x21, 0x00, 0x00, 0x06] # + 3 bytes old PSC + 3 bytes new PSC
OMNIKEY_READ_PROT_APDU = [0xFF, 0xB0, 0x01, 0x00, 0x04]  # READ BINARY at 0x0100
OMNIKEY_READ_SEC_APDU  = [0xFF, 0xB0, 0x01, 0x04, 0x04]  # READ BINARY at 0x0104

# Card constants
MAIN_MEM_SIZE = 256            # main EEPROM bytes
PROT_BITS = 32                 # first 32 bytes have protection bits
PSC_LENGTH = 3                 # 3-byte programmable security code
DEFAULT_WRITE_CHUNK_SIZE = 16  # default chunk size for write operations (bytes)
DEFAULT_READ_CHUNK_SIZE = 32   # default chunk size for read operations (bytes)
                                # Le is a single APDU byte (max 255): requesting
                                # MAIN_MEM_SIZE (256) in one shot overflows it, and
                                # some readers cap the response per-transaction
                                # regardless of Le. read() loops in chunks to work
                                # around both issues.
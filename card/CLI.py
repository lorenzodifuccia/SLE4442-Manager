from card.sle4442 import *
from datetime import datetime
import sys
import base64
import hashlib
import argparse

# CLI Implementation
class CLIManager:
    """Command-line interface manager for SLE4442"""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.intf = SLE4442Interface(log_callback=self.log if verbose else None)

    def log(self, message):
        """Print log message if verbose mode enabled"""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {message}", file=sys.stderr)

    def connect_to_reader(self, reader_index=0):
        """Connect to a reader by index (default: first reader)"""
        self.intf.establish()
        readers = self.intf.list_readers()

        if not readers:
            raise RuntimeError("No smart card readers found")

        if reader_index >= len(readers):
            raise RuntimeError(f"Reader index {reader_index} out of range (0-{len(readers)-1})")

        reader = readers[reader_index]
        self.log(f"Available readers: {', '.join(readers)}")
        self.log(f"Connecting to: {reader}")

        self.intf.connect(reader)
        return reader

    def cmd_list_readers(self):
        """List all available readers"""
        self.intf.establish()
        readers = self.intf.list_readers()

        if not readers:
            print("No readers found")
            return 1

        print(f"Found {len(readers)} reader(s):")
        for i, reader in enumerate(readers):
            print(f"  [{i}] {reader}")
        return 0

    def cmd_info(self, args):
        """Show card information"""
        self.connect_to_reader(args.reader)

        sec = self.intf.read_security()
        prot = self.intf.read_protection_bits()
        reader_info = self.intf.get_reader_info()

        print("=== Card Information ===")
        print(f"Card Type: SLE4442")
        print(f"Main Memory: {MAIN_MEM_SIZE} bytes")
        print(f"Protection Bits: {PROT_BITS} bits")
        print()
        print(f"Security Memory: {sec.hex().upper()}")
        print(f"  Error Counter: 0x{sec[0]:02X} ({sec[0]} attempts left)")
        print(f"  PSC Bytes: {sec[1:].hex().upper()}")
        print()
        print(f"Protection Bits: {prot.hex().upper()}")
        print()
        print(f"Reader: {reader_info['name']}")
        print(f"Reader Type: {reader_info['type']}")

        self.intf.disconnect()
        return 0

    def cmd_read(self, args):
        """Read card memory"""
        self.connect_to_reader(args.reader)

        data = self.intf.read(0, MAIN_MEM_SIZE)

        if args.format == 'hex':
            print(data.hex().upper())
        elif args.format == 'base64':
            print(base64.b64encode(data).decode())
        else:  # hexdump
            print(hexdump(data))

        self.intf.disconnect()
        return 0

    def cmd_write(self, args):
        """Write data to card"""
        # Read input data
        if args.input == '-':
            # Read from stdin
            import sys
            hex_data = sys.stdin.read().strip()
        else:
            # Read from file
            with open(args.input, 'r') as f:
                hex_data = f.read().strip()

        # Clean hex data
        hex_data = hex_data.replace(' ', '').replace('\n', '').replace('\r', '')

        # Validate
        if len(hex_data) != MAIN_MEM_SIZE * 2:
            raise ValueError(
                f"Data must be exactly {MAIN_MEM_SIZE*2} hex characters "
                f"({MAIN_MEM_SIZE} bytes), got {len(hex_data)}"
            )

        data = bytes.fromhex(hex_data)

        # Connect and write
        self.connect_to_reader(args.reader)

        if not args.force:
            print(f"WARNING: About to write {len(data)} bytes to card")
            print(f"SHA-256: {hashlib.sha256(data).hexdigest()}")
            response = input("Continue? [y/N]: ")
            if response.lower() != 'y':
                print("Aborted")
                self.intf.disconnect()
                return 1

        self.log("Writing data to card...")
        bytes_written = self.intf.write(0, data)

        # Verify
        self.log("Verifying written data...")
        verify_data = self.intf.read(0, MAIN_MEM_SIZE)

        if verify_data == data:
            print(f"SUCCESS: {bytes_written} bytes written and verified")
            self.intf.disconnect()
            return 0
        else:
            diff_count = sum(1 for i in range(len(data)) if verify_data[i] != data[i])
            print(f"ERROR: Verification failed - {diff_count} bytes differ")
            self.intf.disconnect()
            return 1

    def cmd_export(self, args):
        """Export card data to file"""
        self.connect_to_reader(args.reader)

        data = self.intf.read(0, MAIN_MEM_SIZE)

        output_file = args.output
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"sle4442_dump_{timestamp}.hex"

        with open(output_file, 'w') as f:
            f.write(data.hex().upper())

        print(f"Exported {len(data)} bytes to: {output_file}")
        print(f"SHA-256: {hashlib.sha256(data).hexdigest()}")

        self.intf.disconnect()
        return 0

    def cmd_unlock(self, args):
        """Unlock card with PSC"""
        pin_hex = args.psc.strip().replace(' ', '').upper()

        if len(pin_hex) != 6:
            raise ValueError("PSC must be 6 hex characters (3 bytes)")

        pin_bytes = bytes.fromhex(pin_hex)

        self.connect_to_reader(args.reader)

        result = self.intf.unlock_with_pin_bytes(pin_bytes)

        print(f"Unlock result: {result}")

        self.intf.disconnect()
        return 0 if result == "unlocked" else 1

    def cmd_change_pin(self, args):
        """Change card PSC"""
        new_pin_hex = args.new_psc.strip().replace(' ', '').upper()

        if len(new_pin_hex) != 6:
            raise ValueError("New PSC must be 6 hex characters (3 bytes)")

        new_pin_bytes = bytes.fromhex(new_pin_hex)

        old_pin_bytes = None
        if args.old_psc:
            old_pin_hex = args.old_psc.strip().replace(' ', '').upper()
            if len(old_pin_hex) != 6:
                raise ValueError("Old PSC must be 6 hex characters (3 bytes)")
            old_pin_bytes = bytes.fromhex(old_pin_hex)

        self.connect_to_reader(args.reader)

        if not args.force:
            print("WARNING: This will permanently change the card PSC!")
            response = input("Continue? [y/N]: ")
            if response.lower() != 'y':
                print("Aborted")
                self.intf.disconnect()
                return 1

        # Change PIN
        self.intf.change_pin(new_pin_bytes, old_pin_bytes)

        # Verify
        sec = self.intf.read_security()
        if sec[1:] == new_pin_bytes:
            print("SUCCESS: PSC changed successfully")
            print(f"New PSC: {sec[1:].hex().upper()}")
            self.intf.disconnect()
            return 0
        else:
            print("ERROR: PSC verification failed")
            self.intf.disconnect()
            return 1


def run_cli_with_args(args):
    """Run CLI based on parsed arguments"""
    try:
        cli = CLIManager(verbose=args.verbose)

        if args.command == 'list':
            return cli.cmd_list_readers()
        elif args.command == 'info':
            return cli.cmd_info(args)
        elif args.command == 'read':
            return cli.cmd_read(args)
        elif args.command == 'write':
            return cli.cmd_write(args)
        elif args.command == 'export':
            return cli.cmd_export(args)
        elif args.command == 'unlock':
            return cli.cmd_unlock(args)
        elif args.command == 'change-pin':
            return cli.cmd_change_pin(args)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def build_cli_parser():
    """Build argument parser for CLI"""
    parser = argparse.ArgumentParser(
        description="SLE4442 Smart Card Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List readers
  %(prog)s list

  # Show card info
  %(prog)s info

  # Read card (hexdump)
  %(prog)s read

  # Read card (raw hex)
  %(prog)s read --format hex

  # Export to file
  %(prog)s export -o backup.hex

  # Unlock card
  %(prog)s unlock FFFFFF

  # Write from file (requires unlock first)
  %(prog)s write data.hex

  # Change PIN (OMNIKEY readers)
  %(prog)s change-pin --old FFFFFF --new 123456

  # Change PIN (standard readers, must unlock first)
  %(prog)s change-pin --new 123456
"""
    )

    parser.add_argument('--nogui', action='store_true',
                       help='Force CLI mode (no GUI)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('-r', '--reader', type=int, default=0,
                       help='Reader index (default: 0)')

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # list command
    subparsers.add_parser('list', help='List available readers')

    # info command
    subparsers.add_parser('info', help='Show card information')

    # read command
    read_parser = subparsers.add_parser('read', help='Read card memory')
    read_parser.add_argument('-f', '--format',
                            choices=['hexdump', 'hex', 'base64'],
                            default='hexdump',
                            help='Output format (default: hexdump)')

    # write command
    write_parser = subparsers.add_parser('write', help='Write data to card')
    write_parser.add_argument('input', help='Input file (use - for stdin)')
    write_parser.add_argument('--force', action='store_true',
                            help='Skip confirmation prompt')

    # export command
    export_parser = subparsers.add_parser('export', help='Export card data to file')
    export_parser.add_argument('-o', '--output', help='Output file (default: auto-generated)')

    # unlock command
    unlock_parser = subparsers.add_parser('unlock', help='Unlock card with PSC')
    unlock_parser.add_argument('psc', help='3-byte PSC in hex (e.g., FFFFFF)')

    # change-pin command
    change_pin_parser = subparsers.add_parser('change-pin', help='Change card PSC')
    change_pin_parser.add_argument('--old', dest='old_psc',
                                   help='Old PSC (required for OMNIKEY readers)')
    change_pin_parser.add_argument('--new', dest='new_psc', required=True,
                                   help='New PSC (6 hex characters)')
    change_pin_parser.add_argument('--force', action='store_true',
                                  help='Skip confirmation prompt')

    return parser
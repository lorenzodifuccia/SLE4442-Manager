def hexdump(data: bytes, width=16):
    """Create hex dump with ASCII representation"""
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hexa = ' '.join(f"{b:02X}" for b in chunk)
        ascii_part = ''.join((chr(b) if 32 <= b < 127 else '.') for b in chunk)
        lines.append(f"{i:04X}  {hexa:<{width*3}}  {ascii_part}")
    return '\n'.join(lines)


def format_apdu(apdu):
    """Format APDU as hex string"""
    return ' '.join(f"{b:02X}" for b in apdu)
"""Code, for converting bencoded data to string and back."""


def be_to_str(data: bytes) -> str:
    """Convert bencoded data from bytes to string"""
    result = []
    for num in data:
        # Non-printable characters, double quotes, square brackets, accent
        if num < 32 or num in [34, 91, 92, 93] or num > 126:
            result.append("[%0.2x]" % num)
        else:
            result.append(chr(num))
    return "".join(result)


def str_to_be(data: str) -> bytes:
    """Convert bencoded data from string to bytes"""
    result = bytearray()
    seq_marker = False
    seq_chars = ""

    for char in data:
        if char == "[":
            seq_marker = True
            continue
        if char == "]":
            result.append(int(seq_chars, 16))
            seq_marker = False
            seq_chars = ""
            continue
        if seq_marker:
            seq_chars += char
        else:
            result.append(ord(char))
    return bytes(result)

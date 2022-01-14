"""Code, which deals with bencoded data."""
from dataclasses import dataclass
from typing import Union

COLON = ord(":")
END_MARKER = ord("e")
START_DICT = ord("d")
START_INTEGER = ord("i")
START_LIST = ord("l")


@dataclass
class BencodedString:
    """An internal container for bencoded strings"""

    def __init__(self, data):
        """Called when the object is created, sets its attributes"""
        self.bytes = bytearray(data)

    def del_prefix(self, index):
        """Delete the prefix of specified length"""
        del self.bytes[:index]

    def get_prefix(self, index):
        """Get the prefix of specified length (as bytes)"""
        return bytes(self.bytes[:index])


def _decode(data: BencodedString) -> Union[bytes, dict, int, list]:
    """Convert the given bencoded string to a Python object.

    Args:
        Some BencodedString

    Raises:
        ValueError:
            If the argument is empty
            If the first byte doesn't match a supported by bencode data type

    Returns:
        A Python object
    """
    if not data.bytes:
        raise ValueError("Cannot decode an empty bencoded string.")

    if data.bytes[0] == START_DICT:
        return _decode_dict(data)

    if data.bytes[0] == START_LIST:
        return _decode_list(data)

    if data.bytes[0] == START_INTEGER:
        return _decode_int(data)

    if chr(data.bytes[0]).isdigit():
        return _decode_bytes(data)

    raise ValueError(
        "Cannot decode data, expected the first byte to be one of "
        f"'d', 'i', 'l' or a digit, got {chr(data.bytes[0])!r} instead."
    )


def _decode_bytes(data: BencodedString) -> bytes:
    """Extract the first byte string from the given bencoded string

    Args:
        Some BencodedString, which starts with a byte string

    Raises:
        ValueError:
            If the byte string doesn't contain a delimiter
            If the real string length is shorter, than the prefix length

    Returns:
        An extracted byte string
    """
    # Get byte string length
    delimiter_index = data.bytes.find(COLON)

    if delimiter_index > 0:
        length_prefix = data.get_prefix(delimiter_index)
        string_length = int(length_prefix.decode("ascii"))
        data.del_prefix(delimiter_index + 1)
    else:
        raise ValueError(
            "Cannot decode a byte string, it doesn't contain a delimiter. "
            "Most likely the bencoded string is incomplete or incorrect."
        )

    # Get byte string data
    if len(data.bytes) >= string_length:
        result_bytes = data.get_prefix(string_length)
        data.del_prefix(string_length)
    else:
        raise ValueError(
            f"Cannot decode a byte string (prefix length "
            f"- {string_length}, real_length - {len(data.bytes)}. "
            "Most likely the bencoded string is incomplete or incorrect."
        )

    return result_bytes


def _decode_dict(data: BencodedString) -> dict:
    """Extract the first dict from the given bencoded string

    Args:
        Some BencodedString, which starts with a dictionary

    Raises:
        ValueError: If bencoded string ended before the end marker was found

    Returns:
        An extracted dictionary
    """
    result_dict = {}
    data.del_prefix(1)

    while True:
        if data.bytes:
            if data.bytes[0] != END_MARKER:
                key = _decode(data)
                value = _decode(data)
                result_dict[key] = value
            else:
                data.del_prefix(1)
                break
        else:
            raise ValueError(
                "Cannot decode a dictionary, reached end of the bencoded "
                "string before the end marker was found. Most likely the "
                "bencoded string is incomplete or incorrect."
            )

    return result_dict


def _decode_int(data: BencodedString) -> int:
    """Extract the first integer from the given bencoded string

    Args:
        Some BencodedString, which starts with an integer

    Raises:
        ValueError: If bencoded string ended before the end marker was found

    Returns:
        An extracted integer
    """
    data.del_prefix(1)
    end_marker_index = data.bytes.find(END_MARKER)

    if end_marker_index > 0:
        result_bytes = data.get_prefix(end_marker_index)
        data.del_prefix(end_marker_index + 1)
    else:
        raise ValueError(
            "Cannot decode an integer, reached the end of the bencoded "
            "string before the end marker was found. Most likely the "
            "bencoded string is incomplete or incorrect."
        )

    return int(result_bytes.decode("ascii"))


def _decode_list(data: BencodedString) -> list:
    """Extract the first list from the given bencoded string

    Args:
        Some BencodedString, which starts with a list

    Raises:
        ValueError: If bencoded string ended before the end marker was found

    Returns:
        An extracted list
    """
    result_list = []
    data.del_prefix(1)

    while True:
        if data.bytes:
            if data.bytes[0] != END_MARKER:
                result_list.append(_decode(data))
            else:
                data.del_prefix(1)
                break
        else:
            raise ValueError(
                "Cannot decode a list, reached end of the bencoded string "
                "before the end marker was found. Most likely the bencoded "
                "string is incomplete or incorrect."
            )

    return result_list


def _encode_bytes(source: bytes) -> bytes:
    """Encode provided bytes as a bencoded string"""
    return str(len(source)).encode("ascii") + b":" + source


def _encode_dict(source: dict) -> bytes:
    """Encode provided dictionary as a bencoded string"""
    result_data = b"d"

    for key, value in source.items():
        result_data += encode(key) + encode(value)

    return result_data + b"e"


def _encode_int(source: int) -> bytes:
    """Encode provided integer as a bencoded string"""
    return b"i" + str(source).encode("ascii") + b"e"


def _encode_list(source: list) -> bytes:
    """Encode provided list as a bencoded string"""
    result_data = b"l"

    for item in source:
        result_data += encode(item)

    return result_data + b"e"


def decode(data: bytes) -> Union[bytes, dict, int, list]:
    """Convert the given bencoded string to a Python object.

    Raises:
        ValueError:
            If the argument is not of type bytes or is empty
            If the first byte doesn't match a supported by bencode data type

    Returns:
        A Python object
    """
    if not isinstance(data, bytes):
        raise ValueError(
            f"Cannot decode data, expected bytes, got {type(data)} instead."
        )
    return _decode(BencodedString(data))


def encode(data: Union[bytes, dict, int, list]) -> bytes:
    """Convert the given Python object to a bencoded string.

    Raises:
        ValueError: If the provided object type is not supported

    Returns:
        A bencoded string
    """
    if isinstance(data, bytes):
        return _encode_bytes(data)

    if isinstance(data, dict):
        return _encode_dict(data)

    if isinstance(data, int):
        return _encode_int(data)

    if isinstance(data, list):
        return _encode_list(data)

    raise ValueError(
        f"Cannot encode data: objects of type {type(data)} are not supported."
    )

"""Code, which deals with torrent data."""
from typing import Any

from bencode.bencode import decode, encode


def _decode_object(data: Any, encoding: str, errors: str) -> Any:
    """Replace bytes with strings in the provided Python object"""
    if isinstance(data, bytes):
        return data.decode(encoding, errors)

    if isinstance(data, dict):
        result_dict = {}
        for key, value in data.items():
            decoded_key = _decode_object(key, encoding, errors)
            if decoded_key.endswith(".utf-8"):
                decoded_value = _decode_object(value, "utf8", errors)
            elif decoded_key in ["ed2k", "filehash", "pieces"]:
                decoded_value = value.hex()
            else:
                decoded_value = _decode_object(value, encoding, errors)
            result_dict[decoded_key] = decoded_value
        return result_dict

    if isinstance(data, list):
        return [_decode_object(item, encoding, errors) for item in data]

    return data


def _encode_object(data: Any, encoding: str, errors: str) -> Any:
    """Replace strings with bytes in the provided Python object"""
    if isinstance(data, str):
        return data.encode(encoding, errors)

    if isinstance(data, dict):
        result_dict = {}
        for key, value in data.items():
            encoded_key = _encode_object(key, encoding, errors)
            if encoded_key.endswith(b".utf-8"):
                encoded_value = _encode_object(value, "utf8", errors)
            elif encoded_key in [b"ed2k", b"filehash", b"pieces"]:
                encoded_value = bytes.fromhex(value)
            else:
                encoded_value = _encode_object(value, encoding, errors)
            result_dict[encoded_key] = encoded_value
        return result_dict

    if isinstance(data, list):
        return [_encode_object(item, encoding, errors) for item in data]

    return data


def decode_torrent(
    data: bytes, encoding: str = "utf_8", errors: str = "strict"
) -> dict:
    """Convert the given torrent to a Python dictionary.

    Fields are decoded:
    - using utf8 (if the key ends with ".utf-8" suffix, like "name.utf-8")
    - using the provided encoding (for other human readable fields)
    - as hex (for binary fields)

    Args:
        data: some binary data to decode
        encoding: which encoding should be used
            (https://docs.python.org/3/library/codecs.html#standard-encodings)
        errors: what to do if decoding is not possible
            (https://docs.python.org/3/library/codecs.html#error-handlers)

    Raises:
        UnicodeDecodeError: If some key or value cannot be decoded using the
            provided encoding
        ValueError: If the first argument is not of type bytes
    """
    if not isinstance(data, bytes):
        raise ValueError(
            f"Cannot decode data, expected bytes, got {type(data)} instead."
        )
    return _decode_object(decode(data), encoding, errors)


def encode_torrent(
    data: dict, encoding: str = "utf8", errors: str = "strict"
) -> bytes:
    """Convert the given Python dictionary to a torrent

    Mirror function for the "decode_torrent" function.

    Raises:
        UnicodeEncodeError: If some key or value cannot be encoded using the
            provided encoding
        ValueError: If the first argument is not of type dict
    """
    if not isinstance(data, dict):
        raise ValueError(
            f"Cannot encode data, expected dict, got {type(data)} instead."
        )
    return encode(_encode_object(data, encoding, errors))

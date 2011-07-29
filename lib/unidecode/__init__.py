# -*- coding: utf-8 -*-
"""Transliterate Unicode text into plain 7-bit ASCII.

Example usage:
>>> from unidecode import unidecode:
>>> unidecode(u"\u5317\u4EB0")
"Bei Jing "

The transliteration uses a straightforward map, and doesn't have alternatives
for the same character based on language, position, or anything else.

In Python 3, a standard string object will be returned. If you need bytes, use:
>>> unidecode("Κνωσός").encode("ascii")
b'Knosos'
"""
Cache = {}

def unidecode(string):
    """Transliterate an Unicode object into an ASCII string

    >>> unidecode(u"\u5317\u4EB0")
    "Bei Jing "
    """

    retval = []

    for char in string:
        codepoint = ord(char)

        if codepoint < 0x80: # Basic ASCII
            retval.append(char)
            continue
        
        if codepoint > 0xeffff:
            continue # Characters in Private Use Area and above are ignored

        section = codepoint >> 8   # Chop off the last two hex digits
        position = codepoint % 256 # Last two hex digits

        try:
            table = Cache[section]
        except KeyError:
            try:
                mod = __import__('lib.unidecode.x%03x'%(section), [], [], ['data'])
            except ImportError:
                Cache[section] = None
                continue   # No match: ignore this character and carry on.

            Cache[section] = table = mod.data

        if table and len(table) > position:
            retval.append( table[position] )

    return ''.join(retval)

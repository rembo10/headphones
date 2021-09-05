"in which we pre-import all the encodings to make sure we don't hit an import lock"

import encodings.ascii
import encodings.base64_codec
import encodings.charmap
import encodings.idna
import encodings.latin_1
import encodings.raw_unicode_escape
import encodings.undefined
import encodings.unicode_escape
import encodings.utf_16
import encodings.utf_32
import encodings.utf_8
import encodings.utf_7

assert encodings # yay flakes

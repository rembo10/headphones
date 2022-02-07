import sys
import os

from typing import Text, Union, Any, Optional, Tuple, List, Dict

if sys.version_info[0] == 2:
    _pathlike = Union[Text, bytes]
else:
    _pathlike = Union[Text, bytes, 'os.PathLike[Any]']
_uri = Union[Text, str]

if sys.version_info[0] == 2:
    if sys.platform == "win32":
        _base = Text
    else:
        _base = bytes
else:
    _base = Text

class fsnative(_base):
    def __init__(self, object: Text=u"") -> None:
        ...

_fsnative = Union[fsnative, _base]

if sys.platform == "win32":
    _bytes_default_encoding = str
else:
    _bytes_default_encoding = Optional[str]

def path2fsn(path: _pathlike) -> _fsnative:
    ...

def fsn2text(path: _fsnative, strict: bool=False) -> Text:
    ...

def text2fsn(text: Text) -> _fsnative:
    ...

def fsn2bytes(path: _fsnative, encoding: _bytes_default_encoding="utf-8") -> bytes:
    ...

def bytes2fsn(data: bytes, encoding: _bytes_default_encoding="utf-8") -> _fsnative:
    ...

def uri2fsn(uri: _uri) -> _fsnative:
    ...

def fsn2uri(path: _fsnative) -> Text:
    ...

def fsn2norm(path: _fsnative) -> _fsnative:
    ...

sep: _fsnative
pathsep: _fsnative
curdir: _fsnative
pardir: _fsnative
altsep: _fsnative
extsep: _fsnative
devnull: _fsnative
defpath: _fsnative

def getcwd() -> _fsnative:
    ...

def getenv(key: _pathlike, value: Optional[_fsnative]=None) -> Optional[_fsnative]:
    ...

def putenv(key: _pathlike, value: _pathlike):
    ...

def unsetenv(key: _pathlike) -> None:
    ...

def supports_ansi_escape_codes(fd: int) -> bool:
    ...

def expandvars(path: _pathlike) -> _fsnative:
    ...

def expanduser(path: _pathlike) -> _fsnative:
    ...

environ: Dict[_fsnative,_fsnative]
argv: List[_fsnative]

def gettempdir() -> _fsnative:
    pass

def mkstemp(suffix: Optional[_pathlike]=None, prefix: Optional[_pathlike]=None, dir: Optional[_pathlike]=None, text: bool=False) -> Tuple[int, _fsnative]:
    ...

def mkdtemp(suffix: Optional[_pathlike]=None, prefix: Optional[_pathlike]=None, dir: Optional[_pathlike]=None) -> _fsnative:
    ...

version_string: str

version: Tuple[int, int, int]

print_ = print

def input_(prompt: Any=None) -> _fsnative:
    ...

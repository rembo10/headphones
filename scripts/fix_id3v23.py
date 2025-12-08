#!/opt/headphones/venv/bin/python
# Fix MP3 tags to ID3v2.3 for all mp3 files under given paths
import sys
import os
from pathlib import Path
try:
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, ID3NoHeaderError
except Exception:
    print("mutagen not installed", file=sys.stderr)
    sys.exit(2)

def convert_file(path):
    try:
        path = str(path)
        if not path.lower().endswith('.mp3'):
            return
        # load to ensure it's an mp3
        audio = MP3(path)
        try:
            tags = ID3(path)
        except ID3NoHeaderError:
            tags = ID3()
        # save with ID3v2.3
        tags.save(path, v2_version=3)
        print(f"Rewrote ID3v2.3: {path}")
    except Exception as e:
        print(f"Error processing {path}: {e}", file=sys.stderr)


def walk_and_convert(root):
    for dirpath, dirnames, filenames in os.walk(root):
        for f in filenames:
            if f.lower().endswith('.mp3'):
                convert_file(os.path.join(dirpath, f))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: fix_id3v23.py <path> [<path> ...]", file=sys.stderr)
        sys.exit(1)
    for p in sys.argv[1:]:
        if os.path.exists(p):
            walk_and_convert(p)
        else:
            print(f"Path does not exist: {p}", file=sys.stderr)

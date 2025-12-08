"""
Module for fixing MP3 ID3v2 tags to version 2.3 format.
This integrates the functionality from the fix_id3v23.py script.
"""

import os
import sys
import headphones.logger

try:
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, ID3NoHeaderError
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    headphones.logger.warning("mutagen library not available for ID3 tag fixing")


def convert_file(path):
    """
    Convert a single MP3 file's ID3 tags to v2.3 format.
    
    Args:
        path: Path to the MP3 file
        
    Returns:
        True if successful, False otherwise
    """
    if not MUTAGEN_AVAILABLE:
        return False
        
    try:
        path = str(path)
        if not path.lower().endswith('.mp3'):
            return False
            
        # Load to ensure it's an mp3
        audio = MP3(path)
        try:
            tags = ID3(path)
        except ID3NoHeaderError:
            tags = ID3()
            
        # Save with ID3v2.3
        tags.save(path, v2_version=3)
        headphones.logger.info(f"Rewrote ID3v2.3: {path}")
        return True
        
    except Exception as e:
        headphones.logger.error(f"Error processing {path}: {e}")
        return False


def walk_and_convert(root):
    """
    Recursively walk through a directory and convert all MP3 files to ID3v2.3.
    
    Args:
        root: Root directory path to start walking from
        
    Returns:
        Number of files successfully converted
    """
    if not MUTAGEN_AVAILABLE:
        headphones.logger.error("mutagen library is required for ID3 tag fixing")
        return 0
        
    converted_count = 0
    
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            for f in filenames:
                if f.lower().endswith('.mp3'):
                    file_path = os.path.join(dirpath, f)
                    if convert_file(file_path):
                        converted_count += 1
    except Exception as e:
        headphones.logger.error(f"Error walking directory {root}: {e}")
        
    return converted_count


def fix_library_id3_tags(library_paths):
    """
    Fix ID3 tags in a library or list of library paths.
    
    Args:
        library_paths: String or list of directory paths to process
        
    Returns:
        Tuple of (success, total_converted, message)
    """
    if not MUTAGEN_AVAILABLE:
        return False, 0, "mutagen library not installed"
        
    if isinstance(library_paths, str):
        library_paths = [library_paths]
        
    total_converted = 0
    
    for path in library_paths:
        if os.path.exists(path):
            headphones.logger.info(f"Starting ID3v2.3 conversion for: {path}")
            converted = walk_and_convert(path)
            total_converted += converted
        else:
            headphones.logger.warning(f"Path does not exist: {path}")
            
    message = f"ID3 tag conversion complete. {total_converted} files processed."
    return True, total_converted, message

#  This file is part of Headphones.
#
#  Headphones is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

"""
Utilities for managing folder format profiles and multi-source library organization.
"""

import os
try:
    from send2trash import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    HAS_SEND2TRASH = False
import headphones
from headphones import logger


class FolderProfile:
    """Represents a folder naming profile for a specific source."""
    
    def __init__(self, name, source_path, folder_format, file_format=None):
        self.name = name
        self.source_path = source_path
        self.folder_format = folder_format
        self.file_format = file_format
    
    def matches_source(self, file_path):
        """Check if a file path matches this profile's source."""
        return file_path.startswith(self.source_path)


def get_folder_profile_for_source(source_origin):
    """
    Get the appropriate folder format profile for a given source origin.
    
    Args:
        source_origin: The source directory path of the file
    
    Returns:
        dict with 'folder_format' and optional 'file_format' keys
    """
    if not headphones.CONFIG.ENABLE_FOLDER_PROFILES:
        return {
            'folder_format': headphones.CONFIG.FOLDER_FORMAT,
            'file_format': headphones.CONFIG.FILE_FORMAT
        }
    
    profiles = headphones.CONFIG.FOLDER_FORMAT_PROFILES
    if not profiles:
        return {
            'folder_format': headphones.CONFIG.FOLDER_FORMAT,
            'file_format': headphones.CONFIG.FILE_FORMAT
        }
    
    # Profiles stored as list: [name1, source1, format1, name2, source2, format2, ...]
    # Parse into tuples of (name, source, format)
    try:
        profile_list = []
        for i in range(0, len(profiles), 3):
            if i + 2 < len(profiles):
                profile_list.append({
                    'name': profiles[i],
                    'source': profiles[i + 1],
                    'folder_format': profiles[i + 2]
                })
        
        # Find matching profile based on source_origin
        if source_origin:
            source_origin = os.path.normpath(source_origin)
            for profile in profile_list:
                profile_source = os.path.normpath(profile['source'])
                if source_origin.startswith(profile_source):
                    logger.debug(f"Using profile '{profile['name']}' for source {source_origin}")
                    return {
                        'folder_format': profile['folder_format'],
                        'file_format': headphones.CONFIG.FILE_FORMAT
                    }
    except Exception as e:
        logger.error(f"Error parsing folder profiles: {e}")
    
    # Default to global settings
    return {
        'folder_format': headphones.CONFIG.FOLDER_FORMAT,
        'file_format': headphones.CONFIG.FILE_FORMAT
    }


def find_duplicate_tracks(artist_name, album_title, track_title):
    """
    Find duplicate tracks with the same artist, album, and title.
    
    Returns a list of track records with different source origins.
    """
    from headphones import db
    
    myDB = db.DBConnection()
    
    # Search in 'have' table (local library)
    duplicates = myDB.select(
        'SELECT Location, SourceOrigin, TrackID FROM have WHERE ArtistName = ? COLLATE NOCASE '
        'AND AlbumTitle = ? COLLATE NOCASE AND TrackTitle = ? COLLATE NOCASE',
        [artist_name, album_title, track_title]
    )
    
    return duplicates


def get_file_quality_score(file_path):
    """
    Calculate a quality score for a file based on format and bitrate.
    Higher score = better quality (prefer to keep, delete others).
    
    Returns: (score, quality_description)
    """
    from mediafile import MediaFile, FileTypeError, UnreadableFileError
    import os
    
    try:
        f = MediaFile(file_path)
    except (FileTypeError, UnreadableFileError, IOError):
        return (0, "unreadable")
    
    score = 0
    desc = ""
    
    # Format scoring (lossless > lossy)
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext in ['.flac', '.aiff', '.aif', '.ape']:
        score += 1000  # Lossless formats
        desc = "Lossless"
    elif file_ext in ['.mp3', '.aac', '.m4a', '.ogg', '.opus', '.wma']:
        score += 500   # Lossy formats
        desc = "Lossy"
    else:
        score += 100
        desc = f"Other ({file_ext})"
    
    # Bitrate scoring (higher = better)
    if f.bitrate:
        score += f.bitrate
        if desc:
            desc += f" ({f.bitrate} kbps)"
    
    return (score, desc)


def get_best_duplicate(duplicates):
    """
    Select the best duplicate to keep based on:
    1. Lossless > Lossy
    2. Higher bitrate > Lower bitrate
    3. File size as tiebreaker
    
    Args:
        duplicates: List of duplicate track records with 'Location' field
    
    Returns:
        Best duplicate record to keep, or None if all are unreadable
    """
    import os
    
    if not duplicates:
        return None
    
    best = None
    best_score = -1
    best_desc = ""
    
    for dup in duplicates:
        if not os.path.exists(dup['Location']):
            continue
        
        score, desc = get_file_quality_score(dup['Location'])
        
        # Tiebreaker: prefer larger files (might be better encoded)
        try:
            file_size = os.path.getsize(dup['Location'])
        except:
            file_size = 0
        
        score += (file_size // 1000000)  # Add MB to score
        
        if score > best_score:
            best_score = score
            best = dup
            best_desc = desc
    
    logger.debug(f"Selected best duplicate: {best['Location'] if best else 'None'} ({best_desc})")
    return best


def handle_duplicate_tracks(duplicates, auto_delete=False, keep_location=None):
    """
    Handle duplicate tracks intelligently.
    
    Args:
        duplicates: List of duplicate track records
        auto_delete: If True, delete inferior copies (keep best)
        keep_location: Specific location to keep (overrides quality-based selection)
    
    Returns:
        dict with 'kept', 'deleted', 'errors' lists
    """
    from headphones import db
    import os
    import shutil
    
    myDB = db.DBConnection()
    result = {'kept': None, 'deleted': [], 'errors': []}
    
    if not duplicates or len(duplicates) < 2:
        return result
    
    # Determine which copy to keep
    if keep_location:
        keep = next((d for d in duplicates if d['Location'] == keep_location), None)
        if not keep:
            msg = f"Specified keep_location not found: {keep_location}"
            logger.error(msg)
            result['errors'].append(msg)
            return result
    else:
        keep = get_best_duplicate(duplicates)
        if not keep:
            msg = "Could not determine best duplicate (all unreadable?)"
            logger.error(msg)
            result['errors'].append(msg)
            return result
    
    result['kept'] = keep['Location']
    
    # Handle other duplicates
    for dup in duplicates:
        if dup['Location'] == keep['Location']:
            continue
        
        if not os.path.exists(dup['Location']):
            # Already deleted, just clean DB
            logger.warning(f"Duplicate path missing on disk, cleaning DB entry: {dup['Location']}")
            myDB.action('DELETE FROM have WHERE Location=?', [dup['Location']])
            continue
        
        if auto_delete:
            try:
                # Delete the file to trash if possible, else permanent delete
                if HAS_SEND2TRASH:
                    send2trash(dup['Location'])
                    logger.info(f"Sent duplicate to trash: {dup['Location']}")
                else:
                    os.remove(dup['Location'])
                    logger.info(f"Deleted duplicate: {dup['Location']}")
                result['deleted'].append(dup['Location'])
                
                # Remove from database
                myDB.action('DELETE FROM have WHERE Location=?', [dup['Location']])
            except Exception as e:
                err_msg = f"Error deleting {dup['Location']}: {e}"
                logger.error(err_msg)
                result['errors'].append(err_msg)
        else:
            # Just mark as orphaned in DB (safe, no file deletion)
            myDB.action(
                'UPDATE have SET Location = NULL WHERE Location = ?',
                [dup['Location']]
            )
            logger.info(f"Marked duplicate for manual review: {dup['Location']}")
            result['deleted'].append(dup['Location'])
    
    return result


def merge_duplicate_tracks(duplicate_list, keep_location):
    """
    Mark duplicate tracks for merging, keeping only one location.
    
    Args:
        duplicate_list: List of duplicate track records
        keep_location: The location to keep
    """
    from headphones import db
    
    myDB = db.DBConnection()
    
    for track in duplicate_list:
        if track['Location'] != keep_location:
            # Mark as merged/duplicate, don't delete (for audit trail)
            myDB.action(
                'UPDATE have SET Location = ? WHERE Location = ?',
                [None, track['Location']]
            )
            logger.info(f"Marked duplicate for merging: {track['Location']} -> {keep_location}")

# Multi-Source Library Organization Guide

## Overview
Headphones now supports organizing music from multiple library sources with conditional folder naming profiles. This allows you to automatically organize compilations, Various Artists, and files from different sources (e.g., iTunes, MyBook) into appropriate folder structures.

## Features Added

### 1. Multiple Library Directories (MUSIC_DIRS)

**Configuration**: In `config.ini`, you can now specify multiple music directories:

```ini
[General]
MUSIC_DIR = /home/user/Musiques
MUSIC_DIRS = ['/home/user/Musiques', '/mnt/mybook/Musiques', '/mnt/mybook/itunes/Music']
```

**Behavior**:
- If `MUSIC_DIRS` is configured, Headphones will scan ALL directories during library scans
- Each directory is scanned independently and tracks are tagged with their source origin
- Useful for aggregating music from multiple physical drives or locations

**Via Symlinks (Alternative)**:
If you prefer not to use `MUSIC_DIRS`, you can create symlinks in a single parent directory:
```bash
ln -s /home/user/Musiques /home/music-root/Musiques
ln -s /mnt/mybook/Musiques /home/music-root/MyBook
ln -s /mnt/mybook/itunes/Music /home/music-root/iTunes
```
Then set `MUSIC_DIR = /home/music-root`

### 2. Folder Format Profiles

**Configuration**: Enable conditional folder naming based on source:

```ini
[General]
ENABLE_FOLDER_PROFILES = 1
FOLDER_FORMAT_PROFILES = ['iTunes Profile', '/mnt/mybook/itunes', 'Various Artists/$Album', 'MyBook Profile', '/mnt/mybook/Musiques', '$Artist/$Album [$Year]']
```

Format: `[profile_name, source_path, folder_format, profile_name2, source_path2, folder_format2, ...]`

**How it works**:
- When post-processing a file, Headphones checks its source directory
- It applies the matching profile's folder format
- Falls back to `FOLDER_FORMAT` if no profile matches

**Example Use Cases**:

**iTunes compilations** → Separate folder structure:
```
FOLDER_FORMAT_PROFILES = ['iTunes', '/mnt/mybook/itunes/Music', 'Various Artists/$Album']
```
Result:
```
iTunes/Various Artists/Best Of 2024/
iTunes/Various Artists/Compilation Name/
```

**Other sources** → Default artist structure:
```
MyBook/Artist Name/Album Name/
```

### 3. Source Origin Tracking

Every track in the database now has a `SourceOrigin` field that records where it came from:
- Automatically set during library scans
- Used to determine which folder profile to apply
- Visible in logs when processing files

### 4. Duplicate Detection and Optional Auto-Deletion

Headphones automatically detects duplicate tracks (same artist, album, title from different sources):

**Log Output Example**:
```
Found 3 copies of 'Various Artists - Track Title' from different sources:
  - /home/user/Musiques/Various Artists/Album1/01 - Track Title.mp3 (source: /home/user/Musiques, quality: Lossy 320 kbps)
  - /mnt/mybook/Musiques/VA/Album1/track01.flac (source: /mnt/mybook/Musiques, quality: Lossless (1411 kbps))
  - /mnt/mybook/itunes/Music/Compilations/Album1/01.m4a (source: /mnt/mybook/itunes/Music, quality: Lossy (256 kbps))
```

**Auto-Delete Behavior** (optional):

By default, duplicates are **logged only** (safe). You can enable automatic deletion:

```ini
[General]
AUTO_DELETE_DUPLICATES = 1
```

When enabled, Headphones will:
1. **Detect duplicates** based on metadata match
2. **Score each copy** by quality:
   - Lossless formats (FLAC, AIFF, APE) = highest priority
   - Lossy formats (MP3, AAC, OGG) = secondary
   - Bitrate as tiebreaker (higher = better)
   - File size as final tiebreaker
3. **Keep the best copy** and delete inferior duplicates
4. **Delete from disk** (not just database)
5. **Log all actions** for audit trail

**Quality Scoring Algorithm**:
```
- Lossless format     → +1000 points
- Lossy format        → +500 points
- Bitrate (kbps)      → +bitrate value
- File size (MB)      → +size in MB
- Winner = highest total score
```

**Examples**:
- FLAC 1411 kbps vs MP3 320 kbps → **FLAC kept** (lossless wins)
- MP3 320 kbps vs MP3 256 kbps → **320 kbps kept** (higher bitrate)
- MP3 320 kbps (5.5 MB) vs MP3 320 kbps (5.2 MB) → **5.5 MB kept** (larger file)

**Safety**:
- Duplicates marked for deletion are logged before action
- Unreadable files are skipped
- Non-existent files are cleaned from database only
- Errors are logged and reported

## Database Schema Changes

The following columns have been added:
- `tracks.SourceOrigin` - VARCHAR, tracks the source directory
- `alltracks.SourceOrigin` - VARCHAR, for synced tracks
- `have.SourceOrigin` - VARCHAR, for local library matches

These are automatically added on first run via database migrations.

## Configuration Workflow

### Step 1: Set Up Multiple Directories

```ini
[General]
MUSIC_DIR = /home/user/Musiques
MUSIC_DIRS = ['/home/user/Musiques', '/mnt/mybook/Musiques', '/mnt/mybook/itunes/Music']
AUTO_DELETE_DUPLICATES = 0
```

### Step 2: Enable Folder Profiles (Optional)

```ini
[General]
ENABLE_FOLDER_PROFILES = 1
FOLDER_FORMAT = $Artist/$Album [$Year]
FOLDER_FORMAT_PROFILES = [
    'iTunes Compilations', '/mnt/mybook/itunes/Music', 'Various Artists/$Album',
    'MyBook Standard', '/mnt/mybook/Musiques', '$Artist/$Album [$Year]'
]
```

### Step 3: Configure Duplicate Handling (Optional)

```ini
[General]
AUTO_DELETE_DUPLICATES = 1
```

When enabled, inferior duplicates are automatically deleted (keeping best quality).

### Step 3: Run Library Scan

Click "Scan Music Library" in the Manage section. Headphones will:
1. Scan all directories in `MUSIC_DIRS`
2. Tag each track with its `SourceOrigin`
3. Log any duplicates found

### Step 4: Configure Post-Processing

Enable the standard post-processing options:
- `MOVE_FILES = 1`
- `RENAME_FILES = 1`
- `DESTINATION_DIR = /path/to/organized/music`

When files are post-processed:
- Headphones checks the source origin
- Applies the matching folder profile
- Files are moved and named accordingly

## Common Use Cases

### Case 1: Separate iTunes and Other Music

**Setup**:
```ini
MUSIC_DIRS = ['/home/user/music', '/mnt/external/iTunes']
ENABLE_FOLDER_PROFILES = 1
FOLDER_FORMAT_PROFILES = [
    'iTunes', '/mnt/external/iTunes', 'iTunes/$Artist/$Album',
    'Local', '/home/user/music', '$Artist/$Album [$Year]'
]
DESTINATION_DIR = /home/user/music-organized
```

**Result**:
```
/home/user/music-organized/
├── iTunes/
│   ├── Artist A/
│   │   └── Album Name/
│   └── Various Artists/
│       └── Compilation/
└── Artist B/
    └── Album Name/
```

### Case 2: Separate Lossy and Lossless

```ini
MUSIC_DIRS = ['/home/user/flac', '/home/user/mp3']
DESTINATION_DIR = /media/music/
LOSSLESS_DESTINATION_DIR = /media/music-lossless/
```

Files are automatically sorted by format and renamed according to their format's folder profile.

### Case 3: Multiple External Drives

```ini
MUSIC_DIRS = [
    '/mnt/drive1/Music',
    '/mnt/drive2/Music', 
    '/mnt/drive3/Music'
]
```

All drives are scanned together. Source tracking helps identify which files came from which drive.

## Troubleshooting

### Profile Not Applied
- Check `ENABLE_FOLDER_PROFILES = 1`
- Verify `FOLDER_FORMAT_PROFILES` syntax (triplets of name, source, format)
- Source path must match the beginning of the file's actual path
- Check logs for profile matching details

### Missing SourceOrigin Data
- If upgrading from an older version, run a fresh library scan
- Existing files may not have SourceOrigin set until rescanned
- Run "Scan Music Library" to populate for existing files

### Duplicate Detection Not Working
- Verify database migrations ran (check logs for "Adding SourceOrigin column")
- Tags must match exactly (Artist, Album, Title)
- Only searches the `have` table (local library)

## API Notes

The `libraryScan` function now accepts a `source_origin` parameter:
```python
libraryScan(dir="/path/to/dir", source_origin="/path/to/dir")
```

This is automatically set when using `MUSIC_DIRS`.

## Performance Considerations

- Multiple directory scans may take longer than a single scan
- Database migrations run once on startup
- Duplicate detection is logged but not blocking
- Folder profile matching is minimal overhead (per-file operation)

## Migration from Single Directory

If you currently use a single `MUSIC_DIR`:

1. Backup your config
2. Update to add `MUSIC_DIRS` list
3. Run a fresh library scan
4. Review logs for duplicates
5. Configure profiles if needed

Your existing `MUSIC_DIR` setting will still work if `MUSIC_DIRS` is empty.

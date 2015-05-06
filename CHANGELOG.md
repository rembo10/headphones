# Changelog

## v0.5.6
Released xx xxx 2015

Highlights:
* Added: Filter out clean/edited/censored releases (#2198)
* Added: Button on the log page to toggle verbose/debug logging
* Fixed: Connecting to SABnzbd over https with python >= 2.7.9
* Improved: Moved the 'freeze db' option to the advanced->misc. tab

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.5.5...v0.5.6).

## v0.5.5
Released 04 May 2015

Highlights:
* Added: force ID3v2.3 during post processing (#2121)
* Added: MusicBrainz authentication (#2125)
* Added: Email notifications (addresses #1045)
* Fixed: Kickass url updated to kickass.to (#2119)
* Fixed: Piratebay returning 0 bytes for all files
* Fixed: Albums stopped automatically refreshing when adding an artist
* Fixed: Min/max sizes for target bitrate
* Fixed: Don't filter any results if looking for a specific download
* Fixed: Sort by size in the specific download table
* Fixed: Deal with beets recommendation.none correctly
* Improved: Close dialog window automatically when choosing a specific download
* Improved: Move some repetitive log messages to debug level

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.5.4...v0.5.5).

## v0.5.4
Released 05 February 2015

Highlights:
* Added: backported 'Scan Artist' feature from `sarakha63/headphones`
* Fixed: change file permissions of cache files according to settings (#2102)
* Fixed: hide Songkick if no regional events are available
* Fixed: only reschedule jobs if timeout changed (#2099)
* Fixed: limit dialog height (#2096)
* Improved: upgraded requests to 2.5.1
* Improved: upgraded unidecode to 0.04.17
* Improved: upgraded tzlocal to 1.1.2
* Improved: upgraded PyTZ to 2014.10
* Improved: upgraded mako to 1.0.1
* Improved: upgraded mutagen to 1.27
* Improved: upgraded beets to 1.3.10

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.5.3...v0.5.4).

## v0.5.3
Released 15 January 2015

Highlights:
* Added: update active artists via API (#2075)
* Fixed: queue instance lacks `add` method (#2055)
* Improved: better SSL error messages (#2058)

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.5.2...v0.5.3).

## v0.5.2
Released 28 December 2014

Highlights:
* Added: advanced option to ignore certain folders by patterns. (#2037)
* Added: advanced option to ignore certain files by patterns (library only)
* Added: specify optional paths to CUE splitting tools (#1938)
* Added: experimental support for OPB (provide details yourself!)
* Fixed: magnet to torrent conversion (#1926)
* Fixed: new KAT URL (#2043)
* Fixed: LMS notifications (#1564)
* Improved: notify user of SSL-related warnings, instead of silently failing.
* Improved: show all search results for 'Choose Specific Release'

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.5.1...v0.5.2).

## v0.5.1
Released 13 November 2014

Highlights:
* Added: allow one to disable interval tasks (#2002)
* Added: script to downgrade Headphones to last version that started (Linux only)
* Fixed: SSL issues in CherryPy. Self-generated certificates will be 2048 now (#1995)
* Fixed: Transmission URL detection (#1998)
* Fixed: missing dependencies for APScheduler and CherryPy (#2001)
* Improved: symlink infinite recursion detection

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.5...v0.5.1).

## v0.5
Released 10 November 2014

Highlights:
* Added: CUE splitter
* Added: filter search result by MusicBrainz Release Group ID
* Added: follow symlinks while scanning library (#1953)
* Fixed: crash during post processing (#1897)
* Fixed: embedding lyrics (#1896)
* Fixed: HTTP errors with older versions of Python 2.6
* Fixed: jump back to top of page (#1948)
* Improved: parse MusicBrainz RGID first when post processing (#1952)
* Improved: Growl unicode characters (#1695)
* Improved: search handling for PB and KAT
* Improved: Last.FM API support (#1877)
* Improved: upgraded CherryPy to version 3.6.0
* Improved: upgraded Requests to version 2.4.1
* Improved: upgraded APScheduler to version 3.0.1
* Improved: lot of code refactoring

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.4...v0.5).

## v0.4
Released 20 September 2014

Highlights:
* Added: support for libav-tools (which replaces FFmpeg under Ubuntu)
* Added: option to freeze library when post processing
* Added: Songkick per area
* Added: rename original NFO file (#1797)
* Removed: removed dead search providers
* Fixed: removed left-overs of old packages
* Improved: rename by original folder (#1811)
* Improved: uTorrent fixess
* Improved: delayed loading of album art
* Improved: search result parser

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.3.4...v0.4).

## v0.3.4
Released 15 May 2014

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.3.3...v0.3.4).

## v0.3.3
Released 05 May 2014

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.3.2...v0.3.3).

## v0.3.2
Released 17 April 2014

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.3.1...v0.3.2).

## v0.3.1
Released 11 April 2014

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.3...v0.3.1).

## v0.3
Released 09 April 2014

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.2.3...v0.3).

## v0.2.3
Released 28 March 2014

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.2.2...v0.2.3).

## v0.2.2
Released 15 January 2014

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.2.1...v0.2.2).

## v0.2.1
Released 13 January 2014

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.2...v0.2.1).

## v0.2
Released 13 January 2014

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.1.2...v0.2).

## v0.1.2
Released 11 October 2013

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.1.1...v0.1.2).

## v0.1.1
Released 26 August 2013

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.1...v0.1.1).

## v0.1
Released 05 August 2013

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/2156e1341405d07c5bcfbe994f6b354b32d94cda...v0.1).

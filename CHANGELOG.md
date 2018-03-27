# Changelog

## v0.5.19
Released 27 March 2018

Highlights:
* Improved: Windows encoding fixes
* Improved: Performance enhancements
* Improved: Many more since the last release. Check the list

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.5.18...v0.5.19).

## v0.5.18
Released 01 December 2016

Highlights:
* Added: PassTheHeadphones support
* Fixed: Special characters in password fields breaking on config page
* Improved: Updated t411 url

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.5.17...v0.5.18).


## v0.5.17
Released 10 November 2016

Highlights:
* Added: t411 support
* Fixed: Rutracker login
* Fixed: Deluge empty password
* Fixed: FreeBSD init script
* Improved: Musicbrainz searching

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.5.16...v0.5.17).

## v0.5.16
Released 10 June 2016

Hotfix update

Highlights:
* Fixed: Waffles url

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.5.15...v0.5.16).

## v0.5.15
Released 07 June 2016

Hotfix update

Highlights:
* Fixed: Update vip mirror url to point to new server
* Fixed: Update waffles url to .ch

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.5.14...v0.5.15).

## v0.5.14
Released 02 June 2016

Highlights:
* Fixed: File/folder format on new installs
* Fixed: Pep8 errors
* Improved: Updated fontawesome
* Improved: Reverted back to less

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.5.13...v0.5.14).

## v0.5.13
Released 25 February 2016

Another hotfix update

Highlights:
* Fixed: Saving config with non-defined options
* Fixed: Pep8 errors

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.5.12...v0.5.13).

## v0.5.12
Released 25 February 2016

This is mostly a hotfix update

Highlights:
* Added: Experimental Deluge Support
* Fixed: Some pep8 stuff
* Improved: Use curly braces for pathrender optional variables

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.5.11...v0.5.12).

## v0.5.11
Released 20 February 2016

Highlights:
* Added: Soft chroot option
* Fixed: Post processing temporary directory fix (#2504)
* Fixed: Ubuntu init script (#2509)
* Fixed: Image cache uncaught exception (#2485)
* Improved: $Date/$date variable in folder renaming
* Improved: Reuse transmission session id

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.5.10...v0.5.11).

## v0.5.10
Released 29 January 2016

Highlights:
* Added: API option to post-process single folders
* Added: Ability to specify extension when re-encoding
* Added: Option to stop renaming folders
* Fixed: Utorrent torrents not being removed (#2385)
* Fixed: Torznab to transmission
* Fixed: Magnet folder names in history
* Fixed: Multiple torcache fixes
* Fixed: Updated requests & urllib3 to latest versions to fix errors with pyOpenSSL
* Improved: Use a temporary folder during post-processing
* Improved: Added verify_ssl_cert option
* Improved: Fixed track matching progress
* Improved: pylint, pep8 & pylint fixes
* Improved: Stop JS links from scrolling to the top of the page

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.5.9...v0.5.10).

## v0.5.9
Released 05 September 2015

Highlights:
* Added: Providers Strike, Jackett, custom Torznabs
* Added: Option to stop post-processing if no good match found (#2343)
* Fixed: Blackhole -> Magnet, limit to torcache
* Fixed: Kat 403 flac error
* Fixed: Last.fm errors
* Fixed: Pushover notifications
* Improved: Rutracker logging, switched to requests lib

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.5.8...v0.5.9).

## v0.5.8
Released 13 July 2015

Highlights:
* Added: Option to only include official extras
* Added: Option to wait until album release date before searching
* Fixed: NotifyMyAndroid notifications
* Fixed: Plex Notifications
* Fixed: Metacritic parsing
* Fixed: Pushbullet notifications
* Fixed: What.cd not honoring custom search term (#2279)
* Improved: XSS Search bug
* Improved: Config page layout
* Improved: Set localhost as default
* Improved: Better single artist scanning

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.5.7...v0.5.8).

## v0.5.7
Released 01 July 2015

Highlights:
* Improved: Moved pushover to use requests lib
* Improved: Plex tokens with Plex Home
* Improved: Added getLogs & clearLogs to api
* Improved: Cache MetaCritic scores. Added user-agent header to fix 403 errors
* Improved: Specify whether to delete folders when force post-processing
* Improved: Convert target bitrate to vbr preset for what.cd searching
* Improved: Switched Pushover to requests lib

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v0.5.6...v0.5.7).

## v0.5.6
Released 08 June 2015

Highlights:
* Added: Metacritic scores
* Added: Series support (e.g. Cafe Del Mar, Now That's What I Call Music, etc)
* Added: Filter out clean/edited/censored releases (#2198)
* Added: Button on the log page to toggle verbose/debug logging
* Fixed: Connecting to SABnzbd over https with python >= 2.7.9
* Fixed: Email Notifications with SSL
* Fixed: Don't limit musicbrainz results to first 100
* Fixed: nzbget url fix
* Fixed: OSX Notifications
* Improved: Cuesplit, allow wav, ape to be split
* Improved: Moved the 'freeze db' option to the advanced->misc. tab
* Improved: Moved kickass searching to json api, so it doesn't throw 404 errors anymore when there are no results
* Improved: SSL for headphones indexer
* Improved: Disable update dialog box if check_github is diabled

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

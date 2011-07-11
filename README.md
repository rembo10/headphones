#![preview thumb](https://github.com/rembo10/headphones/raw/master/data/images/headphoneslogo.png)Headphones

###Installation and Notes

This is a pretty early release of a third-party add-on for SABnzbd.

To run it, just double-click the headphones.py file (in Windows) or launch a terminal, cd into the Headphones directory and run 'python headphones.py' (it takes -q and -d as optional arguments). 

If you run into any issues while upgrading, try dumping your config.ini file and starting over. I'll fix this so any future settings changes will just be added to your existing file.

###Screenshots
First Run

![preview thumb](http://img806.imageshack.us/img806/4202/headphones2.png)

Artist Search Results

![preview thumb](http://img12.imageshack.us/img12/7838/headphones4.png)

Album Selection

![preview thumb](http://img836.imageshack.us/img836/2880/headphones3.png)

iTunes/Import

![preview thumb](http://img62.imageshack.us/img62/1218/headphones1.png)

There are still a few things that I'm working on:

* Post-processing doesn't work yet. Just use the categories setting with SABnzbd to customize your final download directory.

* Settings changes require a restart. I think this has something to do with how configobj caches its data, but I'm not sure.

* Importing your itunes library takes a long time. That's because for each artist, it tries to find all of their releases before moving on to the next artist. I might stagger how the info gets added, i.e. first it adds all the artists, then it goes back and adds all of their release information.

* There are a lot of "duplicates" showing up under albums. MusicBrainz (the music database I'm using) has a 'release groups' category and a 'releases' category. Release Groups are basically albums, but within each release group there are a lot of different versions of albums (US releases, British Releases, re-releases, etc). In order to get track information, I had to use the 'release' category, and by doing so Headphones might add a few different releases for any given release group. I'll change this so it only adds "the best" release out of any given release group.

* "Snatched" downloads don't change status to "Downloaded". I'm keeping a database of snatched downloads, but since post-processing doesn't work yet, I didn't want to change the status until the app knows for sure that the album has downloaded.

* If you currently have an album, it won't show up as "Had" or "Downloaded" under albums. This is just because Headphones is more of a download manager and less of a library manager - also if you only had one song off an album, I don't want to mark it as having the whole album.


If you run into any more issues, visit http://github.com/rembo10/headphones and report an issue. 

This is free software so feel free to use it/modify it as you wish. The code is messy, but it works :-)

If you have any ideas for the next release, also make sure to post that here!
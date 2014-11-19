nab
===

Service for automatically downloading and managing TV shows.


Getting started
-------------------

Nab requires [libtorrent](http://www.libtorrent.org/) to run.
To install, run `python setup.py install`.

You can start Nab with the command `python -m nab`.

### The watchlist

By default, Nab will use a 'watchlist' to decide what to download. The file `watchlist.txt` is located in `C:\Users\<user>\AppData\Local\nab\nab` on Windows and in `\home\<user>\.config\nab` on Linux.

Every line in `watchlist.txt` is considered an entry. They can be shows, seasons or episodes:

```
Game of Thrones
South Park - S10
Sherlock 1x1
Friends
```

Located in the same folder as `watchlist.txt` is `config.yaml`, which is used to change the way Nab behaves.

The general layout of `config.yaml` is:

```
settings:
  downloads: <download folder>
  videos: <video folders>
shows:
  library: <used to find shows that you own>
  watching: <used to find shows that you want>
  filters: <used to filter episodes that you don't want>
databases: <services for looking up show information>
files:
  sources: <used to find torrent files>
  filters: <used to rate torrent files>
downloader: <used to download torrents>
renamer:
  pattern: <how to rename files and where to move them>
  copy: <set to yes to copy files to your videos instead of moving them>
```

### Change how files are named

This is done by changing `renamer: pattern: <pattern>`.

Parts in curly braces `{ }` are substituted when the files are renamed:

| Name     | Description    |
| :------: | -------------- |
| {videos} | Videos folder  |
| {t}      | Show title     |
| {st}     | Season title (usually the same as show title) |
| {s}      | Season number  |
| {e}      | Episode number |
| {et}     | Episode title  |

An example is given below:


```
renamer:
  pattern: '{videos}/{t}/s{s:02d}/e{e:02d} {et}'
```

Example output: `Videos/BlackAdder/s02/e06 Chains.avi`

### Choose my videos or downloads folder

Simply change `settings: downloads: <path>` or `settings: videos: <path>`!

The special word `{user}` translates into the path to the user's files (e.g. `C:\Users\John Smith\`).


### Download missing episodes for my shows

This can be done by adding `filesystem` to the `watching` list:

```
watching:
  - watchlist
  - filesystem
```

This tells Nab that you want all episodes of the shows that are in your filesystem (your videos folder).


Features
-------


### Automatic downloads

Downloads start and end in the background without any user action. Episodes are downloaded straight after airing.


### Intelligent file recognition and renaming

As well as downloading videos, nab sensibly renames them and moves them directly into your video folder to be watched immediately.

Smart recognition of files also allows nab to find series with unusual naming conventions, such as 24 or Bakemonogatari.


### But I'm sure it won't be able to download <blank>!

Nab is designed to find just about anything, it isn't just for the most popular, current shows. It will recognize lots of old or obscure shows and anime.


### Integration with other services

Nab can integrate with services such as uTorrent, Plex and Trakt. These additional services allow Nab to do intelligent things such as not to re-download watched-but-deleted episodes and recognize shows on user 'wishlists'.


### Extensibility and customisability

Nab uses yaml config file allowing considerable customisation. The user can choose where to get show information (such as thetvdb), what shows to download, what file sources to use (The Pirate Bay, Kickass Torrents) as well as file preferences such as video quality, encoding and release groups.

A plugin system using python files allows a user or developer to create new plugins in order to extend functionality or integrate Nab with other services.


Future stuff
-------------

- A web-based GUI so users don't have to delve into text files.
- Support for movies as well as TV shows.
- More plugins supporting things like XBMC and tvrage.


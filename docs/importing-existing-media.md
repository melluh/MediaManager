# Importing existing media

MediaManager can adopt media you already have on disk (e.g. downloaded by Sonarr or Radarr). It periodically scans the root TV and movie directories for folders it does not recognise and offers them to you as import candidates.

A folder is offered as importable when **all** of these are true:

* Its name does not start with a dot.
* It sits directly in the root TV/movie library (subfolders of subfolders are not scanned).
* It is not itself a configured additional library root.
* It is not already claimed by an item in your library, i.e. no movie/show has that folder as its own directory.

Here is an example, using these rules:

```
/
└── data/
    ├── tv/
    │   ├── Rick and Morty                              # WILL be offered
    │   ├── Stranger Things (2016) {tvdb_12345} [x265]  # WILL be offered
    │   ├── Breaking Bad (2008) [tmdbid-1396]           # WILL be offered, unless already in the library
    │   ├── .The Office (2013)                          # WILL NOT, dot-prefixed
    │   └── my-custom-library/                          # WILL NOT, it is a configured library root
    │       └── The Simpsons                            # WILL NOT, not directly in the root library
    └── movies/
        └── Oppenheimer (2023)                          # WILL be offered
```

!!! info
    The list of import candidates is refreshed by a background scan every five minutes, so a folder you just dropped in may not show up immediately. Use the rescan button on the TV/movie import screen to scan right away.

!!! info
    Working out which movie or show a folder holds costs a metadata lookup, so the scan caches the answer in a small `.mediamanager` file inside the folder. That is the only file MediaManager writes into a folder it has not imported, and it never fails a scan — on a read-only library the write is simply skipped. Set `write_import_sidecars = false` in your config to turn it off. A folder named with a `[tmdbid-123]` token is matched from that id directly, which is both faster and exact.

If your folder structure is in the correct format, you can start importing. To do this, log in as an administrator and go to the TV/movie dashboard.

## What importing does

Importing **moves, copies and renames nothing**. You pick the folder and the movie/show it belongs to, and MediaManager records that folder as the media item's own directory, scans it, and records the media files where they already are. Nothing is written to disk at all.

So the "after" picture is the same as the "before" picture — the only change is in MediaManager's database:

```
/
└── data/
    ├── tv/
    │   ├── Rick and Morty                              # UNCHANGED, now the show's own directory
    │   ├── Stranger Things (2016) {tvdb_12345} [x265]  # UNCHANGED, now the show's own directory
    │   ├── .The Office (2013)                          # IGNORED
    │   └── my-custom-library/
    │       └── The Simpsons                            # IGNORED
    └── movies/
        └── Oppenheimer (2023)                          # UNCHANGED, now the movie's own directory
```

That means:

* No second directory appears and no extra disk space is used.
* Your existing file and folder names are left exactly as they are.
* The folder stops being offered as an import candidate straight away, because the library now owns it. You do **not** need to dot-prefix it afterwards.

!!! warning
    Deleting an imported movie or show with the "delete files" option **deletes the folder you imported**, including everything in it. After an import that folder *is* the library copy, not a duplicate of it, so there is no second copy left behind. Be careful with this if you are used to MediaManager's older, copy-based import.

Importing is refused when the movie or show already has files recorded in MediaManager: pointing it at a different folder would orphan the files it already knows about. If you really want to re-point an item at another folder, delete it from your library and add it again.

!!! info
    Newly downloaded media is unaffected by all of this. It still goes into a directory MediaManager names itself:

    ```
    Name (Year) [tmdbid-123]
    ```

    `tmdbid` is replaced with `tvdbid` for media whose metadata came from TVDB, and the ` (Year)` part is left out for media with no known year. That directory is created inside the library the media item is assigned to, or inside the root TV/movie directory when it uses the default library. The files are hardlinked out of the torrent download directory, so this costs no additional disk space; only if the hardlink fails (typically because the download directory and the library are on different filesystems) does MediaManager fall back to copying, which does use twice the space.

!!! info
    Directories created by older MediaManager versions were, for a while, named with the bare title only (e.g. `Rick and Morty`). All these forms are valid — MediaManager remembers the directory name each item actually has on disk, so existing libraries are left alone. Only newly added media gets the `Name (Year) [tmdbid-123]` form.

## More criteria for importing

These are the criteria specifically for the files themselves:

* Video files are looked for recursively inside the folder you import, so files in subfolders are found too.
* Only video files are recorded. Subtitles and other files are left alone — they stay on disk untouched, MediaManager simply does not track them. Archives are **not** extracted; an import reads the folder and never writes to it.
* Episode video files must contain the season and episode number in their **filename**, e.g. `S01E01.mp4` or `S03E07 Rick and Morty.mkv`. Files without such a token are skipped, as are files naming an episode that does not exist for that show. The folder layout does not matter at all: `Season 01`, `S01`, a flat folder with everything in it, or deeply nested subfolders all work equally well — the folder names are never read.
* Every video file found is recorded. A movie folder holding several video files (a director's cut alongside the theatrical release, say) gets a record for each of them, distinguished by the part of the filename that differs.

Because nothing is renamed, an imported library keeps whatever naming scheme it already had. Renaming existing files to a consistent scheme is not part of importing and is not offered at the moment; it may come back later as a separate action you opt into.

## Miscellaneous information

* Make MediaManager ignore directories by prefixing them with a dot.
* After importing, especially TV shows, manually check if all files were picked up.
* MediaManager outputs in the logs if an episode/movie could not be imported.

Last updated: 2 September 2026

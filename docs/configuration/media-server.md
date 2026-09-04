# Media Server

Media server settings are configured in the `[media_server]` section of your `config.toml` file. When configured, movies and shows that are downloaded and have already been scanned in by your media server get a **Watch on \<Server\>** button on their detail page instead of the Download button.

MediaManager currently supports Jellyfin. The lookup is live (not stored in the database): on each page load, MediaManager asks the media server whether it already has the item, briefly caching the result. This means a file that was just downloaded will start showing its watch button as soon as the media server has scanned it in - no MediaManager restart or rescan needed.

## Jellyfin Settings (`[media_server.jellyfin]`)

* `enabled`\
  Set to `true` to enable Jellyfin integration. Default is `false`.
* `url`\
  Internal URL MediaManager uses to talk to the Jellyfin API, e.g. `http://jellyfin:8096` when both containers are on the same Docker network. Do not include a trailing slash.
* `external_url`\
  Browser-facing URL used when building the "Watch on Jellyfin" link, only needed if it differs from `url` (e.g. Jellyfin sits behind a reverse proxy at a different hostname than the one MediaManager uses internally). Falls back to `url` when unset.
* `api_key`\
  API key for Jellyfin. Create one under Jellyfin's **Dashboard → API Keys**.

!!! info
    MediaManager matches media to Jellyfin by IMDb ID first, falling back to the TMDB/TVDB id when no IMDb id is known. Jellyfin needs to have the matching provider metadata plugin enabled (it does by default) for the match to succeed.

## Example Configuration

Here's a complete example of the media server section in your `config.toml`:

```toml title="config.toml"
[media_server]
    [media_server.jellyfin]
    enabled = true
    url = "http://jellyfin:8096"
    external_url = "https://jellyfin.example.com"
    api_key = "your_jellyfin_api_key"
```

!!! warning
    A movie or show only gets a watch button once it is both downloaded *and* Jellyfin has finished scanning the file in. Until then, MediaManager still shows the regular Download button.

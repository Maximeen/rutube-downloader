# RUTUBE video, playlist and section downloader

A `yt-dlp` fork for downloading individual videos, playlists and channel
sections from `rutube.ru`. The script is not tied directly to RuTube's internal
API: the up-to-date extraction logic is maintained by the `yt-dlp` project.

## Installation

Requires Python 3.10+ and a recent `yt-dlp` on Linux or macOS:

```bash
git clone <YOUR-REPOSITORY-URL>
cd rutube-downloader
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

It is also recommended to install the `ffmpeg` and `ffprobe` executables and add
them to `PATH`. They are needed when video and audio have to be merged or
processed. Check:

```bash
ffmpeg -version
```

## Examples

A single video in the best available quality:

```bash
python3 rutube_downloader.py "https://rutube.ru/video/VIDEO_ID/"
```

A whole playlist:

```bash
python3 rutube_downloader.py "https://rutube.ru/plst/308547/" -o downloads
```

The first ten videos at no more than 1080p:

```bash
python3 rutube_downloader.py "https://rutube.ru/plst/308547/" -q 1080 -I 1:10
```

First list the playlist contents without downloading:

```bash
python3 rutube_downloader.py "https://rutube.ru/plst/308547/" --dry-run
```

Age-restricted, private or login-only videos:

```bash
python3 rutube_downloader.py "URL" --cookies-from-browser chrome
```

Chrome/Edge sometimes block reading their own cookie database. In that case,
fully close the browser or export the cookies to a Netscape-format file and pass
it explicitly:

```bash
python3 rutube_downloader.py "URL" --cookies cookies.txt
```

Cookies grant access to your account. Do not publish or commit cookie files to
Git, and do not share them with third parties.

Link types supported by the current `yt-dlp` include:

- video: `https://rutube.ru/video/<id>/`;
- playlist: `https://rutube.ru/plst/<id>/`;
- channel videos and shorts: `/channel/<id>/videos/`, `/channel/<id>/shorts/`;
- public channel page: `/u/<name>/videos/`;
- movie, tag and author pages, if `yt-dlp` recognizes them.

## Re-runs and file names

A playlist is saved into a separate folder with the original numbering. By
default, `.rutube-download-archive.txt` is created in the download directory:
videos already downloaded are skipped on the next run. Disable this with the
`--no-archive` option.

Full help:

```bash
python3 rutube_downloader.py --help
```

When the site changes, first update the engine:

```bash
python3 -m pip install -U "yt-dlp[default]"
```

If the error persists, repeat the command with `--verbose`.

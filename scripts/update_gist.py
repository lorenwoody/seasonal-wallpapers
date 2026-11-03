#!/usr/bin/env python3
"""Select an Overflight playlist; write to the existing Gist only with --apply."""

import argparse
from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

GIST_ID = "6f442483c03f41514f2c43840e30a2fb"
SEASONS = ("fall", "halloween", "christmas", "winter", "spring", "summer")
PLAYLIST_DIR = Path(__file__).resolve().parents[1] / "playlists"


def thanksgiving(year):
    first = date(year, 11, 1)
    return first + timedelta(days=(3 - first.weekday()) % 7 + 21)


def season_for(day):
    if day.month <= 2:
        return "winter"
    if day.month <= 4:
        return "spring"
    if day.month <= 8:
        return "summer"
    if day.month == 10:
        return "halloween"
    if day.month == 12 or (day.month == 11 and day > thanksgiving(day.year)):
        return "christmas"
    return "fall"


def validate_playlist(data, allow_examples=False):
    if not isinstance(data, list) or not data:
        raise ValueError("Playlist must be a nonempty JSON array")
    for index, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise ValueError(f"Entry {index}: expected an object")
        urls = [entry[key] for key in ("url_img", "url_1080p") if key in entry]
        if not urls:
            raise ValueError(f"Entry {index}: requires url_img or url_1080p")
        for value in urls:
            if not isinstance(value, str):
                raise ValueError(f"Entry {index}: media URL must be a string")
            parsed = urlsplit(value)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError(f"Entry {index}: use a public HTTPS media URL without credentials")
            host = parsed.hostname.lower()
            if not allow_examples and (host == "example.invalid" or host.endswith(".invalid")
                                       or host in ("example.com", "example.org", "example.net")):
                raise ValueError(f"Entry {index}: replace temporary example URLs before publishing")
        if "url_1080p" in entry and not urlsplit(entry["url_1080p"]).path.lower().endswith(".mp4"):
            raise ValueError(f"Entry {index}: url_1080p must point directly to an MP4 file")
    return data


def github_api(method, token, body=None):
    encoded = None if body is None else json.dumps(body).encode("utf-8")
    request = Request(
        f"https://api.github.com/gists/{GIST_ID}",
        data=encoded,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "seasonal-wallpapers",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def update_gist(playlist, token, filename=None):
    validate_playlist(playlist)
    gist = github_api("GET", token)
    files = gist.get("files", {})
    if filename is None:
        if len(files) != 1:
            raise ValueError("Gist must have exactly one file, or set GIST_FILENAME to its existing filename")
        filename = next(iter(files))
    if filename not in files:
        raise ValueError("GIST_FILENAME does not match an existing file; refusing to create or rename one")
    existing = files[filename]
    if existing.get("truncated"):
        raise ValueError("Gist content is truncated; refusing an update without a full comparison")
    content = existing.get("content")
    if not isinstance(content, str):
        raise ValueError("Gist API did not return file content")
    try:
        unchanged = json.loads(content) == playlist
    except json.JSONDecodeError:
        unchanged = False
    if unchanged:
        print(f"Unchanged: {filename}; no revision created")
        return False
    # No filename attribute, create, delete, or rename operation: content only.
    github_api("PATCH", token, {"files": {filename: {"content": json.dumps(playlist, indent=2, ensure_ascii=False) + "\n"}}})
    print(f"Updated existing file: {filename}")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", choices=("auto",) + SEASONS, default="auto")
    parser.add_argument("--date", type=date.fromisoformat, help="Chicago calendar date (YYYY-MM-DD), dry runs only")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Update the existing Gist using GIST_TOKEN")
    mode.add_argument("--dry-run", action="store_true", help="Local validation only (the default)")
    args = parser.parse_args(argv)
    if args.apply and args.date:
        parser.error("--date is restricted to dry runs; use --season for a live override")
    today = args.date or datetime.now(ZoneInfo("America/Chicago")).date()
    season = season_for(today) if args.season == "auto" else args.season
    playlist = json.loads((PLAYLIST_DIR / f"{season}.json").read_text(encoding="utf-8"))
    validate_playlist(playlist, allow_examples=not args.apply)
    print(f"Chicago date: {today}; selected season: {season}; entries: {len(playlist)}")
    if not args.apply:
        print("DRY RUN: no network requests or Gist changes; example URLs allowed for template validation")
        return 0
    token = os.environ.get("GIST_TOKEN")
    if not token:
        raise ValueError("GIST_TOKEN is required for --apply")
    update_gist(playlist, token, os.environ.get("GIST_FILENAME") or None)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except HTTPError as error:
        print(f"GitHub API HTTP {error.code}; check token access, Gist ID, and API availability", file=sys.stderr)
        sys.exit(1)
    except URLError:
        print("GitHub API connection failed; check network access and TLS trust", file=sys.stderr)
        sys.exit(1)
    except (ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

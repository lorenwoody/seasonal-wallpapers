# Seasonal wallpapers for Projectivy and Overflight

One existing GitHub Gist supplies the same seasonal wallpaper playlist to all five onn 4K Pro Google TV devices. GitHub Actions selects the season using the current **America/Chicago** date and changes only the contents of the Gist's existing file. The TVs keep their current permanent Raw URL.

**Fall and Christmas contain licensed wallpaper images; the other four seasons still contain temporary examples. Live writes are disabled until you explicitly enable them.** No media is bundled or uploaded.

## Files and season calendar

- `playlists/`: six Overflight JSON playlists. Fall and Christmas use real stills; the other seasons demonstrate a still image and an MP4 with temporary URLs.
- `scripts/update_gist.py`: Python 3.10+ standard library script; uses the system IANA timezone database (available on GitHub's Ubuntu runners).
- `.github/workflows/seasonal-wallpapers.yml`: validation, daily scheduling, and manual dry runs/overrides.
- `tests/test_update_gist.py`: offline tests; all GitHub API writes are mocked.

| Season / file | Chicago dates |
| --- | --- |
| `winter.json` | January–February |
| `spring.json` | March–April |
| `summer.json` | May–August |
| `fall.json` | September and November 1 through Thanksgiving Day |
| `halloween.json` | All of October |
| `christmas.json` | Friday after Thanksgiving through December 31 |

Thanksgiving is the fourth Thursday of November, calculated for each year. In 2026, fall includes November 26 and Christmas starts November 27. October always uses Halloween.

## 1. Replace the temporary media

Edit each playlist to contain media you own, have permission to redistribute, or can lawfully link to from its host. The `example.invalid` URLs are deliberately nonworking placeholders. Replace or remove **both** example entries in each season before using that season live. Publishing rejects example URLs; dry runs accept them to validate the templates.

The format follows [Overflight's official JSON documentation](https://github.com/spocky/projectivy-plugin-wallpaper-overflight#json-format): a top-level array of objects with `location`, `title`, `author`, and at least one media field:

```json
[
  {
    "location": "Fall",
    "title": "TEMPORARY EXAMPLE — replace with your licensed still",
    "author": "Your creator credit",
    "url_img": "https://example.invalid/fall/wallpaper.jpg"
  },
  {
    "location": "Fall",
    "title": "TEMPORARY EXAMPLE — replace with your licensed video",
    "author": "Your creator credit",
    "url_1080p": "https://example.invalid/fall/wallpaper.mp4"
  }
]
```

`url_img` must return an image; `url_1080p` must be a directly accessible MP4 URL whose path ends in `.mp4` (query parameters are allowed). A web page, YouTube link, or download landing page will not work. Use public HTTPS URLs without cookies, login, or embedded credentials; prefer stable links without expiring signatures. Verify playback on the TVs. The script validates URL structure, not remote availability, codec support, ownership, or licensing. The `url_1080p` field follows Overflight's video convention and does not transcode media.

Do not upload copyrighted DesktopHut MP4s without redistribution rights. Keep original creator credits and license information. Check hotlinking terms.

Fall contains seven stills covering autumn forests, fallen leaves, pumpkins, a hearth, and Thanksgiving. Christmas contains six stills covering snowy villages, Christmas trees, hearths, and falling snow. Each direct Wikimedia Commons JPEG URL was downloaded anonymously, returned HTTP 200 with `image/jpeg`, and decoded successfully at its recorded dimensions (all at least 1920 × 1080). Creator credits, original titles, source pages, and CC0/CC BY/CC BY-SA license links are retained in each entry. These are unmodified originals; follow the recorded license when redistributing or adapting them. Commons supports direct media linking; see its [reuse guidance](https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia#Hotlinking). Availability can change; TV playback still needs device verification.

These two playlists currently contain stills only. The relevant Commons video downloads checked during curation offered WebM and MOV, without compatible MP4s. No video placeholder remains in either populated season. Add animated media only after verifying its direct MP4 URL and reuse rights.

## 2. Keep the existing Gist and Raw URL

The destination is fixed in the script:

https://gist.github.com/lorenwoody/6f442483c03f41514f2c43840e30a2fb

Do not create another Gist, delete the existing file, or rename it. The script reads the Gist before writing. If it has one file, it discovers and reuses that exact filename. If it has multiple files, set the repository Actions **variable** `GIST_FILENAME` to the exact existing filename (including case and extension). You can also set this variable for a single-file Gist to explicitly pin the target. An unknown filename causes a failure instead of creating a file.

The PATCH body contains only `files[existing_filename].content`. It does not change the Gist ID, filename, visibility, or description. The existing playlist is compared as parsed JSON; differences in whitespace or object key order alone do not create a revision. Array order does matter. Truncated/missing API content causes a safe failure.

Keep the same URL configured on all five devices. A permanent Gist Raw URL has no commit/revision hash between the Gist ID and filename; a revision-pinned Raw URL will never follow updates. Check your existing URL in Gist before enabling automation. This setup does not change device configuration. Overflight/Projectivy caching controls when each device reloads the playlist, so devices may refresh at different times.

## 3. Create a token and Actions secret

Do this only when you are ready to enable live updates; local tests need no token.

1. Sign in to GitHub as the owner of the existing Gist (`lorenwoody`).
2. Open **Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token (classic)**.
3. Choose an expiration and select only the **`gist`** scope. This grants access to the account's Gists, not just this Gist; protect the token accordingly. A repository's automatic `GITHUB_TOKEN` is not a substitute for Gist write access. This setup uses a classic PAT; do not assume a fine-grained repository token can write Gists.
4. Copy the token directly into `lorenwoody/seasonal-wallpapers` → **Settings → Secrets and variables → Actions → Secrets → New repository secret**. Name it **`GIST_TOKEN`**.
5. Never put the value in a source file, command argument, playlist, issue, pull request, or workflow log. Rotate it if exposed and renew it before expiration.

## 4. Validate safely before approval

No dependency installation is required on Ubuntu with Python 3.10+ and timezone data:

```sh
cd /workspace/seasonal-wallpapers
python3 -m unittest discover -s tests -v
python3 scripts/update_gist.py --dry-run
python3 scripts/update_gist.py --date 2026-11-26
python3 scripts/update_gist.py --date 2026-11-27
python3 scripts/update_gist.py --season halloween --dry-run
```

These commands make **no network requests**. Tests exercise season/date boundaries, Chicago midnight handling, all six JSON templates, comparison, filename preservation, and mocked updates. The default without flags is also a dry run. `--date` is allowed only for dry runs.

PRs and pushes to `main` run validation only. After merging the workflow into the default branch, open **Actions → Seasonal wallpapers → Run workflow**. Choose `auto` or an override season and leave **apply unchecked**. The validation job runs a dry run; the publish job is skipped. GitHub normally exposes the manual workflow UI only after the workflow is on the default branch.

**Do not enable live writes or select apply until live testing has been explicitly approved.** The initial pull request does not update the live Gist.

## 5. Enable automation after explicit approval

1. Replace all temporary entries for every season that will run and verify their media on a TV.
2. Add `GIST_TOKEN` as above. Optionally set the `GIST_FILENAME` repository Actions variable.
3. After approving live testing, add the repository Actions **variable** `GIST_UPDATES_ENABLED` with the exact value **`true`**. This enables scheduled writes too; do this when ready to go live.
4. Run the workflow on the default branch, choose `auto` or a season, and check **apply**. The selected season override applies to this run only. The next scheduled run returns to the calendar selection.
5. Check logs for `Updated existing file` or `Unchanged`, inspect the same Gist's contents, and check the TVs after a playlist refresh. Running again with identical data should log `Unchanged` without adding a Gist revision.

The daily cron is **08:15 UTC**, which is **02:15 CST / 03:15 CDT**. It runs after Chicago midnight throughout the year. GitHub schedules can be delayed; this is a daily update, not an exact midnight switch. Scheduled workflows run only from the default branch and can be disabled after inactivity in public repositories. Writes are serialized without canceling an active update. Manual live writes from other branches are blocked.

For a deliberately authorized local write, set `GIST_TOKEN` securely in your shell environment (do not put the value on a command line) and run `python3 scripts/update_gist.py --apply --season auto`. **The Actions enable variable gates the workflow only; local `--apply` writes directly.** No live command was run as part of the initial implementation.

## Troubleshooting and recovery

| Symptom | Check / action |
| --- | --- |
| Publish job skipped | Expected on PR/push/dry run; live runs need the default branch, `GIST_UPDATES_ENABLED=true`, and schedule or checked apply. |
| Placeholder rejection | Replace or remove every example entry in the selected playlist; keep at least one real entry. |
| HTTP 401 / 403 | Token expiration, owner, classic `gist` scope, account policy, API rate limits, and repository secret name. Never print the token. |
| HTTP 404 | Fixed Gist still exists and token owner can access it. Do not work around this by creating a replacement Gist. |
| Proxy or TLS/network failure | Allow `api.github.com`; retain TLS verification. Gist viewing uses `gist.github.com`, and Raw content uses `gist.githubusercontent.com`. Media hosts must also be reachable from the TVs. |
| Multiple files / filename mismatch | Set `GIST_FILENAME` to the existing target's exact filename; never rename to match a guessed name. |
| Truncated API content | Reduce playlist size or separately implement verified full-content retrieval; the script intentionally refuses to overwrite unseen content. |
| Media will not play | Fetch the media URL without login; confirm it returns media, not HTML; check expiring links, codecs, and supported image/video formats on the device. |
| Gist updated, TVs unchanged | Check permanent versus revision-pinned Raw URL and Overflight's refresh/cache behavior. Refresh/reselect the source as needed. |
| No scheduled runs | Merge workflow to default branch, enable Actions, inspect schedule delays/inactivity restrictions and enable variable. |
| Wrong season | Check Chicago date and prior manual override; next daily run uses `auto`. |
| `ZoneInfoNotFoundError` locally | Install your OS IANA timezone database (`tzdata`); GitHub's Ubuntu runners already provide it. |

To pause writes, remove `GIST_UPDATES_ENABLED` or set it to `false` (also cancel any publish job already running). To roll back media, restore the desired playlist via a reviewed repository change, then run an approved manual apply for that season. Alternatively restore old contents in the **same existing Gist file**, then pause automation or reconcile the repository so the next run does not overwrite the rollback. Keep the original filename and Gist ID throughout.

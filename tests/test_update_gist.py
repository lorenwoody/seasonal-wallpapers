import contextlib
from datetime import date, datetime, timedelta, timezone
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import update_gist as app


class SeasonTests(unittest.TestCase):
    def test_calendar_boundaries(self):
        cases = {
            '2026-01-01': 'winter', '2028-02-29': 'winter',
            '2026-03-01': 'spring', '2026-04-30': 'spring',
            '2026-05-01': 'summer', '2026-08-31': 'summer',
            '2026-09-01': 'fall', '2026-09-30': 'fall',
            '2026-10-01': 'halloween', '2026-10-31': 'halloween',
            '2026-11-01': 'fall', '2026-11-26': 'fall',
            '2026-11-27': 'christmas', '2026-12-31': 'christmas',
            '2027-01-01': 'winter',
        }
        for day, expected in cases.items():
            with self.subTest(day=day):
                self.assertEqual(app.season_for(date.fromisoformat(day)), expected)

    def test_thanksgiving_moves_each_year(self):
        for year in range(2000, 2101):
            holiday = app.thanksgiving(year)
            self.assertEqual(holiday.weekday(), 3)
            self.assertIn(holiday.day, range(22, 29))
            self.assertEqual(app.season_for(holiday), 'fall')
            self.assertEqual(app.season_for(holiday + timedelta(days=1)), 'christmas')

    def test_uses_chicago_date_at_utc_month_boundary(self):
        # March 1 in UTC is still February in Chicago.
        instant = datetime(2026, 3, 1, 2, tzinfo=timezone.utc)
        with patch.object(app, 'datetime') as clock, patch.object(app, 'github_api') as api:
            clock.now.side_effect = lambda zone: instant.astimezone(zone)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(app.main([]), 0)
            self.assertIn('2026-02-28; selected season: winter', output.getvalue())
            self.assertEqual(str(clock.now.call_args.args[0]), 'America/Chicago')
            api.assert_not_called()

    def test_manual_override_and_dry_run(self):
        with patch.object(app, 'github_api') as api:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(app.main(['--date', '2026-07-04', '--season', 'halloween']), 0)
            self.assertIn('selected season: halloween', output.getvalue())
            api.assert_not_called()

    def test_no_live_historical_date(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            app.main(['--apply', '--date', '2026-01-01'])


class PlaylistTests(unittest.TestCase):
    def test_all_six_playlists_are_valid_and_examples_are_guarded(self):
        self.assertEqual({p.stem for p in app.PLAYLIST_DIR.glob('*.json')}, set(app.SEASONS))
        for season in app.SEASONS:
            with self.subTest(season=season):
                data = json.loads((app.PLAYLIST_DIR / f'{season}.json').read_text())
                app.validate_playlist(data, allow_examples=True)
                self.assertTrue(any('url_img' in entry for entry in data))
                if season in ('fall', 'christmas'):
                    app.validate_playlist(data)
                else:
                    self.assertTrue(any('url_1080p' in entry for entry in data))
                    with self.assertRaisesRegex(ValueError, 'temporary example'):
                        app.validate_playlist(data)

    def test_malformed_playlists(self):
        invalid = [{}, [], ['string'], [{}], [{'url_img': None}],
                   [{'url_img': 'http://media.test/still.jpg'}],
                   [{'url_1080p': 'https://media.test/watch?id=1'}],
                   [{'url_img': 'https://user:password@media.test/still.jpg'}]]
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(ValueError):
                app.validate_playlist(data)


class GistTests(unittest.TestCase):
    # Mock-only URL; no test makes an HTTP request or checks real media.
    playlist = [{'title': 'Test fixture', 'url_img': 'https://media.test/still.jpg'}]

    def setUp(self):
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def test_semantically_unchanged_json_never_patches(self):
        with patch.object(app, 'github_api', return_value={'files': {'original.json': {
                'content': json.dumps(self.playlist, indent=4), 'truncated': False}}}) as api:
            self.assertFalse(app.update_gist(self.playlist, 'fake-token'))
            api.assert_called_once_with('GET', 'fake-token')

    def test_changed_content_updates_only_original_filename(self):
        with patch.object(app, 'github_api', side_effect=[{'files': {'original.json': {
                'content': '[]'}}}, {}]) as api:
            self.assertTrue(app.update_gist(self.playlist, 'fake-token'))
            method, token, payload = api.call_args.args
            self.assertEqual((method, token), ('PATCH', 'fake-token'))
            self.assertEqual(set(payload), {'files'})
            self.assertEqual(set(payload['files']), {'original.json'})
            self.assertEqual(set(payload['files']['original.json']), {'content'})
            self.assertEqual(json.loads(payload['files']['original.json']['content']), self.playlist)

    def test_ambiguous_gist_requires_existing_filename(self):
        files = {'a.json': {'content': '[]'}, 'b.json': {'content': '[]'}}
        with patch.object(app, 'github_api', return_value={'files': files}) as api:
            with self.assertRaisesRegex(ValueError, 'exactly one'):
                app.update_gist(self.playlist, 'fake-token')
            self.assertEqual(api.call_count, 1)
        with patch.object(app, 'github_api', side_effect=[{'files': files}, {}]) as api:
            app.update_gist(self.playlist, 'fake-token', 'b.json')
            self.assertEqual(set(api.call_args.args[2]['files']), {'b.json'})

    def test_unknown_filename_or_truncation_never_patches(self):
        for filename, metadata in [('missing.json', {'content': '[]'}),
                                   (None, {'content': '[]', 'truncated': True}),
                                   (None, {})]:
            with self.subTest(filename=filename, metadata=metadata):
                with patch.object(app, 'github_api', return_value={'files': {'original.json': metadata}}) as api:
                    with self.assertRaises(ValueError):
                        app.update_gist(self.playlist, 'fake-token', filename)
                    self.assertEqual(api.call_count, 1)

    def test_examples_rejected_before_any_network_access(self):
        with patch.object(app, 'github_api') as api:
            with self.assertRaises(ValueError):
                app.update_gist([{'url_img': 'https://example.invalid/test.jpg'}], 'fake-token')
            api.assert_not_called()

    def test_api_request_targets_only_fixed_existing_gist(self):
        with patch.object(app, 'urlopen') as opener:
            opener.return_value.__enter__.return_value.read.return_value = b'{}'
            app.github_api('PATCH', 'fake-token', {'files': {'original.json': {'content': '[]'}}})
            request = opener.call_args.args[0]
            self.assertEqual(request.full_url, 'https://api.github.com/gists/' + app.GIST_ID)
            self.assertEqual(request.method, 'PATCH')
            self.assertEqual(opener.call_args.kwargs['timeout'], 30)


if __name__ == '__main__':
    unittest.main()

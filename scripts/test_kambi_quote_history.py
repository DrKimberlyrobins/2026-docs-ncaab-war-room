import json
from pathlib import Path
import tempfile
import unittest

from kambi_markets import archive_pregame


class QuoteHistoryTest(unittest.TestCase):
 def setUp(self):
  self.temp = tempfile.TemporaryDirectory()
  self.addCleanup(self.temp.cleanup)
  self.folder = Path(self.temp.name)
  self.games = [{'id': '1', 'date': '2026-11-06T21:00:00Z'}]
  self.record = {
   'state': 'NOT_STARTED', 'start': '2026-11-06T21:05:00Z',
   'fetchedAt': '2026-11-06T20:45:05Z',
   'periods': {'full': {'total': {'outcomes': [{'line': 145.5, 'price': -110}]}}},
  }
  self.snapshot = {'date': '2026-11-06', 'fetchedAt': '2026-11-06T20:45:00Z',
                   'games': {'1': self.record}, 'offering': 'example'}

 def files(self):
  return sorted(self.folder.rglob('*.json'))

 def test_preserves_price_only_changes_and_duplicate_is_idempotent(self):
  archive_pregame(self.folder, self.snapshot, self.games)
  archive_pregame(self.folder, self.snapshot, self.games)
  self.assertEqual(len(self.files()), 1)
  first = self.files()[0].read_bytes()
  self.record['periods']['full']['total']['outcomes'][0]['price'] = -120
  with self.assertRaises(ValueError):
   archive_pregame(self.folder, self.snapshot, self.games)
  self.snapshot['fetchedAt'] = '2026-11-06T20:50:00Z'
  self.record['fetchedAt'] = '2026-11-06T20:50:05Z'
  archive_pregame(self.folder, self.snapshot, self.games)
  old, new = self.files()
  self.assertEqual(old.read_bytes(), first)
  data = json.loads(new.read_text())['games']['1']
  self.assertEqual(data['fetchedAt'], '2026-11-06T20:50:05Z')
  self.assertEqual(data['periods']['full']['total']['outcomes'][0]['price'], -120)

 def test_filters_started_missing_and_late_offers(self):
  for change in ({'state': 'STARTED'}, {'error': 'source failure'}, {'periods': {}},
                 {'fetchedAt': '2026-11-06T21:00:00Z'},
                 {'start': '2026-11-06T20:45:05Z'}):
   record = {**self.record, **change}
   archive_pregame(self.folder, {**self.snapshot, 'games': {'1': record}}, self.games)
  self.assertEqual(self.files(), [])

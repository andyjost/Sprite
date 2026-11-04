'''Front-end downloads retry transient failures without retaining partial data.'''
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import call, patch
from urllib.error import URLError


spec = importlib.util.spec_from_file_location(
    'frontend_fetch', Path(__file__).resolve().parent.parent / 'frontend/fetch.py')
fetch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch)


class TestFrontendDownload(unittest.TestCase):
  def test_succeeds_on_third_attempt(self):
    for error_type in (URLError, TimeoutError, ConnectionError):
      with self.subTest(error=error_type.__name__), tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / 'source.tar.gz'
        archive.write_bytes(b'old archive with a longer payload')
        payload = b'archive'
        with patch.object(fetch, 'urlopen', side_effect=[
            error_type('first'), error_type('second'), io.BytesIO(payload)]) as open_url, \
            patch.object(fetch.time, 'sleep') as sleep:
          digest = fetch.download('https://example.org/source', archive)
        self.assertEqual(open_url.call_args_list,
            [call('https://example.org/source', timeout=120)] * 3)
        self.assertEqual(sleep.call_args_list, [call(15), call(15)])
        self.assertEqual(archive.read_bytes(), payload)
        self.assertEqual(digest, hashlib.sha256(payload).hexdigest())
        self.assertEqual(archive.with_suffix('.gz.sha256').read_text(),
            digest + '  source.tar.gz\n')

  def test_raises_last_failure_after_three_attempts(self):
    errors = [URLError('first'), TimeoutError('second'), ConnectionError('last')]
    with tempfile.TemporaryDirectory() as tmp:
      archive = Path(tmp) / 'source.tar.gz'
      with patch.object(fetch, 'urlopen', side_effect=errors) as open_url, \
          patch.object(fetch.time, 'sleep') as sleep:
        with self.assertRaises(ConnectionError) as caught:
          fetch.download('https://example.org/source', archive)
      self.assertIs(caught.exception, errors[-1])
      self.assertEqual(open_url.call_count, 3)
      self.assertEqual(sleep.call_args_list, [call(15), call(15)])
      self.assertFalse(archive.with_suffix('.gz.sha256').exists())

  def test_retry_discards_partial_download(self):
    response = unittest.mock.MagicMock()
    response.__enter__.return_value = response
    response.read.side_effect = [b'partial download', ConnectionError('interrupted')]
    with tempfile.TemporaryDirectory() as tmp:
      archive = Path(tmp) / 'source.tar.gz'
      with patch.object(fetch, 'urlopen', side_effect=[response, io.BytesIO(b'ok')]), \
          patch.object(fetch.time, 'sleep') as sleep:
        fetch.download('https://example.org/source', archive)
      self.assertEqual(archive.read_bytes(), b'ok')
      sleep.assert_called_once_with(15)


if __name__ == '__main__':
  unittest.main()

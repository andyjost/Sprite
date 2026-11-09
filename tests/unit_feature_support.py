"""The generated support tables cover the source records without omissions."""
import cytest # from ./lib; must be first
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from curry.backends import refusals


ROOT = Path(__file__).resolve().parent.parent
GENERATOR = ROOT / 'docs/build-feature-support.py'


class TestFeatureSupport(cytest.TestCase):
  def test_generated_tables_cover_packages_and_refused_modules(self):
    expected = json.loads((ROOT / 'tests/data/cpm/index-expected.json').read_text())
    with tempfile.TemporaryDirectory() as work:
      output = Path(work) / 'tables.inc'
      subprocess.run([sys.executable, str(GENERATOR), str(output)], check=True)
      text = output.read_text(encoding='ascii')
    counts, tables = text.split('.. end-counts')
    packages, externals = tables.split('.. begin-refusals')
    results = Counter(pin['result'] for pin in expected['packages'].values())
    for result in ('pass', 'exception', 'open'):
      self.assertIn('.. |cpm-%s-count| replace:: %d\n' %
                    (result, results[result]), counts)
    self.assertIn('.. |cpm-tested-count| replace:: %d\n' %
                  len(expected['packages']), counts)
    self.assertIn('.. |cpm-index-count| replace:: %d\n' %
                  len(expected['index']['versions']), counts)
    self.assertIn('.. |cpm-index-date| replace:: %s\n' %
                  expected['index']['date'], counts)
    self.assertIn('.. |cpm-index-sha256| replace:: ``%s``\n' %
                  expected['index']['sha256'], counts)
    rows = re.findall(
        r'   \* - ``([^`]+)``\n     - ([^\n]+)\n     - ([^\n]+)\n     -(?: ([^\n]*))?',
        packages)
    self.assertEqual({name for name, *_ in rows}, set(expected['packages']))
    self.assertEqual(len(rows), len(expected['packages']))
    for name, version, result, category in rows:
      pin = expected['packages'][name]
      self.assertEqual(version, pin['version'])
      self.assertEqual(result, 'known exception' if pin['result'] == 'exception'
                       else pin['result'])
      if pin['result'] == 'exception':
        self.assertEqual(category, pin['reason'].split(':', 1)[0])
    modules = re.findall(r'     - ``([^`]+)``\n     - ', externals)
    self.assertEqual(set(modules), set(refusals.REFUSED_EXTERNALS))
    for module, entry in refusals.REFUSED_EXTERNALS.items():
      if isinstance(entry, dict):
        for function in entry:
          self.assertIn('``%s``\n     - ``%s``' % (module, function), externals)
    for issue in re.findall(r'#\d+', expected['packages']['currypp']['reason']):
      self.assertIn('`' + issue + ' <https://github.com/andyjost/Sprite/issues/', packages)

  def test_unclassified_exception_stops_generation(self):
    spec = importlib.util.spec_from_file_location('feature_support', GENERATOR)
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    expected = json.loads((ROOT / 'tests/data/cpm/index-expected.json').read_text())
    expected['packages']['allvalues']['reason'] = 'Unclassified exception'
    with self.assertRaisesRegex(ValueError, 'Missing exception class: allvalues'):
      generator.render(expected, generator.load_refusals())

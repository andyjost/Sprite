'''Translate and load the front end's unchanged acceptance programs.'''
import cytest # from ./lib; must be first
import contextlib, csv, pathlib, shutil, tempfile, unittest
from curry import config
import curry

ROOT = pathlib.Path('data/curry/community')
ORIGIN = 'frontend-3.1.0-test-pass'
# Reproduced in unit_community; the reviewer files the named findings.
KNOWN_LOAD_FAILURES = {
    'NegLit.curry': 'community compile: out-of-range Int literal (unit_community)',
    'Prelude.curry': 'community compile: PAKCS Prelude external primitives (unit_community)'
  }
for filename in ('InstanceExport.curry', 'InstanceExport/M.curry',
                 'InstanceExport/N.curry', 'InstanceExport/O.curry',
                 'InstanceExport/P.curry'):
  KNOWN_LOAD_FAILURES[filename] = (
      'community hierarchical import: module/namespace prefix collision (unit_community)'
    )
with (ROOT / 'MANIFEST.tsv').open() as stream:
  MANIFEST = list(csv.DictReader(stream, delimiter='\t'))


def current_only(source):
  relative = source.relative_to(ROOT)
  origin = relative.parts[0]
  upstream = {
      ORIGIN: 'frontend-3.1.0/test/pass',
      'kics2-3.5.0-testsuite': 'kics2-3.5.0/testsuite'
    }.get(origin)
  name = str(pathlib.Path(*relative.parts[1:])).replace('Goals.curry', '.curry')
  row = next((r for r in MANIFEST if r['source'] == upstream
              and r['path'] == name), None)
  if row and row['status'] == 'current-only':
    return row['features'].partition('current-only-reason=')[2]
  return None


def support_paths(source):
  return [str(source.parent), str(ROOT / 'support')]


@contextlib.contextmanager
def frontend_sources(source):
  # This upstream directory contains its own Prelude. Keep its bytes but
  # prevent it from replacing Sprite's installed runtime Prelude in clients.
  with tempfile.TemporaryDirectory(prefix='community-compile-') as work:
    work = pathlib.Path(work)
    for original in (ROOT / ORIGIN).rglob('*.curry'):
      if not original.is_file() or original.name == 'Prelude.curry':
        continue
      target = work / original.relative_to(ROOT / ORIGIN)
      target.parent.mkdir(parents=True, exist_ok=True)
      shutil.copyfile(original, target)
    yield work / source.relative_to(ROOT / ORIGIN), work


class TestCommunityCompile(cytest.TestCase):
  pass


def check_source(self, filename):
  source = ROOT / ORIGIN / filename
  reason = current_only(source)
  if reason and config.frontend_version() == '2.0.0':
    self.skipTest(reason)
  with frontend_sources(source) as (local, work):
    if source.name == 'Prelude.curry':
      shutil.copyfile(source, work / source.name)
    name = str(pathlib.Path(filename).with_suffix('')).replace('/', '.')
    code = (
        'import curry\n'
        'curry.path.insert(0, %r)\n'
        "curry.reset(interpret='new')\n"
        'module = curry.import_(%r)\n'
        'from curry.objects import handle\n'
        'print(handle.getHandle(module).icurry.filename)\n'
      ) % (str(work), name)
    proc = cytest.run_in_subprocess(code, timeout=60, address_space=2 << 30)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    # Verify the fixture was loaded rather than an installed namesake.
    self.assertIn(str(work), proc.stdout)


for row in MANIFEST:
  if row['source'] != 'frontend-3.1.0/test/pass' or row['status'].startswith('left-out:'):
    continue
  filename = row['path']
  def test(self, filename=filename):
    check_source(self, filename)
  if filename in KNOWN_LOAD_FAILURES:
    old_current = (config.frontend_version() == '2.0.0'
                   and current_only(ROOT / ORIGIN / filename))
    test = unittest.skipIf(not old_current, KNOWN_LOAD_FAILURES[filename])(test)
  name = 'test_' + filename[:-6].replace('/', '_')
  setattr(TestCommunityCompile, name, test)

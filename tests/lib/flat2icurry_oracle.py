'''
Oracle harness for the FlatCurry-to-ICurry port.

Every committed .icy file and every .icy file in the test corpus was written
by icurry 3.1.0 under PAKCS.  The port is right when its text is
byte-identical to those files.  For each FlatCurry file, this harness runs
the port and compares the result with the expected .icy file.  When the bytes
differ, it reports the first differing byte and the first differing subterm.

The expected file of ``<dir>/.curry/<subdir>/M.fcy`` is
``<dir>/.curry/sprite-<subdir>/M.icy`` (the test corpus) or ``<dir>/M.icy``
(a committed library product).  The front end writes the hierarchical module
``A.M`` at ``<dir>/.curry/<subdir>/A/M.fcy``; its expected file is then
``<dir>/A/.curry/sprite-<subdir>/M.icy``, where Sprite puts it.  The
interfaces of imports are searched under the root of the module, the ``-i``
directories, and the system Curry path.

The fixed oracle is the overlay archive ``overlay-<subdir>.tgz`` at the root
of the repository.  It holds the ``.fcy``, ``.fint``, and ``.icy`` files of
the test programs, written by the pinned front end and by icurry 3.1.0, and
the FlatCurry interfaces of the Curry library under ``curry/lib/.curry``.
The oracle of a library module is its committed ``.icy`` under ``curry/lib``.
:class:`Overlay` extracts the archive into a scratch directory, so a check
does not depend on the products that other tests leave behind.

Command line::

    python flat2icurry_oracle.py [-i DIR]... [-s SUBDIR]... [-q] FCY...
    python flat2icurry_oracle.py [-i DIR]... [-q] --overlay

Each argument may also be ``FCY=ICY`` to name the expected file.  With
``--overlay`` every file of the overlay archive is checked.  The exit status
is 0 when every file is equal.
'''

from curry import config
from curry.toolchain import flat2icurry as f2i
from curry.utility import readcurry as rc
import argparse, os, shutil, sys, tarfile, tempfile, time

__all__ = [
    'EQUAL', 'DIFFERENT', 'FAILED', 'Overlay', 'Result', 'check', 'check_file'
  , 'check_pairs', 'expected_icy', 'first_difference', 'frontend_subdir'
  , 'overlay_archive', 'report', 'summarize', 'main'
  ]

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
ROOT = os.path.dirname(TESTS)

EQUAL, DIFFERENT, FAILED = 'equal', 'different', 'failed'

class Result:
  '''
  The outcome for one file.  ``unrewritten`` is set when the file was found
  equal through the binding optimization (see ``check_file``).
  '''
  def __init__(
      self, fcyfile, icyfile, status, detail='', seconds=0.0, unrewritten=False
    ):
    self.fcyfile = fcyfile
    self.icyfile = icyfile
    self.status = status
    self.detail = detail
    self.seconds = seconds
    self.unrewritten = unrewritten

  def __repr__(self):
    return 'Result(%r, %r, %r)' % (self.fcyfile, self.icyfile, self.status)

def expected_icy(fcyfile):
  '''The .icy file that icurry wrote for ``fcyfile``, or None.'''
  location = f2i.product_path(fcyfile)
  if location is None:
    return None
  root, subdir, tail = location
  name = os.path.basename(fcyfile)[:-len('.fcy')] + '.icy'
  candidates = [
      os.path.join(root, '.curry', 'sprite-' + subdir, tail, name)
    , os.path.join(root, tail, '.curry', 'sprite-' + subdir, name)
    , os.path.join(root, tail, name)
    ]
  for candidate in candidates:
    if os.path.isfile(candidate):
      return candidate
  return None

def system_curry_path():
  '''The installed Curry library, when SPRITE_HOME is set.'''
  home = os.environ.get('SPRITE_HOME')
  if home:
    return [os.path.join(home, 'curry')]
  return []

def make_finder(fcyfile, prog, importdirs=(), subdirs=None):
  if not subdirs:
    location = f2i.product_path(fcyfile)
    outdir = os.path.dirname(os.path.abspath(fcyfile))
    subdirs = [location[1] if location else os.path.basename(outdir)]
  searchdirs = [f2i.module_root(fcyfile, prog.name)] + list(importdirs) \
             + system_curry_path()
  return f2i.InterfaceFinder(searchdirs, subdirs)

def check_file(
    fcyfile, importdirs=(), subdirs=None, icyfile=None, accept_unrewritten=False
  ):
  '''
  Runs the port on one file and compares the text with the oracle.  The
  translation applies no pass of its own: the routes rewrite the FlatCurry
  file before they translate it (section 8 of the README of the tests), so
  a product of either route pairs with the file beside it as the archive
  pairs with the files of icurry.

  With ``accept_unrewritten`` a file that differs is tried once more as the
  routes would translate it: the binding optimization runs over the program
  in memory, and when the pass changes it and the optimized program
  translates to the oracle, the result is EQUAL with ``unrewritten`` set.
  That is the state of a FlatCurry file that a writer outside the toolchain
  left in the text of the front end beside an ICurry file of the rewritten
  program (the PAKCS oracle does; see test_products_on_disk of
  func_flat2icurry.py).  The file on disk is not touched.
  '''
  start = time.time()
  if icyfile is None:
    icyfile = expected_icy(fcyfile)
  if icyfile is None:
    return Result(fcyfile, None, FAILED, 'no expected .icy file')
  try:
    prog = f2i.load_interface(fcyfile)
    finder = make_finder(fcyfile, prog, importdirs, subdirs)
    interfaces = [finder.find(m) for m in prog.imports]
    actual = f2i.showterm(f2i.translate(prog, interfaces))
  except BaseException as e:
    if isinstance(e, KeyboardInterrupt):
      raise
    return Result(
        fcyfile, icyfile, FAILED, '%s: %s' % (type(e).__name__, e)
      , time.time() - start
      )
  with open(icyfile, 'r', encoding='utf-8', newline='') as istream:
    expected = istream.read()
  if actual == expected:
    return Result(fcyfile, icyfile, EQUAL, '', time.time() - start)
  if accept_unrewritten:
    optimized = f2i.optimize_bindings(prog)
    if optimized is not prog:
      try:
        rewritten = f2i.showterm(f2i.translate(optimized, interfaces))
      except Exception:
        # The plain difference below is the report.
        rewritten = None
      if rewritten == expected:
        return Result(
            fcyfile, icyfile, EQUAL
          , 'equal after the binding optimization: the FlatCurry file is '
            'the text of the front end, unrewritten'
          , time.time() - start, unrewritten=True
          )
  return Result(
      fcyfile, icyfile, DIFFERENT, first_difference(expected, actual)
    , time.time() - start
    )

def check(fcyfiles, importdirs=(), subdirs=None, icyfiles=None, **kwds):
  '''Runs :func:`check_file` on each file.  Returns the list of results.'''
  if icyfiles is None:
    icyfiles = [None] * len(fcyfiles)
  return [
      check_file(fcy, importdirs, subdirs, icy, **kwds)
          for fcy, icy in zip(fcyfiles, icyfiles)
    ]

def check_pairs(pairs, importdirs=(), subdirs=None, **kwds):
  '''Runs :func:`check_file` on each ``(fcy, icy)`` pair.'''
  return [
      check_file(fcy, importdirs, subdirs, icy, **kwds) for fcy, icy in pairs
    ]

def summarize(results):
  '''The counts of equal, different, and failed results.'''
  counts = {EQUAL: 0, DIFFERENT: 0, FAILED: 0}
  for result in results:
    counts[result.status] += 1
  return counts[EQUAL], counts[DIFFERENT], counts[FAILED]

def report(results):
  '''The counts, followed by every result that is not equal.'''
  lines = ['equal %d / different %d / failed %d' % summarize(results)]
  for result in results:
    if result.status != EQUAL:
      lines.append('%-9s %s' % (result.status, result.fcyfile))
      if result.detail:
        lines.append(result.detail)
  return '\n'.join(lines)

# The overlay archive
# ===================
def frontend_subdir():
  '''
  The name of the directory under ``.curry`` into which the front end
  writes.  Sprite's own directory is that name with the prefix ``sprite-``.
  '''
  return config.frontend_subdir()

def overlay_archive(root=ROOT):
  '''The overlay archive for the pinned front end, or None.'''
  path = os.path.join(root, 'overlay-%s.tgz' % frontend_subdir())
  return path if os.path.isfile(path) else None

class Overlay:
  '''
  The overlay archive, extracted into ``directory``.  The members keep their
  paths, so a test module ``M`` of ``tests/data/curry/<d>/`` has its
  FlatCurry at ``<directory>/tests/data/curry/<d>/.curry/<subdir>/M.fcy``.
  '''

  def __init__(self, directory, subdir=None, srcroot=ROOT):
    self.directory = directory
    self.subdir = frontend_subdir() if subdir is None else subdir
    self.srcroot = srcroot

  @classmethod
  def extract(cls, directory, archive=None, srcroot=ROOT):
    '''Extracts the archive into ``directory``.'''
    if archive is None:
      archive = overlay_archive(srcroot)
    if archive is None:
      raise FileNotFoundError('no overlay archive under %s' % srcroot)
    with tarfile.open(archive) as tf:
      tf.extractall(directory, filter='data')
    return cls(directory, srcroot=srcroot)

  def fcy(self, directory, module):
    '''
    The FlatCurry file of the test module ``module`` in ``directory``, which
    is relative to ``tests/data/curry``.
    '''
    return os.path.join(
        self.directory, 'tests', 'data', 'curry', directory, '.curry', self.subdir
      , module + '.fcy'
      )

  def test_pairs(self):
    '''Every ``.fcy`` of a test program with its ``.icy``, sorted.'''
    pairs = []
    for dirpath, _, files in os.walk(os.path.join(self.directory, 'tests')):
      for fn in files:
        if fn.endswith('.fcy'):
          fcy = os.path.join(dirpath, fn)
          icy = expected_icy(fcy)
          if icy:
            pairs.append((fcy, icy))
    return sorted(pairs)

  def fcys(self):
    '''Every ``.fcy`` of the archive, the library included, sorted.'''
    fcys = []
    for dirpath, _, files in os.walk(self.directory):
      fcys.extend(os.path.join(dirpath, fn) for fn in files if fn.endswith('.fcy'))
    return sorted(fcys)

  def test_icys(self):
    '''Every ``.icy`` of a test program, sorted.'''
    icys = []
    for dirpath, _, files in os.walk(os.path.join(self.directory, 'tests')):
      icys.extend(os.path.join(dirpath, fn) for fn in files if fn.endswith('.icy'))
    return sorted(icys)

  def library_dirs(self):
    '''
    The directories under which the library interfaces lie.  The archive
    holds them under ``curry/lib`` (``make -C curry interfaces`` writes them
    there).
    '''
    libdir = os.path.join(self.directory, 'curry', 'lib')
    return [libdir] if os.path.isdir(libdir) else []

  def library_pairs(self):
    '''
    Every library ``.fcy`` of the archive with its oracle: the committed
    ``.icy`` under ``curry/lib`` of the repository, or the copy in the
    archive when the repository has none.  A module without either is left
    out.
    '''
    pairs = []
    for libdir in self.library_dirs():
      for dirpath, _, files in os.walk(libdir):
        for fn in files:
          if not fn.endswith('.fcy'):
            continue
          fcy = os.path.join(dirpath, fn)
          location = f2i.product_path(fcy)
          if location is None or location[1] != self.subdir:
            continue
          root, _, tail = location
          moduledir = os.path.relpath(os.path.join(root, tail), libdir)
          committed = os.path.normpath(os.path.join(
              self.srcroot, 'curry', 'lib', moduledir, fn[:-len('.fcy')] + '.icy'
            ))
          icy = committed if os.path.isfile(committed) else expected_icy(fcy)
          if icy:
            pairs.append((fcy, icy))
    return sorted(pairs)

def first_difference(expected, actual, context=60):
  '''Describes the first difference between two .icy texts.'''
  i = 0
  n = min(len(expected), len(actual))
  while i < n and expected[i] == actual[i]:
    i += 1
  lo = max(0, i - context)
  lines = [
      'first difference at byte %d (expected %d bytes, got %d)'
          % (i, len(expected), len(actual))
    , '  expected: ...%s' % expected[lo:i + context]
    , '  actual:   ...%s' % actual[lo:i + context]
    ]
  structural = structural_difference(expected, actual)
  if structural:
    lines.append('  ' + structural)
  return '\n'.join(lines)

def structural_difference(expected, actual, width=160):
  '''
  Parses both texts and names the first subterm that differs, with the
  enclosing IFunction when there is one.
  '''
  try:
    a = rc.parse(expected)
    b = rc.parse(actual)
  except Exception as e:
    return 'structural comparison failed: %s' % e
  found = _walk(a, b, [])
  if found is None:
    return 'the terms are equal; the texts differ in formatting only'
  path, x, y = found
  def brief(t):
    text = rc.show(t) if not isinstance(t, str) else t
    return text if len(text) <= width else text[:width] + '...'
  return 'at %s:\n    expected: %s\n    actual:   %s' % (
      '.'.join(path) or 'the root', brief(x), brief(y)
    )

def _walk(x, y, path):
  if type(x) != type(y):
    return path, x, y
  if isinstance(x, rc.Applic):
    if x.f != y.f or len(x.args) != len(y.args):
      return path, x, y
    label = x.f.name
    if label == 'IFunction' and x.args:
      label = 'IFunction %s' % rc.show(x.args[0])
    for i, (u, v) in enumerate(zip(x.args, y.args)):
      found = _walk(u, v, path + ['%s[%d]' % (label, i)])
      if found:
        return found
    return None
  if isinstance(x, (list, tuple)):
    if len(x) != len(y):
      return path, 'a sequence of %d' % len(x), 'a sequence of %d' % len(y)
    for i, (u, v) in enumerate(zip(x, y)):
      found = _walk(u, v, path + ['[%d]' % i])
      if found:
        return found
    return None
  if x != y:
    return path, x, y
  return None

def main(argv=None):
  parser = argparse.ArgumentParser(
      description='Compare the FlatCurry-to-ICurry port with the icurry oracle.'
    )
  parser.add_argument('files', nargs='*', metavar='FCY[=ICY]')
  parser.add_argument(
      '-i', '--import-dir', action='append', default=[], metavar='DIR'
    , help='a directory in which to search for the interfaces of imports'
    )
  parser.add_argument(
      '-s', '--subdir', action='append', default=[], metavar='SUBDIR'
    , help='a subdirectory of .curry that holds front-end output'
    )
  parser.add_argument(
      '-q', '--quiet', action='store_true', help='print only the failures and the counts'
    )
  parser.add_argument(
      '--overlay', action='store_true'
    , help='check every file of the overlay archive, the library included'
    )
  args = parser.parse_args(argv)
  if not args.files and not args.overlay:
    parser.error('give FCY files or --overlay')
  tmpdir = None
  try:
    jobs = []  # (fcy, icy, importdirs)
    if args.overlay:
      tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
      overlay = Overlay.extract(tmpdir)
      importdirs = overlay.library_dirs() + args.import_dir
      for fcy, icy in overlay.library_pairs() + overlay.test_pairs():
        jobs.append((fcy, icy, importdirs))
    for item in args.files:
      fcy, _, icy = item.partition('=')
      jobs.append((fcy, icy or None, args.import_dir))
    results = []
    for fcy, icy, importdirs in jobs:
      result = check_file(fcy, importdirs, args.subdir, icy)
      results.append(result)
      if result.status != EQUAL or not args.quiet:
        print('%-9s %s (%.2f s)' % (result.status, result.fcyfile, result.seconds))
      if result.detail:
        print(result.detail)
      sys.stdout.flush()
  finally:
    if tmpdir is not None:
      shutil.rmtree(tmpdir, ignore_errors=True)
  equal, different, failed = summarize(results)
  print('equal %d / different %d / failed %d' % (equal, different, failed))
  return 0 if different == 0 and failed == 0 else 1

if __name__ == '__main__':
  sys.exit(main())

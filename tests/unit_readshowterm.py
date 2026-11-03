import cytest # from ./lib; must be first
import os
from pathlib import Path
import shutil
import tempfile
import time
from unittest.mock import patch
import curry

# A 256 KiB calling-thread stack holds at most 8192 measured 32-byte
# recursive frames.  This depth exceeds that by eight times (four times
# even with 16-byte frames).  The bound holds where the requested size is
# the thread's whole stack (Linux, macOS); Windows CPython only commits it
# and keeps the executable's larger reservation, so there the deep cases
# check the results but not the explicit stacks.
DEEP_DEPTH = 65536

SOURCE = Path('data/curry/readlegacy').resolve()

# PAKCS 3.10.0, read-legacy 3.0.0, LC_ALL=C.UTF-8:
# :load ReadLegacy :eval 'putStr (unlines samples)'
# :eval 'putStr (unlines charSamples)' :quit
GOLDENS = [
    '0', '(-42)', '123456789012345678901234567890',
    '1.25', '(-2.5)', '1.0e-20', '1.0e+20', '-0.0',
    r'"\00\01\a\b\t\n\v\f\r\31\127\228"',
    r"'\''", "'\"'", r"'\\'", r'"a\"b\\c\n"',
    '[]', '[[1,2],[],[3]]', '()', '(1,True)', "(1,False,'x')",
    '(1,2,3,4)', 'Leaf', '(Branch (-3) Leaf (Branch 4 Leaf Leaf))',
    '(Record 7 "record")', '(Just [(1,True),(2,False)])', '(:*: 3 True)',
]

CHAR_GOLDENS = [
    "'\\00'",
    "'\\01'",
    "'\\02'",
    "'\\03'",
    "'\\04'",
    "'\\05'",
    "'\\06'",
    "'\\a'",
    "'\\b'",
    "'\\t'",
    "'\\n'",
    "'\\v'",
    "'\\f'",
    "'\\r'",
    "'\\14'",
    "'\\15'",
    "'\\16'",
    "'\\17'",
    "'\\18'",
    "'\\19'",
    "'\\20'",
    "'\\21'",
    "'\\22'",
    "'\\23'",
    "'\\24'",
    "'\\25'",
    "'\\26'",
    "'\\27'",
    "'\\28'",
    "'\\29'",
    "'\\30'",
    "'\\31'",
    "' '",
    '\'"\'',
    "'\\''",
    "'\\\\'",
    "'~'",
    "'\\127'",
    "'\\228'",
    "'\\955'",
    "'\\128512'",
]

def primitive(name, *args):
  # Step the private binding directly so normalization cannot remove guards.
  from curry.backends.generic.eval import evaluator
  R = curry.import_('ReadShowTerm')
  root = cytest.raw.expr(R[name], *args)
  evaluator.single_step(cytest.raw.interp(), root)
  return curry.inspect.fwd_chain_target(root)


def run_deep_case(case):
  # single_step calls the primitive on this thread, outside evaluation workers.
  # Bound its stack (on POSIX) so a recursive regression fails at a known depth.
  import threading
  from concurrent.futures import ThreadPoolExecutor
  threading.stack_size(256 << 10)
  with ThreadPoolExecutor(max_workers=1) as executor:
    executor.submit(case).result()


def deep_printer_case():
  curry.path.insert(0, str(SOURCE))
  M = curry.import_('ReadLegacy')
  start = time.perf_counter()
  leaf = cytest.raw.expr(M.Leaf)
  one = cytest.raw.expr(1)
  value = leaf
  for _ in range(DEEP_DEPTH):
    value = cytest.raw.expr(M.Branch, one, value, leaf)
  printed = primitive('prim_showTerm', value)
  assert cytest.raw.interp().topython(printed) == (
      '(Branch 1 ' * DEEP_DEPTH + 'Leaf' + ' Leaf)' * DEEP_DEPTH)
  print('deep tree build/show %.3f s' % (time.perf_counter() - start), flush=True)


def deep_cases(case):
  curry.path.insert(0, str(SOURCE))
  M = curry.import_('ReadLegacy')
  depth = DEEP_DEPTH

  def read(text):
    result = primitive('prim_readsUnqualifiedTerm', ['ReadLegacy', 'Prelude'], text)
    assert result.info.name == ':'
    pair, end = result.successors
    assert end.info.name == '[]'
    value, rest = pair.successors
    assert rest.info.name == '[]'
    return value

  def show(value):
    return cytest.raw.interp().topython(primitive('prim_showTerm', value))

  if case == 'parentheses':
    start = time.perf_counter()
    value = read('(' * depth + '0' + ')' * depth)
    assert cytest.raw.interp().topython(value) == 0
    assert show(value) == '0'
    print('deep parentheses %.3f s' % (time.perf_counter() - start), flush=True)
  if case == 'tree':
    start = time.perf_counter()
    text = '(Branch 1 ' * depth + 'Leaf' + ' Leaf)' * depth
    value = read(text)
    # Compare every field without a recursive host-language conversion/equality.
    cursor = value
    for _ in range(depth):
      assert cursor.info.name == 'Branch'
      number, cursor, leaf = cursor.successors
      assert cytest.raw.interp().topython(number) == 1
      assert leaf.info.name == 'Leaf'
    assert cursor.info.name == 'Leaf'
    print('deep tree read/compare %.3f s' % (time.perf_counter() - start), flush=True)
  if case == 'roundtrip':
    start = time.perf_counter()
    text = '(Branch 1 ' * depth + 'Leaf' + ' Leaf)' * depth
    value = read(text)
    printed = show(value)
    assert printed == text
    reread = read(printed)
    assert show(reread) == text
    print('deep tree show/read/show %.3f s' % (time.perf_counter() - start), flush=True)
  if case == 'cons':
    start = time.perf_counter()
    value = read('(1:' * depth + '[]' + ')' * depth)
    cursor = value
    for _ in range(depth):
      assert cursor.info.name == ':'
      head, cursor = cursor.successors
      assert cytest.raw.interp().topython(head) == 1
    assert cursor.info.name == '[]'
    assert show(value) == '[' + ','.join(['1'] * depth) + ']'
    print('deep cons read/compare/show %.3f s' % (time.perf_counter() - start), flush=True)


class TestReadShowTerm(cytest.TestCase):
  def module(self):
    curry.path.insert(0, str(SOURCE))
    return curry.import_('ReadLegacy')

  def test_pakcs_goldens(self):
    M = self.module()
    self.assertEqual(curry.eval(M.samples).one(), GOLDENS)
    self.assertEqual(curry.eval(M.roundTrips(GOLDENS)).one(), True)

  def test_character_goldens(self):
    M = self.module()
    self.assertEqual(curry.eval(M.charSamples).one(), CHAR_GOLDENS)
    self.assertEqual(curry.eval(M.charRoundTrips(CHAR_GOLDENS)).one(), True)

  def test_read_remainder_and_whitespace(self):
    M = self.module()
    self.assertEqual(curry.eval(M.readInt(' \t\r\n\f{- comment -}42 tail')).one(),
                     [(42, 'tail')])
    # Remainders checked once with PAKCS 3.10.0 as well.
    for text, rest in [('42 tail', 'tail'), ('42\ttail', '\ttail'),
                       ('(42) tail', ' tail'), ('((42))rest', 'rest')]:
      self.assertEqual(curry.eval(M.readInt(text)).one(), [(42, rest)])
    for text in ('', '[', ';garbage', '[1,]', '"unterminated', '{- incomplete'):
      with self.subTest(text=text):
        self.assertEqual(curry.eval(M.readInt(text)).one(), [])

  def test_constructor_errors(self):
    M = self.module()
    for prefixes, text, pattern in [
        (['Prelude'], 'Leaf', r'unknown constructor Leaf.*Prelude'),
        (['ReadLegacy', 'Prelude'], 'Absent', r'unknown constructor Absent.*ReadLegacy.*Prelude'),
        (['UnloadedReadLegacy'], 'Leaf', r'UnloadedReadLegacy.*not loaded')]:
      with self.assertRaisesRegex(curry.EvaluationError, pattern):
        curry.eval(M.readTree(prefixes, text)).one()
    self.assertEqual(curry.eval(M.validTree).one(), True)
    curry.import_('ReadLegacyOther')
    self.assertEqual(curry.eval(M.readTree(['ReadLegacyOther', 'ReadLegacy'], 'Leaf')).one(), [])
    self.assertEqual(len(curry.eval(M.readTree(['ReadLegacy', 'ReadLegacyOther'], 'Leaf')).one()), 1)

  def test_deep_terms(self):
    self.module()
    for case in ('parentheses', 'tree', 'roundtrip', 'cons'):
      with self.subTest(case=case):
        child = cytest.run_in_subprocess(
            'from unit_readshowterm import deep_cases, run_deep_case; '
            'run_deep_case(lambda: deep_cases(%r))' % case, 180,
            address_space=4 << 30)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
        print(child.stdout, end='')

  def test_deep_printer(self):
    self.module()
    child = cytest.run_in_subprocess(
        'from unit_readshowterm import deep_printer_case, run_deep_case; '
        'run_deep_case(deep_printer_case)',
        180, address_space=4 << 30)
    self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
    print(child.stdout, end='')

  def test_set_function_strings(self):
    M = self.module()
    R = curry.import_('ReadShowTerm')
    for goal in (M.setStrings, M.setTailStrings):
      result = cytest.raw.values(cytest.raw.expr(goal)).one()
      # Record whether these Curry-level constructions retain a guard in NF.
      pending, guards = [result], 0
      while pending:
        node = pending.pop()
        if not isinstance(node, curry.backends.Node):
          continue
        guards += node.info.name == '_SetGuard'
        pending.extend(node.successors)
      print('set-function string normal-form guards:', guards)
      self.assertEqual(cytest.raw.interp().topython(result), ['a"b\\c\n'])
      string = result.successors[0]
      shown = cytest.raw.values(cytest.raw.expr(R.showTerm, string, typed=True)).one()
      self.assertEqual(cytest.raw.interp().topython(shown), GOLDENS[12])

  def test_guarded_strings(self):
    from curry.expressions import _setgrd, cons, nil
    self.module()
    chars = [0, 1, 7, 8, 9, 10, 11, 12, 13, 31, 34, 39, 92, 127, 228, 955, 128512]
    plain = cytest.raw.expr(''.join(map(chr, chars)))
    expected = cytest.raw.interp().topython(primitive('prim_showTerm', plain))
    for guarded_heads, guarded_tails in [(True, False), (False, True), (True, True)]:
      value = cytest.raw.expr(nil)
      for code in reversed(chars):
        head = cytest.raw.expr(curry.Char(chr(code)))
        if guarded_heads:
          head = cytest.raw.expr(_setgrd(0, head))
        if guarded_tails:
          value = cytest.raw.expr(_setgrd(0, value))
        value = cytest.raw.expr(cons(head, value))
      actual = primitive('prim_showTerm', value)
      self.assertEqual(cytest.raw.interp().topython(actual), expected)

  def test_flatcurry_file(self):
    # Supply the optional CPM packages directory; the ordinary suite is self-contained.
    packages = Path(os.environ.get('SPRITE_TEST_CPM_PACKAGES', 'missing-cpm-packages'))
    if not (packages / 'flatcurry-5.0.0/src/FlatCurry/Files.curry').is_file():
      self.skipTest('optional flatcurry 5.0.0 package sources are absent')
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      for src in sorted(packages.glob('*/src')):
        shutil.copytree(src, root, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('.curry'))
      shutil.copy(SOURCE / 'ReadShowTerm.curry', root / 'ReadShowTerm.curry')
      curry.path.insert(0, str(root))
      small = root / 'ReadLegacySmall.curry'
      small.write_text('module ReadLegacySmall where\nfirst :: Int\nfirst = 7\nsecond :: Int\nsecond = first\n')
      # A cache hit restores ICurry but need not leave the original .fcy.
      with patch.dict(os.environ, {'SPRITE_CACHE_FILE': ''}):
        curry.import_(str(small))
      fcy = root / '.curry' / curry.config.frontend_subdir() / 'ReadLegacySmall.fcy'
      self.assertTrue(fcy.is_file())
      module = root / 'ReadLegacyFile.curry'
      module.write_text('''module ReadLegacyFile where
import FlatCurry.Files
import FlatCurry.Types
names :: String -> IO (String,[String])
names file = do
  Prog name _ _ functions _ <- readFlatCurryFile file
  return (name, [snd qname | Func qname _ _ _ _ <- functions])
''')
      M = curry.import_(str(module))
      self.assertEqual(curry.eval(M.names(str(fcy))).one(),
                       ('ReadLegacySmall', ['first', 'second']))

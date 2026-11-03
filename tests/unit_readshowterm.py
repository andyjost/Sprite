import cytest # from ./lib; must be first
import os
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch
import curry

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

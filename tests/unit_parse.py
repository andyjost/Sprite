import cytest # from ./lib; must be first
from curry import icurry
from glob import glob
import curry, gzip

GENERATE_GOLDENS = False

class ParseJSON(cytest.TestCase):
  '''Tests parsing the ICurry JSON format.'''
  def test_parseJSON(self):
    for jsonfile in glob('data/json/*.json*'):
      open_ = gzip.open if jsonfile.endswith('.gz') else open
      json = cytest.readfile(jsonfile, mode='r', fopen=open_)
      icur = icurry.json.loads(json)

      # Test equality.
      self.assertTrue(icur, icur)

      # Test repr.
      local={}
      exec('from curry.icurry import *', local)
      icur2 = eval(repr(icur), local)
      try:
        self.assertEqual(icur, icur2)
      except:
        # To debug:
        # from cytest.dissect import dissect
        # dissect(icur, icur2)
        # breakpoint()
        raise

      # Check against the golden.
      goldenfile = jsonfile.replace('.json', '.au')
      self.assertEqualToFile(icur, goldenfile, GENERATE_GOLDENS)

  def test_exempt(self):
    curry.import_('head')

  def test_atableFlex(self):
    curry.import_('atableFlex')

  def test_atableNoflex(self):
    curry.import_('atableNoflex')

  def test_btable(self):
    curry.import_('btable')

  def testKielExamples(self):
    '''Parse example programs from Kiel.'''
    for jsonfile in glob('data/json/kiel-*.json'):
      icur = icurry.json.load(jsonfile)
      curry.import_(icur)

class ReadCurryEscapes(cytest.TestCase):
  '''Tests the character escapes of the ICurry text reader.'''
  # The ICurry text writes characters above the ASCII range as decimal
  # escapes.  An old reader decoded '\\160' as '0', which made Prelude.isSpace
  # accept '0' and read "0" fail.
  CASES = [
      (r"'\160'", '\xa0'), (r"'\128'", '\x80'), (r"'\159'", '\x9f')
    , (r"'\255'", '\xff'), (r"'\127'", '\x7f'), (r"'\00'", '\0')
    , (r"'\t'", '\t'), (r"'\n'", '\n'), (r"'\\'", '\\'), (r"'\''", "'")
    , (r"'\"'", '"'), (r"'a'", 'a'), (r"'0'", '0'), (r"' '", ' ')
    # A decimal escape has up to seven digits.  The reader took three, so
    # '\\128512' became four characters.
    , (r"'\1000'", '\u03e8'), (r"'\128512'", '\U0001f600')
    , (r"'\1114111'", '\U0010ffff')
    ]

  def test_char_escapes(self):
    from curry.utility import readcurry
    for text, expected in self.CASES:
      rcdata = readcurry.parse('(ILit (IChar %s))' % text)
      ilit = icurry.readcurry.loads(rcdata)
      self.assertIsInstance(ilit.lit, icurry.IChar, text)
      self.assertEqual(ilit.lit.value, expected, text)
      # The JSON cache must hold the same character.
      ilit2 = icurry.json.loads(icurry.json.dumps(ilit))
      self.assertEqual(ilit2.lit.value, expected, text)

  def test_string_escapes(self):
    '''
    In a string, a decimal escape is read greedily, as in Curry, and the
    empty escape ends it before a digit.
    '''
    from curry.utility.readcurry import lex
    tok, = lex.tokenize(r'"\2281\228\&1\&"')
    self.assertIsInstance(tok, lex.StringToken)
    self.assertEqual(tok, '\u08e9\u00e41')

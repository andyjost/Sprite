'''
Tests for characters as Unicode code points.

A Char holds one code point on both backends.  Text crosses the boundary of
the runtime as UTF-8: the string literals of a program, the files that
readFile, writeFile, and appendFile touch, and the standard streams of putChar
and getChar.  show writes a code point outside printable ASCII as a decimal
escape, as PAKCS does.

Before this, the C++ backend stored a Char as a signed byte: ord (chr 160)
was -96, a character above U+00FF could not exist, and a non-ASCII character
could not be passed from Python.  The Python backend read a file byte by
byte and could not compile a string literal with a non-ASCII character.

The programs are in data/curry/Chars.curry.  The module is built once; the
children of the stream tests load it from the cache.
'''
import cytest # from ./lib; must be first
import curry, os, tempfile, textwrap, unittest
from unittest import mock

SAMPLE = '\u00e4\u00f6\u00fc'  # three characters of two UTF-8 bytes each
EMOJI = '\U0001f600'           # one character of four UTF-8 bytes

# Malformed UTF-8.  Both backends decode it as the 'replace' handler of Python
# does: a byte that starts no sequence gives one U+FFFD, and a sequence cut
# short, by the end of the input or by a byte that cannot continue it, gives
# one U+FFFD for the bytes read so far.
MALFORMED = [
    b'a\xffb'                                      # starts no sequence
  , b'\x80'                                        # a lone continuation byte
  , b'\xc0\x80'                                    # overlong, two bytes
  , b'\xe0\x80\x80'                                # overlong, three bytes
  , b'\xf0\x80\x80\x80'                            # overlong, four bytes
  , b'\xed\xa0\x80'                                # a surrogate, U+D800
  , b'\xf4\x90\x80\x80'                            # above U+10FFFF
  , b'\xf8\x88\x80\x80\x80'                        # a five-byte lead
  , b'\xe2\x82'                                    # cut short by the end
  , b'\xe2\x82a'                                   # cut short by a character
  , b'\xc3'                                        # a lone lead at the end
  , b'a\xc3\xa4\xf0\x9f\x98\x80\xc3\xe2\x82\xac'   # mixed with valid text
  ]

# A child evaluates one goal of the module and prints its values.
CHILD = textwrap.dedent('''
    import curry
    M = curry.import_('Chars')
    print(list(curry.eval(M.%s, converter='topython')))
    ''')

class TestChars(cytest.TestCase):
  @classmethod
  def setUpClass(cls):
    curry.import_('Chars')

  @property
  def M(self):
    return curry.import_('Chars')

  def eval_(self, *args):
    return list(curry.eval(*args, converter='topython'))

  def test_ord_chr(self):
    chr_ = curry.symbol('Prelude.chr')
    ord_ = curry.symbol('Prelude.ord')
    self.assertEqual(self.eval_(ord_, curry.expr(chr_, 160)), [160])
    self.assertEqual(self.eval_(ord_, '\u00e4'), [228])
    self.assertEqual(self.eval_(ord_, EMOJI), [0x1f600])
    self.assertEqual(self.eval_(chr_, 228), ['\u00e4'])
    self.assertEqual(self.eval_(chr_, 0x1f600), [EMOJI])
    self.assertEqual(self.eval_(chr_, 0x10ffff), ['\U0010ffff'])

  @unittest.skipIf(
      curry.flags['backend'] != 'cxx'
    , 'the Python prim_chr rejects a code point above U+10FFFF'
    )
  def test_code_point_above_the_maximum(self):
    '''
    chr clamps its argument to the last code point, but prim_chr does not
    check it.  Such a value shows as a decimal escape, and it crosses into
    Python as U+FFFD, as utf8_encode writes it.  An audit finding: the
    caster raised ValueError instead.
    '''
    prim_chr = curry.symbol('Prelude.prim_chr')
    value, = curry.eval(prim_chr, 0x110000, converter=None)
    self.assertEqual(str(value), "'\\1114112'")
    self.assertEqual(curry.topython(value), '\ufffd')
    chr_ = curry.symbol('Prelude.chr')
    self.assertEqual(self.eval_(chr_, 0x110000), ['\U0010ffff'])

  def test_python_round_trip(self):
    '''A Python string of any code points converts to Curry and back.'''
    for text in ['\u00e4', SAMPLE, EMOJI, 'a\u00a0b', SAMPLE + EMOJI]:
      expr = curry.expr(text)
      self.assertEqual(curry.topython(expr), text, text)
      self.assertEqual(self.eval_(expr), [text], text)
    # show writes every code point outside printable ASCII as a decimal
    # escape, on both backends.
    self.assertEqual(repr(curry.raw_expr('\u00e4')), "<Char '\\228'>")
    self.assertEqual(str(curry.raw_expr('\u00e4')), "'\\228'")
    self.assertEqual(str(curry.raw_expr(EMOJI)), "'\\128512'")
    self.assertEqual(str(curry.raw_expr('a' + SAMPLE)), '"a\\228\\246\\252"')
    self.assertEqual(str(curry.raw_expr('~\x7f\x00')), '"~\\127\\00"')

  def test_show_read_literals(self):
    '''
    Literals in a compiled program, show, read, and a case over characters.
    The source holds raw UTF-8 as well as escapes.
    '''
    M = self.M
    self.assertEqual(self.eval_(M.sample), [SAMPLE])
    self.assertEqual(
        self.eval_(curry.symbol('Prelude.map'), curry.symbol('Prelude.ord'), M.sample)
      , [[228, 246, 252]]
      )
    self.assertEqual(
        self.eval_(M.shown)
      , ["'\\228' '\\160' '\\127' '~' '\\128512' '\\00' '\\n'"]
      )
    self.assertEqual(self.eval_(M.shownString), ['"a\\228\\246\\252"'])
    # topython joins a list of characters into one string.
    self.assertEqual(self.eval_(M.readChars), ['\u00e4\u00e4' + EMOJI + '\u00e4'])
    self.assertEqual(self.eval_(M.readString), [SAMPLE])
    self.assertEqual(self.eval_(M.cases), [[1, 2, 3]])
    # A free variable at a case over character literals is bound to each
    # literal in turn.  The C++ backend reads the literals from a table of
    # Arg-sized entries; the old table held one byte per entry, so the second
    # value and beyond were read out of bounds.
    self.assertEqual(sorted(self.eval_(M.narrowed)), [1, 2, 3])

  def test_files(self):
    '''readFile, writeFile, and appendFile use UTF-8.'''
    M = self.M
    with tempfile.TemporaryDirectory() as tmpdir:
      sample = os.path.join(tmpdir, 'sample.txt')
      out = os.path.join(tmpdir, 'out.txt')
      with open(sample, 'wb') as stream:
        stream.write((SAMPLE + '\n' + EMOJI).encode('utf-8'))
      self.assertEqual(self.eval_(M.readLength, sample), [5])
      self.assertEqual(self.eval_(M.readText, sample), [SAMPLE + '\n' + EMOJI])
      self.assertEqual(self.eval_(M.write, out), [()])
      self.assertEqual(
          cytest.readfile(out, 'rb'), (SAMPLE + EMOJI).encode('utf-8')
        )
      self.assertEqual(self.eval_(M.writeComputed, out), [()])
      # toUpper of the Prelude maps ASCII letters only.
      self.assertEqual(
          cytest.readfile(out, 'rb'), 'AB\u00e4\u00fc\n'.encode('utf-8')
        )
      self.assertEqual(self.eval_(M.roundTrip, out), [4])

  def test_malformed_files(self):
    '''
    A malformed byte sequence in a file becomes U+FFFD.  Both backends give
    the count that the 'replace' handler of Python gives, which follows the
    maximal subparts the Unicode standard recommends.  The cases cover each
    branch of the C++ decoder: a bad lead byte, a bad continuation byte, an
    overlong encoding, a surrogate, a value above the last code point, and a
    sequence cut short.
    '''
    M = self.M
    with tempfile.TemporaryDirectory() as tmpdir:
      bad = os.path.join(tmpdir, 'bad.txt')
      for data in MALFORMED:
        with open(bad, 'wb') as stream:
          stream.write(data)
        expected = [ord(c) for c in data.decode('utf-8', 'replace')]
        self.assertIn(0xfffd, expected)
        self.assertEqual(self.eval_(M.readOrds, bad), [expected], data)

  def test_putChar_getChar(self):
    '''
    putChar writes UTF-8 and getChar reads it.  The C++ backend uses the
    standard streams of the process, so each check runs in a child.
    '''
    proc = cytest.run_in_subprocess(CHILD % 'putThree', timeout=120, text=False)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout, ('\u00e4' + EMOJI + '\n').encode('utf-8') + b'[()]\n')
    proc = cytest.run_in_subprocess(
        CHILD % 'getOrd', timeout=120, text=False
      , input=EMOJI.encode('utf-8') + b'rest'
      )
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout, b'[128512]\n')

  def test_child_streams_hold_utf8(self):
    '''
    The children of these tests read and write UTF-8 under any locale:
    cytest.run_in_subprocess sets PYTHONIOENCODING.  Here the parent asks
    for another encoding, and the child still gets UTF-8.
    '''
    with mock.patch.dict(os.environ, {'PYTHONIOENCODING': 'latin-1'}):
      proc = cytest.run_in_subprocess(
          'import sys; print(sys.stdout.encoding, sys.stdin.encoding)'
        , timeout=60
        )
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout.split(), ['utf-8', 'utf-8'])

  @unittest.skipIf(
      curry.flags['backend'] != 'cxx'
    , 'the Python getChar reads the decoded standard input of the interpreter, '
      'which rejects malformed input'
    )
  def test_getChar_stray_byte(self):
    '''
    A lead byte followed by a byte that cannot continue the sequence: getChar
    gives U+FFFD for the lead and leaves the stray byte for the next call.
    '''
    proc = cytest.run_in_subprocess(
        CHILD % 'getTwoOrds', timeout=120, text=False, input=b'\xc3a'
      )
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout, b'[[65533, 97]]\n')

  def test_cxx_literals(self):
    '''The C++ compiler spells a Char as a char32_t literal and a string as UTF-8.'''
    from curry.backends.cxx import compiler
    show = lambda char: compiler._cxxshow(char, use_char=True)
    self.assertEqual(show('a'), "U'a'")
    self.assertEqual(show("'"), "U'\\''")
    self.assertEqual(show('\\'), "U'\\\\'")
    self.assertEqual(show('\n'), "U'\\xa'")
    self.assertEqual(show('\u00e4'), "U'\\xe4'")
    self.assertEqual(show(EMOJI), "U'\\x1f600'")
    self.assertEqual(
        compiler._cxxshow('a"\\\n\t?\u00e4' + EMOJI)
      , '"a\\"\\\\\\n\\t\\077\\303\\244\\360\\237\\230\\200"'
      )
    self.assertEqual(compiler._cxxshow(''), '""')

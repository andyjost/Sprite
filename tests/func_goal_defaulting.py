'''
Goal parity and type parity with the PAKCS REPL: item Y5 of the typed
boundary (issue #54, epic #48).

Three checks, all against the pinned PAKCS through the oracle scripts of this
directory:

  * TestModuleGoals runs data/curry/goal_defaulting/*.curry under the
    functional driver.  The goals of defaulting.curry have no type
    signatures, so the front end gave most of them dictionary parameters.
    The driver reads the number of value parameters from the scheme and runs
    them; curry.eval supplies the dictionaries, and the oracle (tests/oracle,
    the :eval of the REPL) defaults the constraints as Sprite does.
    rejected.curry holds two goals the table rejects on both sides.

  * TestTextGoals compiles a list of texts with curry.compile(mode='expr')
    without exprtype and compares the values with the goldens of the oracle,
    which evaluates the same text in the REPL.  A trailing "where x free" is
    lifted to parameters on both sides.  The bindings are compared modulo
    the names of the unbound variables: PAKCS names such a variable after
    itself, {x=x} x, and Sprite prints {x=_a} _a.  Three texts are errors on
    both sides: toEnum 65 and maxBound + 1 fail in the defaulting table,
    show [] in the front end.

  * TestTypes compares the type the REPL prints for :type (tests/oracle_type)
    with the scheme Sprite prints, for every goal of defaulting.curry and for
    every text, modulo the names of the type variables and whitespace.  The
    :type of PAKCS does not lift a "where x free" clause, and neither does
    Sprite's expression_scheme, so a text whose variable is absent from the
    result type is an error on both sides there.

IO goals stay out.  tests/oracle runs the REPL in safe mode, which refuses an
initial expression of an I/O type ("Only initial expressions of non I/O type
are allowed!").  unit_goals.py covers IO goals on Sprite alone.

The goldens (*.au-gen) are committed.  The oracle runs only for a golden
that is missing or older than the module.  The golden of a text goal records
its text on its first line, "!goal <text>", and is made again when the text
in TEXTS or ERRORS changes.  A run of PAKCS takes seconds.
'''
import cytest # from ./lib; must be first
from cytest import clean, oracle
from curry.interpreter import compile as compilemod
from curry.typecheck import goals
from curry.typecheck.defaulting import ORACLE_SENTENCE
import curry, os, re, subprocess, tempfile, unittest

SOURCE_DIR = 'data/curry/goal_defaulting/'
MODULE = 'defaulting'
ORACLE_TIMEOUT = 60
TYPE_ORACLE = oracle.oracle(name='oracle_type')

# The text goals: a name for the golden files and the text.
TEXTS = [
    ('plus'        , '1+2')
  , ('divide'      , '3 / 2')
  , ('fromintegral', 'fromIntegral 3')
  , ('nil'         , '[]')
  , ('free'        , 'x where x free')
  , ('just'        , 'Just 5')
  , ('show'        , 'show (1+2)')
  , ('pair'        , "(1, 'a')")
  , ('power'       , '2 ^ 3')
  , ('floats'      , '[1, 2.5]')
  , ('id'          , 'id')
  , ('bind'        , 'x =:= 1 &> True where x free')
  , ('unify'       , 'x =:= y where x, y free')
  , ('append'      , 'xs ++ ys =:= [1, 2] where xs, ys free')
  , ('tuple_free'  , '(x, y) where x, y free')
  , ('choice'      , '1 ? 2')
  , ('fmap'        , 'fmap (+1) (Just 1)')
  , ('enumfrom'    , 'take 3 [1 ..]')
  , ('head_free'   , 'head (x:xs) where x, xs free')
  , ('list_free'   , '[x, 1] where x free')
  ]

# Texts both systems reject, with a phrase of the message of each.
ERRORS = [
    ('toenum'  , 'toEnum 65'   , ORACLE_SENTENCE)
  , ('maxbound', 'maxBound + 1', ORACLE_SENTENCE)
  , ('shownil' , 'show []'     , 'Ambiguous type variable')
  ]

# The phrase of the front end for a type variable it cannot resolve.
AMBIGUOUS = 'Ambiguous type variable'

# Normalization
# =============
_IDENT_CHARS = "A-Za-z0-9_'"

def rename_variables(text, names=()):
  '''
  Renames the unbound variables of one printed value to v1, v2, ... in the
  order of their first occurrence.  A variable is a token _a, _b, ..., as
  both systems print one, or one of ``names``, the lifted variables of the
  goal, which PAKCS prints by name.  The keys of the bindings, ``x=``, are
  kept.
  '''
  alternatives = ['_[a-z]+'] + [re.escape(name) for name in names]
  pattern = re.compile(
      r"(?<![%s])(?:%s)(?![%s]|=)" % (_IDENT_CHARS, '|'.join(alternatives), _IDENT_CHARS)
    )
  seen = {}
  def rename(match):
    return seen.setdefault(match.group(0), 'v%d' % (len(seen) + 1))
  return pattern.sub(rename, text)

def normalize_values(text, names=()):
  '''
  The values of a goal, one per line, modulo the names of the unbound
  variables, the spacing, the format of floating-point numbers, and the
  order of the lines.
  '''
  lines = [rename_variables(line, names) for line in text.split('\n')]
  return clean.clean(lines, standardize_floats=True)

def normalize_type(text):
  '''A type modulo the names of its variables and whitespace.'''
  seen = {}
  def rename(match):
    return seen.setdefault(match.group(0), 'v%d' % (len(seen) + 1))
  text = re.sub(r"(?<![%s.])[a-z][%s]*" % (_IDENT_CHARS, _IDENT_CHARS), rename, text)
  return re.sub(r'\s+', '', text)

def assertEqualModuloVariables(self, sprite, oracle_answer):
  '''
  Compares the cleaned answers of the driver modulo the names of the unbound
  variables, line by line.
  '''
  self.assertEqual(
      sorted(rename_variables(line) for line in sprite.split('\n'))
    , sorted(rename_variables(line) for line in oracle_answer.split('\n'))
    )

def readfile(filename):
  with open(filename, encoding='utf-8') as stream:
    return stream.read()

# The first line of the golden of a text goal.
TEXT_HEADER = '!goal '

def golden(module, goal, filename, text=None, **kwds):
  '''
  The golden result of ``goal`` through ``divine``, as text.  With ``text``,
  the golden belongs to a text goal: its first line is ``!goal <text>``, so
  the file follows the text and not the time stamp of the module alone.  A
  golden whose first line differs is made again.  The returned text has no
  header.
  '''
  goldenfile = os.path.join(SOURCE_DIR, filename)
  header = None if text is None else '%s%s\n' % (TEXT_HEADER, text)
  if header is not None and os.path.isfile(goldenfile):
    with open(goldenfile, encoding='utf-8') as stream:
      if stream.readline() != header:
        os.remove(goldenfile)
  oracle.divine(
      module, goal, [SOURCE_DIR], ORACLE_TIMEOUT, goldenfile=goldenfile, **kwds
    )
  content = readfile(goldenfile)
  if header is not None:
    if not content.startswith(header):
      content = header + content
      with open(goldenfile, 'w', encoding='utf-8') as stream:
        stream.write(content)
    content = content[len(header):]
  return content

def show_values(results):
  '''The values of an evaluation as Sprite prints them, one per line.'''
  return '\n'.join(curry.show_value(value) for value in results) + '\n'


class TestModuleGoals(cytest.FunctionalTestCase):
  '''
  The goals of defaulting.curry through the functional driver, and the two
  goals of rejected.curry as an intended failure.
  '''
  SOURCE_DIR = SOURCE_DIR
  CLEAN_KWDS = {'standardize_floats': True}
  COMPARISON_METHOD = assertEqualModuloVariables
  INTENDED_FAILURES = {'rejected': (curry.CurryTypeError, ORACLE_SENTENCE)}
  ORACLE_TIMEOUT = ORACLE_TIMEOUT

  def test_iterate_goals(self):
    '''
    The driver counts the value parameters from the scheme: the goals with
    dictionary parameters run, and goal17 n = n + 1 is skipped.
    '''
    module = curry.import_(MODULE)
    self.assertEqual(module.goal1.info.arity, 1)
    self.assertEqual(module.goal1.scheme.source_arity, 0)
    self.assertEqual(module.goal17.scheme.source_arity, 1)
    names = [goal.name for goal in self.iterate_goals(module)]
    self.assertEqual(names, sorted('goal%d' % i for i in range(1, 17)))


class TestTextGoals(cytest.TestCase):
  '''
  Text goals through curry.compile(mode='expr') without exprtype; the oracle
  evaluates the same text in the REPL.  One test per text; see TEXTS and
  ERRORS.
  '''
  def setUp(self):
    super().setUp()
    curry.path[:] = [SOURCE_DIR] + curry.path

  @oracle.require
  def check_values(self, name, text):
    module = curry.import_(MODULE)
    expected = golden(module, text, 'text.%s.au-gen' % name, text=text)
    _, names = goals.split_where_free(text)
    goal = curry.compile(text, mode='expr', imports=[module])
    observed = show_values(curry.eval(goal))
    self.assertEqual(
        normalize_values(observed, names), normalize_values(expected, names)
      , 'the values of %r differ:\n--- Sprite:\n%s--- oracle:\n%s'
            % (text, observed, expected)
      )

  @oracle.require
  def check_error(self, name, text, phrase):
    module = curry.import_(MODULE)
    expected = golden(
        module, text, 'text.%s.au-gen' % name, text=text, record_errors=True
      )
    self.assertTrue(
        expected.startswith('!error\n')
      , 'the oracle accepted %r:\n%s' % (text, expected)
      )
    self.assertIn(phrase, expected)
    with self.assertRaises(curry.CompileError) as cm:
      curry.compile(text, mode='expr', imports=[module])
    message = str(cm.exception)
    self.assertIn(phrase, message)
    # The table rejects the same type on both sides.
    oracle_type = re.search(r'^Overloaded type: (.*)$', expected, re.M)
    if oracle_type is not None:
      sprite_type = re.search(r"^cannot handle .* of type (.*)$", message, re.M)
      self.assertIsNotNone(sprite_type, message)
      self.assertEqual(
          normalize_type(sprite_type.group(1)), normalize_type(oracle_type.group(1))
        )


@unittest.skipIf(TYPE_ORACLE is None, 'no type oracle found')
class TestTypes(cytest.TestCase):
  '''
  The type the REPL prints for :type against the scheme Sprite prints: the
  signature of each goal of defaulting.curry and the scheme of each text, as
  the :type command of Sprite's REPL prints it.
  '''
  def setUp(self):
    super().setUp()
    curry.path[:] = [SOURCE_DIR] + curry.path

  def check_type(self, module, goal, filename, sprite_type, text=None):
    '''
    Compares the golden type of ``goal`` with the type ``sprite_type()``
    returns.  A golden that records an error expects a CompileError from
    Sprite.
    '''
    expected = golden(
        module, goal, filename, text=text, script=TYPE_ORACLE
      , record_errors=True
      )
    if expected.startswith('!error\n'):
      self.assertIn(AMBIGUOUS, expected)
      with self.assertRaisesRegex(curry.CompileError, AMBIGUOUS):
        sprite_type()
    else:
      observed = sprite_type()
      self.assertEqual(
          normalize_type(observed), normalize_type(expected)
        , 'the types of %r differ: Sprite %r, oracle %r'
              % (goal, observed, expected.strip())
        )

  def test_module_goals(self):
    '''The signature of each goal of the module, goal17 included.'''
    module = curry.import_(MODULE)
    names = sorted(
        name for name in module.__dict__ if re.match(r'goal\d+$', name)
      )
    self.assertEqual(len(names), 17)
    for name in names:
      goal = getattr(module, name)
      with self.subTest(goal=name):
        self.check_type(
            module, goal, '%s.%s.type.au-gen' % (MODULE, name)
          , lambda goal=goal: goal.signature
          )

  def check_text(self, name, text):
    module = curry.import_(MODULE)
    interp = curry.getInterpreter()
    self.check_type(
        module, text, 'text.%s.type.au-gen' % name
      , lambda: str(compilemod.expression_scheme(interp, text, imports=[module]))
      , text=text
      )


class TestGoldens(cytest.TestCase):
  '''The golden files of the text goals and the oracle scripts.'''
  def setUp(self):
    super().setUp()
    curry.path[:] = [SOURCE_DIR] + curry.path

  @oracle.require
  def test_text_header(self):
    '''
    A text golden follows its text: a golden whose first line names another
    text is made again, and a golden without the header gets one.
    '''
    module = curry.import_(MODULE)
    filename = 'text.selftest.au-gen'
    goldenfile = os.path.join(SOURCE_DIR, filename)
    self.addCleanup(lambda: os.path.isfile(goldenfile) and os.remove(goldenfile))
    with open(goldenfile, 'w', encoding='utf-8') as stream:
      stream.write('%s1+3\n4\n' % TEXT_HEADER)
    self.assertEqual(golden(module, '1+2', filename, text='1+2'), '3\n')
    self.assertEqual(readfile(goldenfile), '%s1+2\n3\n' % TEXT_HEADER)
    # The second call runs no oracle and strips the header.
    mtime = os.stat(goldenfile).st_mtime_ns
    self.assertEqual(golden(module, '1+2', filename, text='1+2'), '3\n')
    self.assertEqual(os.stat(goldenfile).st_mtime_ns, mtime)
    # A golden without the header is kept and gets one.
    with open(goldenfile, 'w', encoding='utf-8') as stream:
      stream.write('3\n')
    self.assertEqual(golden(module, '1+2', filename, text='1+2'), '3\n')
    self.assertEqual(readfile(goldenfile), '%s1+2\n3\n' % TEXT_HEADER)
    # The goldens of the module goals have no header.
    self.assertEqual(golden(module, module.goal1, 'defaulting.goal1.au-gen'), '3\n')

  @oracle.require
  def test_glob_characters(self):
    '''
    The oracle script passes a goal with a shell glob character to the REPL
    as written, even with a one-character file in the working directory.
    '''
    with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmpd:
      with open(os.path.join(tmpd, 'a'), 'w'):
        pass
      proc = subprocess.run(
          ['timeout', str(ORACLE_TIMEOUT), oracle.oracle(), 'Prelude', '1 ? 2']
        , cwd=tmpd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(sorted(proc.stdout.split()), ['1', '2'])


def _value_test(name, text):
  def test(self):
    self.check_values(name, text)
  test.__doc__ = 'values of %s' % text
  return test

def _error_test(name, text, phrase):
  def test(self):
    self.check_error(name, text, phrase)
  test.__doc__ = 'both systems reject %s' % text
  return test

def _type_test(name, text):
  def test(self):
    self.check_text(name, text)
  test.__doc__ = 'type of %s' % text
  return test

for _name, _text in TEXTS:
  setattr(TestTextGoals, 'test_' + _name, _value_test(_name, _text))
  setattr(TestTypes, 'test_' + _name, _type_test(_name, _text))
for _name, _text, _phrase in ERRORS:
  setattr(TestTextGoals, 'test_' + _name, _error_test(_name, _text, _phrase))
  setattr(TestTypes, 'test_' + _name, _type_test(_name, _text))

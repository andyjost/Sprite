'''
Twins and the engine oracle: item Y8 of the typed boundary (#57, epic #48).

A twin is a Python call of ``curry.eval`` and the equivalent Curry text,
with the Python values written as Curry literals.  The corpus lives in this
file (CORPUS): per twin, a function that builds the call and, when the call
has operands without Curry text (a value of an earlier evaluation, an
iterator), the text by hand.  Every other text is the serializer's
(``curry.typecheck.serialize``).  The modules under data/curry/typed_expr/
are generated from the corpus (``python func_typed_expr.py --write``) and
committed; one goal per twin, ``goal_<name> = <text>``.  Four checks:

  * TestTwins runs the twin modules under the functional driver.  The
    oracle (tests/oracle, the :eval of the PAKCS REPL) evaluates the goal
    of the module, and the driver compares its values with those of the
    Python call, which ``evaluate`` substitutes for the goal.  Values are
    compared modulo the names of the unbound variables and the format of
    floats.  TypeCorpus.curry holds the goals that have a type but no
    comparable value (function values, types the table rejects); the
    driver skips it by its name.

  * TestTypes compares, for every goal of the corpus, the undefaulted type
    the engine infers for the Python call with the type the front end
    wrote for the goal into the FlatCurry interface, modulo the names of
    the type variables and the order of the context.  A twin with free
    markers is compiled once more as ``compiled_expression x1 = <text>``,
    the markers lifted to parameters as the REPL lifts ``where x free``,
    because a let-bound free variable gets a Data constraint the engine
    does not give a marker.  Twins whose text was written by hand are
    excluded from this oracle, as the design says; unit tests cover them.

  * TestRoundTrip compiles the Curry text of the conversion rows of the
    design (section 3.7) through curry.compile(mode='expr') and compares
    the values with those of the Python call: the text the serializer
    printed means what the call means.

  * TestCorpus checks that the committed modules are the serializer's
    output for the corpus of this file, that every goal has a twin, and
    the raw text of the Float rows (issue #34: the C++ backend prints
    2.5 as 2.5000000000000000, so that test is an expected failure there).

The goldens (*.au-gen) are committed.  The oracle runs only for a golden
that is missing or older than its module.  A run of PAKCS takes about a
second; the whole corpus about two minutes.  The front end writes under
/tmp, so the suite runs outside a sandbox that forbids it.  No goal yields
an empty string: Sprite prints an empty [Char] value as [] and PAKCS as
"", because the printer of a raw value has no type.
'''
import cytest # from ./lib; must be first
from cytest import clean, oracle
from curry.interpreter import compile as compilemod
from curry.toolchain.flat2icurry import flatcurry as fc
from curry.typecheck import builder, sigtable
from curry.typecheck.serialize import serialize_call
import curry, itertools, os, re, sys, unittest

SOURCE_DIR = 'data/curry/typed_expr/'
ORACLE_TIMEOUT = 60
IS_CXX = curry.flags['backend'] == 'cxx'
GOAL_PREFIX = 'goal_'

# The corpus
# ==========
class Call:
  '''
  The Python call of a twin: the arguments of ``curry.expr``, its keyword
  anchors, and ``exprtype``.
  '''
  def __init__(self, *args, **kwds):
    self.args = args
    self.exprtype = kwds.pop('exprtype', None)
    self.anchors = kwds

  def node(self):
    return curry.expr(*self.args, exprtype=self.exprtype, **self.anchors)

  def values(self):
    '''The values of the call, as Curry values.'''
    return list(curry.eval(self.node()))

  def serialized(self, module=None):
    return serialize_call(
        curry.getInterpreter(), self.args, self.anchors, exprtype=self.exprtype
      , module=module
      )

  def problem(self):
    '''The engine's problem of the call, typed and not solved.'''
    b = builder.TypedBuilder(curry.getInterpreter())
    root = b.specs(self.args, self.anchors)
    return builder.TypedProblem(b, root, self.exprtype)

class Twin:
  '''
  One case: ``make(ns)`` builds the :class:`Call` from a :class:`Namespace`;
  ``text`` is the Curry text when the call has operands without text, else
  None and the serializer prints it.  ``row`` marks a conversion row of
  the design, ``floats`` a case whose printed value holds a Float.
  '''
  def __init__(self, name, make, text=None, row=False, floats=False):
    self.name = name
    self.make = make
    self.text = text
    self.row = row
    self.floats = floats

  @property
  def goal(self):
    return GOAL_PREFIX + self.name

  def curry_text(self, ns):
    '''The Curry text of the twin: by hand, or the serializer's.'''
    if self.text is not None:
      return self.text
    return self.make(ns).serialized(module=ns.modulename).text

class Corpus:
  '''
  A module of the corpus: its name, its Curry header, and its twins.  With
  ``values`` the module runs under the value driver.  With ``lifted`` the
  free markers of a goal are parameters of the goal, as the REPL lifts
  them, so that the type oracle reads the lifted type from the interface;
  such a goal has no value.
  '''
  def __init__(self, modulename, header, twins, values=True, lifted=False):
    self.modulename = modulename
    self.header = header
    self.twins = list(twins)
    self.values = values
    self.lifted = lifted
    names = [twin.name for twin in twins]
    assert len(set(names)) == len(names), 'duplicate twin names in %s' % modulename

  @property
  def filename(self):
    return os.path.join(SOURCE_DIR, self.modulename + '.curry')

  def twin(self, goalname):
    for twin in self.twins:
      if twin.goal == goalname:
        return twin
    raise KeyError(goalname)

  def goal_line(self, twin, ns):
    '''The binding of a twin in the module.'''
    if twin.text is not None or not self.lifted:
      return '%s = %s' % (twin.goal, twin.curry_text(ns))
    serialized = twin.make(ns).serialized(module=self.modulename)
    return serialized.definition(twin.goal)

  def text(self, ns):
    '''The text of the module: the header and one goal per twin.'''
    name = os.path.basename(__file__)
    lines = [GENERATED_NOTE % (name, name), self.header.rstrip('\n'), '']
    for twin in self.twins:
      lines.append(self.goal_line(twin, ns))
    return '\n'.join(lines) + '\n'

GENERATED_NOTE = (
    '-- Generated by tests/%s from its corpus; do not edit.\n'
    '-- Regenerate with "python %s --write" from the tests directory.'
  )

class Namespace:
  '''
  The names a twin builds its call from: the Prelude ``P``, the library
  modules ``DL``, ``DM`` and ``ID``, the module of the twin ``M``, the
  operators, two free markers ``x`` and ``y`` (fresh per namespace), and
  ``value``, the first value of an evaluation.
  '''
  def __init__(self, module=None, modulename=None):
    self.P = curry.import_('Prelude')
    self.DL = curry.import_('Data.List')
    self.DM = curry.import_('Data.Maybe')
    self.ID = curry.import_('Data.Functor.Identity')
    self.M = module
    self.modulename = modulename if module is None else module.__name__
    self.x = curry.free()
    self.y = curry.free()

  def sym(self, name):
    return curry.symbol('Prelude.' + name)

  @property
  def plus(self):
    return self.sym('+')

  @property
  def eq(self):
    return self.sym('=:=')

  @property
  def not_(self):
    return self.sym('not')

  def value(self, *args, **kwds):
    '''The first value of an evaluation: a copy, typed later by its content.'''
    return next(curry.eval(*args, **kwds))

def _twin(name, make, **kwds):
  return Twin(name, make, **kwds)

anchor, ref, cons, nil = curry.expressions.anchor, curry.ref, curry.cons, curry.nil

# The conversion rows of section 3.7 of the design and the literal rows of
# the API tables.  The rows marked ``row`` round-trip through the front end
# in TestRoundTrip.
LITERALS = Corpus('twins_literals', '''\
-- Literals, lists, tuples and strings: the conversion rows of the design.
''', [
    _twin('plus', lambda ns: Call(ns.plus, 1, 2), row=True)
  , _twin('plus_float', lambda ns: Call(ns.plus, 1.5, 1), row=True, floats=True)
  , _twin('int_as_float', lambda ns: Call(1, exprtype='Float'), row=True, floats=True)
  , _twin('int', lambda ns: Call(1), row=True)
  , _twin('int_typed', lambda ns: Call(1, exprtype='Int'), row=True)
  , _twin('float', lambda ns: Call(2.5), row=True, floats=True)
  , _twin('divide', lambda ns: Call(ns.sym('/'), 3, 2), row=True, floats=True)
  , _twin('negative', lambda ns: Call(ns.P.negate, -1), row=True)
  , _twin('abs_float', lambda ns: Call(ns.P.abs, -2.5), floats=True)
  , _twin('bool', lambda ns: Call(True), row=True)
  , _twin('not', lambda ns: Call(ns.not_, True), row=True)
  , _twin('and', lambda ns: Call(ns.sym('&&'), True, False))
  , _twin('char', lambda ns: Call('a'), row=True)
  , _twin('ord', lambda ns: Call(ns.P.ord, 'a'), row=True)
  , _twin('ord_unicode', lambda ns: Call(ns.P.ord, 'ä'))
  , _twin('chr', lambda ns: Call(ns.P.chr, 97))
  , _twin('char_var', lambda ns: Call(ns.P.id, 'a'), row=True)
  , _twin('string', lambda ns: Call('hi'), row=True)
  , _twin('string_length', lambda ns: Call(ns.P.length, 'hello'), row=True)
  , _twin('char_as_string', lambda ns: Call(ns.P.length, 'a'), row=True)
  , _twin('typed_string', lambda ns: Call(curry.typed('a', 'String')), row=True)
  , _twin('empty_string', lambda ns: Call(ns.P.length, ''), row=True)
  , _twin('empty_string_append', lambda ns: Call(ns.sym('++'), '', 'a'))
  , _twin('bytes', lambda ns: Call(b'bytes'), row=True)
  , _twin('reverse_string', lambda ns: Call(ns.P.reverse, 'ab'))
  , _twin('char_then_string', lambda ns: Call(['c', 'ab']), row=True)
  , _twin('string_then_char', lambda ns: Call(['ab', 'c']), row=True)
  , _twin('choice_char_string', lambda ns: Call(curry.choice('c', 'ab')))
  , _twin('fmap_ord_char', lambda ns: Call(ns.P.fmap, ns.P.ord, 'a'), row=True)
  , _twin('escapes', lambda ns: Call('ab\n"q" \\ ä\U0001f600'))
  , _twin('floats', lambda ns: Call([1, 2.5]), row=True, floats=True)
  , _twin('ints', lambda ns: Call([1, 2, 3]), row=True)
  , _twin('nested_list', lambda ns: Call([[1, 2], [3]]))
  , _twin('nil', lambda ns: Call([]), row=True)
  , _twin('typed_nil', lambda ns: Call(curry.typed([], '[Int]')))
  , _twin('range', lambda ns: Call(ns.P.length, list(range(20))))
  , _twin('pair', lambda ns: Call((1, 'a')), row=True)
  , _twin('unit', lambda ns: Call(()), row=True)
  , _twin('triple', lambda ns: Call(([1, 2], ('a', 2.5), True)), floats=True)
  , _twin('fst', lambda ns: Call(ns.P.fst, (1, 'a')))
  , _twin('snd', lambda ns: Call(ns.P.snd, (1, 'a')))
  , _twin('unboxed', lambda ns: Call([ns.P.Int, curry.unboxed(3)]), row=True)
  , _twin('cons', lambda ns: Call(cons(1, 2, nil)))
  , _twin('show_float', lambda ns: Call(ns.P.show, 2.5), floats=True)
  , _twin('show_plus', lambda ns: Call(ns.P.show, [ns.plus, 1, 2]))
  , _twin('show_just', lambda ns: Call(ns.P.show, [ns.P.Just, 1]))
  , _twin('power', lambda ns: Call(ns.sym('^'), 2, 3))
  , _twin('fromintegral', lambda ns: Call(ns.P.fromIntegral, 3))
  , _twin('just', lambda ns: Call(ns.P.Just, 5))
  , _twin('just_float', lambda ns: Call(ns.P.Just, 5, exprtype='Maybe Float'), row=True, floats=True)
  , _twin('read_int', lambda ns: Call(ns.P.read, '5', exprtype='Int'))
  , _twin('apply', lambda ns: Call(ns.P.apply, [ns.plus, 1], 6))
  , _twin('over_application', lambda ns: Call(ns.P.id, ns.P.id, 5))
  , _twin('map_plus', lambda ns: Call(ns.P.map, [ns.plus, 1], [1, 2]))
  , _twin('foldr', lambda ns: Call(ns.P.foldr, ns.plus, 0, [1, 2, 3]))
  , _twin('fmap', lambda ns: Call(ns.P.fmap, [ns.plus, 1], [ns.P.Just, 1]))
  , _twin('enumfrom', lambda ns: Call(ns.P.take, 3, [ns.P.enumFrom, 1]))
  , _twin('choice', lambda ns: Call(curry.choice(1, 2)))
  , _twin('choice_float', lambda ns: Call(curry.choice(1, 2.5)), floats=True)
  , _twin('choice_not', lambda ns: Call(ns.not_, curry.choice(True, False)))
  , _twin('choice_plus', lambda ns: Call(ns.plus, curry.choice(1, 2), 10))
  , _twin('fail', lambda ns: Call(ns.P.id, curry.fail))
  ])

# The library modules: Data.List, Data.Maybe and the newtype Identity, and
# the twins whose leaves are values of an earlier evaluation.
LIBRARY = Corpus('twins_library', '''\
-- The library modules and the twins whose leaves are values of an earlier
-- evaluation.  The REPL of PAKCS refuses a goal whose type names Identity,
-- a type the loaded module does not declare, so the newtype twins reach it
-- through show, runIdentity and ==.
import Data.Functor.Identity
import Data.List
import Data.Maybe
''', [
    _twin('sum', lambda ns: Call(ns.DL.sum, [1, 2, 3]))
  , _twin('sum_floats', lambda ns: Call(ns.DL.sum, [1.5, 2.5]), floats=True)
  , _twin('maximum', lambda ns: Call(ns.DL.maximum, [1, 3, 2]))
  , _twin('nub', lambda ns: Call(ns.DL.nub, [1, 1, 2]))
  , _twin('frommaybe', lambda ns: Call(ns.DM.fromMaybe, 0, ns.P.Nothing))
  , _twin('fromjust', lambda ns: Call(ns.DM.fromJust, [ns.P.Just, 1]))
  , _twin('lookup', lambda ns: Call(ns.P.lookup, 1, [(1, 'a')]))
  , _twin('elem', lambda ns: Call(ns.P.elem, 2, [1, 2]))
  , _twin('zip', lambda ns: Call(ns.P.zip, [1, 2], 'ab'))
  , _twin('unwords', lambda ns: Call(ns.P.unwords, ['a', 'bc']))
  , _twin('concat', lambda ns: Call(ns.P.concat, ['ab', 'c']))
  , _twin('identity_run', lambda ns: Call(ns.ID.runIdentity, [ns.ID.Identity, 5]))
  , _twin('identity_show', lambda ns: Call(ns.P.show, [ns.ID.Identity, 5]))
  , _twin('identity_eq', lambda ns: Call(ns.sym('=='), [ns.ID.Identity, 5], [ns.ID.Identity, 5]))
  , _twin('identity_fmap', lambda ns: Call(
        ns.ID.runIdentity, [ns.P.fmap, [ns.plus, 1], [ns.ID.Identity, 5]]
      ))
  , _twin('identity_apply', lambda ns: Call(
        ns.ID.runIdentity, [ns.P.apply, ns.ID.Identity, 5]
      ))
  # Values of an earlier evaluation: the text is written by hand.
  , _twin('sum_value', lambda ns: Call(ns.DL.sum, ns.value(curry.expr([1.5, 2.5])))
        , text='sum [1.5, 2.5]', floats=True)
  , _twin('fromjust_value', lambda ns: Call(
        ns.plus, [ns.DM.fromJust, ns.value(ns.P.Just, 1)], 2
      ), text='fromJust (Just 1) + 2')
  , _twin('length_value', lambda ns: Call(ns.P.length, ns.value(curry.expr('ab')))
        , text='length "ab"')
  , _twin('sum_reverse_value', lambda ns: Call(
        ns.DL.sum, ns.value(ns.P.reverse, [1, 2, 3])
      ), text='sum (reverse [1, 2, 3])')
  , _twin('fst_value', lambda ns: Call(ns.P.fst, ns.value(curry.expr((1, 'a'))))
        , text="fst (1, 'a')")
  , _twin('show_value', lambda ns: Call(ns.P.show, ns.value(ns.P.Just, [1.5]))
        , text='show (Just [1.5])', floats=True)
  , _twin('node_twice', lambda ns: (lambda n: Call(ns.plus, n, n))(curry.expr(21))
        , text='21 + 21')
  # An iterator: no text of its own either.
  , _twin('iterator', lambda ns: Call(ns.P.take, 3, itertools.count())
        , text='take 3 [0 ..]')
  , _twin('iterator_sum', lambda ns: Call(ns.DL.sum, iter([1, 2, 3]))
        , text='sum [1, 2, 3]')
  ])

# Free variables, constraints, anchors and choices.  A let-bound free
# variable whose type is absent from the result type is an ambiguity error
# in the front end, so every twin keeps its variables in the result.
LOGIC = Corpus('twins_logic', '''\
-- Free variables, constraints, anchors and choices.  Every free variable
-- occurs in the result type: a module binding cannot lift it to a
-- parameter as the REPL does.
''', [
    _twin('free_id', lambda ns: Call(ns.P.id, ns.x))
  , _twin('free_pair', lambda ns: Call((ns.x, ns.y)))
  , _twin('free_unify', lambda ns: Call(([ns.eq, ns.x, ns.y], ns.x)))
  , _twin('free_bind', lambda ns: Call(ns.sym('&>'), [ns.eq, ns.x, 1], ns.x))
  , _twin('free_append', lambda ns: Call(
        ns.sym('&>'), [ns.eq, [ns.sym('++'), ns.x, [3]], [1, 2, 3]], ns.x
      ))
  , _twin('free_tuple_eq', lambda ns: Call(([ns.eq, (ns.x, 2), (1, 2)], ns.x)))
  , _twin('free_head', lambda ns: Call(ns.P.head, [ns.P.Cons, ns.x, ns.y]))
  , _twin('free_list', lambda ns: Call([ns.x, 1]))
  , _twin('free_typed', lambda ns: Call(ns.P.id, curry.free(exprtype='[Int]')))
  , _twin('anchor_cycle', lambda ns: Call(ns.P.take, 2, anchor(cons(1, ref()))))
  , _twin('anchor_keyword', lambda ns: Call(ns.P.take, 3, ref('xs'), xs=cons(7, ref('xs'))))
  , _twin('anchor_nested', lambda ns: Call(
        ns.P.take, 3, anchor(cons(1, anchor(cons(2, ref('o')), name='i')), name='o')
      ))
  , _twin('anchor_free', lambda ns: Call(ns.P.take, 2, anchor(cons(ns.x, ref()))))
  , _twin('anchor_shared', lambda ns: Call(
        ns.plus, ref('v'), ref('v'), v=[ns.plus, 1, 2]
      ))
  , _twin('choice_nested', lambda ns: Call(curry.choice(1, curry.choice(2, 3))))
  , _twin('choice_list', lambda ns: Call([curry.choice(1, 2), 3]))
  ])

# A module with declarations of its own: a newtype, a data type with a Num
# instance, a class, and bindings without signatures.
USER = Corpus('twins_user', '''\
-- Declarations of the module: a newtype, which both systems erase at run
-- time, a data type with a Num instance, a class with two instances, and
-- bindings without signatures, which the front end gives dictionary
-- parameters.

newtype Box a = Box a
  deriving (Eq, Show)

data Nat = Z | S Nat
  deriving (Eq, Show)

instance Num Nat where
  Z + n = n
  S m + n = S (m + n)
  Z * _ = Z
  S m * n = n + m * n
  negate _ = Z
  abs n = n
  signum Z = Z
  signum (S _) = S Z
  fromInt n = if n <= 0 then Z else S (fromInt (n - 1))

twice :: Num a => a -> a
twice x = x + x

natToInt :: Nat -> Int
natToInt Z = 0
natToInt (S n) = 1 + natToInt n

class Pretty a where
  pretty :: a -> String

instance Pretty Bool where
  pretty b = if b then "yes" else "no"

instance Pretty a => Pretty [a] where
  pretty xs = concatMap pretty xs

idf = id
g14 = Just 5
g15 = 1 + 2
addOne x = x + 1
''', [
    _twin('box', lambda ns: Call(ns.M.Box, 5))
  , _twin('box_eq', lambda ns: Call(ns.sym('=='), [ns.M.Box, 5], [ns.M.Box, 5]))
  , _twin('box_show', lambda ns: Call(ns.P.show, [ns.M.Box, 5]))
  , _twin('box_pair', lambda ns: Call(([ns.M.Box, 1], 'a')))
  , _twin('box_list', lambda ns: Call([[ns.M.Box, 1], [ns.M.Box, 2]]))
  , _twin('box_bare', lambda ns: Call(ns.P.apply, ns.M.Box, 5))
  , _twin('nat', lambda ns: Call(ns.M.twice, 2, exprtype='Nat'))
  , _twin('nat_literal', lambda ns: Call(3, exprtype='Nat'), row=True)
  , _twin('toint', lambda ns: Call(ns.M.natToInt, 3), row=True)
  , _twin('toint_twice', lambda ns: Call(ns.M.natToInt, [ns.M.twice, 2]))
  , _twin('nat_list', lambda ns: Call([[ns.M.S, ns.M.Z], ns.M.Z]))
  , _twin('pretty', lambda ns: Call(ns.M.pretty, [True, False]))
  , _twin('idf', lambda ns: Call(ns.M.idf, 1))
  , _twin('g14', lambda ns: Call(ns.M.g14))
  , _twin('g15', lambda ns: Call(ns.M.g15))
  , _twin('addone', lambda ns: Call(ns.M.addOne, 1))
  , _twin('addone_float', lambda ns: Call(ns.M.addOne, 1.5), floats=True)
  , _twin('twice_int', lambda ns: Call(ns.M.twice, 2))
  , _twin('twice_float', lambda ns: Call(ns.M.twice, 1.5), floats=True)
  ])

# Goals with a type but no comparable value: function values, which the
# REPL prints in its own form, types the table rejects, and I/O, which the
# oracle refuses.  The value driver skips the file by its name.
TYPES = Corpus('TypeCorpus', '''\
-- Goals for the type oracle alone: function values, which the PAKCS REPL
-- prints in its own form, types its table rejects, and I/O.
import Data.Maybe
''', [
    _twin('plus_section', lambda ns: Call(ns.plus, 1))
  , _twin('plus_bare', lambda ns: Call(ns.plus))
  , _twin('map_not', lambda ns: Call(ns.P.map, ns.not_))
  , _twin('id', lambda ns: Call(ns.P.id))
  , _twin('const', lambda ns: Call(ns.P.const, 1))
  , _twin('compose', lambda ns: Call(ns.sym('.'), ns.not_, ns.not_))
  , _twin('flip_cons', lambda ns: Call(ns.P.flip, ns.P.Cons, []))
  , _twin('show', lambda ns: Call(ns.P.show))
  , _twin('fromjust', lambda ns: Call(ns.DM.fromJust))
  , _twin('maxbound', lambda ns: Call(ns.P.maxBound))
  , _twin('toenum', lambda ns: Call(ns.P.toEnum, 65))
  , _twin('read', lambda ns: Call(ns.P.read, '5'))
  , _twin('enumfrom', lambda ns: Call(ns.P.enumFrom, 1))
  , _twin('return', lambda ns: Call(ns.sym('return'), 5))
  , _twin('pure_pair', lambda ns: Call(ns.P.pure, (1, 'a')))
  , _twin('mapm', lambda ns: Call(ns.P.mapM_, ns.P.print, [1, 2]))
  , _twin('free_eq', lambda ns: Call(ns.eq, ns.x, ns.y))
  , _twin('free_const', lambda ns: Call(ns.P.const, 1, ns.x))
  ], values=False, lifted=True)

CORPUS = [LITERALS, LIBRARY, LOGIC, USER, TYPES]

def corpus_of(modulename):
  for corpus in CORPUS:
    if corpus.modulename == modulename:
      return corpus
  raise KeyError(modulename)

def namespace(corpus):
  '''The namespace of a corpus, with its module imported.'''
  return Namespace(curry.import_(corpus.modulename))

# Normalization
# =============
_IDENT_CHARS = "A-Za-z0-9_'"
_VARIABLE = re.compile(r"(?<![%s])_[a-z]+[0-9]*(?![%s])" % (_IDENT_CHARS, _IDENT_CHARS))

def rename_variables(text):
  '''
  Renames the unbound variables of one printed value, ``_a``, ``_b`` and
  so on, to ``v1``, ``v2``, ... in the order of their first occurrence.
  '''
  seen = {}
  def rename(match):
    return seen.setdefault(match.group(0), 'v%d' % (len(seen) + 1))
  return _VARIABLE.sub(rename, text)

def normalize_values(text, standardize_floats=True):
  '''
  The values of a goal, one per line, modulo the names of the unbound
  variables, the spacing, the order of the lines, and, by default, the
  format of the floats.
  '''
  lines = [rename_variables(line) for line in text.split('\n')]
  return clean.clean(lines, standardize_floats=standardize_floats)

def assertEqualModuloVariables(self, sprite, oracle_answer):
  '''Compares the cleaned answers of the driver modulo the variable names.'''
  self.assertEqual(
      sorted(rename_variables(line) for line in sprite.split('\n'))
    , sorted(rename_variables(line) for line in oracle_answer.split('\n'))
    )

def show_values(values):
  '''The values of an evaluation as Sprite prints them, one per line.'''
  return '\n'.join(curry.show_value(value) for value in values) + '\n'

def readfile(filename):
  with open(filename, encoding='utf-8') as stream:
    return stream.read()

# Types modulo renaming and the order of the context
# ===================================================
def _renumber(typeexpr, names):
  '''A type with its variables renumbered in the order of ``names``.'''
  if isinstance(typeexpr, fc.TVar):
    return fc.TVar(names.setdefault(typeexpr.index, len(names)))
  if isinstance(typeexpr, fc.FuncType):
    return fc.FuncType(_renumber(typeexpr.domain, names), _renumber(typeexpr.range, names))
  if isinstance(typeexpr, fc.TCons):
    return fc.TCons(typeexpr.name, [_renumber(a, names) for a in typeexpr.args])
  raise TypeError('unexpected type %r' % (typeexpr,))

def canonical_type(scheme, strip=0):
  '''
  The text of a scheme modulo the names of its type variables and the
  order of its context: the variables are named by their first occurrence
  in the type, then in the sorted context; the context is sorted.  With
  ``strip``, that many leading parameters are removed from the type (the
  lifted free markers).  Every name outside the Prelude is qualified; the
  names of the Prelude never are.
  '''
  typeexpr = scheme.typeexpr
  for _ in range(strip):
    typeexpr = typeexpr.range
  names = {}
  body = _renumber(typeexpr, names)
  # Sort the context with the variables of the body named and the others
  # as placeholders, then name the others in that order.
  def key(pred):
    scratch = dict(names)
    placeholder = {}
    def mark(te):
      if isinstance(te, fc.TVar):
        if te.index not in scratch:
          scratch[te.index] = 1000 + placeholder.setdefault(te.index, len(placeholder))
        return fc.TVar(scratch[te.index])
      if isinstance(te, fc.FuncType):
        return fc.FuncType(mark(te.domain), mark(te.range))
      return fc.TCons(te.name, [mark(a) for a in te.args])
    return (pred.classname, sigtable.show_type(mark(pred.typeexpr)))
  context = []
  for pred in sorted(scheme.context, key=key):
    context.append(
        sigtable.Predicate(pred.classname, _renumber(pred.typeexpr, names))
      )
  canonical = sigtable.Scheme(
      '<canonical>', 'type', [(i, fc.KStar) for i in range(len(names))], context
    , body, 0, len(context)
    )
  return sigtable.show_scheme(canonical, qualify=True)

def engine_scheme(call):
  '''The undefaulted scheme the engine infers for a call, what :type prints.'''
  problem = call.problem()
  problem.signature
  return problem.scheme

def lifted_scheme(interp, module, serialized):
  '''
  The scheme the front end infers for the text with its free markers
  lifted to parameters: ``compiled_expression x1 .. xn = <body>``, compiled
  through the text route from ``<body> where x1, .., xn free``.
  '''
  stmts, currypath = compilemod.getImportSpecForExpr(interp, [module])
  func, freevars, _ = compilemod.compile_expression(
      interp, serialized.where_text(), stmts, currypath, lift_freevars=True
    )
  assert freevars == serialized.frees, (freevars, serialized.frees)
  return interp.sigtable.lookup(func, required=True), len(freevars)

# The tests
# =========
class CorpusTestCase(cytest.TestCase):
  '''A test case that imports the modules of the corpus.'''
  def setUp(self):
    super().setUp()
    curry.path[:] = [SOURCE_DIR] + curry.path


class TestTwins(cytest.FunctionalTestCase):
  '''
  The twin modules through the functional driver: the oracle evaluates the
  goal of the module; Sprite evaluates the Python call of the twin.
  '''
  SOURCE_DIR = SOURCE_DIR
  CLEAN_KWDS = {'standardize_floats': True}
  COMPARISON_METHOD = assertEqualModuloVariables
  GOAL_PATTERN = GOAL_PREFIX
  ORACLE_TIMEOUT = ORACLE_TIMEOUT

  def evaluate(self, testname, module, goal):
    twin = corpus_of(testname).twin(goal.name)
    return twin.make(Namespace(module)).values()

  def test_iterate_goals(self):
    '''Every goal of every value module runs, and every twin is a goal.'''
    for corpus in CORPUS:
      if not corpus.values:
        continue
      module = curry.import_(corpus.modulename)
      names = [goal.name for goal in self.iterate_goals(module)]
      self.assertEqual(sorted(names), sorted(twin.goal for twin in corpus.twins))
    self.assertGreaterEqual(
        sum(len(c.twins) for c in CORPUS if c.values), 40
      )


class TestTypes(CorpusTestCase):
  '''
  The undefaulted type of the engine against the type of the FlatCurry
  interface, for every goal of the corpus whose text the serializer wrote.
  '''
  def check_corpus(self, corpus):
    module = curry.import_(corpus.modulename)
    interp = curry.getInterpreter()
    ns = Namespace(module)
    checked = 0
    for twin in corpus.twins:
      if twin.text is not None:
        continue
      with self.subTest(goal=twin.goal):
        call = twin.make(ns)
        serialized = call.serialized(module=corpus.modulename)
        self.assertEqual(
            getattr(module, twin.goal).scheme.fullname
          , '%s.%s' % (corpus.modulename, twin.goal)
          )
        if serialized.frees and not corpus.lifted:
          fint, strip = lifted_scheme(interp, module, serialized)
        else:
          fint, strip = getattr(module, twin.goal).scheme, len(serialized.frees)
        self.assertEqual(serialized.params, [])
        expected = canonical_type(fint, strip)
        observed = canonical_type(engine_scheme(call))
        self.assertEqual(
            observed, expected
          , 'the types of %s differ: engine %s, front end %s'
                % (serialized.text, observed, expected)
          )
        checked += 1
    self.assertGreater(checked, 0)

  def test_canonical_type(self):
    '''The canonical form renames and sorts the context.'''
    P = curry.import_('Prelude')
    plus = curry.symbol('Prelude.+')
    self.assertEqual(canonical_type(plus.scheme), 'Num a => a -> a -> a')
    a, b = fc.TVar(7), fc.TVar(3)
    scheme = sigtable.Scheme(
        'M', 'f', [(7, fc.KStar), (3, fc.KStar)]
      , [sigtable.Predicate('Prelude.Show', b), sigtable.Predicate('Prelude.Data', a)]
      , fc.FuncType(a, fc.FuncType(b, fc.TCons(fc.prelude('(,)'), [b, a]))), 2, 2
      )
    self.assertEqual(canonical_type(scheme), '(Data a, Show b) => a -> b -> (b, a)')
    self.assertEqual(canonical_type(scheme, strip=1), '(Data b, Show a) => a -> (a, b)')
    self.assertEqual(canonical_type(scheme, strip=2), '(Data b, Show a) => (a, b)')
    # A variable of the context alone comes after the variables of the type.
    scheme = sigtable.Scheme(
        'M', 'g', [(1, fc.KStar), (0, fc.KStar)]
      , [sigtable.Predicate('Prelude.Data', fc.TVar(1)), sigtable.Predicate('Prelude.Data', fc.TVar(0))]
      , fc.TCons(fc.prelude('Bool'), []), 0, 2
      )
    self.assertEqual(canonical_type(scheme), '(Data a, Data b) => Bool')
    self.assertEqual(canonical_type(curry.import_('Data.List').sum.scheme), 'Num a => [a] -> a')
    M = curry.import_('twins_user')
    self.assertEqual(canonical_type(M.goal_box.scheme), 'Num a => twins_user.Box a')


class TestRoundTrip(CorpusTestCase):
  '''
  The conversion rows of the design: the Curry text of the row, compiled
  through the text route, evaluates to the values of the Python call.
  '''
  def check_corpus(self, corpus):
    module = curry.import_(corpus.modulename)
    ns = Namespace(module)
    checked = 0
    for twin in corpus.twins:
      if not twin.row:
        continue
      with self.subTest(goal=twin.goal):
        call = twin.make(ns)
        self.assertEqual(call.serialized(module=corpus.modulename).text, twin.curry_text(ns))
        # The text compiles in a module of its own, so the names of the
        # twin module are qualified there.
        text = call.serialized().text
        goal = curry.compile(text, mode='expr', imports=[module])
        expected = show_values(curry.eval(goal))
        observed = show_values(call.values())
        self.assertEqual(
            normalize_values(observed), normalize_values(expected)
          , 'the values of %s differ:\n--- call:\n%s--- text:\n%s' % (text, observed, expected)
          )
        checked += 1
    self.assertGreater(checked, 0)


class TestCorpus(CorpusTestCase):
  '''The committed modules, the goldens and the Float rows.'''

  def test_modules_current(self):
    '''Every committed module is the serializer's output for the corpus.'''
    for corpus in CORPUS:
      with self.subTest(module=corpus.modulename):
        ns = namespace(corpus)
        self.assertEqual(
            readfile(corpus.filename), corpus.text(ns)
          , 'the module %s is out of date; run "python %s --write" from the '
            'tests directory' % (corpus.filename, os.path.basename(__file__))
          )

  def test_corpus_shape(self):
    '''The acceptance counts and the twins the issue names.'''
    value_twins = [t for c in CORPUS if c.values for t in c.twins]
    self.assertGreaterEqual(len(value_twins), 40)
    names = {t.name for t in value_twins}
    self.assertIn('floats', names)                   # [1, 2.5]
    self.assertIn('box', names)                      # the erased newtype
    self.assertIn('identity_run', names)             # Identity 5 through runIdentity
    self.assertIn('sum_value', names)                # a value of an earlier eval
    self.assertTrue(any(t.text is not None for t in value_twins))
    rows = [t for c in CORPUS for t in c.twins if t.row]
    self.assertGreaterEqual(len(rows), 20)
    self.assertTrue(all(t.text is None for t in rows))
    goalnames = [t.goal for t in value_twins]
    self.assertEqual(len(goalnames), len(set(goalnames)))

  def check_float_text(self):
    '''
    The raw printed text of the Float rows against the goldens, without the
    float standardization of the driver: issue #34 on the C++ backend.
    '''
    checked = 0
    for corpus in CORPUS:
      if not corpus.values:
        continue
      module = curry.import_(corpus.modulename)
      ns = Namespace(module)
      for twin in corpus.twins:
        if not twin.floats:
          continue
        goldenfile = os.path.join(SOURCE_DIR, '%s.%s.au-gen' % (corpus.modulename, twin.goal))
        oracle.divine(
            module, getattr(module, twin.goal), [SOURCE_DIR], ORACLE_TIMEOUT
          , goldenfile=goldenfile
          )
        expected = readfile(goldenfile)
        observed = show_values(twin.make(ns).values())
        self.assertEqual(
            normalize_values(observed, standardize_floats=False)
          , normalize_values(expected, standardize_floats=False)
          , 'the text of %s differs: Sprite %r, oracle %r' % (twin.goal, observed, expected)
          )
        checked += 1
    self.assertGreater(checked, 0)

  @oracle.require
  def test_float_text(self):
    # Both backends print a Float as PAKCS does since the fix of #34.
    self.check_float_text()


def _corpus_test(check, corpus):
  def test(self):
    check(self, corpus)
  test.__doc__ = 'the goals of %s' % corpus.modulename
  return test

for _corpus in CORPUS:
  setattr(TestTypes, 'test_' + _corpus.modulename, _corpus_test(TestTypes.check_corpus, _corpus))
  if any(t.row for t in _corpus.twins):
    setattr(TestRoundTrip, 'test_' + _corpus.modulename, _corpus_test(TestRoundTrip.check_corpus, _corpus))

# Regeneration
# ============
def write_modules(corpora=CORPUS):
  '''
  Writes the module of every corpus under data/curry/typed_expr/.  The
  header is written first and the module imported from it, so that the
  twins that name its declarations can be serialized and a stale goal of
  the old text cannot block the regeneration; then the whole module is
  written and imported once more, which checks that it compiles.
  '''
  def write(text):
    with open(corpus.filename, 'w', encoding='utf-8') as stream:
      stream.write(text)
  def fresh_import():
    curry.reset()
    curry.path[:] = [SOURCE_DIR] + curry.path
    return curry.import_(corpus.modulename)
  for corpus in corpora:
    old = readfile(corpus.filename) if os.path.isfile(corpus.filename) else None
    write(corpus.header)
    text = corpus.text(Namespace(fresh_import()))
    write(text)
    fresh_import()
    print('wrote' if old != text else 'unchanged', corpus.filename)

if __name__ == '__main__':
  if '--write' in sys.argv:
    write_modules()
  else:
    unittest.main()

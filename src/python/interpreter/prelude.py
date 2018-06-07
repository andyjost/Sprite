from ..icurry import *
from . import prelude_impl
from .runtime import T_FAIL, T_CHOICE, T_FWD, T_CTOR
import analysis
import operator as op

# ===================
# The Prelude module.
# ===================

def exports():
  '''
  Returns the name of each symbol that must be added to the Prelude but does
  not appear with a definition in Prelude.curry.
  '''
  # Special symbols.
  yield '_Failure'
  yield '_Choice'
  yield '_Fwd'
  yield '_PartApplic'
  # Opaque types.
  yield '[]'
  yield 'IO'
  for ty in _types_:
    name = ty.ident.basename
    if analysis.is_tuple_name(name):
      yield name
  # Helper functions.
  yield '_python_generator_'

def aliases():
  '''Returns prelude aliases.  Simply for convenience.'''
  yield 'Unit', '()'
  yield 'Cons', ':'
  yield 'Nil', '[]'

# Types.
# ======
md0 = { # Builtin type metadata.
    'py.format': '{1}'
  , 'py.topy'  : lambda node: node[1]
  # , 'py.frompy': lambda x: x[1]
  }
_types_ = [
    IType('_Failure', [IConstructor('_Failure', 0, metadata={'py.format':'failure', 'py.tag':T_FAIL})])
  , IType('_Choice', [IConstructor('_Choice', 2, metadata={'py.format':'{1} ? {2}', 'py.tag':T_CHOICE})])
  , IType('_Fwd', [IConstructor('_Fwd', 1, metadata={'py.format':'{1}', 'py.tag':T_FWD})])
  , IType('_PartApplic', [IConstructor('_PartApplic', 2, metadata={'py.tag':T_CTOR})])
  , IType('Bool', [IConstructor('True', 0), IConstructor('False', 0)])
  , IType('Char', [IConstructor('Char', 1, metadata=md0)])
  , IType('Float', [IConstructor('Float', 1, metadata=md0)])
  , IType('Int', [IConstructor('Int', 1, metadata=md0)])
  , IType('IO', [IConstructor('IO', 1)])
  ]

# List
def _listvalues(node):
  n = node[()]
  while n.info.name == ':':
    v,n = n
    yield v.info.show(v)

def _listformat(node):
  return '[%s]' % ', '.join(_listvalues(node))

_types_.append(
    IType('[]', [
        IConstructor(':', 2, metadata={'py.format':_listformat})
      , IConstructor('[]', 0, metadata={'py.format':_listformat})
      ])
  )
del _listformat

# Tuples
MAX_TUPLE_SIZE = 15
Unit = IType('()', [IConstructor('()', 0, metadata={'py.format':'()'})])
_types_.append(Unit)
for i in range(2, MAX_TUPLE_SIZE):
  name = '(%s)' % (','*(i-1))
  Tuple = IType(name, [
      IConstructor(
          name
        , i
        , metadata={
              'py.format':
                  '(%s)' % ', '.join(['{%d}' % j for j in range(1,i+1)])
            }
        )
    ])
  _types_.append(Tuple)

# Functions.
# ==========
_functions_ = [
    IFunction('_python_generator_', 1, metadata={'py.func':prelude_impl._python_generator_})
  , IFunction('*', 2, metadata={'py.primfunc':op.mul})
  , IFunction('+', 2, metadata={'py.primfunc':op.add})
  , IFunction('-', 2, metadata={'py.primfunc':op.sub})
  , IFunction('==', 2, metadata={'py.primfunc':op.eq})
  , IFunction('/=', 2, metadata={'py.primfunc':op.ne})
  , IFunction('<', 2, metadata={'py.primfunc':op.lt})
  , IFunction('>', 2, metadata={'py.primfunc':op.gt})
  , IFunction('<=', 2, metadata={'py.primfunc':op.le})
  , IFunction('>=', 2, metadata={'py.primfunc':op.ge})
  , IFunction('&&', 2, metadata={'py.primfunc':op.and_})
  , IFunction('||', 2, metadata={'py.primfunc':op.or_})
	# The following are defined in the Prelude as pure Curry, but have a better
  # implementation here.
  , IFunction('negate', 1, metadata={'py.primfunc':op.neg})

# ====== Missing from the following ======
# --- Integer division. The value is the integer quotient of its arguments
# --- and always truncated towards negative infinity.
# --- Thus, the value of <code>13 `div` 5</code> is <code>2</code>,
# --- and the value of <code>-15 `div` 4</code> is <code>-4</code>.
# div   :: Int -> Int -> Int
# div external
  , IFunction('div', 2, metadata={'py.primfunc':op.floordiv})
#
# --- Integer remainder. The value is the remainder of the integer division and
# --- it obeys the rule <code>x `mod` y = x - y * (x `div` y)</code>.
# --- Thus, the value of <code>13 `mod` 5</code> is <code>3</code>,
# --- and the value of <code>-15 `mod` 4</code> is <code>-3</code>.
# mod   :: Int -> Int -> Int
# mod external
  , IFunction('mod', 2, metadata={'py.primfunc':lambda x, y: x - y * op.floordiv(x,y)})
# --- Integer division. The value is the integer quotient of its arguments
# --- and always truncated towards zero.
# --- Thus, the value of <code>13 `quot` 5</code> is <code>2</code>,
# --- and the value of <code>-15 `quot` 4</code> is <code>-3</code>.
# quot   :: Int -> Int -> Int
# quot external
  , IFunction('quot', 2, metadata={'py.primfunc':lambda x, y: int(op.truediv(x, y))})
#
# --- Integer remainder. The value is the remainder of the integer division and
# --- it obeys the rule <code>x `rem` y = x - y * (x `quot` y)</code>.
# --- Thus, the value of <code>13 `rem` 5</code> is <code>3</code>,
# --- and the value of <code>-15 `rem` 4</code> is <code>-3</code>.
# rem   :: Int -> Int -> Int
# rem external
  , IFunction('rem', 2, metadata={'py.primfunc':lambda x, y: x - y * int(op.truediv(x, y))})
  , IFunction('prim_negateFloat', 1, metadata={'py.primfunc':op.neg})
# --- Evaluates the argument to head normal form and returns it.
# --- Suspends until the result is bound to a non-variable term.
# ensureNotFree :: a -> a
# ensureNotFree external
  , IFunction('ensureNotFree', 1, metadata={'py.func':prelude_impl.ensureNotFree})
# --- Right-associative application with strict evaluation of its argument
# --- to head normal form.
# ($!)    :: (a -> b) -> a -> b
# ($!) external
  , IFunction('$!', 2, metadata={'py.func':prelude_impl.apply_hnf})
#
# --- Right-associative application with strict evaluation of its argument
# --- to normal form.
# ($!!)   :: (a -> b) -> a -> b
# ($!!) external
  , IFunction('$!!', 2, metadata={'py.func':prelude_impl.apply_nf})
# --- Right-associative application with strict evaluation of its argument
# --- to ground normal form.
# ($##)   :: (a -> b) -> a -> b
# ($##) external
  , IFunction('$##', 2, metadata={'py.func':prelude_impl.apply_gnf})
#
# prim_error    :: String -> _
# prim_error external
#
  , IFunction('prim_error', 1, metadata={'py.func':prelude_impl.error})
# --- A non-reducible polymorphic function.
# --- It is useful to express a failure in a search branch of the execution.
# --- It could be defined by: `failed = head []`
# failed :: _
# failed external
  , IFunction('failed', 0, metadata={'py.func':prelude_impl.failed})
#
# --- The equational constraint.
# --- `(e1 =:= e2)` is satisfiable if both sides `e1` and `e2` can be
# --- reduced to a unifiable data term (i.e., a term without defined
# --- function symbols).
# (=:=)   :: a -> a -> Bool
# (=:=) external
#
# --- Concurrent conjunction.
# --- An expression like `(c1 & c2)` is evaluated by evaluating
# --- the `c1` and `c2` in a concurrent manner.
# (&)     :: Bool -> Bool -> Bool
# (&) external
#
# --- Comparison of arbitrary ground data terms.
# --- Data constructors are compared in the order of their definition
# --- in the datatype declarations and recursively in the arguments.
# compare :: a -> a -> Ordering
# compare external
  , IFunction('compare', 2, metadata={'py.func':prelude_impl.compare})
#
# --- Converts a character into its ASCII value.
# ord :: Char -> Int
# ord external
  , IFunction('ord', 1, metadata={'py.primfunc':ord})
#
# --- Converts an ASCII value into a character.
# chr :: Int -> Char
# chr external
  , IFunction('chr', 1, metadata={'py.primfunc':chr})
# --- Sequential composition of actions.
# --- @param a - An action
# --- @param fa - A function from a value into an action
# --- @return An action that first performs a (yielding result r)
# ---         and then performs (fa r)
# (>>=)             :: IO a -> (a -> IO b) -> IO b
# (>>=) external
  , IFunction('>>=', 2, metadata={'py.func':prelude_impl.compose_io})
#
# --- The empty action that directly returns its argument.
# return            :: a -> IO a
# return external
  , IFunction('return', 1, metadata={'py.func':prelude_impl.return_})
#
# prim_putChar           :: Char -> IO ()
# prim_putChar external
  , IFunction('prim_putChar', 1, metadata={'py.func':prelude_impl.putChar})
#
# --- An action that reads a character from standard output and returns it.
# getChar           :: IO Char
# getChar external
  , IFunction('getChar', 0, metadata={'py.func':prelude_impl.getChar})
#
# prim_readFile          :: String -> IO String
# prim_readFile external
  , IFunction('prim_readFile', 1, metadata={'py.func':prelude_impl.readFile})
# -- for internal implementation of readFile:
# prim_readFileContents          :: String -> String
# prim_readFileContents external
#
# prim_writeFile         :: String -> String -> IO ()
# prim_writeFile external
#
# prim_appendFile         :: String -> String -> IO ()
# prim_appendFile external
#
# --- Catches a possible error or failure during the execution of an
# --- I/O action. `(catch act errfun)` executes the I/O action
# --- `act`. If an exception or failure occurs
# --- during this I/O action, the function `errfun` is applied
# --- to the error value.
# catch :: IO a -> (IOError -> IO a) -> IO a
# catch external
#
# prim_show    :: _ -> String
# prim_show external
#
# -- Non-determinism and free variables:
#
# --- Non-deterministic choice _par excellence_.
# --- The value of `x ? y` is either `x` or `y`.
# --- @param x - The right argument.
# --- @param y - The left argument.
# --- @return either `x` or `y` non-deterministically.
# (?)   :: a -> a -> a
# (?) external
#
# -- Representation of higher-order applications in FlatCurry.
# apply :: (a -> b) -> a -> b
# apply external
  , IFunction('apply', 2, metadata={'py.func':prelude_impl.apply})

#
# -- Only for internal use:
# -- Representation of conditional rules in FlatCurry.
# cond :: Bool -> a -> a
# cond external
#
# -- Only for internal use:
# -- letrec ones (1:ones) -> bind ones to (1:ones)
# letrec :: a -> a -> Bool
# letrec external
#
# --- Non-strict equational constraint. Used to implement functional patterns.
# (=:<=) :: a -> a -> Bool
# (=:<=) external
#
# --- Non-strict equational constraint for linear functional patterns.
# --- Thus, it must be ensured that the first argument is always (after evalutation
# --- by narrowing) a linear pattern. Experimental.
# (=:<<=) :: a -> a -> Bool
# (=:<<=) external
#
# --- internal function to implement =:<=
# ifVar :: _ -> a -> a -> a
# ifVar external
#
# --- internal operation to implement failure reporting
# failure :: _ -> _ -> _
# failure external
  ]
Prelude = IModule(
    name='Prelude', imports=[], types=_types_, functions=_functions_
  )


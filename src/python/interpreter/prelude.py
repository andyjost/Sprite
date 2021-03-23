from .. import icurry
from . import prelude_impl as impl
from . import typecheckers as tc
from . import runtime
from .. import inspect
import operator as op

def exports():
  '''
  Returns the name of each symbol that must be added to the Prelude but does
  not appear with a definition in Prelude.curry.
  '''
  # Special symbols.
  yield '_Failure'
  yield '_Binding'
  yield '_Free'
  yield '_Fwd'
  yield '_Choice'
  yield '_PartApplic'
  # Opaque types.
  yield '[]'
  yield 'IO'
  for ty in _types_:
    name = ty.name
    if inspect.is_tuple_name(name):
      yield name
  yield '(->)'
  # Helper functions.
  yield '_PyGenerator'
  # Clobber the definition of Prelude.? with Sprite's own.
  yield '?'

def aliases():
  '''Returns prelude aliases.  Simply for convenience.'''
  yield 'Unit', '()'
  yield 'Cons', ':'
  yield 'Nil', '[]'


# Types.
# ======
def _T(name, constructors):
  return icurry.IDataType('Prelude.' + name, constructors)
def _C(name, *args, **kwds):
  return icurry.IConstructor('Prelude.' + name, *args, **kwds)

_types_ = [
    _T('_Failure'   , [_C('_Failure', 0, metadata={'py.format':'failure', 'py.tag':runtime.T_FAIL})])
    # A binding is a pair consisting of a Boolean result and pair of equivalent
    # expressions.  After lifting the binding, the result takes its place.  The
    # equivalent expressions consist of a free variable on the left and, on the
    # right, either a different free variable (regular binding) or arbitrary
    # expression (lazy binding).  For example, ``_Binding True (x,y)`` has
    # value True (indicating the binding succeeded) and specifies that free
    # variables x and y are equivalent in this context.
  , _T('_Binding'   , [_C('_Binding', 2, metadata={'py.tag':runtime.T_BIND, 'py.typecheck':tc.Binding})])
    # Free variables have two successors, one for the variable ID (Int) and one
    # for the generator.  The second slot is initially set to Prelude.().  On
    # instantiation, it is replaced with a generator.
  , _T('_Free'      , [_C('_Free', 2, metadata={'py.format':'freevar({1})', 'py.tag':runtime.T_FREE})])
  , _T('_Fwd'       , [_C('_Fwd', 1, metadata={'py.format':'{1}', 'py.tag':runtime.T_FWD})])
  , _T('_Choice'    , [_C('_Choice', 3, metadata={'py.tag':runtime.T_CHOICE})])
  , _T('_PartApplic', [_C('_PartApplic', 2, metadata={'py.format': '{2}', 'py.tag':runtime.T_CTOR})])
  , _T('Bool'       , [_C('True', 0), _C('False', 0)])
  , _T('Char'       , [_C('Char', 1, metadata={'py.format': '{1}', 'py.typecheck': tc.Char})])
  , _T('Float'      , [_C('Float', 1, metadata={'py.format': '{1}', 'py.typecheck': tc.Float})])
  , _T('Int'        , [_C('Int', 1, metadata={'py.format': '{1}', 'py.typecheck': tc.Int})])
  , _T('IO'         , [_C('IO', 1)])
  , _T('(->)'       , [_C('->', 2)])
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
    _T('[]', [
        _C(':' , 2, metadata={'py.format':_listformat})
      , _C('[]', 0, metadata={'py.format':_listformat})
      ])
  )
del _listformat

# Tuples
MAX_TUPLE_SIZE = 15
Unit = _T('()', [_C('()', 0, metadata={'py.format':'()'})])
_types_.append(Unit)
for i in range(2, MAX_TUPLE_SIZE):
  name = '(%s)' % (','*(i-1))
  Tuple = _T(name, [
      _C(
          name
        , i
        , metadata={
              'py.format':
                  '(%s)' % ', '.join(['{%d}' % j for j in range(1,i+1)])
            }
        )
    ])
  _types_.append(Tuple)

def _divMod_impl(x, y):
  # divMod_ x y = (x `div` y, x `mod` y)
  d = op.floordiv(x, y)
  m = x - y * d
  return d, m

def _quotRem_impl(x, y):
  # quotRem_ x y = (x `quot` y, x `rem` y)
  q = int(op.truediv(x, y))
  r = x - y * q
  return q, r

# Functions.
# ==========
def _F(name, *args, **kwds):
  return icurry.IFunction('Prelude.' + name, *args, **kwds)

_functions_ = [
    _F('_PyGenerator', 1
        , metadata={'py.boxedfunc':impl._PyGenerator}
        )
  , _F('+$', 2, metadata={'py.unboxedfunc':op.add}) # Int addition
  , _F('-$', 2, metadata={'py.unboxedfunc':op.sub}) # Int subtraction
  , _F('*$', 2, metadata={'py.unboxedfunc':op.mul}) # Int multiplication
  , _F('prim_Float_plus', 2, metadata={'py.unboxedfunc':op.add}) # Float addition
  , _F('prim_Float_minus', 2, metadata={'py.unboxedfunc':op.sub}) # Float subtraction
  , _F('prim_Float_times', 2, metadata={'py.unboxedfunc':op.mul}) # Float multiplication
  , _F('prim_Float_div', 2, metadata={'py.unboxedfunc':op.truediv}) # Float division
  # , _F('==', 2, metadata={'py.rawfunc':impl.equals})
  , _F('eqInt', 2, metadata={'py.unboxedfunc':op.eq})
  , _F('eqChar', 2, metadata={'py.unboxedfunc':op.eq})
  , _F('eqFloat', 2, metadata={'py.unboxedfunc':op.eq})
  , _F('ltEqInt', 2, metadata={'py.unboxedfunc':op.le})
  , _F('ltEqChar', 2, metadata={'py.unboxedfunc':op.le})
  , _F('ltEqFloat', 2, metadata={'py.unboxedfunc':op.le})
# --- Integer division. The value is the integer quotient of its arguments
# --- and always truncated towards negative infinity.
# --- Thus, the value of <code>13 `div` 5</code> is <code>2</code>,
# --- and the value of <code>-15 `div` 4</code> is <code>-4</code>.
# div_   :: Int -> Int -> Int
  , _F('div_', 2, metadata={'py.unboxedfunc':op.floordiv})
#
# --- Integer remainder. The value is the remainder of the integer division and
# --- it obeys the rule <code>x `mod` y = x - y * (x `div` y)</code>.
# --- Thus, the value of <code>13 `mod` 5</code> is <code>3</code>,
# --- and the value of <code>-15 `mod` 4</code> is <code>-3</code>.
# mod_   :: Int -> Int -> Int
  , _F('mod_', 2, metadata={'py.unboxedfunc':lambda x, y: x - y * op.floordiv(x,y)})
# --- Integer division. The value is the integer quotient of its arguments
# --- and always truncated towards zero.
# --- Thus, the value of <code>13 `quot` 5</code> is <code>2</code>,
# --- and the value of <code>-15 `quot` 4</code> is <code>-3</code>.
# quot_   :: Int -> Int -> Int
  , _F('quot_', 2, metadata={'py.unboxedfunc':lambda x, y: int(op.truediv(x, y))})
#
# --- Integer remainder. The value is the remainder of the integer division and
# --- it obeys the rule <code>x `rem` y = x - y * (x `quot` y)</code>.
# --- Thus, the value of <code>13 `rem` 5</code> is <code>3</code>,
# --- and the value of <code>-15 `rem` 4</code> is <code>-3</code>.
# rem_   :: Int -> Int -> Int
  , _F('rem_', 2, metadata={'py.unboxedfunc':lambda x, y: x - y * int(op.truediv(x, y))})

# --- Returns an integer (quotient,remainder) pair.
# --- The value is the integer quotient of its arguments
# --- and always truncated towards negative infinity.
# divMod_ :: Int -> Int -> (Int, Int)
  , _F('divMod_', 2, metadata={'py.unboxedfunc':_divMod_impl})
#
# --- Returns an integer (quotient,remainder) pair.
# --- The value is the integer quotient of its arguments
# --- and always truncated towards zero.
# quotRem_ :: Int -> Int -> (Int, Int)
  , _F('quotRem_', 2, metadata={'py.unboxedfunc':_quotRem_impl})
  , _F('negateFloat', 1, metadata={'py.unboxedfunc':op.neg})
# --- Evaluates the argument to head normal form and returns it.
# --- Suspends until the result is bound to a non-variable term.
# ensureNotFree :: a -> a
  , _F('ensureNotFree', 1, metadata={'py.boxedfunc':impl.ensureNotFree})
# --- Right-associative application with strict evaluation of its argument
# --- to head normal form.
# ($!)    :: (a -> b) -> a -> b
  , _F('$!', 2, metadata={'py.rawfunc':impl.apply_hnf})
#
# --- Right-associative application with strict evaluation of its argument
# --- to normal form.
# ($!!)   :: (a -> b) -> a -> b
  , _F('$!!', 2, metadata={'py.rawfunc':impl.apply_nf})
# --- Right-associative application with strict evaluation of its argument
# --- to ground normal form.
# ($##)   :: (a -> b) -> a -> b
  , _F('$##', 2, metadata={'py.rawfunc':impl.apply_gnf})
#
# prim_error    :: String -> _
#
  , _F('prim_error', 1, metadata={'py.boxedfunc':impl.error})
# --- A non-reducible polymorphic function.
# --- It is useful to express a failure in a search branch of the execution.
# --- It could be defined by: `failed = head []`
# failed :: _
  , _F('failed', 0, metadata={'py.boxedfunc':impl.failed})
#
# --- The equational constraint.
# --- `(e1 =:= e2)` is satisfiable if both sides `e1` and `e2` can be
# --- reduced to a unifiable data term (i.e., a term without defined
# --- function symbols).
# (=:=)   :: a -> a -> Bool
  , _F('=:=', 2, metadata={'py.rawfunc':impl.eq_constr})
#
# --- Concurrent conjunction.
# --- An expression like `(c1 & c2)` is evaluated by evaluating
# --- the `c1` and `c2` in a concurrent manner.
# (&)     :: Bool -> Bool -> Bool
  , _F('&', 2, metadata={'py.rawfunc':impl.concurrent_and})
#
# --- Converts a character into its ASCII value.
# ord :: Char -> Int
  , _F('prim_ord', 1, metadata={'py.unboxedfunc':ord})
#
# --- Converts an ASCII value into a character.
# chr :: Int -> Char
  , _F('prim_chr', 1, metadata={'py.unboxedfunc':chr})
  , _F('prim_i2f', 1, metadata={'py.unboxedfunc':float})
# --- Sequential composition of actions.
# --- @param a - An action
# --- @param fa - A function from a value into an action
# --- @return An action that first performs a (yielding result r)
# ---         and then performs (fa r)
# (>>=$)             :: IO a -> (a -> IO b) -> IO b
  , _F('>>=$', 2, metadata={'py.rawfunc':impl.compose_io})
#
# prim_readNatLiteral :: String -> [(Int,String)]
  , _F('prim_readNatLiteral', 1, metadata={'py.boxedfunc':impl.readNatLiteral})
# prim_readFloatLiteral :: String -> [(Int,String)]
  , _F('prim_readFloatLiteral', 1, metadata={'py.boxedfunc':impl.readFloatLiteral})
# prim_readCharLiteral :: String -> [(Int,String)]
  , _F('prim_readCharLiteral', 1, metadata={'py.boxedfunc':impl.readCharLiteral})
# prim_readStringLiteral :: String -> [(Int,String)]
  , _F('prim_readStringLiteral', 1, metadata={'py.boxedfunc':impl.readStringLiteral})

#
# --- The empty action that directly returns its argument.
# returnIO            :: a -> IO a
  , _F('returnIO', 1, metadata={'py.boxedfunc':impl.returnIO})
#
# prim_putChar           :: Char -> IO ()
  , _F('prim_putChar', 1, metadata={'py.boxedfunc':impl.putChar})
#
# --- An action that reads a character from standard output and returns it.
# getChar           :: IO Char
  , _F('getChar', 0, metadata={'py.boxedfunc':impl.getChar})
#
# prim_readFile          :: String -> IO String
  , _F('prim_readFile', 1, metadata={'py.boxedfunc':impl.readFile})
# -- for internal implementation of readFile:
# prim_readFileContents          :: String -> String
#
# prim_writeFile         :: String -> String -> IO ()
#
# prim_appendFile         :: String -> String -> IO ()
#
# --- Catches a possible error or failure during the execution of an
# --- I/O action. `(catch act errfun)` executes the I/O action
# --- `act`. If an exception or failure occurs
# --- during this I/O action, the function `errfun` is applied
# --- to the error value.
# catch :: IO a -> (IOError -> IO a) -> IO a
#
# prim_show    :: _ -> String
  , _F('prim_show', 1, metadata={'py.boxedfunc':impl.show})
#
# -- Non-determinism and free variables:
#
# --- Non-deterministic choice _par excellence_.
# --- The value of `x ? y` is either `x` or `y`.
# --- @param x - The right argument.
# --- @param y - The left argument.
# --- @return either `x` or `y` non-deterministically.
# (?)   :: a -> a -> a
  , _F('?', 2, metadata={'py.rawfunc':impl.choice, 'py.format':'{1} ? {2}'})
#
# -- Representation of higher-order applications in FlatCurry.
# apply :: (a -> b) -> a -> b
  , _F('apply', 2, metadata={'py.rawfunc':impl.apply})

#
# -- Only for internal use:
# -- Representation of conditional rules in FlatCurry.
# cond :: Bool -> a -> a
  , _F('cond', 2, metadata={'py.rawfunc':impl.cond})
#
# -- Only for internal use:
# -- letrec ones (1:ones) -> bind ones to (1:ones)
# -- PAKCS only
# letrec :: a -> a -> Bool
#
# --- Non-strict equational constraint. Used to implement functional patterns.
# (=:<=) :: a -> a -> Bool
  , _F('=:<=', 2, metadata={'py.rawfunc':impl.eq_constr_lazy})
#
# --- Non-strict equational constraint for linear functional patterns.
# --- Thus, it must be ensured that the first argument is always (after evalutation
# --- by narrowing) a linear pattern. Experimental.
# (=:<<=) :: a -> a -> Bool
#
# --- internal function to implement =:<=
# ifVar :: _ -> a -> a -> a
#
# --- internal operation to implement failure reporting
# failure :: _ -> _ -> _
#

  ]
Prelude = icurry.IModule(
    name='Prelude', imports=[], types=_types_, functions=_functions_
  )

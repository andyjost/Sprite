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
    name = ty.ident.basename
    if inspect.is_tuple_name(name):
      yield name
  yield '(->)'
  # Helper functions.
  yield '_PyGenerator'
  # Clobber the definition of Prelude.? with Sprite's own.
  yield 'Prelude.?'

def aliases():
  '''Returns prelude aliases.  Simply for convenience.'''
  yield 'Unit', '()'
  yield 'Cons', ':'
  yield 'Nil', '[]'

# Types.
# ======
_types_ = [
    icurry.IType('_Failure', [icurry.IConstructor('_Failure', 0, metadata={'py.format':'failure', 'py.tag':runtime.T_FAIL})])
    # A binding is a pair consisting of a Boolean result and pair of equivalent
    # expressions.  After lifting the binding, the result takes its place.  The
    # equivalent expressions consist of a free variable on the left and, on the
    # right, either a different free variable (regular binding) or arbitrary
    # expression (lazy binding).  For example, ``_Binding True (x,y)`` has
    # value True (indicating the binding succeeded) and specifies that free
    # variables x and y are equivalent in this context.
  , icurry.IType('_Binding', [icurry.IConstructor('_Binding', 2, metadata={'py.tag':runtime.T_BIND, 'py.typecheck':tc.Binding})])
    # Free variables have two successors, one for the variable ID (Int) and one
    # for the instance.  The instance is initially set to Prelude.().  On
    # instantiation, it is replaced with a generator.  Note that () is not a
    # valid generator.
  , icurry.IType('_Free', [icurry.IConstructor('_Free', 2, metadata={'py.format':'freevar({1})', 'py.tag':runtime.T_FREE})])
  , icurry.IType('_Fwd', [icurry.IConstructor('_Fwd', 1, metadata={'py.format':'{1}', 'py.tag':runtime.T_FWD})])
  , icurry.IType('_Choice', [icurry.IConstructor('_Choice', 3, metadata={'py.tag':runtime.T_CHOICE})])
  , icurry.IType('_PartApplic', [icurry.IConstructor('_PartApplic', 2, metadata={'py.format': '{2}', 'py.tag':runtime.T_CTOR})])
  , icurry.IType('Bool', [icurry.IConstructor('True', 0), icurry.IConstructor('False', 0)])
  , icurry.IType('Char', [icurry.IConstructor('Char', 1, metadata={'py.format': '{1}', 'py.typecheck': tc.Char})])
  , icurry.IType('Float', [icurry.IConstructor('Float', 1, metadata={'py.format': '{1}', 'py.typecheck': tc.Float})])
  , icurry.IType('Int', [icurry.IConstructor('Int', 1, metadata={'py.format': '{1}', 'py.typecheck': tc.Int})])
  , icurry.IType('IO', [icurry.IConstructor('IO', 1)])
  , icurry.IType('(->)', [icurry.IConstructor('->', 2)])
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
    icurry.IType('[]', [
        icurry.IConstructor(':', 2, metadata={'py.format':_listformat})
      , icurry.IConstructor('[]', 0, metadata={'py.format':_listformat})
      ])
  )
del _listformat

# Tuples
MAX_TUPLE_SIZE = 15
Unit = icurry.IType('()', [icurry.IConstructor('()', 0, metadata={'py.format':'()'})])
_types_.append(Unit)
for i in range(2, MAX_TUPLE_SIZE):
  name = '(%s)' % (','*(i-1))
  Tuple = icurry.IType(name, [
      icurry.IConstructor(
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
_functions_ = [
    icurry.IFunction('_PyGenerator', 1
        , metadata={'py.boxedfunc':impl._PyGenerator}
        )
  , icurry.IFunction('+$', 2, metadata={'py.unboxedfunc':op.add}) # Int addition
  , icurry.IFunction('-$', 2, metadata={'py.unboxedfunc':op.sub}) # Int subtraction
  , icurry.IFunction('*$', 2, metadata={'py.unboxedfunc':op.mul}) # Int multiplication
  , icurry.IFunction('prim_Float_plus', 2, metadata={'py.unboxedfunc':op.add}) # Float addition
  , icurry.IFunction('prim_Float_minus', 2, metadata={'py.unboxedfunc':op.sub}) # Float subtraction
  , icurry.IFunction('prim_Float_times', 2, metadata={'py.unboxedfunc':op.mul}) # Float multiplication
  , icurry.IFunction('prim_Float_div', 2, metadata={'py.unboxedfunc':op.truediv}) # Float division
  # , icurry.IFunction('==', 2, metadata={'py.rawfunc':impl.equals})
  , icurry.IFunction('eqInt', 2, metadata={'py.unboxedfunc':op.eq})
  , icurry.IFunction('eqChar', 2, metadata={'py.unboxedfunc':op.eq})
  , icurry.IFunction('eqFloat', 2, metadata={'py.unboxedfunc':op.eq})
  , icurry.IFunction('ltEqInt', 2, metadata={'py.unboxedfunc':op.le})
  , icurry.IFunction('ltEqChar', 2, metadata={'py.unboxedfunc':op.le})
  , icurry.IFunction('ltEqFloat', 2, metadata={'py.unboxedfunc':op.le})
# --- Integer division. The value is the integer quotient of its arguments
# --- and always truncated towards negative infinity.
# --- Thus, the value of <code>13 `div` 5</code> is <code>2</code>,
# --- and the value of <code>-15 `div` 4</code> is <code>-4</code>.
# div_   :: Int -> Int -> Int
  , icurry.IFunction('div_', 2, metadata={'py.unboxedfunc':op.floordiv})
#
# --- Integer remainder. The value is the remainder of the integer division and
# --- it obeys the rule <code>x `mod` y = x - y * (x `div` y)</code>.
# --- Thus, the value of <code>13 `mod` 5</code> is <code>3</code>,
# --- and the value of <code>-15 `mod` 4</code> is <code>-3</code>.
# mod_   :: Int -> Int -> Int
  , icurry.IFunction('mod_', 2, metadata={'py.unboxedfunc':lambda x, y: x - y * op.floordiv(x,y)})
# --- Integer division. The value is the integer quotient of its arguments
# --- and always truncated towards zero.
# --- Thus, the value of <code>13 `quot` 5</code> is <code>2</code>,
# --- and the value of <code>-15 `quot` 4</code> is <code>-3</code>.
# quot_   :: Int -> Int -> Int
  , icurry.IFunction('quot_', 2, metadata={'py.unboxedfunc':lambda x, y: int(op.truediv(x, y))})
#
# --- Integer remainder. The value is the remainder of the integer division and
# --- it obeys the rule <code>x `rem` y = x - y * (x `quot` y)</code>.
# --- Thus, the value of <code>13 `rem` 5</code> is <code>3</code>,
# --- and the value of <code>-15 `rem` 4</code> is <code>-3</code>.
# rem_   :: Int -> Int -> Int
  , icurry.IFunction('rem_', 2, metadata={'py.unboxedfunc':lambda x, y: x - y * int(op.truediv(x, y))})

# --- Returns an integer (quotient,remainder) pair.
# --- The value is the integer quotient of its arguments
# --- and always truncated towards negative infinity.
# divMod_ :: Int -> Int -> (Int, Int)
  , icurry.IFunction('divMod_', 2, metadata={'py.unboxedfunc':_divMod_impl})
#
# --- Returns an integer (quotient,remainder) pair.
# --- The value is the integer quotient of its arguments
# --- and always truncated towards zero.
# quotRem_ :: Int -> Int -> (Int, Int)
  , icurry.IFunction('quotRem_', 2, metadata={'py.unboxedfunc':_quotRem_impl})
  , icurry.IFunction('negateFloat', 1, metadata={'py.unboxedfunc':op.neg})
# --- Evaluates the argument to head normal form and returns it.
# --- Suspends until the result is bound to a non-variable term.
# ensureNotFree :: a -> a
  , icurry.IFunction('ensureNotFree', 1, metadata={'py.boxedfunc':impl.ensureNotFree})
# --- Right-associative application with strict evaluation of its argument
# --- to head normal form.
# ($!)    :: (a -> b) -> a -> b
  , icurry.IFunction('$!', 2, metadata={'py.rawfunc':impl.apply_hnf})
#
# --- Right-associative application with strict evaluation of its argument
# --- to normal form.
# ($!!)   :: (a -> b) -> a -> b
  , icurry.IFunction('$!!', 2, metadata={'py.rawfunc':impl.apply_nf})
# --- Right-associative application with strict evaluation of its argument
# --- to ground normal form.
# ($##)   :: (a -> b) -> a -> b
  , icurry.IFunction('$##', 2, metadata={'py.rawfunc':impl.apply_gnf})
#
# prim_error    :: String -> _
#
  , icurry.IFunction('prim_error', 1, metadata={'py.boxedfunc':impl.error})
# --- A non-reducible polymorphic function.
# --- It is useful to express a failure in a search branch of the execution.
# --- It could be defined by: `failed = head []`
# failed :: _
  , icurry.IFunction('failed', 0, metadata={'py.boxedfunc':impl.failed})
#
# --- The equational constraint.
# --- `(e1 =:= e2)` is satisfiable if both sides `e1` and `e2` can be
# --- reduced to a unifiable data term (i.e., a term without defined
# --- function symbols).
# (=:=)   :: a -> a -> Bool
  , icurry.IFunction('=:=', 2, metadata={'py.rawfunc':impl.eq_constr})
#
# --- Concurrent conjunction.
# --- An expression like `(c1 & c2)` is evaluated by evaluating
# --- the `c1` and `c2` in a concurrent manner.
# (&)     :: Bool -> Bool -> Bool
  , icurry.IFunction('&', 2, metadata={'py.rawfunc':impl.concurrent_and})
#
# --- Converts a character into its ASCII value.
# ord :: Char -> Int
  , icurry.IFunction('prim_ord', 1, metadata={'py.unboxedfunc':ord})
#
# --- Converts an ASCII value into a character.
# chr :: Int -> Char
  , icurry.IFunction('prim_chr', 1, metadata={'py.unboxedfunc':chr})
  , icurry.IFunction('prim_i2f', 1, metadata={'py.unboxedfunc':float})
# --- Sequential composition of actions.
# --- @param a - An action
# --- @param fa - A function from a value into an action
# --- @return An action that first performs a (yielding result r)
# ---         and then performs (fa r)
# (>>=$)             :: IO a -> (a -> IO b) -> IO b
  , icurry.IFunction('>>=$', 2, metadata={'py.rawfunc':impl.compose_io})
#
# prim_readNatLiteral :: String -> [(Int,String)]
  , icurry.IFunction('prim_readNatLiteral', 1, metadata={'py.boxedfunc':impl.readNatLiteral})
# prim_readFloatLiteral :: String -> [(Int,String)]
  , icurry.IFunction('prim_readFloatLiteral', 1, metadata={'py.boxedfunc':impl.readFloatLiteral})
# prim_readCharLiteral :: String -> [(Int,String)]
  , icurry.IFunction('prim_readCharLiteral', 1, metadata={'py.boxedfunc':impl.readCharLiteral})
# prim_readStringLiteral :: String -> [(Int,String)]
  , icurry.IFunction('prim_readStringLiteral', 1, metadata={'py.boxedfunc':impl.readStringLiteral})

#
# --- The empty action that directly returns its argument.
# returnIO            :: a -> IO a
  , icurry.IFunction('returnIO', 1, metadata={'py.boxedfunc':impl.returnIO})
#
# prim_putChar           :: Char -> IO ()
  , icurry.IFunction('prim_putChar', 1, metadata={'py.boxedfunc':impl.putChar})
#
# --- An action that reads a character from standard output and returns it.
# getChar           :: IO Char
  , icurry.IFunction('getChar', 0, metadata={'py.boxedfunc':impl.getChar})
#
# prim_readFile          :: String -> IO String
  , icurry.IFunction('prim_readFile', 1, metadata={'py.boxedfunc':impl.readFile})
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
  , icurry.IFunction('prim_show', 1, metadata={'py.boxedfunc':impl.show})
#
# -- Non-determinism and free variables:
#
# --- Non-deterministic choice _par excellence_.
# --- The value of `x ? y` is either `x` or `y`.
# --- @param x - The right argument.
# --- @param y - The left argument.
# --- @return either `x` or `y` non-deterministically.
# (?)   :: a -> a -> a
  , icurry.IFunction('?', 2, metadata={'py.rawfunc':impl.choice, 'py.format':'{1} ? {2}'})
#
# -- Representation of higher-order applications in FlatCurry.
# apply :: (a -> b) -> a -> b
  , icurry.IFunction('apply', 2, metadata={'py.rawfunc':impl.apply})

#
# -- Only for internal use:
# -- Representation of conditional rules in FlatCurry.
# cond :: Bool -> a -> a
  , icurry.IFunction('cond', 2, metadata={'py.rawfunc':impl.cond})
#
# -- Only for internal use:
# -- letrec ones (1:ones) -> bind ones to (1:ones)
# -- PAKCS only
# letrec :: a -> a -> Bool
#
# --- Non-strict equational constraint. Used to implement functional patterns.
# (=:<=) :: a -> a -> Bool
  , icurry.IFunction('=:<=', 2, metadata={'py.rawfunc':impl.eq_constr_lazy})
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

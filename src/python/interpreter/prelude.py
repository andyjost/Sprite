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
  yield '_Constraint'
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
  # Helper functions.
  yield '_python_generator_'

def aliases():
  '''Returns prelude aliases.  Simply for convenience.'''
  yield 'Unit', '()'
  yield 'Cons', ':'
  yield 'Nil', '[]'

# Types.
# ======
_types_ = [
    icurry.IType('_Failure', [
        icurry.IConstructor('_Failure', 0
            , metadata={'py.format':'failure', 'py.tag':runtime.T_FAIL}
            )
      ])
    # Every constraint is a pair consisting of a result and another pair
    # describing the constraint.  For example, ``_EqVars True (x,y)`` has the
    # value True (i.e., the result of =:=, which indicates the constraint
    # succeeded) and indicates that free variables x and y are equivalent
    # within the purview of the constraint.
  , icurry.IType('_Constraint', [
        # A pair of free variables, constrained equal.
        icurry.IConstructor('_EqVars', 2
          , metadata={'py.tag':runtime.T_CONSTR, 'py.typecheck':tc.EqVars}
          )
        # A pair of choiceIDs, constrained equal.
      , icurry.IConstructor('_EqChoices', 2
          , metadata={'py.tag':runtime.T_CONSTR, 'py.typecheck':tc.EqChoices}
          )
        # A pair of (choiceID, LEFT|RIGHT)
      , icurry.IConstructor('_ChoiceConstr', 2
          , metadata={'py.tag':runtime.T_CONSTR, 'py.typecheck':tc.ChoiceConstr}
          )
      ])
    # Free variables have two successors, one for the variable ID (Int) and one
    # for the instance.  The instance is initially set to Prelude.().  On
    # instantiation, it is replaced with a generator.  Note that () is not a
    # valid generator.
  , icurry.IType('_Free', [icurry.IConstructor('_Free', 2, metadata={'py.format':'freevar({1})', 'py.tag':runtime.T_FREE})])
  , icurry.IType('_Fwd', [icurry.IConstructor('_Fwd', 1, metadata={'py.format':'{1}', 'py.tag':runtime.T_FWD})])
  , icurry.IType('_Choice', [icurry.IConstructor('_Choice', 3, metadata={'py.tag':runtime.T_CHOICE})])
  , icurry.IType('_PartApplic', [icurry.IConstructor('_PartApplic', 2, metadata={'py.tag':runtime.T_CTOR})])
  , icurry.IType('Bool', [icurry.IConstructor('True', 0), icurry.IConstructor('False', 0)])
  , icurry.IType('Char', [icurry.IConstructor('Char', 1, metadata={'py.format': '{1}', 'py.typecheck': tc.Char})])
  , icurry.IType('Float', [icurry.IConstructor('Float', 1, metadata={'py.format': '{1}', 'py.typecheck': tc.Float})])
  , icurry.IType('Int', [icurry.IConstructor('Int', 1, metadata={'py.format': '{1}', 'py.typecheck': tc.Int})])
  , icurry.IType('IO', [icurry.IConstructor('IO', 1)])
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

# Functions.
# ==========
_functions_ = [
    icurry.IFunction('_python_generator_', 1
        , metadata={'py.func':impl._python_generator_}
        )
  , icurry.IFunction('*', 2, metadata={'py.primfunc':op.mul})
  , icurry.IFunction('+', 2, metadata={'py.primfunc':op.add})
  , icurry.IFunction('-', 2, metadata={'py.primfunc':op.sub})
  , icurry.IFunction('==', 2, metadata={'py.rawfunc':impl.equals})
# --- Integer division. The value is the integer quotient of its arguments
# --- and always truncated towards negative infinity.
# --- Thus, the value of <code>13 `div` 5</code> is <code>2</code>,
# --- and the value of <code>-15 `div` 4</code> is <code>-4</code>.
# div   :: Int -> Int -> Int
# div external
  , icurry.IFunction('div', 2, metadata={'py.primfunc':op.floordiv})
#
# --- Integer remainder. The value is the remainder of the integer division and
# --- it obeys the rule <code>x `mod` y = x - y * (x `div` y)</code>.
# --- Thus, the value of <code>13 `mod` 5</code> is <code>3</code>,
# --- and the value of <code>-15 `mod` 4</code> is <code>-3</code>.
# mod   :: Int -> Int -> Int
# mod external
  , icurry.IFunction('mod', 2, metadata={'py.primfunc':lambda x, y: x - y * op.floordiv(x,y)})
# --- Integer division. The value is the integer quotient of its arguments
# --- and always truncated towards zero.
# --- Thus, the value of <code>13 `quot` 5</code> is <code>2</code>,
# --- and the value of <code>-15 `quot` 4</code> is <code>-3</code>.
# quot   :: Int -> Int -> Int
# quot external
  , icurry.IFunction('quot', 2, metadata={'py.primfunc':lambda x, y: int(op.truediv(x, y))})
#
# --- Integer remainder. The value is the remainder of the integer division and
# --- it obeys the rule <code>x `rem` y = x - y * (x `quot` y)</code>.
# --- Thus, the value of <code>13 `rem` 5</code> is <code>3</code>,
# --- and the value of <code>-15 `rem` 4</code> is <code>-3</code>.
# rem   :: Int -> Int -> Int
# rem external
  , icurry.IFunction('rem', 2, metadata={'py.primfunc':lambda x, y: x - y * int(op.truediv(x, y))})
  , icurry.IFunction('prim_negateFloat', 1, metadata={'py.primfunc':op.neg})
# --- Evaluates the argument to head normal form and returns it.
# --- Suspends until the result is bound to a non-variable term.
# ensureNotFree :: a -> a
# ensureNotFree external
  , icurry.IFunction('ensureNotFree', 1, metadata={'py.func':impl.ensureNotFree})
# --- Right-associative application with strict evaluation of its argument
# --- to head normal form.
# ($!)    :: (a -> b) -> a -> b
# ($!) external
  , icurry.IFunction('$!', 2, metadata={'py.rawfunc':impl.apply_hnf})
#
# --- Right-associative application with strict evaluation of its argument
# --- to normal form.
# ($!!)   :: (a -> b) -> a -> b
# ($!!) external
  , icurry.IFunction('$!!', 2, metadata={'py.rawfunc':impl.apply_nf})
# --- Right-associative application with strict evaluation of its argument
# --- to ground normal form.
# ($##)   :: (a -> b) -> a -> b
# ($##) external
  , icurry.IFunction('$##', 2, metadata={'py.rawfunc':impl.apply_gnf})
#
# prim_error    :: String -> _
# prim_error external
#
  , icurry.IFunction('prim_error', 1, metadata={'py.func':impl.error})
# --- A non-reducible polymorphic function.
# --- It is useful to express a failure in a search branch of the execution.
# --- It could be defined by: `failed = head []`
# failed :: _
# failed external
  , icurry.IFunction('failed', 0, metadata={'py.func':impl.failed})
#
# --- The equational constraint.
# --- `(e1 =:= e2)` is satisfiable if both sides `e1` and `e2` can be
# --- reduced to a unifiable data term (i.e., a term without defined
# --- function symbols).
# (=:=)   :: a -> a -> Bool
# (=:=) external
  , icurry.IFunction('=:=', 2, metadata={'py.rawfunc':impl.equal_constr})
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
  , icurry.IFunction('compare', 2, metadata={'py.rawfunc':impl.compare})
#
# --- Converts a character into its ASCII value.
# ord :: Char -> Int
# ord external
  , icurry.IFunction('ord', 1, metadata={'py.primfunc':ord})
#
# --- Converts an ASCII value into a character.
# chr :: Int -> Char
# chr external
  , icurry.IFunction('chr', 1, metadata={'py.primfunc':chr})
# --- Sequential composition of actions.
# --- @param a - An action
# --- @param fa - A function from a value into an action
# --- @return An action that first performs a (yielding result r)
# ---         and then performs (fa r)
# (>>=)             :: IO a -> (a -> IO b) -> IO b
# (>>=) external
  , icurry.IFunction('>>=', 2, metadata={'py.rawfunc':impl.compose_io})
#
# --- The empty action that directly returns its argument.
# return            :: a -> IO a
# return external
  , icurry.IFunction('return', 1, metadata={'py.func':impl.return_})
#
# prim_putChar           :: Char -> IO ()
# prim_putChar external
  , icurry.IFunction('prim_putChar', 1, metadata={'py.func':impl.putChar})
#
# --- An action that reads a character from standard output and returns it.
# getChar           :: IO Char
# getChar external
  , icurry.IFunction('getChar', 0, metadata={'py.func':impl.getChar})
#
# prim_readFile          :: String -> IO String
# prim_readFile external
  , icurry.IFunction('prim_readFile', 1, metadata={'py.func':impl.readFile})
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
  , icurry.IFunction('?', 2, metadata={'py.rawfunc':impl.choice, 'py.format':'{1} ? {2}'})
#
# -- Representation of higher-order applications in FlatCurry.
# apply :: (a -> b) -> a -> b
# apply external
  , icurry.IFunction('apply', 2, metadata={'py.rawfunc':impl.apply})

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
Prelude = icurry.IModule(
    name='Prelude', imports=[], types=_types_, functions=_functions_
  )


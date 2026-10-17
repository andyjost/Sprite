
class CurryError(Exception):
  '''The root of the Curry exception tree.'''

class CompileError(CurryError):
  '''Raised when an error occurs while compiling Curry code.'''

class InstantiationError(CurryError):
  '''Raised when a free variable is bound to an unboxed value.'''

class NotConstructorError(CurryError, ValueError):
  '''Raised when a non-constructor value occurs where disallowed.'''
  def __init__(self, arg):
   self.arg = arg

class ModuleLookupError(CurryError, ValueError):
  '''Raised when a Curry module is not found.'''

class SymbolLookupError(CurryError, AttributeError):
  '''Raised when a Curry symbol is not found.'''

class TypeLookupError(CurryError, AttributeError):
  '''Raised when a Curry type is not found.'''

class CurryIndexError(CurryError, IndexError):
  '''Raised when indexing into a Curry expression fails.'''
  pass

class CurryTypeError(CurryError, TypeError):
  '''Raised when a type error occurs while evaluating a Curry program.'''

class IntOverflowError(CurryError, OverflowError):
  '''An Int is outside the signed 64-bit range.'''

class NoValueError(CurryError, LookupError):
  '''Results.one found no value.'''

class ManyValuesError(CurryError, ValueError):
  '''Results.one found a second value.'''

class StaleError(CurryError, RuntimeError):
  '''An object belongs to an earlier session or module version.'''

class TimeoutError(CurryError, RuntimeError):
  pass

class PrerequisiteError(CurryError, IOError):
  '''Raised when a build prerequisite is invalid.'''

class DynloadError(CurryError, RuntimeError):
  '''Raised when a compiled Curry module cannot be loaded.'''

######
# Evaluation Errors
class EvaluationError(CurryError):
  '''Signals an error raised from a Curry program.'''
  pass

class EvaluationSuspended(EvaluationError):
  '''Evaluation failed due to suspended constraints.'''
  def __init__(self):
    EvaluationError.__init__(self, 'Evaluation Suspended!')

class MonadError(EvaluationError):
  # Prelude.IOError
  CTOR_INDEX = 0
  def __init__(self):
    EvaluationError.__init__(self, 'An IO error occurred in monadic actions!')

class UserMonadError(MonadError):
  # Prelude.UserError
  CTOR_INDEX = 1
  def __init__(self):
    EvaluationError.__init__(self, 'A user error occurred in monadic actions!')

class FailMonadError(MonadError):
  # Prelude.FailError
  CTOR_INDEX = 2
  def __init__(self):
    EvaluationError.__init__(
        self, 'A failed computation occurred in monadic actions!'
      )

class NondetMonadError(MonadError):
  # Prelude.NondetError
  # Non-determinism occurred in monadic actions.
  CTOR_INDEX = 3
  def __init__(self):
    EvaluationError.__init__(
        self, 'non-determinism in monadic actions occurred!'
      )


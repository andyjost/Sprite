
class CompileError(BaseException):
  '''Raised when an error occurs while compiling Curry code.'''

class InstantiationError(BaseException):
  '''Raised when a free variable is bound to an unboxed value.'''

class NotConstructorError(ValueError):
  '''Raised when a non-constructor value occurs where disallowed.'''
  def __init__(self, arg):
   self.arg = arg

class ModuleLookupError(ValueError):
  '''Raised when a Curry module is not found.'''

class SymbolLookupError(AttributeError):
  '''Raised when a Curry symbol is not found.'''

class TypeLookupError(AttributeError):
  '''Raised when a Curry type is not found.'''

class CurryIndexError(IndexError):
  '''Raised when indexing into a Curry expression fails.'''
  pass

class CurryTypeError(TypeError):
  '''Raised when a type error occurs while evaluating a Curry program.'''

assert 'TimeoutError' not in globals() # Python 2.x
class TimeoutError(RuntimeError):
  pass

class PrerequisiteError(IOError):
  '''Raised when a build prerequisite is invalid.'''

######
# Evaluation Errors
class EvaluationError(BaseException):
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


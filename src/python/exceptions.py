class CompileError(BaseException):
  '''Raised when an error occurs while compiling Curry code.'''

class EvaluationSuspended(BaseException):
  '''Raised when evaluation fails due to suspended constraints.'''

class InstantiationError(BaseException):
  '''Raised when a free variable is bound to an unboxed value.'''

class NotConstructorError(ValueError):
  '''Raised when a non-constructor value occurs and is disallowed.'''
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
  '''Raised when a prerequisite file is not found.'''

class ExecutionError(RuntimeError):
  '''
  The root of all exceptions represent errors in the Curry program that were
  properly handled by Sprite.
  '''
  pass

class MonadError(ExecutionError):
  # Prelude.IOError
  # An IO error occurred in monadic actions.
  CTOR_INDEX = 0

class UserMonadError(MonadError):
  # Prelude.UserError
  # A user error in monadic actions.
  CTOR_INDEX = 1

class FailMonadError(MonadError):
  # Prelude.FailError
  # A failed computation occurred in monadic actions.
  CTOR_INDEX = 2

class NondetMonadError(MonadError):
  # Prelude.NondetError
  # Non-determinism occurred in monadic actions.
  CTOR_INDEX = 3
  def __init__(self):
    RuntimeError.__init__(self, 'non-determinism in monadic actions occurred')



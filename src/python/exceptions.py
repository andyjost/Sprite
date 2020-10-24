class CompileError(BaseException):
  '''Raised when an error occurs while compiling Curry code.'''

class EvaluationSuspended(BaseException):
  '''Raised when evaluation fails due to suspended constraints.'''

class InstantiationError(BaseException):
  '''Raised when a free variable is bound to an unboxed value.'''

class ModuleLookupError(ValueError):
  '''Raised when a Curry module is not found.'''

class SymbolLookupError(AttributeError):
  '''Raised when a Curry symbol is not found.'''

class TypeLookupError(AttributeError):
  '''Raised when a Curry type is not found.'''

class CurryTypeError(TypeError):
  '''Raised when a type error occurs while evaluating a Curry program.'''

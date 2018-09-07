class CompileError(BaseException):
  '''Raised when an error occurs while compiling Curry code.'''

class EvaluationSuspended(BaseException):
  '''Raised when evaluation fails due to suspended constraints.'''

class InstantiationError(BaseException):
  '''Raised when a free variable reduces to an unboxed built-in.'''

class ModuleLookupError(AttributeError):
  '''Raised when a Curry module is not found.'''

class SymbolLookupError(AttributeError):
  '''Raised when a Curry symbol is not found.'''

class TypeLookupError(AttributeError):
  '''Raised when a Curry type is not found.'''


class ModuleLookupError(AttributeError):
  '''Raised when a Curry module is not found.'''

class SymbolLookupError(AttributeError):
  '''Raised when a Curry symbol is not found.'''

class TypeLookupError(AttributeError):
  '''Raised when a Curry type is not found.'''

class CompileError(BaseException):
  '''Raised when an error occurs while compiling Curry code.'''

class InstantiationError(BaseException):
  '''Raised when a free variable reduces to an unboxed built-in.'''


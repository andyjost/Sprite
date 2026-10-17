
class CurryError(Exception):
  '''The root of the Curry exception tree.'''

class CompileError(CurryError):
  '''Raised when an error occurs while compiling Curry code.'''
  def __init__(self, message, report=None, line=None, column=None):
    import re
    report = message if report is None else report
    match = re.search(r'(?m)^([^\n]*?\.curry):(\d+):(\d+)([^\n]*\bError:[^\n]*)', message)
    if match:
      import os
      line, column = int(match[2]), int(match[3])
      first = os.path.basename(match[1]) + ':' + match[2] + ':' + match[3] + match[4]
      following = message[match.end():].strip().splitlines()
      if first.endswith('Error:') and following:
        first += ' ' + following[0].strip()
      message = first
    CurryError.__init__(self, message.strip())
    self.report, self.line, self.column = report, line, column

class NotConstructorError(CurryError, ValueError):
  '''Raised when a non-constructor value occurs where disallowed.'''
  def __init__(self, arg):
   self.arg = arg

class ModuleLookupError(CurryError, ModuleNotFoundError):
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
  def __init__(self, lines, where=None, symbol=None, expected=None, actual=None, value=None):
    if isinstance(lines, str):
      lines = [lines]
    CurryError.__init__(self, '\n'.join(lines))
    self.lines = list(lines)
    self.where, self.symbol = where, symbol
    self.expected, self.actual, self.value = expected, actual, value

  @property
  def first_line(self):
    return self.lines[0]

class TypeSyntaxError(CurryTypeError):
  '''A type annotation cannot be parsed or has an invalid type or kind.'''

class InterfaceError(CurryTypeError):
  '''The interface of a module cannot be read.'''

class ModuleExistsError(CurryError, ValueError):
  '''A module of the given name is already loaded.'''

class LoadError(CurryError, OSError):
  '''An object could not be written, read or replaced.'''

class FlagError(CurryError, ValueError):
  '''An unknown flag or a value its validator refuses.'''

class CurryWarning(UserWarning):
  '''A warning of the front end or loader.'''

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

class SuspensionError(EvaluationError):
  '''Evaluation failed due to suspended constraints.'''
  def __init__(self, message='Evaluation suspended'):
    EvaluationError.__init__(self, message)

class DivisionByZeroError(EvaluationError, ZeroDivisionError):
  '''An integral division has a zero divisor.'''

class CurryIOError(EvaluationError, OSError):
  '''An uncaught error of an I/O action.'''
  def __str__(self):
    return str(self.args[0]) if self.args else ''

class CurryFileNotFoundError(CurryIOError, FileNotFoundError):
  '''An I/O action could not find its file.'''

class NondetError(EvaluationError):
  '''A choice occurred inside an I/O action.'''
  CTOR_INDEX = 3
  def __init__(self, message='non-determinism in monadic actions occurred!'):
    EvaluationError.__init__(self, message)

class StackLimitError(EvaluationError, RecursionError):
  '''An evaluation reached its stack limit.'''

class EvaluationTimeout(EvaluationError):
  '''An evaluation exceeded its time limit.'''

class InstantiationError(EvaluationError):
  '''A free variable of function type could not be instantiated.'''

# Internal callers use the public suspension class too.
EvaluationSuspended = SuspensionError

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

class NondetMonadError(NondetError):
  # Prelude.NondetError
  # Non-determinism occurred in monadic actions.
  CTOR_INDEX = 3
  def __init__(self):
    EvaluationError.__init__(
        self, 'non-determinism in monadic actions occurred!'
      )

def evaluation_error(message, kind='evaluation', filename=None):
  """Translate the runtime's explicit error kind at the native boundary."""
  cls = {
      'evaluation': EvaluationError, 'io': CurryIOError
    , 'file_not_found': CurryFileNotFoundError, 'nondet': NondetError
    , 'overflow': IntOverflowError, 'division': DivisionByZeroError
    , 'stack': StackLimitError
    }[kind]
  error = cls(message)
  if kind == 'file_not_found':
    error.filename = filename
  return error

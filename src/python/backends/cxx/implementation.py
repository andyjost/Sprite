'''
The implementation of a function of the C++ backend as text, for
curry.inspect.getimpl.

A function of a module compiled by g++ is read from the generated .cpp file
beside the shared object: its step function, from the banner that names the
function to the next banner.  An interpreted function (flag ``interpret``)
is the disassembly of its bytecode, with the constants the materializer kept
when it attached the code.  A built-in identifies its implementation language.
'''

from ...common import T_FUNC
from ...objects.handle import getHandle
from . import bytecode, curryrtbindings as curryrt, materialize
import os

__all__ = ['getimpl']

def getimpl(symbol):
  '''
  The code of the step function of ``symbol``, a CurryNodeInfo, as text.
  Raises ValueError when the backend has no code for it.
  '''
  info = symbol.info
  if info.tag != T_FUNC:
    raise _no_code(symbol)
  from ... import inspect
  function = inspect.geticurry(symbol)
  module = symbol.module
  if function.is_external and module is not None and \
      getHandle(module).backend_handle.get_builtin_symbol(symbol.name) is None:
    return '%s: external, not implemented (no primitive in the runtime)' % symbol.fullname
  if module is not None and \
      materialize.function_primitive(getHandle(module).backend_handle, function) is not None:
    return '%s: registered %s primitive' % (symbol.fullname, curryrt.primitive_kind(info))
  if curryrt.icurry_is_interpreted(info) or curryrt.icurry_is_jit(info):
    # The JIT compiled the bytecode; the disassembly is the code it holds.
    return _bytecode_text(symbol)
  moduleobj = symbol.module
  sofile = None if moduleobj is None else getHandle(moduleobj).sofilename
  if sofile is None:
    raise _no_code(symbol, 'its module has no compiled object')
  cppfile = os.path.splitext(sofile)[0] + '.cpp'
  if not os.path.exists(cppfile):
    raise _no_code(symbol, 'the generated file %s does not exist' % cppfile)
  text = _function_text(cppfile, symbol.fullname)
  if text is None:
    M = getHandle(moduleobj).backend_handle
    if M is not None and M.get_builtin_symbol(symbol.name) is not None:
      raise _no_code(symbol, 'it is a built-in of the C++ runtime')
    raise _no_code(symbol, 'it is not defined in %s' % cppfile)
  return text

def _no_code(symbol, reason=None):
  message = 'no implementation code available for %r' % symbol.fullname
  if reason is not None:
    message = '%s: %s' % (message, reason)
  return ValueError(message)

def _function_text(cppfile, fullname):
  '''
  The lines of the step function of ``fullname`` in a generated .cpp file:
  from its banner to the line before the next banner or section mark.  None
  when the file has no banner for the function.
  '''
  banner = '/****** %s ******/' % fullname
  lines = []
  with open(cppfile, encoding='utf-8') as stream:
    for line in stream:
      if lines:
        if line.startswith('/****** ') or line.startswith('/* SECTION:'):
          break
        lines.append(line)
      elif line.rstrip('\n') == banner:
        lines.append(line)
  while lines and not lines[-1].strip():
    lines.pop()
  return ''.join(lines) if lines else None

def _bytecode_text(symbol):
  '''
  The bytecode of an interpreted function as text: a banner, the sizes of
  the frame, and one line per instruction.  The constants are shown when
  the code attached in this process is the code the table runs.
  '''
  info = symbol.info
  bc = curryrt.icurry_bytecode(info)
  code = materialize.BYTECODE.get(symbol.fullname)
  if code is None and symbol.module is not None:
    # Images deliberately build no Python emitter objects at load. Restore
    # one only when inspection asks for its symbolic constants.
    from ...interpreter.loadsave import compilable_icurry
    interp = symbol.interpreter
    module = symbol.module
    complete = compilable_icurry(interp, module, getHandle(module).icurry)
    function = complete.functions.get(symbol.name)
    if function is not None:
      code = bytecode.compile_function(function, materialize.Materializer(interp, module))
      materialize.BYTECODE[symbol.fullname] = code
  consts = None
  if code is not None and list(code.code) == list(bc['code']):
    consts = code.consts
  lines = [
      '/****** %s ******/' % symbol.fullname
    , 'bytecode: %d units, %d constants, %d registers, %d variables, '
      'stack %d' % (
          len(bc['code']), bc['nconsts'], bc['nregs'], bc['nvars']
        , bc['nstack']
        )
    ]
  lines.extend(bytecode.disassemble(bc['code'], consts))
  return '\n'.join(lines)

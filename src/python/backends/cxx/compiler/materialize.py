'''
Code for converting the intermediate representation to executable code.
'''

from ....common import T_FUNC, F_MONADIC
from .. import cyrtbindings as cyrt
from .... import icurry
from . import render
from ....utility import encoding, filesys
import pprint, six, textwrap

__all__ = [
    'materialize_function'
  , 'materialize_function_info_stub'
  , 'materialize_type'
  ]

def materialize_function(interp, ir, debug=False, ifun=None):
  '''Materializes a C++ function from the IR.'''
  container = {}
  source = render.render(ir.lines) # Python source code for this function.
  assert ifun is not None
  srcdir = filesys.getDebugSourceDir()
  name = encoding.symbolToFilename(ifun.fullname) + '.cpp'
  srcfile = filesys.makeNewfile(srcdir, name)
  with open(srcfile, 'w') as out:
    out.write(source)
    out.write('\n\n\n')
    comment = (
        'This file was created by Sprite because %s was compiled in cxx '
        'mode.'
      ) % ifun.name
    out.write('\n'.join('// ' + line for line in textwrap.wrap(comment)))
    out.write('\n\n// Globals:\n// --------\n')
    closures = pprint.pformat(ir.closure.dict, indent=2)
    out.write('\n'.join('// ' + line for line in closures.split('\n')))
    out.write('\n\n// ICurry:\n// -------\n')
    out.write('\n'.join('// ' + line for line in str(ifun).split('\n')))
  # co = compile(source, srcfile, 'exec')
  # six.exec_(co, ir.closure.dict, container)
  # entry = list(container.values()).pop()
  source = None # FIXME
  entry.source = source
  return entry

def materialize_type(interp, itype, moduleobj, extern):
  M = moduleobj._cxx
  if M.is_builtin_type(itype.name):
    return M.get_type(itype.name)
  else:
    flags = lambda ictor: \
        icurry.metadata.getmd(ictor, extern, itype=itype).get('all.flags', 0)
    infos = [
        M.create_infotable(ictor.name, ictor.arity, tag, flags(ictor))
          for tag,ictor in enumerate(itype.constructors)
      ]
    return M.create_type(itype.name, infos)

def materialize_function_info_stub(interp, ifun, moduleobj, extern):
  M = moduleobj._cxx
  if M.is_builtin_function(ifun.name):
    return M.get_function(ifun.name)
  else:
    metadata = icurry.metadata.getmd(ifun, extern)
    return M.create_infotable(
        ifun.name
      , ifun.arity
      , T_FUNC
      , F_MONADIC if metadata.get('all.monadic') else 0
      )


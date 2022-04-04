'''
Code for converting the intermediate representation to executable code.
'''

from ....common import T_CTOR, T_FUNC
from .... import icurry, objects
from ...generic import renderer
from ....utility import encoding, filesys
import pprint, six, textwrap
from ..graph import InfoTable

__all__ = [
    'materialize_function'
  , 'materialize_function_info_stub'
  , 'materialize_type'
  ]

def materialize_function(interp, ifun, ir, debug=False):
  '''Materializes a Python function from the IR.'''
  container = {}
  source = renderer.PY_RENDERER.renderLines(ir.lines)
  if debug:
    # If debugging, write a source file so that PDB can step into this
    # function.
    assert ifun is not None
    srcdir = filesys.getDebugSourceDir()
    name = encoding.symbolToFilename(ifun.fullname) + '.py'
    srcfile = filesys.makeNewfile(srcdir, name)
    with open(srcfile, 'w') as out:
      out.write(source)
      out.write('\n\n\n')
      comment = (
          'This file was created by Sprite because %s was compiled in debug '
          'mode.  It exists to help PDB show the compiled code.'
        ) % ifun.name
      out.write('\n'.join('# ' + line for line in textwrap.wrap(comment)))
      out.write('\n\n# Globals:\n# --------\n')
      closures = pprint.pformat(ir.closure.dict, indent=2)
      out.write('\n'.join('# ' + line for line in closures.split('\n')))
      out.write('\n\n# ICurry:\n# -------\n')
      out.write('\n'.join('# ' + line for line in str(ifun).split('\n')))
    co = compile(source, srcfile, 'exec')
    six.exec_(co, ir.closure.dict, container)
  else:
    six.exec_(source, ir.closure.dict, container)
  entry = list(container.values()).pop()
  entry.source = source
  return entry

def materialize_constructor_info(interp, itype, icons, moduleobj, extern):
  # For builtins, the 'all.tag' metadata contains the tag.
  builtin = 'all.tag' in icons.metadata
  info = InfoTable(
      icons.name
    , icons.arity
    , T_CTOR + icons.index if not builtin else icons.metadata['all.tag']
    , getattr(icons.metadata, 'all.flags', 0)
    , None
    , getattr(icons.metadata, 'py.format', None)
    , _gettypechecker(interp, icons.metadata)
    )
  return objects.CurryNodeInfo(info, icurry=icons)

def materialize_function_info_stub(interp, ifun, moduleobj, extern):
  info = InfoTable(
      ifun.name
    , ifun.arity
    , T_FUNC
    , ifun.metadata.get('all.flags', 0)
    , None
    , getattr(ifun.metadata, 'py.format', None)
    , _gettypechecker(interp, ifun.metadata)
    )
  return objects.CurryNodeInfo(info, icurry=ifun)

def materialize_type(interp, itype, moduleobj, extern):
  '''
  Synthesize the constructors of a type.
  '''
  infos = []
  for icons in itype.constructors:
    info_object = materialize_constructor_info(interp, itype, icons, moduleobj, extern)
    infos.append(info_object)
  typedef = objects.CurryDataType(itype, infos, moduleobj)
  for node_info in infos:
    node_info.typedef = typedef
    node_info.info.typedef = typedef
  return typedef

# FIXME: several things in the info table now have an interpreter bound.  It
# would be great to simplify that.  Maybe it should just be added as an entry
# to the info table.
def _gettypechecker(interp, metadata):
  '''
  If debugging is enabled, and a typechecker is defined, get it and bind the
  interpreter.
  '''
  if interp.flags['debug']:
    checker = getattr(metadata, 'py.typecheck', None)
    if checker is not None:
      return lambda *args: checker(interp, *args)

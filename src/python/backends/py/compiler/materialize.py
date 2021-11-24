'''
Code for converting the intermediate representation to executable code.
'''

from . import render
from ....utility import encoding, filesys
import pprint, six, textwrap

__all__ = 'materialize'

def materialize(interp, ir, debug=False, ifun=None):
  '''Materializes a Python function from the IR.'''
  container = {}
  source = render.render(ir.lines) # Python source code for this function.
  if debug:
    # If debugging, write a source file so that PDB can step into this
    # function.
    assert ifun is not None
    srcdir = filesys.getDebugSourceDir()
    name = encoding.symbolToFilename(ifun.fullname)
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
  entry = container.values().pop()
  entry.source = source
  return entry

'''
Code for converting the intermediate representation to executable code.
'''

from . import render
from ....utility import encoding, filesys
import pprint, textwrap

__all__ = 'materialize'

def materialize(interp, ir, debug=False, ifun=None):
  '''Materializes the Python function.'''
  container = {}
  source = render.render(ir.lines) # Python source code for this function.
  if debug:
    # If debugging, write a source file so that PDB can step into this
    # function.
    assert ifun is not None
    srcdir = filesys.getDebugSourceDir()
    name = encoding.symbolToFilename(ifun.name)
    srcfile = filesys.makeNewfile(srcdir, name)
    with open(srcfile, 'w') as out:
      out.write('# %s' % ifun.fullname)
      out.write(source)
      out.write('\n\n\n')
      comment = (
          'This file was created by Sprite because %s was compiled in debug '
          'mode.  It exists to help PDB show the compiled code.'
        ) % ifun.name
      out.write('\n'.join('# ' + line for line in textwrap.wrap(comment)))
      out.write('\n\n# Globals:\n# --------\n')
      context = pprint.pformat(ir.closure.context, indent=2)
      out.write('\n'.join('# ' + line for line in context.split('\n')))
      out.write('\n\n# ICurry:\n# -------\n')
      out.write('\n'.join('# ' + line for line in str(ifun).split('\n')))
    co = compile(source, srcfile, 'exec')
    exec co in ir.closure.context, container
  else:
    exec source in ir.closure.context, container
  entry = container[ir.entry]
  entry.source = source
  return entry

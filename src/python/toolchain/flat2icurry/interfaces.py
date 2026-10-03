'''
Finds and reads the FlatCurry interfaces of imported modules.

The Curry front end writes the interface ``M.fint`` of a module ``M`` beside
its ``M.fcy``.  Two layouts occur.  The front end puts the files of the
hierarchical module ``A.B`` under ``<root>/.curry/<subdir>/A/B.fint``, and
Sprite keeps per-directory products under ``<root>/A/.curry/<subdir>/B.fint``.
The finder tries both.  When no interface exists, the full ``.fcy`` serves,
because the translation uses only names, visibilities, and data types.
'''

from . import flatcurry as fc
from .errors import Flat2ICurryError
import os

__all__ = ['InterfaceFinder', 'load_interface', 'module_root', 'product_path']

SUFFIXES = ('.fint', '.fcy')

_LOADED = {}

def load_interface(filename):
  '''Reads a FlatCurry file.  Files are cached by name, size, and time.'''
  st = os.stat(filename)
  key = (filename, st.st_size, st.st_mtime_ns)
  prog = _LOADED.get(key)
  if prog is None:
    prog = _LOADED[key] = fc.load(filename)
  return prog

class InterfaceFinder:
  '''
  Looks up the interface of a module by name.

  Args:
    searchdirs:
        The directories to search, as a Curry path.
    subdirs:
        The names of the subdirectories of ``.curry`` that hold the front
        end output, e.g., ``['pakcs-3.4.1']``.
    progs:
        Programs already in hand, used before any file is read.
  '''
  def __init__(self, searchdirs, subdirs, progs=()):
    self.searchdirs = [os.path.abspath(d) for d in searchdirs]
    self.subdirs = list(subdirs)
    self.progs = {prog.name: prog for prog in progs}

  def candidates(self, modname):
    parts = modname.split('.')
    for searchdir in self.searchdirs:
      for subdir in self.subdirs:
        for suffix in SUFFIXES:
          yield os.path.join(searchdir, '.curry', subdir, *parts) + suffix
          if len(parts) > 1:
            yield os.path.join(
                searchdir, *parts[:-1], '.curry', subdir, parts[-1] + suffix
              )

  def filename(self, modname):
    '''The file that holds the interface of ``modname``.'''
    tried = []
    for candidate in self.candidates(modname):
      if os.path.isfile(candidate):
        return candidate
      tried.append(candidate)
    raise Flat2ICurryError(
        'no FlatCurry interface for module %r; tried:\n    %s'
            % (modname, '\n    '.join(tried))
      )

  def find(self, modname):
    '''The FlatCurry interface of ``modname``.'''
    prog = self.progs.get(modname)
    if prog is None:
      prog = self.progs[modname] = load_interface(self.filename(modname))
    return prog

def product_path(filename):
  '''
  Splits the path of a front-end product into ``(root, subdir, tail)``.  The
  file lies at ``<root>/.curry/<subdir>/<tail>/M.ext``; ``tail`` is empty for
  a module at the top level and ``A/B`` for a module under ``A.B``.  Returns
  None when no ``.curry`` directory encloses the file.
  '''
  outdir = os.path.dirname(os.path.abspath(filename))
  tail = []
  while True:
    parent, name = os.path.split(outdir)
    if not name or parent == outdir:
      return None
    if os.path.basename(parent) == '.curry':
      return os.path.dirname(parent), name, os.path.join(*tail) if tail else ''
    tail.insert(0, name)
    outdir = parent

def module_root(fcyfile, modname):
  '''
  The directory from which the module ``modname`` was compiled, given its
  FlatCurry file.  The file of module ``A.B`` lies at
  ``<root>/.curry/<subdir>/A/B.fcy`` or at ``<root>/A/.curry/<subdir>/B.fcy``.
  '''
  outdir = os.path.dirname(os.path.abspath(fcyfile))
  parts = modname.split('.')[:-1]
  tail = os.path.join(*parts) if parts else ''
  if tail and outdir.endswith(os.sep + tail):
    outdir = outdir[:-len(tail) - 1]
    return os.path.dirname(os.path.dirname(outdir))
  root = os.path.dirname(os.path.dirname(outdir))
  if tail and root.endswith(os.sep + tail):
    root = root[:-len(tail) - 1]
  return root

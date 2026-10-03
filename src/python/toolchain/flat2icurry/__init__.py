'''
The translation from FlatCurry to ICurry.

This is a port of the Curry package ``icurry`` 3.1.0 by Michael Hanus.  It
reads the FlatCurry of a module and the FlatCurry interfaces of its imports,
and it produces the ICurry term that ``icurry`` writes to a .icy file.  The
passes run in this order:

  1. Newtype elimination (:mod:`elimnewtype`).
  2. Case completion against the data declarations of the module and its
     imports (:mod:`casecompletion`).
  3. Lifting of nested cases, lets, and free declarations into new
     functions (:mod:`caselifting`).
  4. The name-to-index maps and the ICurry generation (:mod:`compiler`).

:func:`showterm` prints the result as the PAKCS ``showTerm`` does, so the
text is byte-identical to the output of ``icurry`` under PAKCS.

One defect of ``icurry`` 3.1.0 is kept behind the flag ``icurry_compat``,
which is on by default: a type annotation at the root of a rule hides a
case, a let, or a free declaration from the block builder.  See
:func:`compiler.to_iblock`.  The oracle tests keep the flag on, so the
output stays byte-identical to the files ``icurry`` wrote.  The build route
(:mod:`curry.toolchain._frontend`) turns it off, so the programs it compiles
run.
'''

from .casecompletion import complete_prog
from .caselifting import lift_prog
from .compiler import NameMaps, flat2icurry
from .elimnewtype import elim_newtype
from .errors import Flat2ICurryError
from .flatcurry import data_decls_of, load as load_flatcurry, read as read_flatcurry
from .interfaces import InterfaceFinder, load_interface, module_root, product_path
from .terms import showterm

__all__ = [
    'Flat2ICurryError', 'InterfaceFinder', 'load_flatcurry', 'load_interface'
  , 'module_root', 'product_path', 'read_flatcurry', 'showterm', 'translate'
  , 'translate_file', 'write_icurry'
  ]

def translate(prog, interfaces, icurry_compat=True):
  '''
  Translates a FlatCurry program to ICurry.

  Args:
    prog:
        The FlatCurry program.
    interfaces:
        The FlatCurry interfaces of the imports of ``prog``, in import order.
    icurry_compat:
        Whether to keep the output of ``icurry`` 3.1.0 for a type annotation
        at the root of a rule.  See :func:`compiler.to_iblock`.

  Returns:
    The ICurry program, an ``IProg`` term.
  '''
  interfaces = list(interfaces)
  prog = elim_newtype(interfaces, prog)
  datadecls = []
  for p in [prog] + interfaces:
    datadecls.extend(data_decls_of(p))
  ccprog = complete_prog(datadecls, prog)
  clprog = lift_prog(ccprog)
  maps = NameMaps.build(prog, interfaces, clprog)
  return flat2icurry(maps, clprog, icurry_compat)

def translate_file(fcyfile, finder, icurry_compat=True):
  '''
  Translates the FlatCurry file ``fcyfile``.  ``finder`` is an
  :class:`InterfaceFinder` that supplies the interfaces of the imports.
  '''
  prog = load_interface(fcyfile)
  interfaces = [finder.find(modname) for modname in prog.imports]
  return translate(prog, interfaces, icurry_compat)

def write_icurry(iprog, filename):
  '''Writes an ICurry program to a .icy file.'''
  with open(filename, 'w', encoding='utf-8', newline='') as ostream:
    ostream.write(showterm(iprog))

'''
The translation from FlatCurry to ICurry.

This is a port of the Curry package ``icurry`` 3.1.0 by Michael Hanus.  It
reads the FlatCurry of a module and the FlatCurry interfaces of its imports,
and it produces the ICurry term that ``icurry`` writes to a .icy file.  The
passes run in this order:

  0. The rewrite step of the routes (:func:`rewrite_prog`), when the
     caller asks for it: the binding optimization (:mod:`bindingopt`; the
     Boolean equalities whose value is required to be True become
     equational constraints, as the preprocessing of PAKCS makes them) and
     the set0 lift (:mod:`setlift`; ``set0 e`` over the captured variables
     of ``e`` becomes ``setk L xs``).  The routes from Curry to ICurry do
     not ask for it here: they apply it to the FlatCurry file itself
     before the translation (:func:`rewrite_file`), as PAKCS applies its
     preprocessing, so the file on disk is the rewritten program and the
     ``icurry`` program sees it too.  The flag serves a caller that must
     not touch the file, such as the option ``--rewrite`` of the command
     line.  The oracle tests do not ask for it.  The command line of
     :mod:`rewrite` applies the step to files by hand.
  1. Newtype elimination (:mod:`elimnewtype`).
  2. Case completion against the data declarations of the module and its
     imports (:mod:`casecompletion`).
  3. Lifting of nested cases, lets, and free declarations into new
     functions (:mod:`caselifting`).
  4. The name-to-index maps and the ICurry generation (:mod:`compiler`).

:func:`showterm` prints the result as the PAKCS ``showTerm`` does, so the
text is byte-identical to the output of ``icurry`` under PAKCS.
:func:`write_flatcurry` writes a FlatCurry program as the front end does.

One defect of ``icurry`` 3.1.0 is kept behind the flag ``icurry_compat``,
which is on by default: a type annotation at the root of a rule hides a
case, a let, or a free declaration from the block builder.  See
:func:`compiler.to_iblock`.  The oracle tests keep the flag on, so the
output stays byte-identical to the files ``icurry`` wrote.  The build route
(:mod:`curry.toolchain._frontend`) turns it off, so the programs it compiles
run.
'''

from . import bindingopt, setlift, flatcurry as fc
from .bindingopt import optimize_bindings, optimize_file
from .casecompletion import complete_prog
from .caselifting import lift_prog
from .compiler import NameMaps, flat2icurry
from .elimnewtype import elim_newtype
from .errors import Flat2ICurryError
from .flatcurry import (
    data_decls_of, load as load_flatcurry, read as read_flatcurry
  , show as show_flatcurry, write as write_flatcurry
  )
from .interfaces import InterfaceFinder, load_interface, module_root, product_path
from .setlift import optimize_set0
from .terms import showhaskell, showterm

__all__ = [
    'Flat2ICurryError', 'InterfaceFinder', 'load_flatcurry', 'load_interface'
  , 'module_root', 'optimize_bindings', 'optimize_file', 'optimize_set0'
  , 'product_path', 'read_flatcurry', 'rewrite_file', 'rewrite_prog'
  , 'show_flatcurry', 'showhaskell', 'showterm', 'translate'
  , 'translate_file', 'write_flatcurry', 'write_icurry'
  ]

def rewrite_prog(prog, equivalence=True, interfaces=()):
  '''
  Applies the rewrite step of the routes to a FlatCurry program in memory:
  the binding optimization, then the set0 lift.  Returns the program and
  the pair of counts (equalities replaced, set0 calls lifted); the program
  is ``prog`` itself when both counts are zero.  The result of the binding
  optimization counts only when it replaced an equality, as
  :func:`bindingopt.optimize_bindings` has it (a rule it rebuilt without a
  replacement, its ``$`` reduced, is not handed on), so the lift runs over
  the program the former route translated.  Without ``equivalence`` the
  binding optimization replaces ``===`` and ``/==`` alone (see
  :func:`bindingopt.transform_prog`).
  '''
  optimized, n = bindingopt.transform_prog(prog, equivalence)
  if not n:
    optimized = prog
  lifted, m = setlift.transform_prog(optimized, interfaces)
  return lifted, (n, m)

def rewrite_file(fcyfile, equivalence=True, searchdirs=()):
  '''
  Applies the rewrite step to the FlatCurry file ``fcyfile`` in place, as
  the routes do after the front end wrote it.  The file is written again,
  in the format of the front end, when a pass changed the program; else it
  is left as it is, with its time.  Returns the pair of counts of
  :func:`rewrite_prog`.
  '''
  prog = load_flatcurry(fcyfile)
  interfaces = []
  if any(setlift.contains_set0(fd.rule.body) for fd in prog.functions
      if not isinstance(fd.rule, fc.External)):
    from .interfaces import local_type_interfaces
    interfaces = local_type_interfaces(fcyfile, prog, searchdirs)
  newprog, counts = rewrite_prog(prog, equivalence, interfaces)
  if any(counts):
    write_flatcurry(newprog, fcyfile)
  return counts

def translate(prog, interfaces, icurry_compat=True, rewrite=False):
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
    rewrite:
        Whether to apply the rewrite step of the routes first, the binding
        optimization and the set0 lift.  See :func:`rewrite_prog`.

  Returns:
    The ICurry program, an ``IProg`` term.
  '''
  interfaces = list(interfaces)
  if rewrite:
    prog, _ = rewrite_prog(prog, interfaces=interfaces)
  prog = elim_newtype(interfaces, prog)
  datadecls = []
  for p in [prog] + interfaces:
    datadecls.extend(data_decls_of(p))
  from .flatcurry import typed_format
  ccprog = complete_prog(datadecls, prog, preserve_completed=typed_format(prog, interfaces))
  clprog = lift_prog(ccprog)
  maps = NameMaps.build(prog, interfaces, clprog)
  return flat2icurry(maps, clprog, icurry_compat)

def translate_file(fcyfile, finder, icurry_compat=True, rewrite=False):
  '''
  Translates the FlatCurry file ``fcyfile``.  ``finder`` is an
  :class:`InterfaceFinder` that supplies the interfaces of the imports.
  '''
  prog = load_interface(fcyfile)
  interfaces = [finder.find(modname) for modname in prog.imports]
  return translate(prog, interfaces, icurry_compat, rewrite)

def write_icurry(iprog, filename):
  '''Writes an ICurry program to a .icy file.'''
  from ... import cache
  cache.write_file(filename, showterm(iprog))

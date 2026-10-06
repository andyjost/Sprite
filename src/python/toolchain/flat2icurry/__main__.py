'''
Command line: translate a FlatCurry file to ICurry.

    python -m curry.toolchain.flat2icurry [-i DIR]... [-s SUBDIR]... [-o FILE] M.fcy

The interfaces of the imports are searched under the root directory of the
module and the ``-i`` directories, in the ``.curry`` subdirectories named by
``-s``.  Without ``-s``, the subdirectory of ``.curry`` that holds ``M.fcy``
is used.

``--bindingopt`` applies the binding optimization to the program in memory
before the translation and leaves ``M.fcy`` as it is: the ICurry of a
FlatCurry file the routes have not rewritten yet, without a change to the
file.  To rewrite the file itself, as the routes do, run
``python -m curry.toolchain.flat2icurry.rewrite M.fcy``.
'''

from . import (
    InterfaceFinder, load_interface, module_root, product_path, showterm
  , translate, write_icurry
  )
import argparse, os, sys

def main(argv=None):
  parser = argparse.ArgumentParser(
      prog='python -m curry.toolchain.flat2icurry'
    , description='Translate a FlatCurry file to ICurry.'
    )
  parser.add_argument('fcyfile', help='the FlatCurry file (.fcy)')
  parser.add_argument(
      '-i', '--import-dir', action='append', default=[], metavar='DIR'
    , help='a directory in which to search for the interfaces of imports'
    )
  parser.add_argument(
      '-s', '--subdir', action='append', default=[], metavar='SUBDIR'
    , help='a subdirectory of .curry that holds front-end output'
    )
  parser.add_argument(
      '-o', '--output', default='-', metavar='FILE'
    , help='the output file; "-" is standard output (the default)'
    )
  parser.add_argument(
      '--no-icurry-compat', dest='icurry_compat', action='store_false'
    , help='look through a type annotation at the root of a rule, which '
           'icurry 3.1.0 does not'
    )
  parser.add_argument(
      '--bindingopt', action='store_true'
    , help='apply the binding optimization to the program in memory first: '
           'a Boolean equality required to be True becomes constrEq; the '
           'file is not touched (the routes rewrite it instead, see '
           'curry.toolchain.flat2icurry.bindingopt)'
    )
  args = parser.parse_args(argv)
  prog = load_interface(args.fcyfile)
  location = product_path(args.fcyfile)
  if location is not None:
    subdirs = args.subdir or [location[1]]
  else:
    subdirs = args.subdir or [os.path.basename(os.path.dirname(args.fcyfile))]
  searchdirs = [module_root(args.fcyfile, prog.name)] + args.import_dir
  finder = InterfaceFinder(searchdirs, subdirs)
  iprog = translate(
      prog, [finder.find(modname) for modname in prog.imports]
    , args.icurry_compat, args.bindingopt
    )
  if args.output == '-':
    sys.stdout.write(showterm(iprog))
    sys.stdout.write('\n')
  else:
    write_icurry(iprog, args.output)
  return 0

if __name__ == '__main__':
  sys.exit(main())

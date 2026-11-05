"""Remove Sprite products of selected modules, or all in this directory."""
import argparse
from pathlib import Path
import shutil
from curry import config


def main(argv=None):
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('-v', '--verbose', action='store_true')
  parser.add_argument('modules', nargs='*')
  args = parser.parse_args(argv)
  def remove(path):
    if args.verbose:
      print('REMOVE:', path)
    if path.is_dir() and not path.is_symlink():
      shutil.rmtree(path)
    else:
      path.unlink(missing_ok=True)
  def product_dirs(parent):
    root = parent / '.curry'
    # frontend-exec uses the compiler-version directory; Sprite's own
    # translator names its directory after the configured PAKCS pair.
    return [root / config.intermediate_subdir(), *root.glob('sprite-[0-9]*')]
  if not args.modules:
    for directory in product_dirs(Path('.')):
      remove(directory)
  for name in args.modules:
    path = Path(name)
    stem = path.name.removesuffix('.lcurry').removesuffix('.curry')
    module = path.parent / stem.replace('.', '/')
    # Sprite writes products beside each source directory. frontend-exec
    # writes qualified module paths below its root output directory.
    candidates = [(module.parent, module.name), (path.parent, stem.replace('.', '/'))]
    for parent, relative in candidates:
      for directory in product_dirs(parent):
        product = directory / relative
        for entry in product.parent.glob(product.name + '.*'):
          remove(entry)



if __name__ == '__main__':
  main()

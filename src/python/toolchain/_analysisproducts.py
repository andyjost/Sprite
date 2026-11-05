"""Serve shipped library analyses without invoking a writable front end."""
from pathlib import Path
import hashlib
import os
from .. import config


def shipped_request(arguments):
  """Accept only ordinary stock-reader requests for the installed source.

  Other outputs, options and source overrides go through the real front end.
  In particular, a force or a preprocessing option must never use this cache.
  """
  search, modules, suffixes = [Path.cwd()], [], set()
  outdir = None
  major, minor, _ = config.analysis_subdir().removeprefix('sprite-').split('.')
  compiler_definition = '-D__SPRITE__=%d' % (int(major) * 100 + int(minor))
  args = iter(arguments)
  for argument in args:
    if argument in ('-i', '--import-dir'):
      value = next(args, None)
      if value is None:
        return False
      search.extend(Path(p) for p in value.split(os.pathsep))
    elif argument.startswith('-i'):
      search.extend(Path(p) for p in argument[2:].split(os.pathsep))
    elif argument.startswith('--import-dir='):
      search.extend(Path(p) for p in argument.split('=', 1)[1].split(os.pathsep))
    elif argument in ('-o', '--outdir'):
      value = next(args, None)
      if value is None:
        return False
      outdir = Path(value)
    elif argument.startswith('--outdir='):
      outdir = Path(argument.split('=', 1)[1])
    elif argument in ('--flat', '--acy'):
      suffixes.update(('.fcy', '.fint') if argument == '--flat' else ('.acy',))
    elif argument in ('--extended', '--no-verb', '--no-warn', '--no-overlap-warn', '-q'):
      pass
    elif argument == compiler_definition:
      pass
    elif argument.startswith('-'):
      return False
    else:
      modules.append(argument)
  if not modules or not suffixes or outdir != Path('.curry') / config.analysis_subdir():
    return False
  library = Path(config.system_curry_path()).resolve()
  search.append(library)
  for module in modules:
    name = module.removesuffix('.curry')
    path = Path(name).parent / Path(*Path(name).name.split('.'))
    found = next((root / Path(str(path) + suffix) for root in search
                  for suffix in ('.lcurry', '.curry')
                  if (root / Path(str(path) + suffix)).is_file()), None)
    if found is None:
      return False
    try:
      relative = found.resolve().relative_to(library)
    except ValueError:
      return False
    # Stock readers use the top of the module hierarchy as the product root.
    if relative.with_suffix('') != path:
      return False
    receipt = found.parent / '.curry' / config.intermediate_subdir() / (found.stem + '.icy.source')
    if not receipt.is_file() or receipt.read_text().strip() != \
        hashlib.sha256(found.read_bytes()).hexdigest():
      return False
    for suffix in suffixes:
      if not (library / outdir / relative.with_suffix(suffix)).is_file():
        return False
  return True

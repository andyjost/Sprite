"""Source-free library interfaces for external front-end commands."""
from contextlib import contextmanager
from pathlib import Path
import shutil
import hashlib
import os
from .. import config


_views = {}


def interface_view(outdir):
  return _view(outdir, loaded_only=False)


@contextmanager
def loaded_interface_view(outdir, search):
  from . import _findcurry, _frontend, _interfaces
  interp = _findcurry._translation_interp.get()
  needed = False
  if interp is not None:
    for name in interp.modules:
      source = _findcurry.loaded_source(name)
      if source is None:
        continue
      root = os.path.realpath(_frontend.source_root(source))
      with _findcurry.resolving(None):
        for directory in search:
          candidate = os.path.join(directory, *name.split('.')) + '.curry'
          if os.path.isfile(candidate) or _interfaces.interface_file(name, [directory]):
            needed |= os.path.realpath(directory) != root
            break
        else:
          needed = True
  if needed:
    with _view(outdir, loaded_only=True) as library:
      yield library
  else:
    yield None


@contextmanager
def _view(outdir, loaded_only):
  outdir = Path(outdir)
  from ..backends.cxx import tiered
  products = []
  from ._findcurry import _translation_interp, loaded_source
  interp = _translation_interp.get()
  names = set() if loaded_only else set(config.syslibs())
  if interp is not None:
    names.update(interp.modules)
  for name in sorted(names):
    parts = name.split('.')
    loaded = loaded_source(name)
    if loaded is not None:
      from ._filenames import icurryfilename
      source = Path(icurryfilename(loaded)).with_suffix('')
    else:
      source = Path(config.installed_path('curry')).joinpath(*parts[:-1],
          '.curry', config.intermediate_subdir(), parts[-1])
    for suffix in ('.fint', '.icurry'):
      product = source.with_suffix(source.suffix + suffix)
      if product.is_file():
        stat = product.stat()
        products.append((name, suffix, product, stat.st_mtime_ns,
                         hashlib.sha256(product.read_bytes()).digest()))
  key = (tuple((name, str(product)) for name, _, product, _, _ in products), os.getpid(), config.installed_path('curry'),
         config.frontend_subdir(), config.intermediate_subdir(), str(outdir))
  stamp = [(name, suffix, time, digest)
           for name, suffix, _, time, digest in products]
  cached = _views.get(key)
  if cached and cached[0] == stamp and Path(cached[1]).is_dir():
    yield cached[1]
    return
  work = Path(tiered._tmpdir()) / ('interfaces%d' % next(tiered._state.counter))
  library = work.joinpath('interfaces', *(['parent'] * outdir.parts.count('..')))
  library.mkdir(parents=True)
  for name, suffix, product, _, _ in products:
    parts = name.split('.')
    target = library.joinpath(*parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(product, str(target) + suffix)
    nested = library.joinpath(*(outdir.parts[1:] if outdir.anchor else outdir.parts), *parts)
    if nested != target:
      nested.parent.mkdir(parents=True, exist_ok=True)
      shutil.copy2(product, str(nested) + suffix)
  _views[key] = stamp, str(library)
  yield str(library)

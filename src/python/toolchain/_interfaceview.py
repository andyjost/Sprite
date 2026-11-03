"""Source-free library interfaces for external front-end commands."""
from contextlib import contextmanager
from pathlib import Path
import shutil
import hashlib
import os
from .. import config


_views = {}


@contextmanager
def interface_view(outdir):
  outdir = Path(outdir)
  from ..backends.cxx import tiered
  products = []
  for name in config.syslibs():
    parts = name.split('.')
    source = Path(config.installed_path('curry')).joinpath(*parts[:-1],
        '.curry', config.intermediate_subdir(), parts[-1])
    for suffix in ('.fint', '.icurry'):
      product = source.with_suffix(source.suffix + suffix)
      if product.is_file():
        stat = product.stat()
        products.append((name, suffix, product, stat.st_mtime_ns,
                         hashlib.sha256(product.read_bytes()).digest()))
  key = (os.getpid(), config.installed_path('curry'),
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

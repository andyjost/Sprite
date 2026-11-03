"""Source-free library interfaces for external front-end commands."""
from contextlib import contextmanager
from pathlib import Path
import shutil
import tempfile
from .. import config


@contextmanager
def interface_view(outdir):
  outdir = Path(outdir)
  with tempfile.TemporaryDirectory(prefix='sprite-frontend-') as work:
    # Leave enough parents inside the temporary tree for every '..'. The
    # front end applies the output directory to interface paths as well.
    library = Path(work).joinpath('interfaces', *(['parent'] * outdir.parts.count('..')))
    library.mkdir(parents=True)
    for name in config.syslibs():
      parts = name.split('.')
      source = Path(config.installed_path('curry')).joinpath(*parts[:-1],
          '.curry', config.intermediate_subdir(), parts[-1])
      target = library.joinpath(*parts)
      target.parent.mkdir(parents=True, exist_ok=True)
      for suffix in ('.fint', '.icurry'):
        product = source.with_suffix(source.suffix + suffix)
        if product.is_file():
          shutil.copyfile(product, str(target) + suffix)
          nested = library.joinpath(*(outdir.parts[1:] if outdir.anchor else outdir.parts), *parts)
          if nested != target:
            nested.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(product, str(nested) + suffix)
    yield str(library)

"""Translate ICurry text directly to the runtime module image."""
from . import _filenames


class ICurry2Image:
  manages_product_lock = True

  def __init__(self, interp):
    self.interp = interp

  def __repr__(self):
    return 'icurry2image'

  def __call__(self, file_in, currypath, **kwds):
    from ..backends.cxx import image
    from . import _findcurry
    path, _ = image.ensure(self.interp, file_in,
        _findcurry.import_path(self.interp,
            _findcurry.imports_path(currypath, **kwds)),
        importing=kwds.get('image_importing', False))
    return _filenames.ImageProduct(path, file_in)

  def is_stale(self, filename, currypath=None):
    if not filename.endswith('.img'):
      return False
    from ..backends.cxx import image
    try:
      header = image._check(self.interp, _filenames.icurryfilename(filename), filename)
      from . import _interfaces
      import os
      search = _interfaces.search_path(_filenames.curryfilename(filename), currypath)
      for name, expected in header['imports'].items():
        parts = name.split('.')
        paths = (os.path.join(directory, *parts[:-1], '.curry',
            _filenames.SUBDIR, parts[-1] + '.img') for directory in search)
        actual = next((path for path in paths if os.path.isfile(path)), None)
        if image.digest(actual) != expected:
          return True
      return False
    except (OSError, ValueError, KeyError):
      return True

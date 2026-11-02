"""Translate ICurry text directly to the runtime module image."""
from . import _filenames


class ICurry2Image:
  manages_product_lock = True

  def __init__(self, interp, check_budget=True):
    self.interp = interp
    self.check_budget = check_budget

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
      source = _filenames.icurryfilename(filename)
      header = image.read(filename)
      facts = image._facts(self.interp, source, {})
      # A current compiled product is accepted regardless of inline budget.
      # A foreign image budget must not prune that later product and cause
      # an implicit import to replace it. Image attachment still checks the
      # budget and builds a private image when interpreted code is needed.
      keys = ('source', 'route', 'registry')
      if self.check_budget:
        keys += ('budget',)
      if any(header.get(key) != facts[key] for key in keys):
        return True
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

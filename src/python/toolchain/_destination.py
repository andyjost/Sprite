"""Publication destinations shared by installed-module product writers."""
import os
from contextlib import contextmanager
from contextvars import ContextVar
from . import _filenames, _findcurry
from .. import config


def canonical(filename):
  """Normalize a product spelling; use realpath separately for identity."""
  if isinstance(filename, _filenames.ImageProduct):
    return _filenames.ImageProduct(os.path.abspath(filename),
                                  os.path.abspath(filename.icyfile),
                                  os.path.abspath(filename.original_icyfile))
  if not filename.endswith('.curry') and os.path.islink(filename):
    # A standalone product alias has no source layout of its own. Resolve
    # it before deriving sibling products, preserving ordinary source paths.
    return os.path.realpath(filename)
  return os.path.abspath(filename)


def writable(filename):
  directory = os.path.dirname(canonical(filename))
  while not os.path.exists(directory):
    directory = os.path.dirname(directory)
  return os.access(directory, os.W_OK) and bool(os.stat(directory).st_mode & 0o222)


_importing = ContextVar('product_importing', default=False)


@contextmanager
def publication(importing):
  # The stage builds the installation, including dependencies imported by
  # its compiler. Runtime importers retain their private destinations.
  token = _importing.set(importing and not staging())
  try:
    yield
  finally:
    _importing.reset(token)


def staging():
  """The installation builder's sanitized child environment owns this flag."""
  return os.environ.get('SPRITE_STAGE_LIBRARY') == '1'


def needs_private(filename, products):
  filename = canonical(filename)
  product = _filenames.icurryfilename(filename) if filename.endswith('.curry') else filename
  return not writable(product) or (_findcurry._installed_library_file(filename) and (
      _importing.get() or any(path is not None and
          not _findcurry._installed_library_file(canonical(path))
          for path in products)))


def select(filename, products=(), force=False):
  """Return a source generation; later writers inherit its destination."""
  filename = canonical(filename)
  from ..backends.cxx import tiered
  source = _filenames.sourcefilename(filename)
  if not force and not needs_private(filename, products):
    return filename
  from ..icurry.types import IModule
  raw = IModule(_filenames.module_name(source), [], [], [], filename=source)
  generation = _findcurry.generation_for_source(source)
  if generation is not None:
    raw._loaded_generation = generation
  copy, _ = tiered._private_copy(raw)
  if filename.endswith('.curry'):
    return copy
  return _filenames.replacesuffix(copy, os.path.splitext(filename)[1])


def interfaces(source, currypath, dependencies=None, source_imports=False):
  """Resolve interface prerequisites, including their interface imports.

  Front-end input discovery prefers current source headers with source_imports.
  """
  from . import _interfaces
  from ..utility import curryname
  def source_names(path):
    from ..cache import SourceInfo
    source = _filenames.sourcefilename(path)
    with open(source, 'rb') as stream:
      return SourceInfo(source, stream.read()).imports
  search = _interfaces.search_path(canonical(source),
      curryname.makeCurryPath(currypath))
  pending = [canonical(source)]
  seen = set()
  products = []
  while pending:
    path = pending.pop()
    if path in seen:
      continue
    seen.add(path)
    icy = _filenames.icurryfilename(path)
    try:
      names = source_names(path) if source_imports else _interfaces.imports(icy)
    except (OSError, ValueError):
      try:
        names = _interfaces.imports(icy) if source_imports else source_names(path)
      except (OSError, ValueError):
        names = []
    for name in names:
      generation = _findcurry.loaded_generation(name)
      if generation is not None:
        # Destination provenance belongs to the generation, not today's path.
        captured = [generation]
        visited = set()
        while captured:
          item = captured.pop()
          if id(item) in visited:
            continue
          visited.add(id(item))
          products.append(item.image if item.image else
                          item.object or item.image or item.source_spelling)
          captured.extend(dep for _, dep in item.imports if dep is not None)
        continue
      interface = None
      dependency = None
      for directory in _findcurry.module_path(name, search):
        candidate = os.path.join(directory, *name.split('.')) + '.curry'
        interface = _interfaces.interface_file(name, [directory])
        if os.path.isfile(candidate):
          # The front end will elaborate this source even when no interface
          # exists yet. Its planned product already fixes the destination.
          dependency = canonical(candidate)
          if interface is None:
            interface = _filenames.replacesuffix(dependency, '.fint')
          break
        if interface is not None:
          break
      if interface is not None:
        interface = canonical(interface)
        products.append(interface)
        if dependency is not None:
          if dependencies is not None:
            dependencies.append(dependency)
          pending.append(dependency)
        elif interface.endswith('.fint'):
          dependency = interface[:-5] + '.icy'
          if os.path.isfile(dependency):
            pending.append(dependency)
  return products


def images(interp, names):
  """The actual resolved images, rather than their installation spellings."""
  from ..backends.cxx import image
  from ..objects.handle import getHandle
  products = []
  for name in names:
    if name not in interp.modules:
      continue
    raw = getHandle(interp.modules[name]).icurry
    generation = getattr(raw, '_loaded_generation', None)
    if generation is not None:
      products.append(generation.image if generation.image else
                      generation.object or generation.image or generation.source_spelling)
    elif raw.filename:
      products.append(image._path(interp, raw.filename))
  return products

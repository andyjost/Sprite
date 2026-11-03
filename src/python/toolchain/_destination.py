"""Publication destinations shared by installed-module product writers."""
import os
from . import _filenames, _findcurry


def canonical(filename):
  if isinstance(filename, _filenames.ImageProduct):
    return _filenames.ImageProduct(os.path.realpath(filename),
                                  os.path.realpath(filename.icyfile),
                                  os.path.realpath(filename.original_icyfile))
  return os.path.realpath(filename)


def writable(filename):
  directory = os.path.dirname(canonical(filename))
  while not os.path.exists(directory):
    directory = os.path.dirname(directory)
  return os.access(directory, os.W_OK) and bool(os.stat(directory).st_mode & 0o222)


def needs_private(filename, products):
  filename = canonical(filename)
  return _findcurry._installed_library_file(filename) and (
      not writable(_filenames.icurryfilename(filename)
          if filename.endswith('.curry') else filename) or any(path is not None and
          not _findcurry._installed_library_file(canonical(path))
          for path in products))


def select(filename, products=(), force=False):
  """Return a source generation; later writers inherit its destination."""
  filename = canonical(filename)
  if not force and not needs_private(filename, products):
    return filename
  from ..backends.cxx import tiered
  from ..icurry.types import IModule
  source = _filenames.sourcefilename(filename)
  raw = IModule(_filenames.module_name(source), [], [], [], filename=source)
  copy, _ = tiered._private_copy(raw)
  if filename.endswith('.curry'):
    return copy
  return _filenames.replacesuffix(copy, os.path.splitext(filename)[1])


def interfaces(source, currypath, dependencies=None):
  """Resolve interface prerequisites, including their interface imports."""
  from . import _interfaces
  from ..utility import curryname
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
      names = _interfaces.imports(icy)
    except (OSError, ValueError):
      try:
        with open(_filenames.sourcefilename(path), encoding='utf-8') as stream:
          tokens = list(_filenames._header_tokens(stream.read()))
        names = [tokens[i + 1] for i, token in enumerate(tokens[:-1])
                 if token == 'import']
      except OSError:
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
                          item.object or item.image or item.source)
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
                      generation.object or generation.image or generation.source)
    elif raw.filename:
      products.append(image._path(interp, raw.filename))
  return products

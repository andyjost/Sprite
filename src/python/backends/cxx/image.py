'''Portable, content-validated module images. See DeveloperNotes.rst.'''
import contextlib
import collections.abc
import hashlib
import json
import logging
import os
import struct

from ... import cache, exceptions, icurry
from ...objects.handle import getHandle
from ...utility.binding import binding
from ...utility.strings import int_text
from ...toolchain import _filenames, _loadcurry, _productlock, _destination
from . import bytecode, curryrtbindings as curryrt

logger = logging.getLogger(__name__)
MAGIC = b'SPRTIMG\0'
# Version 13 invalidates summaries that inlined private primitive wrappers.
VERSION = 14
PREFIX = struct.Struct('<8sII')

class _InputChanged(Exception):
  pass


def digest(filename):
  if filename is None:
    return None
  try:
    with open(filename, 'rb') as stream:
      return hashlib.sha256(stream.read()).hexdigest()
  except FileNotFoundError:
    return None


def filename(source):
  return _filenames.replacesuffix(_destination.canonical(source), '.img') if source else None


def read(path):
  from ...toolchain._findcurry import verify_loaded_product
  verify_loaded_product(path)
  with open(path, 'rb') as stream:
    data = stream.read()
  if len(data) < PREFIX.size:
    raise ValueError('truncated module image')
  magic, version, size = PREFIX.unpack_from(data)
  if magic != MAGIC:
    raise ValueError('invalid module image magic')
  if version != VERSION:
    raise ValueError('unsupported module image version %d' % version)
  encoded = data[PREFIX.size:PREFIX.size + size]
  header = json.loads(encoded)
  if not isinstance(header, dict) or not all(key in header
      for key in ('body', 'source', 'route', 'budget', 'imports', 'name', 'registry')) \
      or not isinstance(header['imports'], dict):
    raise ValueError('invalid module image header')
  if encoded != json.dumps(header, sort_keys=True, separators=(',', ':')).encode('ascii'):
    raise ValueError('invalid module image header encoding')
  body = data[PREFIX.size + size:]
  if hashlib.sha256(body).hexdigest() != header['body']:
    raise ValueError('corrupt module image body')
  return header


def _facts(interp, source, imports, registry=None):
  source = _destination.canonical(source)
  from ...toolchain._frontend import ROUTE_VERSION
  from . import toolchain
  from ...toolchain import _findcurry
  generation = _findcurry.generation_for_source(source, interp)
  icy_digest = generation.product_digest('.icy') if generation is not None else digest(
      _filenames.icurryfilename(source))
  return dict(source=icy_digest, route=ROUTE_VERSION,
      budget=interp.flags['inline_budget'], imports=imports,
      registry=toolchain.registered_names(source) if registry is None else registry)


def writable(source):
  if not source:
    return False
  return _destination.writable(filename(source))




def _private_path(interp, source):
  from . import tiered
  source = _filenames.sourcefilename(_destination.canonical(source))
  from ...toolchain import _findcurry
  if _findcurry._installed_library_file(source):
    generations = interp.__dict__.setdefault('_product_generations', {})
    key = (source, digest(_filenames.icurryfilename(source)),
           interp.flags['inline_budget'])
    with _findcurry.loader_inputs() as records:
      generation = generations.get(key)
      if generation is None or not _findcurry.is_loader_snapshot(
          _filenames.module_name(source), generation[0], generation[1]):
        copy = _destination.select(source, force=True)
        generation = generations[key] = (copy, dict(records))
      # Reusing this private image also reuses its copier authorization.
      records.update(generation[1])
      return filename(generation[0])
  key = '%s:%s' % (os.path.realpath(source), interp.flags['inline_budget'])
  return os.path.join(tiered._tmpdir(), hashlib.sha256(key.encode()).hexdigest() + '.img')


def _path(interp, source):
  if not source:
    return None
  from . import tiered
  from ...toolchain import _findcurry
  generation = _findcurry.generation_for_source(source, interp)
  if generation is not None and generation.image is not None:
    return _findcurry.verify_product(generation, generation.image)
  if _findcurry._installed_library_file(source):
    key = (_filenames.sourcefilename(_destination.canonical(source)),
           digest(_filenames.icurryfilename(source)), interp.flags['inline_budget'])
    generation = getattr(interp, '_product_generations', {}).get(key)
    if generation is not None and not _findcurry.is_loader_snapshot(
        _filenames.module_name(source), generation[0], generation[1]):
      interp._product_generations.pop(key, None)
      generation = None
    if generation is None and not tiered._foreign_flags(interp):
      return filename(_destination.canonical(source))
  if tiered._foreign_flags(interp) or tiered._state.tmpdir is not None:
    private = _private_path(interp, source)
    if tiered._foreign_flags(interp) or os.path.isfile(private):
      return private
  return filename(source)


def generation_digest(generation):
  """Identity of the implementation retained by the loaded module."""
  return (generation.product_digest('image') or generation.product_digest('object')
      or generation.product_digest('.icy'))


def _check(interp, source, path, imports=None, registry=None):
  header = read(path)
  # Check local facts before resolving any dependency of an old source.
  facts = _facts(interp, source, {}, registry)
  if any(header.get(k) != facts[k] for k in ('source', 'route', 'budget', 'registry')):
    raise ValueError('stale module image')
  if imports is not None and header['imports'] != imports:
    raise ValueError('stale module image imports')
  return header


def _import_images(interp, names, currypath):
  result = {}
  for name in names:
    module = interp.import_(name, currypath=currypath)
    h = getHandle(module)
    generation = getattr(h.icurry, '_loaded_generation', None)
    if generation is not None:
      result[name] = generation_digest(generation)
      continue
    result[name] = None
  return result


class _SummaryFunctions(collections.abc.Mapping):
  '''Materialize only the declarations the importing optimizer looks up.'''
  def __init__(self, fullname, functions):
    self.fullname = fullname
    self.records = {info.name: (vis, md, info) for vis, md, info in functions}
    self.loaded = {}

  def __len__(self):
    return len(self.records)

  def __iter__(self):
    return iter(self.records)

  def __getitem__(self, name):
    if name not in self.loaded:
      record = self.records[name]
      module = icurry.IModule.fromBOM(self.fullname, (), (), [record],
          'cxx.material')
      self.loaded[name] = module.functions[name]
    return self.loaded[name]


def _from_bom(bom, source):
  module = icurry.IModule.fromBOM(bom.fullname, bom.imports, bom.types,
      (), 'cxx.material', filename=source, aliases=bom.aliases,
      metadata=dict(bom.metadata, **{'cxx.is_merged': True}))
  module.functions = _SummaryFunctions(bom.fullname, bom.functions)
  # BOM declarations have exempt bodies: their call graph has no edges.
  # Recorded inline bodies already passed the recursion check at translation.
  module._inline_recursive = frozenset()
  return module


def _summaries(interp, module, currypath=None):
  '''Prepare read-only import summaries before taking a product lock.'''
  from ...utility import curryname
  _import_images(interp, module.imports, currypath)
  summaries = []
  pending = list(module.imports)
  seen = set()
  while pending:
    name = pending.pop()
    if name in seen:
      continue
    seen.add(name)
    dep = interp.modules[name]
    h = getHandle(dep)
    generation = getattr(h.icurry, '_loaded_generation', None)
    if generation is not None:
      summaries.append((dep, h.icurry))
      pending.extend(name for name, _ in generation.imports)
      continue
    if h.icurry.filename:
      summaries.append((dep, h.icurry))
      pending.extend(h.icurry.imports)
  for prefix in list(curryname.prefixes(module.fullname))[:-1]:
    if prefix not in interp.modules:
      package = icurry.IPackage(prefix)
      package.filename = os.path.dirname(module.filename or '')
      interp.import_(package)
  return summaries


def optimize(interp, module, currypath=None, summaries=None):
  if summaries is None:
    summaries = _summaries(interp, module, currypath)
  with interp._private_modules(), contextlib.ExitStack() as stack:
    # The passes only need ICurry declarations, including for the local
    # module. Do not create runtime tables while holding a product lock.
    entries = [(module.fullname, module)] + [
        (getHandle(dep).fullname, summary) for dep, summary in summaries]
    for name, summary in entries:
      stack.enter_context(binding(interp.modules, name, summary))
      parent, _, local = name.rpartition('.')
      package = interp.modules.get(parent)
      package_ir = getattr(package, '.icurry', package)
      if isinstance(package_ir, icurry.IPackage):
        stack.enter_context(binding(package_ir, local, summary))
    interp.optimize(module)


class Encoder:
  def __init__(self):
    self.data = bytearray()

  def word(self, value):
    self.data.extend(struct.pack('<I', value & 0xffffffff))

  def text(self, value):
    data = value.encode('utf-8')
    self.word(len(data))
    self.data.extend(data)

  def real(self, value):
    self.data.extend(struct.pack('<d', value))

  def metadata(self, md):
    md = getattr(md, '_asdict', md)
    entries = {k: v for k, v in md.items()
        if k.startswith(('all.', 'cxx.opt.')) and type(v) in (str, int, bool)}
    self.word(len(entries))
    for key, value in sorted(entries.items()):
      self.text(key)
      if isinstance(value, str):
        self.word(0)
        self.text(value)
      elif isinstance(value, bool):
        self.word(2)
        self.word(value)
      else:
        self.word(1)
        self.word(value)

  def reference(self, ref):
    _, module, name = ref
    self.text(module)
    self.text(name)

  def constant(self, value):
    kind = value[0]
    self.word(ord(kind))
    if kind in ('R', 'T'):
      self.reference(value)
    elif kind == 'I':
      self.text(int_text(value[1]))
    elif kind == 'S':
      self.text(value[1])
    elif kind == 'C':
      self.word(value[1])
    elif kind == 'F':
      self.real(value[1])
    elif kind == 'P':
      self.reference(value[1])
      self.word(value[2])
    elif kind == 'V':
      vkind, values = value[1:]
      self.word(ord(vkind))
      self.word(len(values))
      for item in values:
        if vkind in ('i', 'p'):
          self.text(int_text(item))
        elif vkind == 'c':
          self.word(ord(item) if isinstance(item, str) else item)
        else:
          self.real(item)
    else:
      raise ValueError('unknown image constant %r' % (value,))


class Resolver:
  def __init__(self, interp, module):
    self.module = module
    self.references = {}
    self.tags = {}
    for dep in tuple(interp.modules.values()):
      h = getHandle(dep)
      if not isinstance(h.icurry, icurry.IModule):
        continue
      for name, symbol in h.symbols.items():
        fullname = h.fullname + '.' + name
        self.references[fullname] = ('R', symbol.icurry.modulename, symbol.name)
      for datatype in h.icurry.types.values():
        for ctor in datatype.constructors:
          fullname = h.fullname + '.' + ctor.name
          self.tags[fullname] = interp.symbol(fullname).info.tag
    self.refresh()

  def refresh(self):
    module = self.module
    self.local = set(module.functions) | {
        ctor.name for datatype in module.types.values()
        for ctor in datatype.constructors}

  def symbol(self, name):
    prefix = self.module.fullname + '.'
    if name.startswith(prefix) and name[len(prefix):] in self.local:
      return ('R', self.module.fullname, name[len(prefix):])
    return self.references[name]

  def tag(self, name):
    ref = self.symbol(name)
    if ref[1] == self.module.fullname:
      for datatype in self.module.types.values():
        for tag, ctor in enumerate(datatype.constructors):
          if ctor.name == ref[2]:
            return tag
    return self.tags[name]

  def datatype(self, name):
    ref = self.symbol(name)
    return ('T', ref[1], ref[2])


def write(interp, module, currypath=None, path=None, imports=None):
  if not module.filename:
    return None
  if imports is None:
    imports = _import_images(interp, module.imports, currypath)
  if path is None:
    path = _path(interp, module.filename)
  path = _publication_path(interp, module.filename, path, imports)
  from .materialize import function_primitive
  native = curryrt.Module.find_or_create(module.fullname)
  builtins = {f.name for f in module.functions.values()
      if function_primitive(native, f, module) is not None}
  from .toolchain import registered_names
  registry = registered_names(module.filename)
  resolver = Resolver(interp, module)
  with _productlock.locked(path):
    try:
      _check(interp, module.filename, path, imports, registry)
      return path
    except (OSError, ValueError, KeyError, exceptions.CurryError):
      pass
    return _write(interp, module, path, imports, builtins, registry, resolver)


def _write(interp, module, path, imports, builtins, registry, resolver):
  out = Encoder()
  out.text(module.fullname)
  out.word(len(module.imports))
  for name in module.imports:
    out.text(name)
  out.word(len(module.aliases))
  for name, target in sorted(module.aliases.items()):
    out.text(name)
    out.text(target)
  out.metadata(module.metadata)
  out.word(len(module.types))
  for datatype in module.types.values():
    out.text(datatype.name)
    flags = datatype.metadata.get('all.flags', 0)
    if datatype.name.startswith('_Dict#'):
      flags |= curryrt.F_DICTIONARY
    out.word(flags)
    out.metadata(datatype.metadata)
    out.word(len(datatype.constructors))
    for ctor in datatype.constructors:
      out.text(ctor.name)
      out.word(ctor.arity)
      out.word(ctor.metadata.get('all.flags', 0))
      out.metadata(ctor.metadata)
  out.word(len(module.functions))
  codes = []
  for function in module.functions.values():
    out.text(function.name)
    out.word(function.arity)
    out.word(function.metadata.get('all.flags', 0) | (curryrt.F_BUILTIN if function.name in builtins else 0))
    out.word(not function.is_private)
    out.metadata({})
    if function.name not in builtins:
      codes.append(bytecode.compile_function(function, resolver))
    else:
      codes.append(bytecode.FunctionCode(function.fullname))
  for code in codes:
    for number in (code.nregs, code.nvars, code.nstack, len(code.code)):
      out.word(number)
    for unit in code.code:
      out.word(unit)
    out.word(len(code.consts))
    for value in code.consts:
      out.constant(value)
  # Translation summaries are separate from the executable code.
  out.word(len(module.functions))
  for function in module.functions.values():
    out.metadata(function.metadata)
  header = _facts(interp, module.filename, imports, registry)
  parsed_digest = getattr(module, '_source_digest', header['source'])
  if parsed_digest != header['source']:
    raise _InputChanged('ICurry changed during image translation')
  header['source'] = parsed_digest
  header['name'] = module.fullname
  header['body'] = hashlib.sha256(out.data).hexdigest()
  header = json.dumps(header, sort_keys=True, separators=(',', ':')).encode('ascii')
  data = PREFIX.pack(MAGIC, VERSION, len(header)) + header + out.data
  cache.write_file(path, bytes(data))
  return path


def _publication_path(interp, source, path, imports, importing=False):
  from ...toolchain import _findcurry
  source = _destination.canonical(source)
  from . import tiered
  if (importing and not _destination.staging() and
      _findcurry._installed_library_file(source)) or \
      _destination.needs_private(_filenames.icurryfilename(source),
      _destination.images(interp, imports)) or not writable(source) \
      or tiered._foreign_flags(interp):
    return _private_path(interp, source)
  return path


def ensure(interp, icyfile, currypath=None, importing=False):
  from ...toolchain import _findcurry
  with _findcurry.loader_inputs(), _findcurry.resolving(interp):
    while True:
      try:
        result = _ensure(interp, icyfile, currypath, importing)
        break
      except _InputChanged:
        pass
    generation = _findcurry.generation_for_source(icyfile, interp)
    if generation is not None and generation.image is None:
      generation.image = result[0]
      generation.digests[os.path.realpath(result[0])] = digest(result[0])
    return result


def _ensure(interp, icyfile, currypath=None, importing=False):
  icyfile = _destination.canonical(icyfile)
  source = _filenames.sourcefilename(icyfile)
  from ...toolchain import _findcurry, _interfaces, _curry2icurry
  generation = _findcurry.generation_for_source(source, interp)
  if generation is not None:
    path = generation.image
    if path is not None:
      _findcurry.verify_product(generation, path)
      imports = {name: generation_digest(dep) if dep is not None else None
          for name, dep in generation.imports}
      return path, dict(_facts(interp, source, imports), name=generation.name)
  if generation is None:
    # Explicit ICurry inputs enter at this writer too. Resolve imports before
    # testing the translation receipt, just as the normal build plan does.
    interp.import_(_interfaces.imports(icyfile), currypath=currypath)
    search = _findcurry.import_path(interp, currypath)
    search = interp.path if search is None else search
    if _curry2icurry.icurry_is_stale(icyfile, search):
      if source == icyfile or not os.path.isfile(source):
        raise ValueError('stale ICurry imports without source for rebuilding')
      with _destination.publication(importing):
        selected = _curry2icurry.curry2icurry(source, search)
      return ensure(interp, selected, currypath, importing=importing)
  path = _path(interp, source)
  if not importing:
    from . import tiered
    if not tiered._foreign_flags(interp):
      path = filename(source)
  try:
    header = _check(interp, source, path)
    imports = _import_images(interp, header['imports'], currypath)
    search = _findcurry.import_path(interp, currypath)
    if not _interfaces.is_current(icyfile, interp.path if search is None else search):
      raise ValueError('stale ICurry imports')
    path = _publication_path(interp, source, path, imports, importing)
    return path, _check(interp, source, path, imports)
  except (OSError, ValueError, KeyError, exceptions.CurryError) as exc:
    log = logger.warning if os.path.isfile(path) and str(exc) != 'stale module image' else logger.info
    log('module image %s: %s: %s; translating again', path, type(exc).__name__, exc)
  from ... import toolchain
  raw = _loadcurry.loadicurry(icyfile)
  interp.import_(raw.imports, currypath=currypath)
  imports = _import_images(interp, raw.imports, currypath)
  toolchain.mergebuiltins(raw, interp.backend)
  toolchain.validatemodule(raw)
  summaries = _summaries(interp, raw, currypath)
  imports.update(_import_images(interp,
      [getHandle(dep).fullname for dep, _ in summaries], currypath))
  from .materialize import function_primitive
  native = curryrt.Module.find_or_create(raw.fullname)
  builtins = {f.name for f in raw.functions.values()
      if function_primitive(native, f, raw) is not None}
  path = _publication_path(interp, source, path, imports, importing)
  # Imports and native summary reads precede the file lock. Only this
  # module's passes, bytecode emission and publication need serialization.
  from .toolchain import registered_names
  registry = registered_names(source)
  resolver = Resolver(interp, raw)
  with contextlib.ExitStack() as locks:
    try:
      locks.enter_context(_productlock.locked(path))
    except OSError:
      private = _private_path(interp, source)
      if path == private:
        raise
      path = private
      locks.enter_context(_productlock.locked(path))
    if raw._source_digest != digest(icyfile):
      raise _InputChanged('ICurry changed after parsing')
    try:
      header = _check(interp, source, path, registry=registry)
      return path, _check(interp, source, path,
          {name: imports[name] for name in header['imports']}, registry)
    except (OSError, ValueError, KeyError, exceptions.CurryError):
      pass
    optimize(interp, raw, currypath, summaries=summaries)
    resolver.refresh()
    imports = {name: imports[name] for name in raw.imports}
    path = _write(interp, raw, path, imports, builtins, registry, resolver)
    return path, _check(interp, source, path, imports, registry)


def load(interp, icyfile, currypath=None):
  from ...toolchain import _findcurry
  generation = _findcurry.generation_for_source(icyfile, interp)
  if generation is not None:
    return getHandle(interp.modules[generation.name]).icurry
  while True:
    path, header = ensure(interp, icyfile, currypath, importing=True)
    try:
      return attach(interp, _filenames.sourcefilename(icyfile), path, header)
    except ValueError as exc:
      if 'image changed before attachment' not in str(exc):
        raise


def current(interp, source, currypath=None):
  from ...toolchain import _findcurry
  generation = _findcurry.generation_for_source(source, interp)
  if generation is not None:
    return getHandle(interp.modules[generation.name]).icurry
  if not source:
    return None
  path = _path(interp, source)
  try:
    header = _check(interp, source, path)
    imports = _import_images(interp, header['imports'], currypath)
    if any(header[k] != v for k, v in _facts(interp, source, imports).items()):
      return None
  except (OSError, ValueError, KeyError, exceptions.CurryError):
    return None
  try:
    return attach(interp, _filenames.sourcefilename(source), path, header)
  except ValueError as exc:
    if 'image changed before attachment' not in str(exc):
      raise
    return None


def attach(interp, source, path, header):
  owner = curryrt.Module.find_or_create(header['name'])
  bom = curryrt.load_image(owner, path,
      json.dumps(header, sort_keys=True, separators=(',', ':')))
  module = _from_bom(bom, source)
  # Material tables live in the runtime module, whose lifetime must cover
  # symbol construction and publication by the importer.
  module._image_owner = owner
  module._attached_image = path
  from .jit import backend
  jit = interp.flags.get('jit', 'off')
  if (jit != 'off' and interp.flags.get('interpret') != 'off'
      and backend(interp) == 'llvm'):
    from . import llvmjit, materialize
    try:
      items = [(info, bom.fullname + '.' + info.name) for _, _, info in bom.functions
          if curryrt.icurry_is_interpreted(info) or curryrt.icurry_is_jit(info)]
      llvmjit.attach_cache(path, header, items)
      if jit == 'hot':
        llvmjit.start_hot_tier(materialize.jit_threshold())
      else:
        for _, _, info in bom.functions:
          if curryrt.icurry_bytecode(info) is not None:
            llvmjit.enqueue(info, bom.fullname + '.' + info.name)
    except llvmjit.Unavailable as exc:
      if not materialize._JIT_WARNED:
        materialize._JIT_WARNED = True
        materialize.logger.warning(
            'The JIT is unavailable; the functions stay interpreted: %s', exc)
  return module

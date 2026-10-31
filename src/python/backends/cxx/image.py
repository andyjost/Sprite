'''Portable, content-validated module images. See DeveloperNotes.rst.'''
import atexit
import contextlib
import hashlib
import json
import logging
import os
import struct

from ... import cache, icurry
from ...objects.handle import getHandle
from ...utility.binding import binding
from ...utility.strings import int_text
from ...toolchain import _filenames, _loadcurry, _productlock
from . import bytecode, curryrtbindings as curryrt

logger = logging.getLogger(__name__)
MAGIC = b'SPRTIMG\0'
VERSION = 3
PREFIX = struct.Struct('<8sII')
_SHUTDOWN_REGISTERED = False


def _stop_hot_tier():
  # Native LLVM compilation releases the GIL. Let it finish before Python
  # destroys the LLVM context and its libraries at interpreter shutdown.
  from . import llvmjit
  llvmjit._hot_enabled = False
  with llvmjit._lock:
    pass


def digest(filename):
  try:
    with open(filename, 'rb') as stream:
      return hashlib.sha256(stream.read()).hexdigest()
  except FileNotFoundError:
    return None


def filename(source):
  return _filenames.replacesuffix(source, '.img')


def read(path):
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
      for key in ('body', 'source', 'route', 'budget', 'imports', 'name')) \
      or not isinstance(header['imports'], dict):
    raise ValueError('invalid module image header')
  if encoded != json.dumps(header, sort_keys=True, separators=(',', ':')).encode('ascii'):
    raise ValueError('invalid module image header encoding')
  body = data[PREFIX.size + size:]
  if hashlib.sha256(body).hexdigest() != header['body']:
    raise ValueError('corrupt module image body')
  return header


def _facts(interp, source, imports):
  from ...toolchain._frontend import ROUTE_VERSION
  return dict(source=digest(source), route=ROUTE_VERSION,
      budget=interp.flags['inline_budget'], imports=imports)


def _import_images(interp, names, currypath):
  result = {}
  for name in names:
    module = interp.import_(name, currypath=currypath)
    h = getHandle(module)
    path = filename(h.icurry.filename)
    try:
      header = read(path)
      expected = _facts(interp, h.icurry.filename,
          {dep: digest(filename(getHandle(interp.modules[dep]).icurry.filename))
           for dep in header['imports']})
      current = all(header[k] == v for k, v in expected.items())
    except (OSError, ValueError, KeyError):
      current = False
    if not current:
      # A compiled import also needs a translation summary. Recover its
      # translation input, then use image summaries for its own imports.
      from ... import toolchain
      from ...toolchain import plans
      jsonfile = next((candidate for candidate in
          reversed(_filenames.jsonfilenames(h.icurry.filename))
          if os.path.isfile(candidate)), None)
      if jsonfile is None:
        plan = plans.makeplan(interp,
            plans.MAKE_ICURRY | plans.MAKE_JSON | plans.ZIP_JSON)
        jsonfile = toolchain.makecurry(plan, h.icurry.filename,
            currypath or interp.path, is_sourcefile=True)
      complete = _loadcurry.loadjson(jsonfile)
      toolchain.mergebuiltins(complete, interp.backend)
      toolchain.validatemodule(complete)
      optimize(interp, complete, currypath)
      write(interp, complete, currypath)
    result[name] = digest(path)
  return result


def _from_bom(bom, source):
  return icurry.IModule.fromBOM(bom.fullname, bom.imports, bom.types,
      bom.functions, 'cxx.material', filename=source, aliases=bom.aliases,
      metadata=dict(bom.metadata, **{'cxx.is_merged': True}))


def optimize(interp, module, currypath=None):
  '''Run the passes against image summaries, including for AOT imports.'''
  from ...interpreter.import_ import _provisionalModule
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
    path = filename(h.icurry.filename)
    while True:
      header = read(path)
      expected = _facts(interp, h.icurry.filename,
          {dep: digest(filename(getHandle(interp.modules[dep]).icurry.filename))
           for dep in header['imports']})
      if any(header[k] != value for k, value in expected.items()):
        _import_images(interp, [name], currypath)
        continue
      try:
        bom = curryrt.load_image(h.backend_handle, path,
            json.dumps(header, sort_keys=True, separators=(',', ':')),
            attach_code=False)
        break
      except ValueError as exc:
        if 'image changed before attachment' not in str(exc):
          raise
    summaries.append((dep, _from_bom(bom, h.icurry.filename)))
    pending.extend(header['imports'])
  for prefix in list(curryname.prefixes(module.fullname))[:-1]:
    if prefix not in interp.modules:
      package = icurry.IPackage(prefix)
      package.filename = os.path.dirname(module.filename)
      interp.import_(package)
  with interp._private_modules():
    with _provisionalModule(interp, module), contextlib.ExitStack() as stack:
      for dep, summary in summaries:
        h = getHandle(dep)
        stack.enter_context(binding(interp.modules, h.fullname, summary))
        package = interp.modules.get(h.packagename())
        package_ir = getattr(package, '.icurry', None)
        if isinstance(package_ir, icurry.IPackage):
          stack.enter_context(binding(package_ir, h.name, summary))
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
    self.interp = interp
    self.module = module
    self.local = set(module.functions) | {
        ctor.name for datatype in module.types.values()
        for ctor in datatype.constructors}

  def symbol(self, name):
    prefix = self.module.fullname + '.'
    if name.startswith(prefix) and name[len(prefix):] in self.local:
      return ('R', self.module.fullname, name[len(prefix):])
    info = self.interp.symbol(name)
    return ('R', info.icurry.modulename, info.name)

  def tag(self, name):
    ref = self.symbol(name)
    if ref[1] == self.module.fullname:
      for datatype in self.module.types.values():
        for tag, ctor in enumerate(datatype.constructors):
          if ctor.name == ref[2]:
            return tag
    return self.interp.symbol(name).info.tag

  def datatype(self, name):
    ref = self.symbol(name)
    return ('T', ref[1], ref[2])


def write(interp, module, currypath=None):
  imports = _import_images(interp, module.imports, currypath)
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
    out.word(datatype.metadata.get('all.flags', 0))
    out.metadata(datatype.metadata)
    out.word(len(datatype.constructors))
    for ctor in datatype.constructors:
      out.text(ctor.name)
      out.word(ctor.arity)
      out.word(ctor.metadata.get('all.flags', 0))
      out.metadata(ctor.metadata)
  out.word(len(module.functions))
  codes = []
  resolver = Resolver(interp, module)
  native = curryrt.Module.find_or_create(module.fullname)
  for function in module.functions.values():
    out.text(function.name)
    out.word(function.arity)
    out.word(function.metadata.get('all.flags', 0))
    out.word(not function.is_private)
    out.metadata({})
    if native.get_builtin_symbol(function.name) is None:
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
  header = _facts(interp, module.filename, imports)
  header['name'] = module.fullname
  header['body'] = hashlib.sha256(out.data).hexdigest()
  header = json.dumps(header, sort_keys=True, separators=(',', ':')).encode('ascii')
  data = PREFIX.pack(MAGIC, VERSION, len(header)) + header + out.data
  path = filename(module.filename)
  with _productlock.locked(path):
    cache.write_file(path, bytes(data))
  return path


def ensure(interp, jsonfile, currypath=None):
  source = _filenames.curryfilename(jsonfile)
  path = filename(source)
  try:
    header = read(path)
    imports = _import_images(interp, header['imports'], currypath)
    expected = _facts(interp, source, imports)
    if any(header[key] != value for key, value in expected.items()):
      raise ValueError('stale module image')
  except (OSError, ValueError, KeyError) as exc:
    log = logger.warning if os.path.isfile(path) and str(exc) != 'stale module image' else logger.info
    log('module image %s: %s; translating again', path, exc)
    from ... import toolchain
    raw = _loadcurry.loadjson(jsonfile)
    interp.import_(raw.imports, currypath=currypath)
    toolchain.mergebuiltins(raw, interp.backend)
    toolchain.validatemodule(raw)
    optimize(interp, raw, currypath)
    write(interp, raw, currypath)
    header = read(path)
  return path, header


def load(interp, jsonfile, currypath=None):
  while True:
    path, header = ensure(interp, jsonfile, currypath)
    try:
      return attach(interp, _filenames.curryfilename(jsonfile), path, header)
    except ValueError as exc:
      if 'image changed before attachment' not in str(exc):
        raise


def current(interp, source, currypath=None):
  path = filename(source)
  try:
    header = read(path)
    imports = _import_images(interp, header['imports'], currypath)
    if any(header[k] != v for k, v in _facts(interp, source, imports).items()):
      return None
  except (OSError, ValueError, KeyError):
    return None
  try:
    return attach(interp, source, path, header)
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
  from .jit import backend
  jit = interp.flags.get('jit', 'off')
  if jit != 'off' and backend(interp) == 'llvm':
    from . import llvmjit, materialize
    try:
      if jit == 'hot':
        llvmjit.start_hot_tier(materialize.jit_threshold())
        global _SHUTDOWN_REGISTERED
        if not _SHUTDOWN_REGISTERED:
          atexit.register(_stop_hot_tier)
          _SHUTDOWN_REGISTERED = True
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

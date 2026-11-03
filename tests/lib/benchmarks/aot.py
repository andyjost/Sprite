'''Budget provenance for benchmark children and saved records.

Images can be regenerated without replacing an AOT object. Its ABI stamp's
input receipt, copied from the generated C++, records the object's budget.
Never substitute the current image or interpreter budget for that receipt.
'''
import json, os, runpy, sys, tempfile


def change_time(st):
  # Windows ctime is creation time and can survive replacement. Use the
  # write clock there, together with the object and stamp identity checks.
  return st.st_mtime_ns if sys.platform == 'win32' else st.st_ctime_ns


def measurement_mark(directory=None):
  # Use the same coarse filesystem clock as the product change-time check.
  with tempfile.TemporaryFile(dir=directory) as marker:
    return change_time(os.fstat(marker.fileno()))


def object_budget(path):
  from curry.backends.cxx.toolchain import Cpp2So
  receipt = Cpp2So._read_stamp_records(path)[3]
  budget = receipt.get('budget') if isinstance(receipt, dict) else None
  return budget if type(budget) is int else None


def messages(requested, objects):
  result = []
  for name, actual in sorted(objects.items()):
    if actual == requested:
      continue
    local = name.rsplit('.', 1)[-1]
    command = ('rm -f "$(sprite-make -S)/%s.cpp" '
        '"$(sprite-make -S)/%s.so" "$(sprite-make -S)/%s.dll" '
        '"$(sprite-make -S)/%s.dylib" && '
        'SPRITE_INTERPRETER_FLAGS=inline_budget:%s sprite-make --so %s.curry'
        % (local, local, local, local, requested, local))
    result.append('%s: AOT inline budget %s, requested %s; rebuild in '
        "the module's source directory: %s" %
        (name, 'unknown' if actual is None else actual, requested, command))
  return result


def record_messages(record):
  meta = record.get('meta', {})
  requested = meta.get('requested_inline_budget')
  return sorted(set(meta.get('aot_probe_warnings', [])) | {message for objects in meta.get('aot_inline_budgets', [])
      for message in (messages(requested, objects) if objects is not None else
          ['AOT inline budget report unavailable'])})


def identity(path):
  try:
    st = os.stat(path)
    return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns]
  except OSError:
    return None


def path_key(path, path_module=os.path):
  if path_module.sep == '\\':
    if path[:8].lower() == '\\\\?\\unc\\':
      path = '\\\\' + path[8:]
    elif path.startswith('\\\\?\\'):
      path = path[4:]
  return path_module.normcase(path)


def canonical_path(path):
  return path_key(os.path.realpath(path))


class Snapshot(dict):
  def __init__(self):
    super().__init__()
    self.symlinks = {}
    self.paths = {}
    self.followed = set()

  def follow(self, path):
    # Include root ancestors and links in link targets, even when directory
    # deduplication later prevents a second walk through an alias.
    pending = [os.path.abspath(path)]
    while pending:
      current = pending.pop()
      if current in self.followed:
        continue
      self.followed.add(current)
      parent = os.path.dirname(current)
      if parent != current:
        pending.append(parent)
      if os.path.islink(current):
        try:
          target = os.readlink(current)
          self.symlinks[current] = (target, canonical_path(current))
          pending.append(os.path.abspath(os.path.join(parent, target)))
        except OSError:
          self.symlinks[current] = (None, None)


def snapshot(directories):
  # A cold command can choose its imports dynamically. Record all candidate
  # objects, without loading modules or running the command before timing.
  products, visited = Snapshot(), set()
  for directory in directories:
    products.follow(directory)
    for root, dirs, files in os.walk(directory, followlinks=True):
      for name in dirs:
        products.follow(os.path.join(root, name))
      canonical = canonical_path(root)
      if canonical in visited:
        dirs[:] = []
        continue
      visited.add(canonical)
      for filename in files:
        if filename.endswith(('.so', '.dll', '.dylib')):
          path = os.path.join(root, filename)
          for candidate in (path, path + '.abi'):
            products.follow(candidate)
            products.paths[os.path.abspath(candidate)] = canonical_path(candidate)
          products[canonical_path(path)] = dict(identity=identity(path),
              stamp_identity=identity(path + '.abi'))
  return products


def binding_changes(before):
  warnings = []
  for path, (target, resolved) in getattr(before, 'symlinks', {}).items():
    try:
      current = os.readlink(path)
    except OSError:
      current = None
    if current != target or canonical_path(path) != resolved:
      warnings.append('AOT symlink binding changed: %s (%r -> %r); '
          'all item budgets unknown' % (path, target, current))
  for path, resolved in getattr(before, 'paths', {}).items():
    if canonical_path(path) != resolved:
      warnings.append('AOT product path binding changed: %s; '
          'all item budgets unknown' % path)
  return warnings


def mapped_identity(path, generation):
  # Linux exposes the identity of the mapped file even after replacement.
  if sys.platform.startswith('linux') and generation is not None:
    with open('/proc/self/maps') as stream:
      for line in stream:
        fields = line.split()
        major, minor = (int(x, 16) for x in fields[3].split(':'))
        if (os.makedev(major, minor), int(fields[4])) == tuple(generation[:2]):
          return True
    return False
  # Without mapped-file identities, certify ordinary loader objects only
  # when their saved load-time digest still matches the current file.
  import hashlib
  loader = sys.modules.get('curry.backends.cxx.loader')
  for loaded, digest in (loader._objects.values() if loader else []):
    if loaded == path:
      try:
        with open(path, 'rb') as stream:
          return hashlib.sha256(stream.read()).hexdigest() == digest
      except OSError:
        return False
  return False


def write_report(filename):
  objects = {}
  runtime = sys.modules.get('curry.backends.cxx.curryrtbindings')
  if runtime is not None:
    for name, module in runtime.Module.getall().items():
      path = runtime.SharedCurryModule.find_sofilename(name)
      if path is None:
        continue
      before = identity(path)
      stamp = identity(path + '.abi')
      budget = object_budget(path)
      if (before != identity(path) or stamp != identity(path + '.abi')
          or not mapped_identity(path, before)):
        budget = None
      # Preserve the runtime's spelling: it may be lexical or canonical.
      # The parent checks canonical identities and saved lexical bindings.
      objects[name] = dict(path=path, identity=before,
          stamp_identity=stamp, budget=budget)
  with open(filename, 'w', encoding='ascii') as stream:
    json.dump(objects, stream, sort_keys=True)


def checked_budgets(probe, since=None, before=None):
  if probe is None:
    return None, []
  warnings = binding_changes(before)
  if warnings:
    return {name: None for name in probe}, warnings
  budgets = {}
  for name, obj in probe.items():
    changed = (obj['identity'] is None or
        identity(obj['path']) != obj['identity'] or
        identity(obj['path'] + '.abi') != obj['stamp_identity'])
    if before is not None:
      baseline = before.get(canonical_path(obj['path']))
      changed |= (baseline is None or
          baseline['identity'] != obj['identity'] or
          baseline['stamp_identity'] != obj['stamp_identity'])
    if since is not None:
      # A postmeasurement probe cannot certify a generation made during
      # measurement (or by the probe itself). Check stamps as well as objects.
      for path in (obj['path'], obj['path'] + '.abi'):
        try:
          changed |= change_time(os.stat(path)) >= since
        except OSError:
          pass
    budgets[name] = None if changed else obj['budget']
    if changed:
      warnings.append('%s: AOT object generation changed %s; budget unknown' %
          (name, 'during measurement or probe' if since is not None else 'after probe'))
  return budgets, warnings


def adoption_possible(mode):
  flags = mode.get('flags') or {}
  return (mode.get('backend') == 'cxx' and flags.get('jit') in ('hot', 'eager')
      and flags.get('interpret') != 'off')


def main():
  filename, kind, *args = sys.argv[1:]
  try:
    execute(kind, args)
  finally:
    # Report before temporary-module atexit cleanup removes fresh objects.
    write_report(filename)


def execute(kind, args):
  sys.argv = args
  if kind == 'module':
    sys.argv = ['sprite-exec'] + args
    runpy.run_module('curry', run_name='__main__', alter_sys=True)
  elif args[0] == '-c':
    sys.argv = ['-c'] + args[2:]
    exec(compile(args[1], '<string>', 'exec'), {'__name__': '__main__'})
  else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(args[0])))
    runpy.run_path(args[0], run_name='__main__')


if __name__ == '__main__':
  main()

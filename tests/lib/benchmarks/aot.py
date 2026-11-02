'''Budget provenance for benchmark children and saved records.

Images can be regenerated without replacing an AOT object. Its ABI stamp's
input receipt, copied from the generated C++, records the object's budget.
Never substitute the current image or interpreter budget for that receipt.
'''
import atexit, json, os, runpy, sys


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
  return sorted({message for objects in meta.get('aot_inline_budgets', [])
      for message in (messages(requested, objects) if objects is not None else
          ['AOT inline budget report unavailable'])})


def write_report(filename):
  curry = sys.modules.get('curry')
  objects = {}
  if curry is not None:
    loader = sys.modules.get('curry.backends.cxx.loader')
    if loader is not None:
      for name, (path, digest) in loader._objects.copy().items():
        objects[name] = object_budget(path)
  with open(filename, 'w', encoding='ascii') as stream:
    json.dump(objects, stream, sort_keys=True)


def main():
  filename, kind, *args = sys.argv[1:]
  atexit.register(write_report, filename)
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

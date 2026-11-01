# timing.py: the numbers of the README.  ./run never calls it.
#
#   python timing.py [DIR]
#
# prints the median of 100 calls of touches 'shape.h', after 100 warm calls,
# in Curry and in plain Python over the same six rules as a dict, then two
# questions on a generated build of 272 targets, with the time each module
# took to import.  The generated module goes to DIR, or to a temporary
# directory; a second run with the same DIR imports its saved translation.
# The script measures the interpreter, jit:off, unless the environment sets
# SPRITE_INTERPRETER_FLAGS.
import os, statistics, sys, tempfile, time
os.environ.setdefault('SPRITE_INTERPRETER_FLAGS', 'jit:off')
import curry
here = os.path.dirname(os.path.abspath(__file__))
curry.path.insert(0, here)
start = time.perf_counter()
from curry.lib import Build
print(f"the import of Build.curry took {time.perf_counter() - start:.2f} s")
flags = os.environ['SPRITE_INTERPRETER_FLAGS']

def median_ms(f, n=100):
    for _ in range(n):
        f()
    times = []
    for _ in range(n):
        start = time.perf_counter()
        f()
        times.append(time.perf_counter() - start)
    return 1000 * statistics.median(times)

def curry_touches(module, changed):
    return sorted(set(curry.eval(module.touches(changed))))

# The six rules again, as the dict you would keep in step with them.
NEEDS = {
    'demo':      ['main.o', 'report.o', 'libgeom.a'],
    'libgeom.a': ['vec.o', 'shape.o'],
    'main.o':    ['main.c', 'shape.h', 'vec.h'],
    'report.o':  ['report.c', 'vec.h'],
    'shape.o':   ['shape.c', 'shape.h', 'vec.h'],
    'vec.o':     ['vec.c', 'vec.h'],
}

# The six lines you would write over the dict: every target forward, and the
# ones whose walk reaches the file.  The test `in` stops at the first path
# to a target; touches in Curry finds every path.
def depends(rules, target):
    for f in rules.get(target, []):
        yield f
        yield from depends(rules, f)

def touches(rules, changed):
    return sorted(t for t in rules if changed in depends(rules, t))

def report(name, module, rules, changed):
    values = list(curry.eval(module.touches(changed)))
    assert sorted(set(values)) == touches(rules, changed)
    in_curry = median_ms(lambda: curry_touches(module, changed))
    in_python = median_ms(lambda: touches(rules, changed))
    edges = sum(map(len, rules.values()))
    print(f"touches '{changed}' over the {len(rules)} rules and {edges} edges "
          f"of {name}: {len(values)} values, {len(set(values))} targets; "
          f"Curry {in_curry:.2f} ms, Python {in_python:.4f} ms "
          f"(median of 100 calls after 100 warm calls, {flags})")

report('Build.curry', Build, NEEDS, 'shape.h')

# A build of 272 targets: 8 programs of 3 libraries each, 24 libraries of 10
# objects each, and 240 objects, each of a source, a header of its own and
# one header shared by all.
def big_rules():
    rules = {}
    for p in range(8):
        rules[f'prog{p}'] = [f'lib{l}.a' for l in range(3 * p, 3 * p + 3)]
    for l in range(24):
        rules[f'lib{l}.a'] = [f'mod{m}.o' for m in range(10 * l, 10 * l + 10)]
    for m in range(240):
        rules[f'mod{m}.o'] = [f'mod{m}.c', f'mod{m}.h', 'common.h']
    return rules

def write_module(rules, directory):
    def literal(files):
        return '[' + ', '.join(f'"{f}"' for f in files) + ']'
    lines = ['module Big where', '', 'needs :: String -> [String]']
    lines += [f'needs "{t}" = {literal(fs)}' for t, fs in rules.items()]
    lines += ['', 'depends :: String -> String',
              'depends t = anyOf [f ? depends f | f <- needs t]', '',
              'touches :: String -> String', 'touches (depends t) = t', '']
    text = '\n'.join(lines)
    path = os.path.join(directory, 'Big.curry')
    if not (os.path.exists(path) and open(path).read() == text):
        with open(path, 'w') as stream:
            stream.write(text)

def measure_big(directory):
    rules = big_rules()
    write_module(rules, directory)
    curry.path.insert(0, directory)
    start = time.perf_counter()
    from curry.lib import Big
    print(f"the import of Big.curry took {time.perf_counter() - start:.2f} s")
    report('Big.curry', Big, rules, 'mod17.h')    # a header one object includes
    report('Big.curry', Big, rules, 'common.h')   # the header all objects include

if len(sys.argv) > 1:
    os.makedirs(sys.argv[1], exist_ok=True)
    measure_big(sys.argv[1])
else:
    with tempfile.TemporaryDirectory() as directory:
        measure_big(directory)

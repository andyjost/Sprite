"""Python algorithms paired with the deterministic Curry throughput goals.

Values are checked against Sprite before a timing can enter the record.
Peano is compared by its unary length, without timing the conversion.
"""
import itertools, json, sys, time

def tak(x, y, z):
    if x <= y:
        return z
    return tak(tak(x - 1, y, z), tak(y - 1, z, x), tak(z - 1, x, y))

def tak1():
    return tak(27, 16, 8)

def queens10():
    nq = 10
    def safe(x, d, l):
        for q in l:
            if x == q or x == q + d or x == q - d:
                return False
            d += 1
        return True
    def gen(n):
        if n == 0:
            return [[]]
        return [[q] + b for b in gen(n - 1) for q in range(1, nq + 1) if safe(q, 1, b)]
    return len(gen(nq))

def primes():
    def the_filter(ns):
        n = next(ns)
        return n, (x for x in ns if x % n != 0)
    stream = itertools.count(2)
    for i in range(2001):  # at primes 2000: index 2000 of the stream, the 2001st prime
        p, stream = the_filter(stream)
    return p

class O: __slots__ = ()
class S:
    __slots__ = ('n',)
    def __init__(self, n): self.n = n
O_ = O()
def add(a, b):
    # add O n = n ; add (S n) m = S (add n m)  -- iterative to avoid the recursion depth
    k = 0
    while isinstance(a, S):
        a = a.n; k += 1
    r = b
    for _ in range(k):
        r = S(r)
    return r
def times(a, b):
    # times O _ = O ; times (S n) m = add (times n m) m
    if isinstance(a, O):
        return O_
    return add(times(a.n, b), b)
def count(n):
    k = 0
    while isinstance(n, S):
        n = n.n; k += 1
    return k
def peano():
    one = S(O_); two = S(S(O_)); three = add(one, two); four = add(two, two)
    five = add(two, three); six = add(three, three); seven = add(three, four)
    r = one
    for m in (two, three, four, five, six, seven):
        r = times(r, m)
    return count(r)


def palindrome():
    return [str(n) == str(n)[::-1] for n in range(1, 50001)]


def quicksort(values):
    if not values:
        return []
    pivot, rest = values[0], values[1:]
    return (quicksort([v for v in rest if v < pivot]) + [pivot]
            + quicksort([v for v in rest if v >= pivot]))


def qsortlet(values):
    if not values:
        return []
    pivot, rest = values[0], values[1:]
    left, right = [], []
    for value in rest:
        (left if value <= pivot else right).append(value)
    return qsortlet(left) + [pivot] + qsortlet(right)


def hamming():
    def merge(xs, ys):
        x, y = next(xs), next(ys)
        while True:
            if x == y:
                yield x
                x, y = next(xs), next(ys)
            elif x < y:
                yield x
                x = next(xs)
            else:
                yield y
                y = next(ys)
    def stream():
        yield 1
        yield from merge((n * 2 for n in stream()),
                         merge((n * 3 for n in stream()),
                               (n * 5 for n in stream())))
    return list(itertools.islice(stream(), 200))


def psort():
    def perms(values):
        if not values:
            yield []
        else:
            for rest in perms(values[1:]):
                for i in range(len(rest) + 1):
                    yield rest[:i] + values[:1] + rest[i:]
    return next(values for values in perms(list(range(10, 0, -1)))
                if all(a <= b for a, b in zip(values, values[1:])))


def takpeano():
    def leq(a, b):
        while isinstance(a, S) and isinstance(b, S):
            a, b = a.n, b.n
        return isinstance(a, O)
    def takeuchi(x, y, z):
        if leq(x, y):
            return z
        return takeuchi(takeuchi(x.n, y, z), takeuchi(y.n, z, x),
                        takeuchi(z.n, x, y))
    def unary(n):
        value = O_
        for _ in range(n):
            value = S(value)
        return value
    return count(takeuchi(unary(24), unary(16), unary(8)))


PROGRAMS = {'Tak1': tak1, 'Queens10': queens10, 'Primes': primes, 'Peano': peano,
    'Palindrome': palindrome, 'Hamming': hamming, 'Psort': psort, 'TakPeano': takpeano,
    'Quicksort': lambda: quicksort(list(range(1001, 3001)) + list(range(1, 1001))),
    'Qsortlet': lambda: qsortlet(list(range(501, 1001)) + list(range(1, 501)))}
EXPECTED = {'Tak1': 16, 'Queens10': 724, 'Primes': 17393, 'Peano': 5040,
    'Hamming': [1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 15, 16, 18, 20, 24, 25, 27, 30, 32, 36, 40, 45,
        48, 50, 54, 60, 64, 72, 75, 80, 81, 90, 96, 100, 108, 120, 125, 128, 135, 144, 150,
        160, 162, 180, 192, 200, 216, 225, 240, 243, 250, 256, 270, 288, 300, 320, 324, 360,
        375, 384, 400, 405, 432, 450, 480, 486, 500, 512, 540, 576, 600, 625, 640, 648, 675,
        720, 729, 750, 768, 800, 810, 864, 900, 960, 972, 1000, 1024, 1080, 1125, 1152, 1200,
        1215, 1250, 1280, 1296, 1350, 1440, 1458, 1500, 1536, 1600, 1620, 1728, 1800, 1875,
        1920, 1944, 2000, 2025, 2048, 2160, 2187, 2250, 2304, 2400, 2430, 2500, 2560, 2592,
        2700, 2880, 2916, 3000, 3072, 3125, 3200, 3240, 3375, 3456, 3600, 3645, 3750, 3840,
        3888, 4000, 4050, 4096, 4320, 4374, 4500, 4608, 4800, 4860, 5000, 5120, 5184, 5400,
        5625, 5760, 5832, 6000, 6075, 6144, 6250, 6400, 6480, 6561, 6750, 6912, 7200, 7290,
        7500, 7680, 7776, 8000, 8100, 8192, 8640, 8748, 9000, 9216, 9375, 9600, 9720, 10000,
        10125, 10240, 10368, 10800, 10935, 11250, 11520, 11664, 12000, 12150, 12288, 12500,
        12800, 12960, 13122, 13500, 13824, 14400, 14580, 15000, 15360, 15552, 15625, 16000,
        16200], 'Psort': list(range(1, 11)), 'TakPeano': 9,
    'Palindrome': [str(n) == str(n)[::-1] for n in range(1, 50001)],
    'Quicksort': list(range(1, 3001)), 'Qsortlet': list(range(1, 1001))}


def check(program, value):
    expected = EXPECTED[program]
    if value != expected:
        raise ValueError('%s counterpart value %r differs from %r'
                         % (program, value, expected))


def curry_value(program, text):
    lines = text.strip().splitlines()
    # sprite-exec -t prints a timing after the value.
    value = lines[0].strip() if lines else ''
    if program in ('Peano', 'TakPeano'):
        return value.count('S') if value.count('O') == 1 else None
    if program in ('Palindrome', 'Quicksort', 'Qsortlet', 'Hamming', 'Psort'):
        try:
            return json.loads(value.replace('True', 'true').replace('False', 'false'))
        except ValueError:
            return None
    try:
        return int(value)
    except ValueError:
        return None


def main():
    sys.setrecursionlimit(100000)
    program = sys.argv[1]
    start_cpu, start_wall = time.process_time(), time.perf_counter()
    value = PROGRAMS[program]()
    elapsed_cpu = time.process_time() - start_cpu
    elapsed_wall = time.perf_counter() - start_wall
    check(program, value)
    print(json.dumps(dict(value=value, eval_cpu=elapsed_cpu, eval_wall=elapsed_wall)))


if __name__ == '__main__':
    main()

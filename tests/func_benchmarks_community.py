'''
One value goal per supported community benchmark, with the PAKCS 3.4.1
answers committed beside the sources. Set SPRITE_BENCHMARK_VERIFY_ORACLE=1
to check those answers with the oracle of the selected installation too.
Original sources are never rewritten to make a benchmark finish.
'''
import cytest # from ./lib; must be first
from cytest import oracle
from benchmarks.suites import community_programs
import json, os, pathlib, shutil, subprocess, tempfile

ORACLE_TIMEOUT = 20
SPRITE_TIMEOUT = 30
# Programs whose original workload exceeds the functional oracle budget.
ORACLE_LIMITS = {
    'curry2go-1.7.0-suite/NRev',
    'curry2go-1.7.0-suite/PermSort',
    'curry2go-1.7.0-suite/PermSortPeano',
    'curry2go-1.7.0-suite/PrimesHO',
    'curry2go-1.7.0-suite/Queens',
    'curry2go-1.7.0-suite/ReverseHO',
    'curry2go-1.7.0-suite/SortPrimes',
    'curry2go-1.7.0-suite/TakInt',
    'curry2go-1.7.0-suite/TakPeano',
    'kics2-3.5.0-suite/PrimesPeano',
    'kics2-3.5.0-suite/Queens',
    'kics2-3.5.0-suite/QueensUser',
    'kics2-3.5.0-suite/ShareNonDet',
    'kics2-3.5.0-suite/TakPeano',
  }


class TestCommunityBenchmarks(cytest.TestCase):
  def check_program(self, program, filename):
    if program in ORACLE_LIMITS:
      self.skipTest('PAKCS 3.4.1 exceeds the 20-second functional budget')
    source = pathlib.Path(filename)
    golden = source.with_suffix('.main.au-gen')
    self.assertTrue(golden.is_file(), 'missing PAKCS 3.4.1 golden: ' + program)
    expected = golden.read_text()
    if os.environ.get('SPRITE_BENCHMARK_VERIFY_ORACLE') == '1':
      # Sprite's interfaces use its shipped Prelude. Native PAKCS 3.4.1
      # has another Prelude, so its compiler needs a separate product tree.
      with tempfile.TemporaryDirectory(prefix='sprite-benchmark-oracle-') as work:
        shutil.copytree(
            source.parent, work, dirs_exist_ok=True
          , ignore=shutil.ignore_patterns('.curry', '*.au-gen')
          )
        env = dict(os.environ, CURRYPATH=work, LC_ALL='C.UTF-8')
        proc = subprocess.run(
            cytest.limit_prefix(address_space=6 << 30, timeout=ORACLE_TIMEOUT)
            + [oracle.oracle(), source.stem, source.stem + '.main']
          , cwd=work, env=env, capture_output=True, text=True
          )
      self.assertEqual(proc.returncode, 0, proc.stderr)
      self.assertSameResultMultiset(proc.stdout, expected)
    code = (
        'import curry, json\n'
        "curry.reset(interpret='off')\n"
        'curry.path.insert(0, %r)\n'
        'module = curry.import_(%r)\n'
        'print(json.dumps([curry.show(v) for v in curry.eval(module.main)]))\n'
      ) % (str(source.parent), source.stem)
    proc = cytest.run_in_subprocess(
        code, timeout=SPRITE_TIMEOUT, address_space=6 << 30
      )
    evidence = os.environ.get('SPRITE_BENCHMARK_EVIDENCE')
    if evidence:
      with open(evidence, 'a') as stream:
        stream.write(json.dumps(dict(
            program=program, oracle=expected, sprite=proc.stdout
          , status=proc.returncode, stderr=proc.stderr
          )) + '\n')
    self.assertEqual(proc.returncode, 0, proc.stderr)
    actual = '\n'.join(json.loads(proc.stdout))
    self.assertSameResultMultiset(actual, expected)


def value_test(program, filename):
  def test(self):
    self.check_program(program, filename)
  test.__doc__ = program + '.main'
  return oracle.require(test)


for _program, _filename in community_programs().items():
  _name = 'test_' + _program.replace('/', '_').replace('-', '_').replace('.', '_')
  setattr(TestCommunityBenchmarks, _name, value_test(_program, _filename))

'''Issue #184: runtime module tables belong to their interpreter.'''
import cytest # from ./lib; must be first
import curry
from curry import config
from pathlib import Path
import tempfile
import unittest


class TestIssue184(cytest.TestCase):
  def run_child(self, code):
    child = cytest.run_in_subprocess(code, timeout=180)
    self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
    return child.stdout

  def test_edited_module_in_second_interpreter(self):
    for flags in ({}, {'interpret': 'all', 'jit': 'off'}):
      with self.subTest(flags=flags):
        output = self.run_child(r'''
from curry.interpreter import Interpreter
from pathlib import Path
import tempfile
with tempfile.TemporaryDirectory() as work:
    source = Path(work) / 'Separate.curry'
    source.write_text('module Separate where\nvalue :: Int\nvalue = 1\n')
    first = Interpreter(flags=%r)
    first.path.insert(0, work)
    a = first.import_('Separate')
    assert list(first.eval(a.value)) == [1]
    source.write_text('module Separate where\nvalue :: Int\nvalue = 2\n')
    second = Interpreter(flags=%r)
    second.path.insert(0, work)
    b = second.import_('Separate')
    values = list(second.eval(b.value))
    print('second', values)
    assert values == [2], values
    assert list(first.eval(a.value)) == [1]
''' % (flags, flags))
        self.assertIn('second [2]', output)

  def test_path_copy_and_installed_module_in_either_order(self):
    original = Path(config.installed_path('curry', 'Data/Char.curry')).read_text()
    edited = original.replace("ord c - ord '0'", "ord c - ord '0' + 1")
    self.assertNotEqual(original, edited)
    for mode in ('new', 'all'):
      for override_first in (True, False):
        with self.subTest(mode=mode, override_first=override_first):
          self.run_child(r'''
from curry.interpreter import Interpreter
from pathlib import Path
import tempfile
with tempfile.TemporaryDirectory() as work:
    source = Path(work) / 'Data' / 'Char.curry'
    source.parent.mkdir()
    source.write_text(%r)
    changed = Interpreter(flags={'interpret': %r, 'jit': 'off'})
    normal = Interpreter(flags={'interpret': %r, 'jit': 'off'})
    changed.path.insert(0, work)
    ordered = [changed, normal] if %r else [normal, changed]
    loaded = [(interp, interp.import_('Numeric')) for interp in ordered]
    for interp, module in loaded:
        values = list(interp.eval(module.readNat('1')))
        expected = [[(2, '')]] if interp is changed else [[(1, '')]]
        assert values == expected, (values, expected)
    # Repeat after both registries have their modules.
    for interp, module in loaded:
        values = list(interp.eval(module.readNat('1')))
        assert values == ([[(2, '')]] if interp is changed else [[(1, '')]])
''' % (edited, mode, mode, override_first))

  def test_reset_preserves_other_interpreter_and_prelude(self):
    for mode in ('new', 'all'):
      with self.subTest(mode=mode):
        self.run_child(r'''
from curry.interpreter import Interpreter
from curry.objects.handle import getHandle
flags = {'interpret': %r, 'jit': 'off'}
first = Interpreter(flags=flags)
second = Interpreter(flags=flags)
a = first.compile('value :: Int\nvalue = 11', modulename='ResetSeparate')
b = second.compile('value :: Int\nvalue = 22', modulename='ResetSeparate')
prelude = getHandle(second.prelude).backend_handle
assert (prelude is getHandle(first.prelude).backend_handle) == (flags['interpret'] == 'new')
for _ in range(2):
    first.reset()
    assert (getHandle(first.prelude).backend_handle is prelude) == (flags['interpret'] == 'new')
    assert list(second.eval(b.value)) == [22]
    assert list(second.eval(getattr(second.prelude, '+')(1, 2))) == [3]
    assert list(first.eval(getattr(first.prelude, '+')(3, 4))) == [7]
''' % mode)

  def test_show_ordering_after_reset(self):
    for mode in ('new', 'all'):
      with self.subTest(mode=mode):
        self.run_child(r'''
import os
os.environ['SPRITE_INTERPRETER_FLAGS'] = 'interpret:%s,jit:off'
import curry
held = curry.eval(curry.parse('compare (1 :: Int) 2')).one()
assert curry.show(held) == 'LT'
curry.reset()
current = curry.eval(curry.parse('compare (1 :: Int) 2')).one()
assert curry.show(current) == 'LT'
''' % mode)

  def test_show_ordering_in_other_interpreter_after_reset(self):
    for mode in ('new', 'all'):
      with self.subTest(mode=mode):
        self.run_child(r'''
import curry
from curry.interpreter import Interpreter
flags = {'interpret': %r, 'jit': 'off'}
first = Interpreter(flags=flags)
second = Interpreter(flags=flags)
held = first.eval(first.prelude.compare(1, 2)).one()
assert curry.show(held) == 'LT'
first.reset()
current = second.eval(second.prelude.compare(1, 2)).one()
assert curry.show(current) == 'LT'
''' % mode)

  def test_constructor_class_identity_and_stale_term_use(self):
    for mode in ('new', 'all'):
      with self.subTest(mode=mode):
        self.run_child(r'''
import curry
import unittest
from curry.interpreter import Interpreter
interp = Interpreter(flags={'interpret': %r, 'jit': 'off'})
held = type(interp.prelude.LT)
interp.reset()
current = type(interp.prelude.LT)
assert not (held == current)
assert not (current == held)
assert held == held
assert current == current
assert not (current == type(interp.prelude.GT))
assert not (current == object())
term = interp.eval(interp.prelude.LT).one()
assert current == term
check = unittest.TestCase()
for use in (lambda: held(), lambda: hash(held),
            lambda: curry.show(held), lambda: held == term):
    with check.assertRaises(curry.StaleError):
        use()
''' % mode)

  def test_reset_does_not_hide_a_shared_dependency(self):
    self.run_child(r'''
from curry.interpreter import Interpreter
from curry.objects.handle import getHandle
from pathlib import Path
import tempfile
with tempfile.TemporaryDirectory() as work:
    source = Path(work) / 'RegistryDependency.curry'
    source.write_text('module RegistryDependency where\nf :: Int -> Int\n'
                      'f n = if n == 0 then 1 else f (n - 1) + 1\n')
    first = Interpreter(flags={'interpret': 'new', 'jit': 'off'})
    first.path.insert(0, work)
    held = first.import_('RegistryDependency')
    assert not getHandle(held).backend_handle.shared
    first.reset()
    compiler = Interpreter(flags={'interpret': 'off', 'jit': 'off'})
    compiler.path.insert(0, work)
    compiled = compiler.import_('RegistryDependency')
    assert getHandle(compiled).backend_handle.shared
    caller = Path(work) / 'RegistryCaller.curry'
    caller.write_text('module RegistryCaller where\nimport RegistryDependency\n'
                      'value :: Int\nvalue = f 41\n')
    module = first.import_('RegistryCaller')
    assert first.eval(module.value).one() == 42
    assert getHandle(first.modules['RegistryDependency']).backend_handle is getHandle(compiled).backend_handle
''')

  def test_queries_do_not_claim_private_tables(self):
    self.run_child(r'''
from curry.interpreter import Interpreter
from curry.objects.handle import getHandle
from curry.backends.cxx import curryrtbindings as rt
from pathlib import Path
import tempfile
with tempfile.TemporaryDirectory() as work:
    source = Path(work) / 'RegistryQuery.curry'
    source.write_text('module RegistryQuery where\nf :: Int\nf = 7\n')
    compiler = Interpreter(flags={'interpret': 'off', 'jit': 'off'})
    compiler.path.insert(0, work)
    compiled = compiler.import_('RegistryQuery')
    shared = getHandle(compiled).backend_handle
    other = Interpreter(flags={'interpret': 'all', 'jit': 'off'})
    other.path.insert(0, work)
    assert rt.Module.find_or_create(other._its, 'RegistryQuery') is shared
    interpreted = other.import_('RegistryQuery')
    assert not getHandle(interpreted).backend_handle.shared
    assert getHandle(interpreted).backend_handle is not shared
    assert other.eval(interpreted.f).one() == 7
    other.reset()
    assert rt.Module.find_or_create(other._its, 'RegistryQuery') is shared
''')

  def test_llvm_hot_swap_is_private(self):
    try:
      import llvmlite
    except ImportError:
      self.skipTest('llvmlite is unavailable')
    self.run_child(r'''
import os, time, tempfile
from pathlib import Path
os.environ['SPRITE_JIT_THRESHOLD'] = '5'
from curry.interpreter import Interpreter
from curry.backends.cxx import curryrtbindings as rt, llvmjit
flags = {'interpret': 'all', 'jit': 'hot', 'jit_backend': 'llvm', 'inline_budget': 0}

def hot(interp, module, expected, name='f'):
    function = getattr(module, name)
    deadline = time.monotonic() + 30
    while not rt.icurry_is_jit(function.info):
        assert time.monotonic() < deadline, llvmjit.statistics()
        assert interp.eval(function(10)).one() == expected
        time.sleep(0.02)
    assert interp.eval(function(10)).one() == expected

with tempfile.TemporaryDirectory() as work:
    source = Path(work) / 'HotSeparate.curry'
    template = ('module HotSeparate where\nf :: Int -> Int\n'
                'f n = if n == 0 then %d else f (n - 1) + 1\n'
                'g :: Int -> Int\ng n = if n == 0 then f 0 else g (n - 1) + 1\n')
    source.write_text(template % 1)
    first = Interpreter(flags=flags)
    first.path.insert(0, work)
    a = first.import_('HotSeparate')
    hot(first, a, 11)
    # Attach a different image after the first generation has linked code.
    source.write_text(template % 2)
    quiet = Interpreter(flags=dict(flags, jit='off'))
    second = Interpreter(flags=flags)
    second.path.insert(0, work)
    b = second.import_('HotSeparate')
    assert a.f.info is not b.f.info
    assert first.eval(a.f(10)).one() == 11
    hot(second, b, 12)
    assert first.eval(a.f(10)).one() == 11
    first.reset()
    assert second.eval(b.f(10)).one() == 12
    quiet.reset()
    hot(second, b, 12, 'g')
    # Equal image bodies still need constants bound to their own tables.
    again = first.import_('HotSeparate')
    hot(first, again, 12)
    second.reset()
    assert first.eval(again.f(10)).one() == 12
''')

  def test_reserved_importer_keeps_private_imports(self):
    original = Path(config.installed_path('curry', 'Data/List.curry')).read_text()
    edited = original.replace('minimum xs@(_:_) =  foldl1 min xs',
                              'minimum xs@(_:_) =  maximum xs')
    self.assertNotEqual(original, edited)
    for mode in ('all', 'new'):
      for changed_first in (True, False):
        with self.subTest(mode=mode, changed_first=changed_first):
          self.run_child(r'''
from curry.interpreter import Interpreter
from curry.objects.handle import getHandle
from pathlib import Path
import tempfile
with tempfile.TemporaryDirectory() as work:
    source = Path(work) / 'Data' / 'List.curry'
    source.parent.mkdir()
    source.write_text(%r)
    flags = {'interpret': %r, 'jit': 'off', 'inline_budget': 0}
    changed, normal = Interpreter(flags=flags), Interpreter(flags=flags)
    changed.path.insert(0, work)
    ordered = [changed, normal] if %r else [normal, changed]
    def load(interp):
        return interp.compile('import Control.SetFunctions\n'
            'value :: Int\nvalue = minValue (set0 (1 ? 2))\n',
            modulename='ReservedCaller')
    loaded = [(interp, load(interp)) for interp in ordered]
    for interp, module in loaded:
        values = list(interp.eval(module.value))
        assert values == ([2] if interp is changed else [1]), values
    a = getHandle(changed.modules['Control.SetFunctions']).backend_handle
    b = getHandle(normal.modules['Control.SetFunctions']).backend_handle
    assert a is not b
    assert not a.shared
    assert b.shared == (flags['interpret'] == 'new')
    changed.reset()
    again = load(changed)
    assert list(changed.eval(again.value)) == [2]
    normal_module = next(m for i, m in loaded if i is normal)
    assert list(normal.eval(normal_module.value)) == [1]
''' % (edited, mode, changed_first))

  @cytest.posix_only('multiple compiled generations of one name')
  def test_compiled_caller_uses_selected_dependency(self):
    self.run_child(r'''
import os
os.environ['SPRITE_INTERPRETER_FLAGS'] = 'inline_budget:0'
from curry.interpreter import Interpreter
from pathlib import Path
import tempfile
with tempfile.TemporaryDirectory() as work:
    roots = [Path(work) / name for name in ('a', 'b')]
    flags = {'interpret': 'off', 'jit': 'off', 'inline_budget': 0}
    first, second = Interpreter(flags=flags), Interpreter(flags=flags)
    for interp, root, value in zip((first, second), roots, (11, 22)):
        root.mkdir()
        (root / 'SlotDep.curry').write_text('module SlotDep where\n'
            'f :: Int -> Int\nf n = if n == 0 then %d else f (n - 1)\n' % value)
        interp.path.insert(0, str(root))
        dep = interp.import_('SlotDep')
        assert interp.eval(dep.f(1)).one() == value
    from curry.backends.cxx import curryrtbindings as rt
    from curry.objects.handle import getHandle
    for interp, root, expected in ((first, roots[0], 11), (second, roots[1], 22)):
        actual = interp.eval(interp.modules['SlotDep'].f(1)).one()
        assert actual == expected
        assert rt.Module.find_or_create(interp._its, 'SlotDep') is getHandle(interp.modules['SlotDep']).backend_handle
        (root / 'SlotCaller.curry').write_text('module SlotCaller where\n'
            'import SlotDep\nvalue :: Int\nvalue = f 1\n')
        module = interp.import_('SlotCaller')
        values = list(interp.eval(module.value))
        assert values == [expected], (values, expected)
    original = getHandle(first.modules['SlotCaller']).backend_handle.shlib
    reopened = rt.SharedCurryModule(original.sofilename(), second._its)
    assert list(first.eval(first.modules['SlotCaller'].value)) == [11]
''')

  @cytest.posix_only('multiple compiled generations of one name')
  def test_cxx_hot_jobs_are_private(self):
    self._cxx_private_jobs(False)

  @cytest.posix_only('multiple compiled generations of one name')
  def test_reset_preserves_other_cxx_hot_job(self):
    self._cxx_private_jobs(True)

  @cytest.posix_only('multiple compiled generations of one name')
  def test_reset_preserves_other_running_cxx_job(self):
    self._cxx_private_jobs(True, running=True)

  def _cxx_private_jobs(self, reset, running=False):
    self.run_child(r'''
import os, time, tempfile
from pathlib import Path
os.environ['SPRITE_JIT_THRESHOLD'] = '5'
from curry.interpreter import Interpreter
from curry.backends.cxx import curryrtbindings as rt, tiered
from curry.objects.handle import getHandle
flags = {'interpret': 'new', 'jit': 'hot', 'jit_backend': 'cxx', 'inline_budget': 0}
with tempfile.TemporaryDirectory() as work:
    first, second = Interpreter(flags=flags), Interpreter(flags=flags)
    running = %r
    gate = Path(work) / 'release'
    entered = Path(work) / 'entered'
    if running:
        import sys
        arm = rt.cxx_arm
        def blocked(*args):
            args = list(args)
            wrapper = ("import os, sys, time\nfrom pathlib import Path\n"
                "Path(sys.argv[1]).touch()\n"
                "while not Path(sys.argv[2]).exists(): time.sleep(0.01)\n"
                "os.execv(sys.argv[3], sys.argv[3:])\n")
            args[2] = [sys.executable, '-c', wrapper, str(entered), str(gate)] + args[2]
            return arm(*args)
        rt.cxx_arm = blocked
    modules = []
    for interp, name, value in ((first, 'a', 11), (second, 'b', 22)):
        root = Path(work) / name
        root.mkdir()
        (root / 'PrivateHot.curry').write_text('module PrivateHot where\n'
            'f :: Int -> Int\nf n = if n == 0 then %%d else f (n - 1)\n' %% value)
        interp.path.insert(0, str(root))
        modules.append(interp.import_('PrivateHot'))
    if running:
        for _ in range(6):
            assert second.eval(modules[1].f(1)).one() == 22
        deadline = time.monotonic() + 30
        while not entered.exists():
            assert time.monotonic() < deadline, tiered.status()
            time.sleep(0.01)
        assert tiered.status()['running'] == 1
    if %r:
        first.reset()
        gate.touch()
        selected = [(second, modules[1], 22)]
    else:
        selected = [(first, modules[0], 11), (second, modules[1], 22)]
    for interp, module, expected in selected:
        for _ in range(6):
            assert interp.eval(module.f(1)).one() == expected
        assert tiered.wait(timeout=90, interp=interp)
        assert getHandle(module).backend_handle.shlib is not None, tiered.status()
        assert interp.eval(module.f(1)).one() == expected
    for interp, module, expected in selected:
        assert interp.eval(module.f(1)).one() == expected
    tiered.finish()
''' % (running, reset))

  @cytest.posix_only('multiple compiled generations of one name')
  def test_first_use_in_two_interpreters(self):
    self.run_child(r'''
from curry.interpreter import Interpreter
from curry.backends.cxx import curryrtbindings as rt
from curry.objects.handle import getHandle
from pathlib import Path
import tempfile
with tempfile.TemporaryDirectory() as work:
    first, second = (Interpreter(flags={'interpret': 'off', 'jit': 'off'})
                     for _ in range(2))
    loaded = []
    from curry import toolchain
    from curry.toolchain import plans
    for interp, value in ((first, 11), (second, 22)):
        root = Path(work) / str(value)
        root.mkdir()
        source = root / 'PrivateTrap.curry'
        source.write_text('module PrivateTrap where\nf :: Int\nf = %d\n' % value)
        plan = plans.makeplan(None, plans.MAKE_ICURRY)
        icy = toolchain.makecurry(plan, str(source), [str(root)], is_sourcefile=True)
        interp.path.insert(0, str(root))
        module = interp.import_(toolchain.loadicurry(icy), currypath=list(interp.path))
        assert rt.is_trapped(getHandle(module).symbols['f'].info)
        loaded.append((interp, module, value))
    for interp, module, value in loaded:
        assert interp.eval(module.f).one() == value
        assert not rt.is_trapped(getHandle(module).symbols['f'].info)
    assert first.eval(loaded[0][1].f).one() == 11
''')


if __name__ == '__main__':
  unittest.main()

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
import sys, tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
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
    original = Path(config.installed_path('curry', 'lib', 'Data/Char.curry')).read_text()
    edited = original.replace("ord c - ord '0'", "ord c - ord '0' + 1")
    self.assertNotEqual(original, edited)
    for mode in ('new', 'all'):
      for override_first in (True, False):
        with self.subTest(mode=mode, override_first=override_first):
          self.run_child(r'''
from curry.interpreter import Interpreter
from pathlib import Path
import sys, tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
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
import sys, tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
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
import sys, tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
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
import os, sys, time, tempfile
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

with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
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

  def test_llvm_cached_reload_during_resolution(self):
    try:
      import llvmlite
    except ImportError:
      self.skipTest('llvmlite is unavailable')
    self.run_child(r'''
import logging, os, shutil, sys, tempfile
from pathlib import Path
os.environ['SPRITE_JIT_THRESHOLD'] = '1000000000'
from curry.interpreter import Interpreter, session
from curry.backends.cxx import curryrtbindings as rt, llvmjit
flags = {'interpret': 'all', 'jit': 'hot', 'jit_backend': 'llvm', 'inline_budget': 0}
with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
    os.environ['SPRITE_JIT_CACHE'] = str(Path(work) / 'cache')
    source = Path(work) / 'ReloadCached.curry'
    for value in (17, 29):
        source.write_text('module ReloadCached where\nf :: Int -> Int\nf n = %d\n' % value)
        fill = Interpreter(flags=flags)
        fill.path.insert(0, work)
        m = fill.import_('ReloadCached')
        llvmjit.compile(m.f.info, 'ReloadCached.f')
        context = llvmjit._jit.modules[rt.icurry_address(m.f.info)]
        Path(context.private).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(context.local, context.private)
    source.write_text('module ReloadCached where\nf :: Int -> Int\nf n = 17\n')
    first = Interpreter(flags=flags)
    first.path.insert(0, work)
    m = first.import_('ReloadCached')
    info = m.f.info
    old = llvmjit._jit.modules[rt.icurry_address(info)]
    assert 'ReloadCached.f' in old.cached and not old.resolved
    seen = []
    class Reload(logging.Handler):
        def emit(self, record):
            if seen or 'resolved ReloadCached.f' not in record.getMessage():
                return
            seen.append(record.getMessage())
            assert not llvmjit._lock.locked()
            session.reload(first, m, text='f :: Int -> Int\nf n = 29\n')
            assert rt.icurry_address(m.f.info) == rt.icurry_address(info)
            new = llvmjit._jit.modules[rt.icurry_address(info)]
            assert new is not old and 'ReloadCached.f' in new.cached
    handler = Reload()
    llvmjit.logger.addHandler(handler)
    llvmjit.logger.setLevel(logging.INFO)
    before = llvmjit.statistics().copy()
    try:
        assert first.eval(m.f(0)).one() == 29, 'old cached address was installed'
    finally:
        llvmjit.logger.removeHandler(handler)
    assert len(seen) == 1
    new = llvmjit._jit.modules[rt.icurry_address(info)]
    assert 'ReloadCached.f' in new.resolved, 'replacement trampoline was overwritten'
    assert rt.icurry_is_jit(info)
    after = llvmjit.statistics()
    assert after['linked'] == before['linked'] + 2, (before, after)
    assert after['functions'] == before['functions'], (before, after)
    assert first.eval(m.f(0)).one() == 29
''')

  def test_llvm_direct_compile_refused_install_counts(self):
    try:
      import llvmlite
    except ImportError:
      self.skipTest('llvmlite is unavailable')
    self.run_child(r'''
from unittest import mock
from curry.interpreter import Interpreter
from curry.backends.cxx import curryrtbindings as rt, llvmjit
import sys, tempfile
from pathlib import Path
with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
    first = Interpreter(flags={'interpret': 'all', 'jit': 'off', 'inline_budget': 0})
    source = Path(work) / 'RefusedCompile.curry'
    source.write_text('module RefusedCompile where\nf :: Int -> Int\nf n = 17\n')
    first.path.insert(0, work)
    m = first.import_('RefusedCompile')
    info = m.f.info
    first.reset()
    before = llvmjit.statistics().copy()
    llvmjit.compile(info, 'RefusedCompile.f')
    after = llvmjit.statistics()
    assert not rt.icurry_is_jit(info)
    assert after['functions'] == before['functions'], (before, after)
    assert after['hot'] == before['hot'], (before, after)
    # A native refusal must also propagate when the Python token is valid.
    source = Path(work) / 'RefusedLiveCompile.curry'
    source.write_text('module RefusedLiveCompile where\ng :: Int -> Int\ng n = 23\n')
    m = first.import_('RefusedLiveCompile')
    info = m.g.info
    before = llvmjit.statistics().copy()
    with mock.patch.object(rt, 'icurry_set_step', return_value=False) as install:
        llvmjit.compile(info, 'RefusedLiveCompile.g')
    assert install.call_count == 1
    assert install.call_args.args[2].valid
    assert not rt.icurry_is_jit(info)
    after = llvmjit.statistics()
    assert after['functions'] == before['functions'], (before, after)
    assert after['hot'] == before['hot'], (before, after)
''')

  def test_llvm_cached_lazy_cross_interpreter_after_reset(self):
    try:
      import llvmlite
    except ImportError:
      self.skipTest('llvmlite is unavailable')
    self.run_child(r'''
import os, sys, tempfile
from pathlib import Path
os.environ['SPRITE_JIT_THRESHOLD'] = '1000000000'
from curry.interpreter import Interpreter
from curry.backends.cxx import curryrtbindings as rt, llvmjit
flags = {'interpret': 'all', 'jit': 'hot', 'jit_backend': 'llvm', 'inline_budget': 0}
with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
    os.environ['SPRITE_JIT_CACHE'] = str(Path(work) / 'cache')
    source = Path(work) / 'RetiredCached.curry'
    source.write_text('module RetiredCached where\nf :: Int -> Int\nf n = 17\n')
    fill = Interpreter(flags=flags)
    fill.path.insert(0, work)
    m = fill.import_('RetiredCached')
    llvmjit.compile(m.f.info, 'RetiredCached.f')
    filled = llvmjit._jit.modules[rt.icurry_address(m.f.info)]
    assert Path(filled.local).is_file() or Path(filled.private).is_file(), 'cache was not populated'
    tracker, records = llvmjit._jit.generations[filled.runtime_key][-1]
    native_step = tracker[records[0][1]]
    first, second = Interpreter(flags=flags), Interpreter(flags=flags)
    first.path.insert(0, work)
    m = first.import_('RetiredCached')
    info = m.f.info
    context = llvmjit._jit.modules[rt.icurry_address(info)]
    assert 'RetiredCached.f' in context.cached
    assert 'RetiredCached.f' not in context.resolved
    results = second.eval(m.f(0))
    ticket = rt.icurry_work(info)
    first.reset()
    before = llvmjit.statistics().copy()
    assert results.one() == 17
    assert not rt.icurry_is_jit(info), 'retired cached table was swapped'
    assert 'RetiredCached.f' not in context.resolved, 'retired object was resolved'
    assert llvmjit.statistics() == before, (before, llvmjit.statistics())
    # A caller that bypasses the resolver still cannot install on this table.
    assert rt.icurry_set_step(info, native_step, ticket) is False
    assert not rt.icurry_is_jit(info)
''')

  def test_reload_refuses_another_interpreters_module(self):
    try:
      import llvmlite
    except ImportError:
      self.skipTest('llvmlite is unavailable')
    self.run_child(r'''
import os, threading, time
os.environ['SPRITE_JIT_THRESHOLD'] = '2'
import curry
from curry.interpreter import Interpreter, session
from curry.utility.locking import native_metadata
from curry.backends.cxx import curryrtbindings as rt, llvmjit
flags = {'interpret': 'all', 'jit': 'hot', 'jit_backend': 'llvm', 'inline_budget': 0}
first, second = Interpreter(flags=flags), Interpreter(flags=flags)
curry._interpreter_ = second
entered, release, done = threading.Event(), threading.Event(), threading.Event()
original = llvmjit._compile_groups_locked
def held(*args, **kw):
    entered.set()
    assert release.wait(30)
    try:
        return original(*args, **kw)
    finally:
        done.set()
llvmjit._compile_groups_locked = held
a = first.compile('f :: Int -> Int\nf n = 11\n', modulename='ForeignReload')
b = second.compile('f :: Int -> Int\nf n = 22\n', modulename='ForeignReload')
info = a.f.info
for _ in range(2):
    assert first.eval(a.f(0)).one() == 11
assert entered.wait(30)
tokens = [rt.icurry_work(m.f.info) for m in (a, b)]
try:
    for reload in (curry.reload, lambda m, **kw: session.reload(second, m, **kw),
                   lambda m, **kw: native_metadata(session._replace_module)(
                       second, m, None, kw['text'], ())):
        try:
            reload(a, text='g :: Int\ng = 33\n')
        except curry.exceptions.StaleError as error:
            assert 'another interpreter' in str(error), str(error)
        else:
            raise AssertionError('foreign module reload was accepted')
        assert all(token.valid for token in tokens), 'reload mutated a generation'
        assert first.modules['ForeignReload'] is a
        assert second.modules['ForeignReload'] is b
        assert first.eval(a.f(0)).one() == 11
        assert second.eval(b.f(0)).one() == 22
finally:
    release.set()
assert done.wait(30)
deadline = time.monotonic() + 30
while not rt.icurry_is_jit(info):
    rt.icurry_apply_posted()
    assert time.monotonic() < deadline, llvmjit.statistics()
    time.sleep(.005)
assert first.eval(a.f(0)).one() == 11
assert second.modules['ForeignReload'] is b
assert second.eval(b.f(0)).one() == 22
''')

  def test_llvm_reload_rearms_loaded_functions(self):
    self._llvm_reload_rearms(False)

  def test_llvm_reload_preserves_other_hot_work(self):
    self._llvm_reload_rearms(True)

  def _llvm_reload_rearms(self, other):
    try:
      import llvmlite
    except ImportError:
      self.skipTest('llvmlite is unavailable')
    self.run_child(r'''
import os, sys, tempfile, threading, time
from pathlib import Path
os.environ['SPRITE_JIT_THRESHOLD'] = '4'
import curry
from curry.interpreter import Interpreter
from curry.backends.cxx import curryrtbindings as rt, llvmjit
from curry.objects.handle import getHandle
flags = {'interpret': 'all', 'jit': 'hot', 'jit_backend': 'llvm', 'inline_budget': 0}
first = Interpreter(flags=flags)
second = Interpreter(flags=flags) if %r else first
curry._interpreter_ = first
with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
    for name, body in [('ReloadRearmM', 'f :: Int\nf = 1\n'),
                       ('ReloadRearmN', 'g :: Int -> Int\ng n = 17\nh :: Int -> Int\nh n = 23\nk :: Int -> Int\nk n = 29\n')]:
        (Path(work) / (name + '.curry')).write_text('module ' + name + ' where\n' + body)
    first.path.insert(0, work)
    if second is not first:
        second.path.insert(0, work)
    m = first.import_('ReloadRearmM')
    n = second.import_('ReloadRearmN')
    def call(function, value, count):
        for _ in range(count):
            assert second.eval(function(0)).one() == value
    def swapped(function):
        deadline = time.monotonic() + 3
        while not rt.icurry_is_jit(function.info):
            rt.icurry_apply_posted()
            assert time.monotonic() < deadline, (function, llvmjit.statistics())
            time.sleep(0.005)
    call(n.g, 17, 4)
    swapped(n.g)
    # Hold taken work without making the reload caller own a JIT lock.
    entered, release = threading.Event(), threading.Event()
    original = llvmjit._compile_groups_locked
    def held(*args, **kw):
        entered.set()
        assert release.wait(10)
        return original(*args, **kw)
    llvmjit._compile_groups_locked = held
    call(n.k, 29, 5)
    assert entered.wait(3), llvmjit.statistics()
    old = rt.icurry_work(n.h.info)
    try:
        curry.reload(m, text='f :: Int\nf = 2\n')
        current = rt.icurry_work(n.h.info)
        assert old.valid == (second is not first)
        assert rt.icurry_is_jit(n.g.info), 'reload discarded compiled code'
    finally:
        release.set()
    call(n.h, 23, 5)
    swapped(n.h)
    assert current.valid, 'still-loaded bytecode retained a stale generation'
    call(n.k, 29, 4)
    swapped(n.k)
    assert second.eval(n.g(0)).one() == 17
''' % other)

  def test_llvm_reset_discards_taken_work(self):
    self._llvm_reset_work(False)

  def test_llvm_reset_interrupts_batches(self):
    self._llvm_reset_work(True)

  def test_llvm_cross_interpreter_reset_discards_taken_work(self):
    self._llvm_reset_work(False, cross=True)

  def test_llvm_hard_reset_discards_taken_work(self):
    self._llvm_reset_work(False, hard=True)

  def test_llvm_internal_hard_reset_discards_taken_work(self):
    self._llvm_reset_work(False, hard='helper')

  def test_llvm_lazy_cross_interpreter_after_reset(self):
    self._llvm_reset_work(False, lazy=True)

  def test_llvm_reload_discards_taken_work(self):
    self._llvm_reset_work(False, reload=True)

  def test_llvm_reload_discards_posted_work(self):
    self._llvm_reset_work(False, reload=True, posted=True)

  def _llvm_reset_work(self, between, cross=False, hard=False, lazy=False,
                       reload=False, posted=False):
    try:
      import llvmlite
    except ImportError:
      self.skipTest('llvmlite is unavailable')
    self.run_child(r'''
import os, sys, tempfile, threading, time
from pathlib import Path
os.environ['SPRITE_JIT_THRESHOLD'] = '1' if %r else '2'
import curry, importlib, logging
from curry.interpreter import Interpreter
from curry.backends.cxx import curryrtbindings as rt, llvmjit
flags = {'interpret': 'all', 'jit': 'hot', 'jit_backend': 'llvm', 'inline_budget': 0}
first, second = Interpreter(flags=flags), Interpreter(flags=flags)
cross, hard, lazy, reload, posted = %r, %r, %r, %r, %r
if hard:
    curry._interpreter_ = first
entered, release, done = threading.Event(), threading.Event(), threading.Event()
between = %r
llvmjit.BATCH_SIZE = 2
logs = []
logged = threading.Event()
class Capture(logging.Handler):
    def emit(self, record):
        logs.append(record.getMessage())
        if logs[-1].startswith('jit hot: compiled ') and 'SurvivingHot.f' in logs[-1]:
            logged.set()
llvmjit.logger.addHandler(Capture())
llvmjit.logger.setLevel(logging.INFO)
ready, take = threading.Event(), threading.Event()
take_hot = rt.icurry_take_hot
def gated_take():
    ready.set()
    assert take.wait(30)
    return take_hot()
rt.icurry_take_hot = gated_take
with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
    source = Path(work) / 'RetiredHot.curry'
    def write(value):
        source.write_text('module RetiredHot where\n' + ''.join(
            'f%%d :: Int -> Int\nf%%d n = %%d\n' %% (i, i, value)
            for i in range(34)))
    write(11)
    first.path.insert(0, work)
    a = first.import_('RetiredHot')
    b = second.compile('f :: Int -> Int\nf n = 22\n', modulename='SurvivingHot')
    assert ready.wait(30)
    old = [getattr(a, 'f%%d' %% i).info for i in range(34)]
    compiled = []
    batch = llvmjit._jit.compile_batch
    def record(items, **kw):
        compiled.extend(info for info, name in items if info in old)
        return batch(items, **kw)
    llvmjit._jit.compile_batch = record
    posts = []
    post_step = rt.icurry_post_step
    def record_post(ticket, step):
        if ticket.info in old:
            posts.append(ticket.info)
        result = post_step(ticket, step)
        return result
    rt.icurry_post_step = record_post
    original = llvmjit._compile_groups_locked
    def held(*args, **kw):
        if not between and not posted:
            entered.set()
            assert release.wait(30)
        try:
            result = original(*args, **kw)
            if posted:
                entered.set()
                assert release.wait(30)
            return result
        finally:
            done.set()
    llvmjit._compile_groups_locked = held
    sleep = time.sleep
    def pause(seconds):
        if between and seconds == 0 and threading.current_thread() is llvmjit._hot_thread:
            entered.set()
            assert release.wait(30)
        else:
            sleep(seconds)
    llvmjit.time.sleep = pause
    # Prepare the receiving interpreter's goal while the source is live.
    if lazy:
        results = second.eval(a.f0(0))
        first.reset()
    # The group lock holds all calls until every function is queued.
    with llvmjit._group_lock:
        if lazy:
            assert results.one() == 11
        for i in range(0 if lazy else 1 if posted else 33):
            for _ in range(2):
                assert (second if cross else first).eval(getattr(a, 'f%%d' %% i)(0)).one() == 11
        for _ in range(2):
            assert second.eval(b.f(0)).one() == 22
    take.set()
    assert entered.wait(30), 'hot thread did not reach hold'
    # Leave another entry queued while the worker holds the taken group.
    if not lazy and not posted:
        for _ in range(2):
            assert first.eval(a.f33(0)).one() == 11
    owner = first._its.registry_id
    try:
        if reload:
            curry._interpreter_ = first
            again = curry.reload(a, text='g :: Int -> Int\ng n = 33\n')
            assert again is a and not hasattr(again, 'f0')
        elif hard:
            if hard == 'helper':
                from curry.interpreter import reload as hard_reload
                hard_reload('curry', flags)
            else:
                curry._reload_flags = flags
                importlib.reload(curry)
            first = curry._interpreter_
            first.path.insert(0, work)
        elif not lazy:
            first.reset()
        remaining = rt.icurry_take_hot()
        assert all(ticket.owner != owner for ticket in remaining)
        write(33)
        if not reload:
            again = first.import_('RetiredHot')
    finally:
        release.set()
    assert done.wait(30)
    deadline = time.monotonic() + 30
    while not rt.icurry_is_jit(b.f.info):
        assert time.monotonic() < deadline, llvmjit.statistics()
        second.eval(b.f(0)).one()
        sleep(0.01)
    rt.icurry_apply_posted()
    assert all(not rt.icurry_is_jit(info) for info in old), 'retired generation was swapped'
    assert len(compiled) == (2 if between else 1 if posted else 0), ('stale batches compiled', len(compiled))
    if not between and not posted:
        assert not posts, ('retired steps posted', posts)
    assert first.eval((again.g if reload else again.f0)(0)).one() == 33
    assert second.eval(b.f(0)).one() == 22
    assert logged.wait(30), logs
    if not between and not posted:
        assert not any('jit hot: compiled RetiredHot.' in line for line in logs), logs
''' % (lazy, cross, hard, lazy, reload, posted, between))

  def test_eager_reset_preserves_other_cxx_hot_threshold(self):
    self.run_child(r'''
import os, sys, tempfile
from pathlib import Path
os.environ['SPRITE_JIT_THRESHOLD'] = '3'
from curry.interpreter import Interpreter
from curry.backends.cxx import curryrtbindings as rt, tiered
from curry.objects.handle import getHandle
first = Interpreter(flags={'interpret': 'all', 'jit': 'eager', 'jit_backend': 'cxx'})
first.import_('Prelude')
second = Interpreter(flags={'interpret': 'new', 'jit': 'hot', 'jit_backend': 'cxx'})
with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
    source = Path(work) / 'MixedHot.curry'
    source.write_text('module MixedHot where\nf :: Int -> Int\nf n = n + 1\n')
    second.path.insert(0, work)
    module = second.import_('MixedHot')
    first.reset()
    first.import_('Prelude')
    for _ in range(4):
        assert second.eval(module.f(41)).one() == 42
    assert tiered.wait_for('MixedHot', timeout=90, interp=second), tiered.status()
    assert getHandle(module).backend_handle.shlib is not None
    assert not rt.icurry_is_interpreted(module.f.info)
    tiered.finish()
''')

  def test_reserved_importer_keeps_private_imports(self):
    original = Path(config.installed_path('curry', 'lib', 'Data/List.curry')).read_text()
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
import sys, tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
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
import sys, tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
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
import os, sys, time, tempfile
from pathlib import Path
os.environ['SPRITE_JIT_THRESHOLD'] = '5'
from curry.interpreter import Interpreter
from curry.backends.cxx import curryrtbindings as rt, tiered
from curry.objects.handle import getHandle
flags = {'interpret': 'new', 'jit': 'hot', 'jit_backend': 'cxx', 'inline_budget': 0}
with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
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
import sys, tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
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

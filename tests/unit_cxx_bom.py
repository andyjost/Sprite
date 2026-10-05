'''
Tests of the plain-data bill of materials of a generated C++ module.

A generated module spells its bill of materials (its imports, its data types,
its functions, and the metadata of each) as static arrays of plain records
(cyrt/bom.hpp) and exports one record, _bom_.  The compiler writes the arrays
as data: it instantiates no template for them, and no constructor runs when
the module loads.  The loader reads the record, checks its layout version,
and decodes it into the bill of materials the runtime and Python read.
Before this, a module defined std::unordered_map and ModuleBOM objects, and
their instantiation cost about half of the time g++ spent on a small module.
'''
import cytest # from ./lib; must be first
from curry import common, config, exceptions, icurry
from curry.backends.cxx import compiler
from curry.backends.cxx import cyrtbindings as cyrt
from curry.objects.handle import getHandle
from curry.toolchain._loadcurry import loadjson
import collections, curry, os, re, shutil, subprocess, tempfile, unittest

# The undefined symbols a module of the old format imported for its metadata
# maps and its ModuleBOM: the allocator, the hash table, and the string of
# the standard library.
HEAP_SYMBOLS = (
    '_Znwm', '_Znam', '_ZdlPv', '_ZdaPv', '_Hashtable', 'basic_string'
  )

def dynamic_symbols(sofile, undefined=False):
  '''The dynamic symbols of a shared object, by name (nm -D).'''
  cmd = ['nm', '-D'] + (['-u'] if undefined else []) + [sofile]
  proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
  return [line.split()[-1] for line in proc.stdout.splitlines() if line.strip()]

def shlib_of(module):
  '''The SharedCurryModule of a loaded module.'''
  return getHandle(module).icurry.metadata['cxx.shlib']

@unittest.skipIf(
    curry.flags['backend'] != 'cxx'
  , 'the module format belongs to the C++ backend'
  )
class TestPlainDataBOM(cytest.TestCase):
  '''
  The bill of materials of data/curry/CxxBom.curry: as the emitter writes it,
  as the compiler stores it, and as the loader reads it back.
  '''
  def load(self):
    module = curry.import_('CxxBom')
    return module, shlib_of(module)

  def test_value(self):
    module, _ = self.load()
    self.assertEqual(list(curry.eval(module.main, converter='topython')), [9])

  def test_decoded_bom(self):
    '''The loader decodes every table of the record.'''
    module, shlib = self.load()
    bom = shlib.bom
    self.assertEqual(bom.fullname, 'CxxBom')
    self.assertTrue(bom.filename.endswith('CxxBom.curry'), bom.filename)
    self.assertEqual(sorted(bom.imports), ['Data.Maybe', 'Prelude'])
    self.assertEqual(bom.aliases, {})
    self.assertIs(bom.metadata['cxx.is_merged'], True)
    # The type, with the metadata of the type and of each constructor.
    (type_md, ctor_mds, datatype), = bom.types
    self.assertEqual(datatype.name, 'Shape')
    self.assertEqual(
        [ctor.name for ctor in datatype.constructors]
      , ['Circle', 'Square', 'Dot']
      )
    self.assertEqual(type_md, {})
    self.assertEqual(ctor_mds, [{}, {}, {}])
    # The functions, with their visibility and a metadata value of each kind.
    functions = {info.name: (vis, md) for vis, md, info in bom.functions}
    vis, md = functions['+++']
    self.assertIs(vis, True)
    self.assertIs(type(md['all.flags']), int)
    self.assertTrue(md['all.flags'] & common.F_OPERATOR)
    self.assertIs(md['all.monadic'], False)
    # The alias pass records the end of the chain: plus calls +++, which
    # calls plusInt.
    _, md = functions['plus']
    self.assertEqual(md['all.alias_target'], 'Prelude.plusInt')
    _, md = functions['greet']
    self.assertIs(md['all.monadic'], True)
    self.assertIs(functions['area'][0], False)
    self.assertIs(functions['main'][0], True)
    # The info tables are the ones the module exports.
    infos = {info.name: info for _, _, info in bom.functions}
    self.assertEqual(infos['+++'].arity, 2)
    self.assertEqual(infos['main'].arity, 0)

  def test_generated_file(self):
    '''The emitter writes the record and its tables as plain data.'''
    _, shlib = self.load()
    text = cytest.readfile(shlib.sofilename()[:-len('.so')] + '.cpp')
    self.assertIn('// FORMAT: %d\n' % compiler.FORMAT_VERSION, text)
    self.assertIn('extern bom::Module const _bom_;\n', text)
    self.assertIn(
        'bom::Module const _bom_ = {\n    /*version  */ bom::VERSION\n', text
      )
    self.assertIn('  , /*fullname */ "CxxBom"\n', text)
    for table in [
        'static char const * const ', 'static bom::Type const '
      , 'static bom::Function const ', 'static bom::Metadata const * const '
      , 'static bom::Entry const '
      ]:
      self.assertIn(table, text)
    self.assertIn('    "Prelude"\n', text)
    # One entry of each kind.
    functions = {info.name: md for _, md, info in shlib.bom.functions}
    self.assertIn(
        '{"all.flags", bom::INTEGER, %d, nullptr}'
            % functions['+++']['all.flags']
      , text
      )
    self.assertIn('{"all.monadic", bom::BOOLEAN, 1, nullptr}', text)
    self.assertIn('{"all.monadic", bom::BOOLEAN, 0, nullptr}', text)
    self.assertIn(
        '{"all.alias_target", bom::STRING, 0, "Prelude.plusInt"}', text
      )
    # An empty metadata object and an empty table are null.
    self.assertIn(' = {nullptr, 0};\n', text)
    self.assertIn('  , /*aliases  */ nullptr, 0\n', text)
    # Nothing of the old format: no map, no ModuleBOM, nothing of the
    # standard library.
    self.assertNotIn('ModuleBOM', text)
    self.assertIsNone(re.search(r'^static Metadata const', text, re.M))
    self.assertNotIn('std::', text)

  def test_object_builds_nothing_at_load(self):
    '''
    The object of a module imports no allocator, hash table, or string of the
    standard library: its bill of materials is data.  The staged Prelude,
    the largest module, is checked as well.
    '''
    if shutil.which('nm') is None:
      self.skipTest('nm is not installed')
    _, shlib = self.load()
    prelude = shlib_of(curry.import_('Prelude'))
    for sofile in shlib.sofilename(), prelude.sofilename():
      undefined = dynamic_symbols(sofile, undefined=True)
      self.assertTrue(undefined, sofile)
      heap = [s for s in undefined if any(h in s for h in HEAP_SYMBOLS)]
      self.assertEqual(heap, [], sofile)
      self.assertIn('_bom_', dynamic_symbols(sofile))
    # The record of the Prelude decodes: its tables are large and it has
    # aliases.
    bom = prelude.bom
    self.assertGreater(len(bom.functions), 1000)
    self.assertGreater(len(bom.types), 10)
    self.assertEqual(
        {k: bom.aliases[k] for k in ('Unit', 'Cons', 'Nil')}
      , {'Unit': '()', 'Cons': ':', 'Nil': '[]'}
      )

  def test_loader_checks(self):
    '''
    The loader refuses a record of another layout version, a library without
    a record, and a record without a name.  A minimal record of the current
    version loads with empty tables.
    '''
    cxx = config.cxx_tool()
    if cxx is None:
      self.skipTest('no C++ compiler is installed')
    tmpdir = tempfile.mkdtemp(prefix='sprite-bom-')
    self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
    include = os.path.realpath(config.installed_path('include'))

    def build(name, body):
      src = os.path.join(tmpdir, name + '.cpp')
      sofile = os.path.join(tmpdir, name + '.so')
      with open(src, 'w') as stream:
        stream.write(
            '#include "cyrt/bom.hpp"\nusing namespace cyrt;\n'
            'extern "C" {\n%s\n}\n' % body
          )
      cmd = [
          cxx, '-shared', '-fPIC', '-std=c++17', '-I' + include, src
        , '-o', sofile
        ]
      subprocess.run(cmd, check=True, capture_output=True, text=True)
      return sofile

    record = (
        'extern bom::Module const _bom_;\n'
        'bom::Module const _bom_ = {%s, %s, nullptr, nullptr, 0, nullptr'
        ', nullptr, 0, nullptr, 0, nullptr, 0};'
      )
    # The C++ DynloadError reaches Python as a RuntimeError.
    sofile = build('CxxBomOld', record % ('bom::VERSION + 1', '"CxxBomOld"'))
    with self.assertRaisesRegex(
        RuntimeError, r'layout version \d+, and this runtime reads version \d+'
      ):
      cyrt.SharedCurryModule(sofile)
    sofile = build('CxxBomNone', 'int cxxbom_nothing = 1;')
    with self.assertRaisesRegex(RuntimeError, '_bom_'):
      cyrt.SharedCurryModule(sofile)
    sofile = build('CxxBomNoName', record % ('bom::VERSION', 'nullptr'))
    with self.assertRaisesRegex(RuntimeError, 'no name'):
      cyrt.SharedCurryModule(sofile)
    sofile = build('CxxBomEmpty', record % ('bom::VERSION', '"CxxBomEmpty"'))
    shlib = cyrt.SharedCurryModule(sofile)
    bom = shlib.bom
    self.assertEqual(
        (
            bom.fullname, bom.filename, bom.imports, bom.metadata, bom.aliases
          , bom.types, bom.functions
          )
      , ('CxxBomEmpty', '', [], {}, {}, [], [])
      )

  def test_metadata_value_kinds(self):
    '''
    The emitter stores a str, an int, and a bool, and refuses another type
    or an int outside the C++ range with an error that names the key.  A key
    of another backend is left out.
    '''
    interp = curry.getInterpreter()
    def module(metadata):
      ifun = icurry.IFunction(
          'CxxBomMeta.f', 0, True, None, icurry.IBody(icurry.IExempt())
        , metadata=metadata
        )
      return icurry.IModule('CxxBomMeta', ['Prelude'], [], [ifun])
    target = compiler.compile(
        interp
      , module({
            'all.text': 'x', 'all.number': -7, 'all.flag': True
          , 'other.ignored': 1.5
          })
      )
    text = '\n'.join(target['.metadata'])
    self.assertIn('{"all.flag", bom::BOOLEAN, 1, nullptr}', text)
    self.assertIn('{"all.number", bom::INTEGER, -7, nullptr}', text)
    self.assertIn('{"all.text", bom::STRING, 0, "x"}', text)
    self.assertNotIn('ignored', text)
    with self.assertRaisesRegex(exceptions.CompileError, "'all.weird'.*float"):
      compiler.compile(interp, module({'all.weird': 1.5}))
    with self.assertRaisesRegex(exceptions.CompileError, "'all.big'.*fit"):
      compiler.compile(interp, module({'all.big': 2 ** 31}))


@unittest.skipIf(
    curry.flags['backend'] != 'cxx'
  , 'the module format belongs to the C++ backend'
  )
class TestFunctionNames(cytest.TestCase):
  '''
  The record names a function by the name field of its table.  A primitive
  of the runtime therefore carries its Curry name (prim_showIntLiteral), not
  the name of the Curry function that wraps it (showIntLiteral x =
  prim_showIntLiteral $## x): with the wrapper's name, the two rows of the
  Prelude's record collided, the primitive took the wrapper's place in the
  symbol table, and an interpreted module that named the wrapper called the
  primitive on an argument the wrapper would have normalized first.
  '''

  WRAPPERS = [
      'showCharLiteral', 'showFloatLiteral', 'showIntLiteral'
    , 'showStringLiteral', 'readCharLiteral', 'readFloatLiteral'
    , 'readNatLiteral', 'readStringLiteral', 'error', 'appendFile', 'ioError'
    , 'putChar', 'readFile', 'writeFile'
    ]

  def test_wrapper_and_primitive_are_two_symbols(self):
    interp = curry.getInterpreter()
    imodule = getattr(interp.prelude, '.icurry')
    shlib = imodule.metadata['cxx.shlib']
    rows = {}
    for _, _, info in shlib.bom.functions:
      rows.setdefault(info.name, []).append(info)
    for name in self.WRAPPERS:
      prim = 'prim_' + name
      self.assertEqual(len(rows[name]), 1, name)
      self.assertEqual(len(rows[prim]), 1, prim)
      wrapper = curry.symbol('Prelude.' + name).info
      primitive = curry.symbol('Prelude.' + prim).info
      self.assertEqual(wrapper.name, name)
      self.assertEqual(primitive.name, prim)
      self.assertIsNot(wrapper, primitive)
      self.assertEqual(str(wrapper), str(rows[name][0]))

  def test_wrapper_normalizes(self):
    '''A module compiled from a string names the wrapper and gets its text.'''
    goal = curry.compile(
        '(showsPrec 11 (-2.5 :: Float) "", showsPrec 0 (-3 :: Int) "")', 'expr'
      )
    self.assertEqual(
        list(curry.eval(goal, converter='topython')), [('(-2.5)', '-3')]
      )

  def test_no_two_rows_share_a_name(self):
    '''
    The loader keys the record by name, so two rows with one name collide,
    whatever the names.  The loader asserts the same of every module when
    it builds the symbol table (interpreter.import_.load).
    '''
    interp = curry.getInterpreter()
    shlib = getattr(interp.prelude, '.icurry').metadata['cxx.shlib']
    names = collections.Counter(info.name for _, _, info in shlib.bom.functions)
    self.assertEqual([name for name, n in names.items() if n > 1], [])
    self.assertGreater(len(names), 1000)
    for name, symbol in getattr(interp.prelude, '.symbols').items():
      info = getattr(symbol, 'info', None)
      if info is not None:
        self.assertEqual(info.name, name)

  def test_builtin_tables_carry_the_curry_name(self):
    '''
    A built-in of the runtime answers to the Curry name it is registered
    under (currylib/prelude.cpp), and its table carries that name.  The
    loader asserts that the two agree when the Prelude is imported from
    its ICurry: under interpret 'all', and in the compile of the Prelude
    itself.  The table of nonstrictEq said nonStrictEq once.
    '''
    interp = curry.getInterpreter()
    M = getHandle(interp.prelude).backend_handle
    jsonfile = os.path.join(
        config.system_curry_path(), '.curry', config.intermediate_subdir()
      , 'Prelude.json.z'
      )
    imodule = loadjson(jsonfile)
    builtins = []
    for name in imodule.functions:
      info = M.get_builtin_symbol(name)
      if info is not None:
        builtins.append(name)
        self.assertEqual(info.name, name)
    self.assertIn('nonstrictEq', builtins)
    self.assertGreater(len(builtins), 50)

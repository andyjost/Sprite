'''
The build steps of the C++ backend: ICurry-JSON to C++, and C++ to a shared
object.

The C++ compiler is the slow step.  Every generated module includes
cyrt/cyrt.hpp, and parsing that header costs about two thirds of the time g++
needs for a small module.  So the toolchain precompiles the header once, and
g++ loads the result.  See PrecompiledHeader.

Generated code comes in two flavors, as the runtime does (make DEBUG=1).  The
release flavor drops the assertions, the stack protector, and the procedure
linkage table.  The debug flavor keeps the assertions and compiles for a
debugger.  A module follows the flavor of the installed runtime
(config.cxx_flavor) unless the interpreter flag ``debug`` is set.  See
FLAVOR_FLAGS and Cpp2So.flavor.

A compiled module stays valid as long as the runtime headers it was compiled
against and the flags of its flavor do not change.  Cpp2So records a digest of
both beside each shared object (the ABI stamp, <module>.so.abi) and compiles
the module again when the installation gives another digest.  See
runtime_digest, object_digest, and Cpp2So.is_stale.  A generated .cpp file
carries a format stamp; Json2Cpp, which writes the file, refuses one of
another format.  See Json2Cpp.is_stale.
'''
from ..generic.toolchain import Json2TargetSource
from . import compiler
from ... import config, exceptions
from ...objects.handle import getHandle
from ...utility import curryname, filesys
from ...toolchain import plans, _filenames, _loadcurry, _system
import functools, hashlib, itertools, logging, os, re

logger = logging.getLogger(__name__)

def runtime_headers(include_dir=None):
  '''
  The installed runtime headers, in a fixed order.  Generated code includes
  cyrt/cyrt.hpp, which pulls in all of them.  ``include_dir`` is the include
  directory to search; by default, the installed one.
  '''
  if include_dir is None:
    include_dir = config.installed_path('include')
  top = os.path.join(include_dir, 'cyrt')
  for dirpath, dirnames, filenames in os.walk(top):
    dirnames[:] = sorted(d for d in dirnames if not d.endswith('.gch'))
    for name in sorted(filenames):
      if name.endswith(('.hpp', '.hxx', '.h')):
        yield os.path.join(dirpath, name)

@functools.lru_cache(maxsize=None)
def runtime_digest(include_dir=None):
  '''
  A digest of the runtime headers under ``include_dir`` (by default, the
  installed ones): the ABI that generated code is compiled against.  The
  digest covers the names and the contents of the headers, not their time
  stamps.  So a new copy of the same headers, as make stage installs, gives
  the same digest, and a change to any header gives another.  The result is
  cached for the life of the process.

  Returns None when the tree holds no header.  Such an installation cannot
  compile, so its objects are trusted as they are (see Cpp2So.is_stale).

  Raises:
    PrerequisiteError: a header cannot be read.  make stage links the
    installed headers to the source tree, so this happens when the source
    tree is gone.  The message names the installation.
  '''
  base = include_dir
  if base is None:
    base = config.installed_path('include')
  digest = hashlib.sha256()
  found = False
  for filename in runtime_headers(include_dir):
    found = True
    digest.update(os.path.relpath(filename, base).encode('utf-8'))
    digest.update(b'\0')
    try:
      with open(filename, 'rb') as stream:
        digest.update(stream.read())
    except OSError as exc:
      raise exceptions.PrerequisiteError(
          'cannot read the runtime header %r of the installation at %r (%s).'
          '  Is the installation complete?' % (filename, base, exc)
        )
    digest.update(b'\0')
  if not found:
    return None
  return digest.hexdigest()[:16]

# The compiler flags of the two flavors of generated code.  They follow the
# flags of the runtime build (see the build flavor in configure).  The release
# flavor drops the assertions (-DNDEBUG) and the stack protector, calls the
# runtime without the procedure linkage table, and lets the compiler bind the
# functions of a translation unit locally.  The debug flavor keeps the
# assertions and compiles for a debugger.
FLAVOR_FLAGS = {
    'release': [
        '-O3', '-DNDEBUG', '-fno-stack-protector', '-fno-plt'
      , '-fno-semantic-interposition'
      ]
  , 'debug': ['-O0', '-g']
  }

# The link flags of a module.  A module binds its own functions locally.  So a
# call to a function of the runtime headers that the compiler did not inline
# does not go through the procedure linkage table to the copy in the module
# loaded first.
LINK_FLAGS = ['-Wl,-Bsymbolic-functions']

def flavor_flags(flavor):
  '''The compiler flags of a flavor of generated code: 'release' or 'debug'.'''
  return list(FLAVOR_FLAGS[flavor])

# The compiler flags of the collectors of the runtime (make GC=...).  The
# inline writers of the runtime headers (Node::rewrite and the others in
# node.hxx) differ under the Memory Pool System, so a module is compiled
# with the macro of the installed collector.  See src/cyrt/graph/gc/mps.cpp.
GC_FLAGS = {
    'wdgc': []
  , 'mps': ['-DSPRITE_GC_MPS']
  }

def gc_flags(gc=None):
  '''
  The compiler flags of a collector of the runtime, by default the collector
  of the installed runtime (config.cxx_gc).
  '''
  if gc is None:
    gc = config.cxx_gc()
  return list(GC_FLAGS[gc])

def object_digest(flavor=None, include_dir=None, gc=None):
  '''
  The stamp of an object compiled now: a digest of the runtime headers
  (runtime_digest), of the flags of ``flavor``, by default the flavor of the
  installed runtime (config.cxx_flavor), and of the flags of the collector
  ``gc``, by default the installed one (config.cxx_gc).  So a change to a
  header, to the flags of a flavor, or to the collector compiles every
  object again, once.  The flags of the environment (CXXFLAGS) are not part
  of it.

  Returns None when the tree holds no header (see runtime_digest).
  '''
  headers = runtime_digest(include_dir)
  if headers is None:
    return None
  if flavor is None:
    flavor = config.cxx_flavor()
  digest = hashlib.sha256(headers.encode('utf-8'))
  for flag in flavor_flags(flavor) + gc_flags(gc) + LINK_FLAGS:
    digest.update(b'\0')
    digest.update(flag.encode('utf-8'))
  return digest.hexdigest()[:16]

def extend_plan_skeleton(interp, skeleton):
  assert interp is not None
  if interp.flags['interpret'] == 'all':
    # Every module is interpreted from its JSON (see Json2Cpp.ends_plan).
    # The plan ends there, so a compiled object is never looked for.
    return
  flag, suffixes, _ = skeleton[-1]
  skeleton[-1] = flag, suffixes, Json2Cpp(interp)
  skeleton.append((plans.MAKE_TARGET_OBJECT, ['.cpp'], Cpp2So(interp)))
  skeleton.append((plans.UNCONDITIONAL, ['.so'] , None))

# The format stamp of a generated .cpp file.  The stamp heads the file.
FORMAT_PAT = re.compile(r'// FORMAT: (\d+)')

def format_version(file_in):
  '''The format stamp of a generated file.  A file without one is format 1.'''
  with open(file_in, 'r') as stream:
    for line in itertools.islice(stream, 16):
      m = FORMAT_PAT.match(line)
      if m:
        return int(m.group(1))
  return 1

def source_is_stale(file_in):
  '''
  Tells whether a generated .cpp file is unusable: its format stamp is not
  the emitter's (compiler.FORMAT_VERSION).  It was written for another
  runtime, and the runtime would read its static data with the wrong layout.
  '''
  return format_version(file_in) != compiler.FORMAT_VERSION

class Json2Cpp(Json2TargetSource):
  NAME = 'json2cpp'
  SUFFIX = '.cpp'

  def ends_plan(self, filename):
    '''
    Tells whether the plan ends at ``filename``, a JSON file this step would
    compile.  Under the interpreter flag ``interpret`` set to 'new', a
    module that reached the JSON stage without a compiled object is
    interpreted by the runtime (cyrt/icurry.hpp; see materialize.py), so
    this step and the C++ compiler do not run for it.  A module with a
    current object never reaches this step: the object is the newest file.
    '''
    return self.interp.flags['interpret'] == 'new' \
        and filename.endswith(('.json', '.json.z'))

  def is_stale(self, filename):
    '''
    Tells whether a .cpp file this step wrote is unusable (source_is_stale).
    The plan asks this step when the file ends the plan (sprite-make --cxx);
    with a compile step after it, Cpp2So asks the same question.  The plan
    asks about the JSON input of this step as well, which is never refused.
    '''
    return filename.endswith('.cpp') and source_is_stale(filename)

class PrecompiledHeader(object):
  '''
  The precompiled form of cyrt/cyrt.hpp.

  The files live in <root>/cyrt/cyrt.hpp.gch/.  The root is the installed
  include directory unless SPRITE_CXX_PCH_ROOT says otherwise (see
  config.cxx_pch_root).  g++ accepts a directory of that name in place of one
  file and uses the member that matches its options.  So each flavor (the
  optimized build, the debug build, custom CXXFLAGS) gets its own member,
  named after the optimization flags and a hash of the compiler and the full
  flag list.

  A member is stale when it is older than any header, its sources.  The
  comparison uses modification times: make stage links the installed headers
  to the sources, and make install copies a header only when the source is
  newer, so a build that changes no header keeps the member.
  When the directory cannot be written or the build fails, the toolchain logs
  one warning per root and compiles without the header.  The generated code
  is the same either way.
  '''
  HEADER = os.path.join('cyrt', 'cyrt.hpp')

  # The roots for which a build failed in this process.  No second attempt.
  _failed = set()

  def __init__(self, root, cxx, cxxflags):
    self.root = root
    self.cxx = cxx
    self.cxxflags = list(cxxflags)
    self.directory = os.path.join(root, self.HEADER + '.gch')
    self.filename = os.path.join(self.directory, self.flavor + '.gch')

  @property
  def flavor(self):
    '''The member name for this compiler and these flags, without suffix.'''
    exe = os.path.realpath(self.cxx)
    try:
      stamp = str(os.path.getmtime(exe))
    except OSError:
      stamp = ''
    key = '\0'.join([exe, stamp] + self.cxxflags)
    digest = hashlib.sha1(key.encode('utf-8')).hexdigest()[:12]
    level = ''.join(
        flag[1:] for flag in self.cxxflags
                 if flag.startswith('-O') or flag == '-g'
      )
    return '%s-%s' % (level or 'default', digest)

  @staticmethod
  def header_files():
    '''The installed headers.  The precompiled header depends on them all.'''
    return runtime_headers()

  def is_current(self):
    '''True when the member exists and no header is newer.'''
    try:
      stamp = os.path.getmtime(self.filename)
      return all(os.path.getmtime(f) <= stamp for f in self.header_files())
    except OSError:
      return False

  def prepare(self):
    '''
    Builds the member if it is missing or stale.  Returns True when g++ can
    use it, and False when the toolchain must compile without it.
    '''
    if self.root in self._failed:
      return False
    if self.is_current():
      return True
    try:
      self.build()
    except (OSError, exceptions.CompileError) as exc:
      self._failed.add(self.root)
      logger.warning(
          'cannot build the precompiled header %r (%s); generated code is '
          'compiled without it.  Set SPRITE_CXX_PCH_ROOT to a writable '
          'directory, or to the empty string to silence this warning.'
        , self.filename, exc
        )
      return False
    return True

  def build(self):
    '''Compiles the header into a temporary file, then moves it into place.'''
    header = config.installed_path('include', self.HEADER)
    os.makedirs(self.directory, exist_ok=True)
    # A partial file must never sit in the .gch directory, where g++ would
    # try it.  Build beside the directory and move the result in.
    tmp = os.path.join(
        os.path.dirname(self.directory)
      , '.%s.%d.tmp' % (os.path.basename(self.filename), os.getpid())
      )
    cmd = [self.cxx, '-x', 'c++-header'] + self.cxxflags + [header, '-o', tmp]
    logger.info('Precompiling %r', self.filename)
    logger.debug('Command: %s', ' '.join(cmd))
    with filesys.remove_file_on_error(tmp):
      _system.pexec(cmd)
      os.replace(tmp, self.filename)

class Cpp2So(object):
  '''
  Compiles a generated .cpp file into a shared object, in the flavor of the
  installed runtime or, under the interpreter flag ``debug``, in the debug
  flavor (see flavor).  Each object gets an ABI stamp: a file beside it that
  holds the digest of the runtime headers and of the flavor flags the object
  was compiled with (object_digest).  See is_stale.
  '''
  STAMP_SUFFIX = '.abi'

  def __init__(self, interp):
    self.interp = interp

  def __repr__(self):
    return 'cpp2so'

  @property
  def flavor(self):
    '''
    The flavor this step compiles in: 'debug' under the interpreter flag
    ``debug`` or in a debug installation (make DEBUG=1), else 'release'.
    '''
    if self.interp.flags['debug']:
      return 'debug'
    return config.cxx_flavor()

  def digest(self):
    '''The stamp this step writes: the object_digest of its flavor.'''
    return object_digest(self.flavor)

  def accepted_digests(self):
    '''
    The stamps of the objects this step keeps.  An object of the installed
    flavor is always kept.  Under the interpreter flag ``debug`` an object of
    the debug flavor is kept as well.  So a debug session keeps the objects
    of the installation and its own, and a session without the flag compiles
    the debug objects again, once.  Empty when the installation holds no
    headers.
    '''
    installed = object_digest()
    if installed is None:
      return set()
    digests = {installed}
    if self.interp.flags['debug']:
      digests.add(object_digest('debug'))
    return digests

  def is_stale(self, filename):
    '''
    Tells whether a cached file of this step is unusable.  The plan then
    starts again from the file before it (Plan.prune_stale).

    A .cpp file is stale when its format stamp is not the emitter's
    (source_is_stale; a file without a stamp is format 1).

    A .so file is stale when its ABI stamp is missing or holds a digest this
    step does not accept (accepted_digests): the object was compiled against
    other headers or with the flags of another flavor.  The check reads the
    headers, not time stamps, so a new copy of the same runtime keeps every
    object, and a copied cache keeps its objects.  An installation without
    headers (runtime_digest gives None) cannot compile anything, so its
    objects are trusted as they are.
    '''
    if filename.endswith('.so'):
      accepted = self.accepted_digests()
      return bool(accepted) and self.read_stamp(filename) not in accepted
    return source_is_stale(filename)

  @classmethod
  def stampfile(cls, sofile):
    '''The ABI stamp of a shared object.'''
    return sofile + cls.STAMP_SUFFIX

  @classmethod
  def read_stamp(cls, sofile):
    '''The digest recorded in the ABI stamp of ``sofile``, or None.'''
    try:
      with open(cls.stampfile(sofile), 'r') as stream:
        return stream.read().strip()
    except OSError:
      return None

  def write_stamp(self, sofile):
    '''
    Records the stamp of this step (digest) beside ``sofile``.  Without
    headers there is no digest, and no stamp is written.
    '''
    digest = self.digest()
    if digest is None:
      return
    stamp = self.stampfile(sofile)
    tmp = '%s.%d.tmp' % (stamp, os.getpid())
    with filesys.remove_file_on_error(tmp):
      with open(tmp, 'w') as stream:
        stream.write(digest + '\n')
      os.replace(tmp, stamp)

  @classmethod
  def remove_stamp(cls, sofile):
    '''Removes the ABI stamp of ``sofile``, if there is one.'''
    try:
      os.unlink(cls.stampfile(sofile))
    except FileNotFoundError:
      pass

  def format_version(self, file_in):
    '''The format stamp of a generated file (format_version).'''
    return format_version(file_in)

  IMPORT_PAT = re.compile(r'// IMPORTS: (.*)')
  def _importedModules(self, file_in):
    '''
    Returns a list containing the full names of all modules imported by the
    specified .cpp file.  This information is stored in a comment near the top
    of the file.
    '''
    with open(file_in, 'r') as stream:
      for line in stream:
        m = re.match(self.IMPORT_PAT, line)
        if m:
          return [name for name in m.group(1).split() if name]
      else:
        raise exceptions.PrerequisiteError(
            'Cannot find IMPORTS list in %r' % file_in
          )

  def _sofilename(self, modulename):
    '''
    Gets the name of the .so file implementing the given module.
    '''
    module = self.interp.import_(modulename)
    h = getHandle(module)
    sofilename = h.sofilename
    if sofilename is None:
      raise exceptions.PrerequisiteError(
          'No .so filename for module %r' % h.fullname
        )
    return sofilename

  def _dependencies(self, file_in):
    '''
    Generates the .so files the specified .cpp file depends on.  They are added
    to the link line so that ldd will automatically load the correct modules.
    '''
    for modulename in self._importedModules(file_in):
      yield self._sofilename(modulename)

  def _cxxflags(self):
    '''
    The flags that shape the compilation of a translation unit.  The
    precompiled header is built with the same list, and its member name is a
    digest of it.  The include directory is spelled by its real path, so the
    digest does not depend on the spelling of SPRITE_HOME: make stage names
    the installation through the link install/, the test drivers through its
    real path, and both must find the member the stage built.
    '''
    yield '-I%s' % os.path.realpath(config.installed_path('include'))
    yield '-fPIC'
    yield '-std=c++17'
    for flag in flavor_flags(self.flavor):
      yield flag
    for flag in gc_flags():
      yield flag
    for flag in os.environ.get('CXXFLAGS', '').split():
      yield flag

  def _pchflags(self):
    '''
    Prepares the precompiled header.  Yields the include flag that lets g++
    find it when it lives outside the installed include directory.
    '''
    root = config.cxx_pch_root()
    cxx = config.cxx_tool()
    if root is None or cxx is None:
      return
    pch = PrecompiledHeader(root, cxx, self._cxxflags())
    if pch.prepare() and root != config.installed_path('include'):
      yield '-I%s' % root

  def _compileCommand(self, file_in, file_out):
    cxx = config.cxx_tool()
    if cxx is None:
      raise exceptions.CompileError(
          'cannot compile %r: no C++ compiler is installed at %r.  Install '
          'one and configure Sprite with --with-cxx-postinstall, or use the '
          'modules that make stage compiled.'
        % (file_in, config.installed_path('tools', 'cxx'))
        )
    yield cxx
    for flag in self._pchflags():
      yield flag
    yield '-shared'
    for flag in self._cxxflags():
      yield flag
    yield '-Wl,-eentry'
    for flag in LINK_FLAGS:
      yield flag
    yield file_in
    for sofilename in self._dependencies(file_in):
      yield sofilename
    yield '-L%s' % config.installed_path('lib')
    yield '-lcyrt'
    yield '-o'
    yield file_out

  @_system.updateCheck
  def __call__(self, file_in, currypath, **ignored):
    if self.is_stale(file_in):
      # The emitter wrote this file, or the plan accepted it.  If its stamp
      # does not read back, every process would write and compile every
      # module again.  Stop here instead.
      raise exceptions.CompileError(
          'the format stamp of %r reads as %r, but the emitter writes %r'
        % (file_in, self.format_version(file_in), compiler.FORMAT_VERSION)
        )
    file_out = _filenames.replacesuffix(file_in, '.so')
    logger.info('Compiling %r', file_out)
    cmd = list(self._compileCommand(file_in, file_out))
    logger.debug('Command: %s', ' '.join(cmd))
    # The old stamp goes before the compiler runs.  An object without a stamp
    # is stale, so a compile that stops between the compiler and the new
    # stamp (a kill, a time limit) leaves nothing a later process would trust
    # under the old digest.
    self.remove_stamp(file_out)
    _system.pexec(cmd)
    self.write_stamp(file_out)
    return file_out

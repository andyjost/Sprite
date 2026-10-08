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
against, the flags of its flavor and the installation it links against do not
change.  Cpp2So records the first two as a digest and the third as text
beside each shared object (the ABI stamp, <module>.so.abi) and compiles the
module again when the installation gives another digest or another path.
See runtime_digest, object_digest, and Cpp2So.is_stale.  A generated .cpp
file carries a format stamp; Json2Cpp, which writes the file, refuses one of
another format.  See Json2Cpp.is_stale.

An object names no path, so it serves any tree (format 13 of the generated
code).  Each object carries a SONAME, the full name of its module and the
format version, "sprite-<module>.so.<format>" (soname); the linker records the
SONAMEs of the objects of the imports as the NEEDED entries of an object,
and the loader imports those modules before it opens the object, so the
dynamic linker finds each name mapped (loader.load_module).  The record of
a module names its source relative to the installation or to the object
(compiler._source_file_name).  See Cpp2So for the link line.

A compile stores its products in the product cache, and a plan places the
cached products of a module instead of generating and compiling it when the
cache holds them.  See Cpp2So.restore, Cpp2So.store and
curry.toolchain._productcache.
'''
from ..generic.toolchain import Json2TargetSource
from . import compiler
from ... import config, exceptions
from ...objects.handle import getHandle
from ...utility import curryname, filesys
from ...toolchain import plans, _filenames, _loadcurry, _makecurry, _productcache, _system
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
# loaded first.  The linker records every library of the link line as a
# NEEDED entry (--no-as-needed), so the NEEDED entries of an object name the
# objects of all its imports, in the order of the IMPORTS line of the
# generated file, whether or not the object takes a symbol from each.  The
# default differs between toolchains (g++ of Debian and Ubuntu passes
# --as-needed, which drops a library the object takes no symbol from), and
# the loader reads the imports of an object from these entries
# (loader.needed_modules), so the form is pinned here.  The flags enter the
# digest of the stamp (object_digest).
LINK_FLAGS = ['-Wl,-Bsymbolic-functions', '-Wl,--no-as-needed']

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

# The flag of the counters of writes into old nodes of the block heap (make
# GC_WRITE_COUNTERS=1; see src/cyrt/graph/gc/wdgc.cpp).  Their sites in the
# runtime headers (the indexer of indexing.hxx, Node::successor_node) are
# empty inline functions without it, so a module is compiled with the
# setting of the installed runtime.
GC_WRITE_COUNTERS_FLAGS = ['-DSPRITE_GC_WRITE_COUNTERS']

def gc_flags(gc=None, write_counters=None):
  '''
  The compiler flags of a collector of the runtime, by default the collector
  of the installed runtime (config.cxx_gc), with the flag of the write
  counters when ``write_counters`` is true, by default when the installed
  runtime has them (config.cxx_gc_write_counters).  The counters belong to
  the block heap: 'mps' never gets the flag.
  '''
  if gc is None:
    gc = config.cxx_gc()
  if write_counters is None:
    write_counters = config.cxx_gc_write_counters()
  flags = list(GC_FLAGS[gc])
  if gc == 'wdgc' and write_counters:
    flags += GC_WRITE_COUNTERS_FLAGS
  return flags

def object_digest(flavor=None, include_dir=None, gc=None, write_counters=None):
  '''
  The digest of the ABI stamp of an object compiled now: a digest of the
  runtime headers (runtime_digest), of the flags of ``flavor``, by default
  the flavor of the installed runtime (config.cxx_flavor), of the flags of
  the collector ``gc`` and of its write counters, by default the installed
  ones (config.cxx_gc, config.cxx_gc_write_counters), of the link flags, of
  the compiler the runtime was built with (config.cxx_compiler: its version
  and target, as the build recorded them in sysconfig/cxx_compiler) and of
  the format of the generated code (compiler.FORMAT_VERSION).  So a change
  to a header, to the flags of a flavor, to the collector, to the write
  counters, to the compiler of the build or to the format compiles every
  object again, once.  The digest covers what decides whether an object
  fits a runtime, and nothing of where the runtime is installed: two
  installations of one runtime give one digest, so the product cache can
  serve both, and a package relocated by its manager keeps its objects.
  The installation is the second line of the stamp, as text (see Cpp2So).
  The compiler enters through the record of the build, not through a probe
  of the compiler at hand: an installation without a compiler computes the
  digest of its shipped objects all the same.  The flags of the environment
  (CXXFLAGS) are not part of the digest.

  Returns None when the tree holds no header (see runtime_digest).
  '''
  headers = runtime_digest(include_dir)
  if headers is None:
    return None
  if flavor is None:
    flavor = config.cxx_flavor()
  digest = hashlib.sha256(headers.encode('utf-8'))
  for flag in flavor_flags(flavor) + gc_flags(gc, write_counters) + LINK_FLAGS:
    digest.update(b'\0')
    digest.update(flag.encode('utf-8'))
  digest.update(b'\0compiler ')
  digest.update(config.cxx_compiler().encode('utf-8'))
  digest.update(b'\0format %d' % compiler.FORMAT_VERSION)
  return digest.hexdigest()[:16]

def installation_path():
  '''
  The real path of the installation: the text of the second line of an ABI
  stamp.  The stamp names the installation the object was compiled under,
  and an object whose stamp names another is stale (Cpp2So.is_stale): a
  copy of an installation made by hand compiles its objects again, and a
  package whose manager rewrote the text keeps them (the decision of issue
  #100).  The object itself names no path since format 13 of the generated
  code: it names the objects of its imports and the runtime library by
  SONAME (see soname), so the line is the one tie between an object and an
  installation.
  '''
  return os.path.realpath(config.prefix())

# The prefix of the SONAME of a compiled module.  A system library is named
# "lib<name>.so.<version>" (libgcc_s.so.1, libc.so.6), which a bare
# "<module>.so.<format>" would match; the prefix holds a character no
# module name holds, so the two kinds of name never meet.
SONAME_PREFIX = 'sprite-'

def soname(fullname, format_version=None):
  '''
  The SONAME of the object of the module ``fullname``: the full name of the
  module and the format of the generated code (compiler.FORMAT_VERSION by
  default), in the form "sprite-<module>.so.<format>", for instance
  "sprite-Data.List.so.13".  The compile step gives every object its
  SONAME, and the linker records the SONAME of each object on the link
  line as a NEEDED entry of the importer.  The dynamic linker satisfies
  such an entry with an object of that name that the process has mapped
  already, whatever its path, so the loader imports the modules an object
  needs before it opens the object (loader.needed_modules).  The format
  version is part of the name, so an object of another format never
  satisfies the entry; the ABI stamp keeps such an object out of a process
  in any case.  A dot of the module name is a dot of the SONAME; the
  prefix and the suffix ".so." bound the name (module_of_soname).
  '''
  if format_version is None:
    format_version = compiler.FORMAT_VERSION
  return '%s%s.so.%d' % (SONAME_PREFIX, fullname, format_version)

def module_of_soname(name):
  '''
  The full name of the module whose object has the SONAME ``name`` (see
  soname), or None when ``name`` is not of that form: the name of a system
  library, or of the runtime library.  The format version is not checked.
  '''
  if not name.startswith(SONAME_PREFIX):
    return None
  fullname, sep, version = name[len(SONAME_PREFIX):].rpartition('.so.')
  if not sep or not fullname or not version.isdigit():
    return None
  if not curryname.isLegalModulename(fullname):
    return None
  return fullname

# The sources of the code generator of this backend, whose change changes the
# generated code: the emitter and its helpers in this directory, the generic
# emitter, the optimizer with its analyses, which rewrite the ICurry before
# the emitter reads it, and the readers of the ICurry on the way from the
# .icy file to the emitter (the ICurry types and their JSON reader, the
# loader and the JSON writer of the toolchain).  A directory stands for its
# Python files.  They are part of the key of the product cache (see
# Cpp2So.product_facts): the format stamp of a generated file names its
# layout, which changes less often than the code, and the cache must not
# serve the code of one tree to another tree whose generator differs.
GENERATOR_SOURCES = [
    os.path.join('backends', 'cxx', 'compiler.py')
  , os.path.join('backends', 'cxx', 'materialize.py')
  , os.path.join('backends', 'cxx', 'passthrough.py')
  , os.path.join('backends', 'generic', 'compiler.py')
  , os.path.join('backends', 'generic', 'renderer.py')
  , os.path.join('interpreter', 'optimize.py')
  , os.path.join('icurry')
  , os.path.join('icurry', 'analysis')
  , os.path.join('icurry', 'types')
  , os.path.join('toolchain', '_icurry2json.py')
  , os.path.join('toolchain', '_loadcurry.py')
  ]

def generator_files():
  '''The files of GENERATOR_SOURCES, relative to the package, sorted.'''
  package = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
  for relpath in GENERATOR_SOURCES:
    path = os.path.join(package, relpath)
    if os.path.isdir(path):
      for name in sorted(os.listdir(path)):
        if name.endswith('.py'):
          yield os.path.join(relpath, name), os.path.join(path, name)
    else:
      yield relpath, path

@functools.lru_cache(maxsize=None)
def generator_digest():
  '''A digest of the files of GENERATOR_SOURCES, cached for the life of the process.'''
  digest = hashlib.sha256()
  for relpath, path in generator_files():
    digest.update(relpath.encode('utf-8'))
    digest.update(b'\0')
    try:
      with open(path, 'rb') as stream:
        digest.update(stream.read())
    except FileNotFoundError:
      pass
    digest.update(b'\0')
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
    this step and the C++ compiler do not run for it.  Under 'tiered' the
    same holds, and the module is compiled in the background after its load
    (see tiered.py).  A module with a current object never reaches this
    step: the object is the newest file.
    '''
    return self.interp.flags['interpret'] in ('new', 'tiered') \
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
  newer, so a build that changes no header keeps the member.  A stale member
  of another flavor is removed when a flavor prepares its own (see
  remove_stale_members): g++ never compares a member with the headers, and
  it takes the first member of the directory whose options agree with the
  compilation.
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
      self.remove_stale_members()
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
    self.remove_stale_members()
    return True

  def remove_stale_members(self):
    '''
    Removes the other members of the directory that are older than a header.
    g++ tries the members in the order of the directory and uses the first
    one whose options agree with the compilation; it never compares a member
    with the headers.  So when a compilation defines a macro that the
    current member was built without (the macro of the write counters, or
    of the Memory Pool System), g++ rejects that member and may take a stale
    one of an earlier runtime, and the module is compiled against old
    headers.  A flavor whose member is removed builds it again.  A member
    that another process reads stays readable after the unlink.
    '''
    try:
      newest = max(os.path.getmtime(f) for f in self.header_files())
      names = os.listdir(self.directory)
    except (OSError, ValueError):
      return
    for name in names:
      path = os.path.join(self.directory, name)
      if path == self.filename or not name.endswith('.gch'):
        continue
      try:
        if os.path.getmtime(path) < newest:
          logger.info('Removing the stale precompiled header %r', path)
          os.unlink(path)
      except OSError:
        pass

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
  flavor (see flavor).  Each object gets an ABI stamp, a text file beside it
  (<module>.so.abi) of two lines::

      <digest>
      <installation>

  The first line is the digest of the runtime headers and of the flags the
  object was compiled with (object_digest), 16 hex digits.  The second line
  is the real path of the installation the object was compiled under
  (installation_path).  An object is current when the digest is accepted
  (accepted_digests) and the path is the installation of the process
  (is_stale).  So a copy of an installation made by hand keeps objects
  whose stamps name the original and compiles them again, and a package
  whose manager rewrites the path at install time (conda lists the stamps
  in info/has_prefix as text files) keeps its objects.  A stamp of one
  line, written before the path joined it, is stale.

  The link line names no path that the object keeps.  The object gets the
  SONAME of its module (soname; the module name comes from the header of
  the generated file, "// MODULE: N"), the objects of its imports stand on
  the line by their files and enter the object as their SONAMEs (the
  NEEDED entries; every import, in the order of the IMPORTS line, see
  LINK_FLAGS), and the runtime library enters as "libcyrt.so", which
  the extension module of the backend has loaded.  So readelf -d shows no
  absolute path, and an object compiled in one tree loads in a copy of the
  tree at another path, or from the product cache in another tree.  A
  program that opens such an object with dlopen and without the loader
  must open the objects of its imports first, in dependency order, with
  the runtime library loaded or on the search path; or it must name, on
  LD_LIBRARY_PATH, a directory that holds each import under its SONAME.

  A compile stores its products in the product cache (store), and the plan
  places the cached products of a module instead of a compile (restore).
  '''
  STAMP_SUFFIX = '.abi'

  def __init__(self, interp):
    self.interp = interp

  def __repr__(self):
    return 'cpp2so'

  def ends_plan(self, filename):
    '''
    Tells whether the plan ends at ``filename``, a generated .cpp file this
    step would compile.  Under the interpreter flag ``interpret`` set to
    'tiered', a module with a generated file and no object (a background
    compile that was cancelled) is interpreted from the JSON beside the
    file, which loadcurry reads, and the background compile starts from the
    generated file.  Without the JSON the plan goes on.
    '''
    return self.interp.flags['interpret'] == 'tiered' \
        and filename.endswith('.cpp') \
        and _loadcurry.json_beside(filename) is not None

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

    A .so file is stale when its ABI stamp is missing, holds a digest this
    step does not accept (accepted_digests), or names another installation
    (stamp_is_current): the object was compiled against other headers, with
    the flags of another flavor, or under another installation.  The check
    reads the headers, not time stamps, so a new copy of the same runtime
    keeps every object, and a relocated package keeps its objects.  An
    installation without headers (runtime_digest gives None) cannot compile
    anything, so its objects are trusted as they are.  A .so file is stale
    as well when an import of its module runs without an object
    (import_lacks_an_object).
    '''
    if filename.endswith('.so'):
      if not self.stamp_is_current(filename):
        return True
      return self.import_lacks_an_object(filename)
    return source_is_stale(filename)

  def stamp_is_current(self, sofile):
    '''
    Tells whether the ABI stamp of ``sofile`` holds a digest this step
    accepts and names this installation.  The paths are compared as real
    paths, so a stamp that spells the installation through a link (the
    prefix a package manager wrote) names it all the same.  True without
    a digest to compare (an installation without headers).
    '''
    accepted = self.accepted_digests()
    if not accepted:
      return True
    digest, path = self.read_stamp_lines(sofile)
    if digest not in accepted or path is None:
      return False
    return os.path.realpath(path) == installation_path()

  def import_lacks_an_object(self, sofile):
    '''
    Tells whether an import of the module of ``sofile`` runs without a
    compiled object.  The imports are read from the generated file beside
    the object, or from the NEEDED entries of the object when the file is
    gone (sprite-make --tidy removes it; loader.needed_modules), and
    imported first.  The two lists agree: the linker records every import
    (LINK_FLAGS).

    The object names the objects of its imports as needed libraries, by
    SONAME (see _dependencies), and the dynamic linker satisfies each name
    with the object of that name the process has mapped.  When an import
    was edited, its object is stale: under the interpreter flag
    ``interpret`` the import is interpreted from its ICurry, no object of
    its name is mapped, and the load of the importer would fail.  So an
    object is loaded only when every import was loaded from its object; a
    module whose import is interpreted is interpreted too (or compiled
    again, without the flag).  An object whose imports cannot be read is
    trusted; the loader reads them once more before it opens the object
    (loader.load_module).
    '''
    from . import loader
    cppfile = _filenames.replacesuffix(sofile, '.cpp')
    try:
      if os.path.isfile(cppfile):
        imports = self._importedModules(cppfile)
      else:
        imports = loader.needed_modules(sofile)
    except (exceptions.PrerequisiteError, OSError, ValueError) as exc:
      logger.debug('The imports of %r cannot be read (%s)', sofile, exc)
      return False
    for modulename in imports:
      module = self.interp.import_(modulename)
      if getHandle(module).sofilename is None:
        logger.debug(
            'The object %r is not loaded: its import %s has no object'
          , sofile, modulename
          )
        return True
    return False

  @classmethod
  def stampfile(cls, sofile):
    '''The ABI stamp of a shared object.'''
    return sofile + cls.STAMP_SUFFIX

  @classmethod
  def read_stamp_lines(cls, sofile):
    '''
    The two lines of the ABI stamp of ``sofile``: the digest and the real
    path of the installation.  A missing line is None; so is each of a
    missing stamp.
    '''
    try:
      with open(cls.stampfile(sofile), 'r') as stream:
        lines = stream.read().splitlines()
    except OSError:
      return None, None
    lines = [line.strip() for line in lines[:2]]
    lines += [None] * (2 - len(lines))
    return lines[0] or None, lines[1] or None

  @classmethod
  def read_stamp(cls, sofile):
    '''The digest recorded in the ABI stamp of ``sofile``, or None.'''
    return cls.read_stamp_lines(sofile)[0]

  def write_stamp(self, sofile):
    '''
    Records the stamp of this step beside ``sofile``: its digest and the
    real path of this installation (see the class).  Without headers there
    is no digest, and no stamp is written.
    '''
    digest = self.digest()
    if digest is None:
      return
    stamp = self.stampfile(sofile)
    tmp = '%s.%d.tmp' % (stamp, os.getpid())
    with filesys.remove_file_on_error(tmp):
      with open(tmp, 'w') as stream:
        stream.write('%s\n%s\n' % (digest, installation_path()))
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

  MODULE_PAT = re.compile(r'// MODULE: (\S+)')
  def _moduleName(self, file_in):
    '''
    The full name of the module of the generated file ``file_in``, from the
    comment in its header ("// MODULE: N"; compiler.vEmitHeader).  The
    SONAME of the object is formed from it (soname).
    '''
    with open(file_in, 'r') as stream:
      for line in itertools.islice(stream, 16):
        m = self.MODULE_PAT.match(line)
        if m:
          return m.group(1)
    raise exceptions.PrerequisiteError(
        'Cannot find the MODULE line in %r' % file_in
      )

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
    Generates the .so files the specified .cpp file depends on.  They stand
    on the link line by their files, and the linker records each one by
    its SONAME (soname) in the NEEDED entries of the object (LINK_FLAGS),
    so the object names no path of this tree.
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

  def prepare_header(self):
    '''
    Builds the precompiled header when it is missing or stale.  Returns True
    when g++ can use it, False when the header is disabled, no compiler is
    installed, or the build failed (then the objects compile without it).
    sprite-make --jobs calls this once before its children start, so that
    the children do not each build the header.
    '''
    root = config.cxx_pch_root()
    cxx = config.cxx_tool()
    if root is None or cxx is None:
      return False
    return PrecompiledHeader(root, cxx, self._cxxflags()).prepare()

  def _pchflags(self):
    '''
    Prepares the precompiled header.  Yields the include flag that lets g++
    find it when it lives outside the installed include directory.
    '''
    if self.prepare_header():
      root = config.cxx_pch_root()
      if root != config.installed_path('include'):
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
    yield '-Wl,-soname,%s' % soname(self._moduleName(file_in))
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
    directory = os.path.dirname(os.path.abspath(file_out))
    if not os.access(directory, os.W_OK):
      # The first write would fail with a bare "permission denied".  Name
      # the cause instead.  The common case is a read-only installation
      # whose shipped object is stale here: its stamp names another
      # installation or runtime (see object_digest).
      stamp = self.read_stamp(file_out)
      if not os.path.isfile(file_out):
        state = 'no object exists there'
      elif stamp is None:
        state = 'the object there has no ABI stamp'
      elif self.stamp_is_current(file_out):
        state = 'the object there is current, but a compile was asked for'
      else:
        state = 'the object there is stale (its ABI stamp names another ' \
                'installation or runtime)'
      raise exceptions.CompileError(
          'cannot compile %r: the directory %r cannot be written, and %s.  '
          'Make the directory writable, or run the program with sprite-exec, '
          'whose tiered default interprets a module without a current object.'
        % (file_in, directory, state)
        )
    logger.info('Compiling %r', file_out)
    cmd = list(self._compileCommand(file_in, file_out))
    logger.debug('Command: %s', ' '.join(cmd))
    # The old stamp goes before the compiler runs.  An object without a stamp
    # is stale, so a compile that stops between the compiler and the new
    # stamp (a kill, a time limit) leaves nothing a later process would trust
    # under the old digest.  The old object goes too: it may be a hard link
    # into the product cache, which must not be written into (the linker
    # writes a new file as well; this makes sure of it).
    self.remove_stamp(file_out)
    try:
      os.unlink(file_out)
    except FileNotFoundError:
      pass
    _system.pexec(cmd)
    self.write_stamp(file_out)
    self.store(file_in, file_out, currypath)
    return file_out

  # The product cache
  # =================
  # The products of a compile (the generated file, the object and its stamp)
  # are stored under the digest of the stamp and a key of the facts that
  # decide them (product_facts, product_key), and the plan asks this step to
  # place the cached products of a module before each step
  # (plans.Plan.restore, _makecurry.Maker.make).  See
  # curry.toolchain._productcache.

  PRODUCT_SUFFIXES = ('.cpp', '.so')

  def product_facts(self, curryfile):
    '''
    The facts, as strings, that decide the generated code and the object of
    a module beyond its source chain: the key of the product cache digests
    them (see _productcache.product_key).  In order: the format of the
    generated code (compiler.FORMAT_VERSION) and the digest of the sources
    of the code generator (generator_digest); the keys of the optimizer
    passes and the inline budget of the interpreter, which shape the code;
    and the intermediate directory and the route from Curry to ICurry
    (cache.frontend_digest), which decide the ICurry of a source.  No fact
    names a tree: the products name no path since format 13 (the SONAMEs
    and the record), so an entry serves every tree of one runtime, and a
    second worktree compiles nothing the first compiled.  Before format 13
    the real paths of the installation and of the directory of the source
    were facts, because the object named both.
    '''
    from ...interpreter import optimize
    from ... import cache
    flags = self.interp.flags
    return [
        'format %d' % compiler.FORMAT_VERSION
      , 'generator ' + generator_digest()
      , 'optimizers ' + ' '.join(key for key, _ in optimize.default_optimizers)
      , 'inline_budget %d' % flags['inline_budget']
      , 'subdir ' + config.intermediate_subdir()
      , 'frontend ' + cache.frontend_digest()
      ]

  def product_key(self, filename, currypath):
    '''
    The key of the product cache for the module of ``filename``, a file of
    its chain (see _productcache.product_key), or None when the module has
    no text to digest.
    '''
    curryfile = _filenames.curryfilename(filename)
    return _productcache.product_key(
        curryfile, currypath, self.product_facts(curryfile)
      )

  def restore(self, file_in, currypath):
    '''
    Places the cached products of the module of ``file_in``, a current JSON
    or generated file of the module, beside it: the generated file, the
    object, and a stamp for this installation.  Returns the object, or None
    when the cache is off or holds no entry, when the module is excluded
    (_productcache.excluded), when a recompile is forced
    (SPRITE_FORCE_RECOMPILE_CXX), when the directory cannot be written, or
    when an import of the module runs without an object
    (import_lacks_an_object): the object stays in place for a later plan,
    which finds it current once the import has its object, but the module
    is not loaded from it now.  Nothing is placed under the interpreter
    flag ``interpret`` set to 'new' either: that mode interprets a module
    without a current object and never compiles it (Json2Cpp.ends_plan),
    and a cached object would make the module compiled after all.  The
    placement counts on the compile clock.
    '''
    if not file_in.endswith(('.json', '.json.z', '.cpp')):
      return None
    if not _productcache.enabled() or config.force_recompile_cxx():
      return None
    if self.interp.flags['interpret'] == 'new':
      return None
    if _productcache.excluded(_filenames.curryfilename(file_in)):
      return None
    digest = self.digest()
    if digest is None:
      return None
    sofile = _filenames.replacesuffix(file_in, '.so')
    directory = os.path.dirname(os.path.abspath(sofile))
    if not os.access(directory, os.W_OK):
      return None
    try:
      key = self.product_key(file_in, currypath)
    except OSError as exc:
      logger.debug('No product cache key for %r (%s)', file_in, exc)
      return None
    if key is None:
      return None
    names = [
        os.path.basename(_filenames.replacesuffix(file_in, suffix))
        for suffix in self.PRODUCT_SUFFIXES
      ]
    if _productcache.lookup(digest, key, names) is None:
      return None
    with _makecurry.compile_clock:
      try:
        placed = _productcache.restore(digest, key, directory, names)
      except OSError as exc:
        logger.warning(
            'cannot restore %r from the product cache (%s); it is compiled'
          , sofile, exc
          )
        return None
      if placed is None:
        return None
      self.write_stamp(sofile)
    logger.info('Restored %r from the product cache', sofile)
    if self.import_lacks_an_object(sofile):
      return None
    return sofile

  def store(self, cppfile, sofile, currypath):
    '''
    Stores the products of a compile in the product cache: the generated
    file, the object and its stamp.  Nothing when the cache is off.  A
    cache that cannot be written is logged once and left alone.
    '''
    if not _productcache.enabled():
      return
    if _productcache.excluded(_filenames.curryfilename(cppfile)):
      return
    digest = self.digest()
    if digest is None:
      return
    try:
      key = self.product_key(cppfile, currypath)
      if key is None:
        return
      _productcache.store(digest, key, [cppfile, sofile, self.stampfile(sofile)])
    except OSError as exc:
      if 'store' not in self._warned:
        self._warned.add('store')
        logger.warning(
            'cannot store %r in the product cache at %r (%s); set '
            'SPRITE_PRODUCT_CACHE to a writable directory, or to the empty '
            'string to turn the cache off'
          , sofile, _productcache.root(), exc
          )
      return
    logger.debug('Stored %r in the product cache', sofile)

  # The warnings this process logged once about the cache.
  _warned = set()

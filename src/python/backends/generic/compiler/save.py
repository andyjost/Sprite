from .... import config
from . import render, statics
from ....utility import filesys
import abc, os, six

MAX_JUSTIFY_FUNCTION_NAME = 36
MAX_JUSTIFY_NEEDED        = 8

class PackageCreator(abc.ABC):
  '''
  Writes a Curry module to a Python package.

  Creates the package directory and places an __init__.py and backend-specific
  implementation under it.  The initializer loads the implementation and
  imports it into the Curry system.  So, importing the package has the effect
  of loading that Curry module.
  '''
  FILES = '__init__.py',

  def __init__(self, ir, filename, defaultgoal=None):
    self.defaultgoal = defaultgoal
    self.ir          = ir
    self.filename    = os.path.normpath(
        ir.icurry.name if filename is None else filename
      )

  def createPackage(self):
    # If the package would contain only the __init__.py file, just create a .py
    # file instead.
    if len(self.FILES) == 1 and self.FILES[0] == '__init__.py':
      filename = self.filename + '.py' if not self.filename.endswith('.py') \
                                       else self.filename
      generator = self.getGenerator('__init__.py')
      self.createFile(filename, generator)
    else:
      filesys.getdir(self.filename)
      for filename in self.FILES:
        filename = os.path.join(self.filename, filename)
        self.createFile(filename)

  def createFile(self, filename, generator=None):
    generator = self.getGenerator(filename) if generator is None else generator
    text = generator()
    with open(filename, 'w') as stream:
      stream.write(text)

  def getGenerator(self, filename):
    base = os.path.basename(filename)
    stem = os.path.splitext(base)[0]
    generator_name = 'generate%s' % stem
    return getattr(self, generator_name)


class FileGenerator(object):
  '''
  Template method used to generate file.  Derived classes must provide a
  sequences of SECTIONS and RENDERER.  The generate method will generate the
  sections in order and the render method will render them as a string.
  '''

  def render(self):
    return self.RENDERER.renderLines(self.generate())

  def generate(self):
    for section_name in self.SECTIONS:
      section = getattr(self, section_name)
      for line in section():
        yield line
      yield ''
    yield ''


class ModuleInterfaceGenerator(abc.ABC, FileGenerator):
  '''
  Generates the contents of the __init__.py file needed to load a Curry
  module.
  '''
  RENDERER = render.PY_RENDERER
  SECTIONS = (
      'banner'
    , 'imports'
    , 'symbolDefs'
    , 'moduleDef'
    , 'moduleImport'
    , 'link'
    , 'moduleMain'
    )

  def __init__(self, ir, defaultgoal=None):
    self.defaultgoal = defaultgoal
    self.ir = ir

  @property
  def fullname(self):
    return self.imodule.fullname

  @property
  def imodule(self):
    return self.ir.icurry

  def banner(self):
    banner = 'Python interface for Curry module %r' % self.imodule.fullname
    yield '# ' + '-' * len(banner)
    yield '# ' + banner
    yield '# ' + '-' * len(banner)

  def imports(self):
    curry = config.python_package_name()
    yield 'import %s' % curry
    yield 'from %s.icurry import \\' % curry
    yield '    IModule, IDataType, IConstructor, PUBLIC, PRIVATE'
    yield ''
    yield "if 'interp' not in globals():"
    yield '  interp = %s.getInterpreter()' % curry

  @abc.abstractmethod
  def symbolDefs(self):
    pass

  def moduleDef(self):
    imodule = self.imodule
    py = render.PY_RENDERER
    yield '# Interface'
    yield '# ---------'
    yield '_icurry_ = IModule.fromBOM('
    yield '    fullname=%r' % imodule.fullname
    yield '  , filename=%r' % imodule.filename
    yield '  , imports=%s'  % repr(imodule.imports)
    if not imodule.types:
      yield '  , types=[]'
    else:
      yield '  , types=['
      for prefix, itype in py.prettylist(six.itervalues(imodule.types), level=1):
        yield '%sIDataType(%r, [' % (prefix, itype.fullname)
        for prefix, ictor in py.prettylist(itype.constructors, level=2):
          yield '%s%r' % (prefix, ictor)
        yield py.blockdelim(2, '])')
      yield py.blockdelim(1, ']')
    if not imodule.functions:
      yield '  , functions=[]'
    else:
      yield '  , functions=['
      functions = imodule.functions.values()
      w1 = py.justify(
          [repr(ifun.fullname) for ifun in functions]
        , maximum=MAX_JUSTIFY_FUNCTION_NAME
        )
      w2 = py.justify(
          [repr(ifun.needed) for ifun in functions]
        , maximum=MAX_JUSTIFY_NEEDED
        )
      fmt = '%s(%-{0}r, %r, %-7r, %-{1}r, %s)'.format(w1, w2)
      for prefix, ifun in py.prettylist(functions, level=1):
        yield fmt % (
            prefix, ifun.fullname, ifun.arity, ifun.vis, ifun.needed
          , ifun.body.linkname
          )
      yield py.blockdelim(1, ']')
      yield py.blockdelim(0, ')')

  def moduleImport(self):
    yield '_module_ = interp.import_(_icurry_)'

  def link(self):
    return generateLinkSection(self.ir, self.RENDERER)

  def moduleMain(self):
    yield '# Module main'
    yield '# -----------'
    yield '''if __name__ == '__main__':'''
    yield   '  from %s import __main__' % config.python_package_name()
    yield   '  __main__.moduleMain(__file__, %r, goal=%r)' % \
              (self.imodule.fullname, self.defaultgoal)

def generateLinkSection(ir, renderer, prefix=None):
  yield '# Linking'
  yield '# -------'
  items = ir.closure.dict.items()
  width = renderer.justify([name for name,_ in items])
  fmt = '{}%-{}s = %s'.format('' if prefix is None else prefix, width)
  for name, value in sorted(items, key=statics.sortkey):
    if name.startswith(statics.PX_DATA):
      yield fmt % (name, value)
    elif name.startswith(statics.PX_FUNC):
      yield 'from %s import %s as %s' % (value.__module__, value.__name__, name)
    elif name.startswith(statics.PX_INFO):
      yield fmt % (name, 'interp.symbol(%r)' % value.fullname)
    elif name.startswith(statics.PX_STR):
      yield fmt % (name, '%r' % value)
    elif name.startswith(statics.PX_TYPE):
      yield fmt % (name, 'interp.type(%r)' % value.fullname)

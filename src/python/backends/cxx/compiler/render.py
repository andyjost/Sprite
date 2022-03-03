from ...generic.compiler import render as generic_render, statics
from .... import config
import six

__all__ = ['render']

MAX_JUSTIFY_FUNCTION_NAME = 36
MAX_JUSTIFY_NEEDED        = 8

def render(obj, **kwds):
  return generic_render.render(obj, cls=Renderer, **kwds)

class Renderer(generic_render.Renderer):
  COMMENT_STR = '//'
  BLOCK_OPEN = '{'
  BLOCK_CLOSE = '}'

  def __init__(self, *args, **kwds):
    kwds['hcol'] = 20
    super(Renderer, self).__init__(*args, **kwds)

  def _convertIR2Lines(self, ir):
    imodule = ir.icurry
    banner = 'C++ code for Curry module %r' % imodule.fullname
    yield '// ' + '-' * len(banner)
    yield '// ' + banner
    yield '// ' + '-' * len(banner)
    yield ''
    curry = config.python_package_name()
    yield '#include "cyrt/cyrt.hpp"'
    yield 'using namespace cyrt;'
    # yield "if 'interp' not in globals():"
    # yield '  interp = %s.getInterpreter()' % curry
    yield ''
    for line in ir.lines:
      yield line
    yield ''
    # yield ''
    # yield '// Interface'
    # yield '// ---------'
    # yield '_icurry_ = IModule.fromBOM('
    # yield '    fullname=%r' % imodule.fullname
    # yield '  , filename=%r' % imodule.filename
    # yield '  , imports=%s'  % repr(imodule.imports)
    # if not imodule.types:
    #   yield '  , types=[]'
    # else:
    #   yield '  , types=['
    #   for prefix, itype in self._plist(six.itervalues(imodule.types), level=1):
    #     yield '%sIDataType(%r, [' % (prefix, itype.fullname)
    #     for prefix, ictor in self._plist(itype.constructors, level=2):
    #       yield '%s%r' % (prefix, ictor)
    #     yield self._close(2, '])')
    #   yield self._close(1, ']')
    # if not imodule.functions:
    #   yield '  , functions=[]'
    # else:
    #   yield '  , functions=['
    #   functions = imodule.functions.values()
    #   w1 = self._justify(
    #       [repr(ifun.fullname) for ifun in functions]
    #     , maximum=MAX_JUSTIFY_FUNCTION_NAME
    #     )
    #   w2 = self._justify(
    #       [repr(ifun.needed) for ifun in functions]
    #     , maximum=MAX_JUSTIFY_NEEDED
    #     )
    #   fmt = '%s(%-{0}r, %r, %-7r, %-{1}r, %s)'.format(w1, w2)
    #   for prefix, ifun in self._plist(functions, level=1):
    #     yield fmt % (
    #         prefix, ifun.fullname, ifun.arity, ifun.vis, ifun.needed
    #       , ifun.body.linkname
    #       )
    #   yield self._close(1, ']')
    #   yield self._close(0, ')')
    # yield ''
    # yield '_module_ = interp.import_(_icurry_)'
    # yield ''
    # yield ''
    # yield '# Linking'
    # yield '# -------'
    # for line in self._convertClosure2Lines(ir.closure):
    #   yield line
    # yield ''
    # yield ''
    # yield '''if __name__ == '__main__':'''
    # yield   '  from %s import __main__' % config.python_package_name()
    # yield   '  __main__.moduleMain(__file__, %r, goal=%r)' % (imodule.fullname, self.goal)
    # yield ''
    # yield ''

  def _convertClosure2Lines(self, closure):
    breakpoint()
    # items = [item for item in closure.dict.items() if self.cpred(item[0])]
    # width = self._justify([name for name,_ in items])
    # fmt = '%-{}s = %s'.format(width)
    # for name, value in sorted(items, key=self._sortkey):
    #   if name.startswith(statics.PX_DATA):
    #     yield fmt % (name, value)
    #   elif name.startswith(statics.PX_FUNC):
    #     yield 'from %s import %s as %s' % (value.__module__, value.__name__, name)
    #   elif name.startswith(statics.PX_INFO):
    #     yield fmt % (name, 'interp.symbol(%r)' % value.fullname)
    #   elif name.startswith(statics.PX_STR):
    #     yield fmt % (name, '%r' % value)
    #   elif name.startswith(statics.PX_TYPE):
    #     yield fmt % (name, 'interp.type(%r)' % value.fullname)

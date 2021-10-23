from .. import types, visit
from ...utility.visitation import dispatch

__all__ = ['find_static_strings']

def find_static_strings(iobj):
  '''
  A static string is a sequence of ICCall nodes constructing a list of
  characters.
  '''
  visitor = FindStaticStrings()
  visit.visit(visitor, iobj)
  return visitor.replacements


class FindStaticStrings(object):
  def __init__(self):
    self.headcall = None
    self.string = None
    self.replacements = {}

  @dispatch.on('iobj')
  def __call__(self, iobj, **kwds):
    self.endofstring(iobj, **kwds)

  @__call__.when(types.ICCall)
  def __call__(self, iccall, **kwds):
    if iccall.symbolname == 'Prelude.[]':
      self.headcall = id(iccall)
      self.string = []
      return
    elif self.headcall and iccall.symbolname == 'Prelude.:':
      char, tail = iccall.exprs
      if type(getattr(char, 'lit', None)) is types.IChar:
        self.headcall = id(iccall)
        self.string.append(char.lit.value)
        return
    self.endofstring(iccall, **kwds)

  def endofstring(self, inext, parent=None, key=None, index=None, **kwds):
    if self.headcall:
      if self.string:
        string = ''.join(self.string[::-1])
        self.replacements[self.headcall] = types.IString(string)
      self.headcall = None
      self.string = None


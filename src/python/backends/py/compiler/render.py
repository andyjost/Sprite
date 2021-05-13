from ....utility import visitation
import collections

@visitation.dispatch.on('arg')
def indent(arg, level=-1):
  '''
  Indents list-formatted Python code into a flat list of strings.  See
  ``render``.
  '''
  assert False

@indent.when(str)
def indent(line, level=-1):
  yield '  ' * level + line

@indent.when(collections.Sequence, no=str)
def indent(seq, level=-1):
  for line in seq:
    for rline in indent(line, level+1):
      yield rline

def render(pycode):
  '''
  Renders list-formatted Python code into a string containing valid Python.

  The input is possibly-nested lists of strings.  The list nestings correspond
  to indentation levels.
  '''
  return '\n'.join(indent(pycode))

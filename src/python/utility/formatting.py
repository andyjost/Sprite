from ..utility.visitation import dispatch
from collections import Sequence

@dispatch.on('arg')
def indent(arg, n=2):
  return indent(str(arg), n)

@indent.when(str)
def indent(string, n=2):
  space = ' ' * n
  return '\n'.join('%s%s' % (space, text) for text in string.split('\n'))
  
@indent.when(Sequence, no=(str,))
def indent(seq, n=2):
  return '\n'.join(indent(line, n) for line in seq)
  

def wrapblock(arg, n=2, line_prefix=' '):
  lines = str(arg).strip('\n').split('\n')
  if len(lines) > 1:
    return '\n%s' % indent(lines, n)
  else:
    return line_prefix + lines[0]
  

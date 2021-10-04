'''
Code to clean up Curry output.  The idea is that cleaned output from an Oracle
such as PAKCS or KiCS2 can be compared directly to cleaned outpu from Sprite.
The cleaner might, for instance, standarize whitespace, remove empty lines, or
sort the output values.
'''
from curry.utility import visitation
import collections

@visitation.dispatch.on('arg')
def clean(arg, **kwds):
  '''
  Clean up Curry output for string-based comparisons.

  Each line is treated as a value of the program.  Insignificant whitespace is
  removed, and the lines are sorted.
  '''
  raise RuntimeError('unhandled type: %s' % type(arg))

@clean.when(collections.Sequence, no=(str,))
def clean(lines, **kwds):
  if not kwds.get('keep_empty_lines', False):
    lines = (line for line in lines if line)
  if not kwds.get('keep_spacing', False):
    lines = (line.replace(' ','').replace('\t','') for line in lines)
  if kwds.get('sort_lines', True):
    lines = sorted(lines)
  return '\n'.join(lines)

@clean.when(str)
def clean(string, **kwds):
  return clean(string.split('\n'), **kwds)


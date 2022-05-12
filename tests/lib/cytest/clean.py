'''
Code to clean up Curry output.  The idea is that cleaned output from an Oracle
such as PAKCS or KiCS2 can be compared directly to cleaned outpu from Sprite.
The cleaner might, for instance, standarize whitespace, remove empty lines, or
sort the output values.
'''
from curry.utility import visitation
import collections, re

P_FLOAT = re.compile(r'''([+-]?\d*\.\d+)''')

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
  # There are tiny differences in the representation of floating point values
  # between the various systems involved: PAKCS, KiCS2, Python, and Sprite.
  # Rather than try to make them all match perfectly we can just add a bit of
  # tolerance to floating-point comparisons.  To do this, we read any
  # floating-point value in the result and print it here with the maximum
  # number or relevant decimal places (17).  Since the output of every system
  # goes through this conversion, they ought to all match when the values are
  # identical.  This is still not perfect due to the possibility of round-off
  # errors.
  sf_option = kwds.get('standardize_floats', False)
  if sf_option:
    float_format = sf_option if isinstance(sf_option, str) else '%0#.17g'
    lines = (
        re.sub(
            P_FLOAT
          , lambda match: float_format % float(match.group(0))
          , line
          )
          for line in lines
      )
  if not kwds.get('keep_spacing', False):
    lines = (line.replace(' ','').replace('\t','') for line in lines)
  if kwds.get('sort_lines', True):
    lines = sorted(lines)
  return '\n'.join(lines)

@clean.when(str)
def clean(string, **kwds):
  return clean(string.split('\n'), **kwds)


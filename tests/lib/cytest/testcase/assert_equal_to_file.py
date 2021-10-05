from cStringIO import StringIO
import collections, gzip, unittest

def assertEqualToFile(
    tc, objs, filename, update=False, checker=unittest.TestCase.assertEqual
  ):
  '''
  Compare an object or objects against a golden file.

  Parameters:
  -----------
  ``objs``
      An object or sequence of objects to compare.
  ``filename``
      The name of the file that stores the golden result.
  ``update``
      If true, then just update the golden file.
  ``checker``
      The function called to compare values.
  '''
  if isinstance(objs, str):
    sprite_answer = objs
  else:
    buf = StringIO()
    if isinstance(objs, collections.Sequence):
      for obj in objs: buf.write(str(obj))
    else:
      buf.write(str(objs))
    sprite_answer = buf.getvalue()
  open_ = gzip.open if filename.endswith('.gz') else open
  if update:
    with open_(filename, 'wb') as au:
      au.write(sprite_answer)
  else:
    with open_(filename, 'rb') as au:
      correct_answer = au.read()
    checker(tc, sprite_answer, correct_answer)



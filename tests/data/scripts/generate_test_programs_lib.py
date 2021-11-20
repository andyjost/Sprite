import os
import sys

from six.moves import cStringIO as StringIO


def generate_test_programs(spec):
  '''
  Generates test programs.

  Each file generated is a Curry source file.  Sets of generated files can be
  used for functional testing.  The reason for doing it this way is simply that
  it is easier to maintain a script than work with a huge number of tiny files.
  This also makes it possible to generate all combinations of a motif
  programmatically (e.g., to flip the operand order when testing commutative
  operators).

  File names follow the patter {prefix}ddd.curry, where prefix is a prefix
  string provided by the caller and ddd is a sequence of digits (the number of
  digits is also controlled by the caller).  Does not touch files that already
  exist and contain the text that would be written.

  See tests/data/curry/eqconstr/generate_test_programs.py for an example.

  Parameters:
  -----------
    ``spec`  `
        A list of 4-tuples containing the following:
          ``programtext``
              A list of strings, where each is the text of a Curry program.  A
              separate file will be generated for each string.
          ``fileprefix``
              String to prepend to each filename generated.
          ``digits``
              The number of digits to use in file numbers.  Zeros will be
              prepadded to file numbers.  Setting this large enough ensures
              tests are run in the correct order.  Consider these sorted lists:
              (digits=1) [test_1, test_10, test_2, ...] vs. (digits=2)
              [test_01, test_02, ..., test_10].
          ``predef``
              A block of text prepended to the program.  Useful for type
              definitions.  Can also be used to prepend something like 'main = '
              if each program is a one-liner.
  '''
  for programtext, fileprefix, digits, predef in spec:
    for i, program_text in enumerate(programtext):
      filename = ('{}{:0%sd}.curry' % digits).format(fileprefix, i)
      text = StringIO()
      text.write(predef)
      text.write(program_text)
      if not os.path.exists(filename) or open(filename).read() != text.getvalue():
        print >>sys.stderr, 'generating', filename
        with open(filename, 'w') as out:
          out.write(text.getvalue())


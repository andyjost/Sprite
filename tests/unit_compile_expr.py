'''
Type annotations and recursive lets read by curry.parse.  See unit_compile.py for the split of these tests.
'''
import cytest # from ./lib; must be first
import curry
from curry import inspect
from curry.backends.generic.eval import evaluator

def parsed_node(text, **kwds):
  node = cytest.raw.expr(curry.parse(text, **kwds))
  return evaluator.single_step(cytest.raw.interp(), node)


class TestCompileExpr(cytest.TestCase):
  @cytest.check_expressions()
  def test_type_annotation(self):
    '''A text annotation fixes the type of the parsed term.'''
    # 1+2.  Without an annotation, the constraint Num a is defaulted to Int by the
    # table of the PAKCS REPL (unit_goals.py), and the body passes the
    # dictionary.
    yield parsed_node('1+2'), None, None, None, [3]
    # The C++ backend represents the explicit step of parsed_node as a
    # forward node at the root; the Python
    # backend rewrites the root in place.  Compare the forward target so one
    # expectation serves both backends.  The optimizer replaces the call of
    # the alias _impl#+#Prelude.Num#Prelude.Int by a call of plusInt.
    e = parsed_node('(1+2) :: Int')
    yield inspect.fwd_chain_target(e), None \
           , '<plusInt <Int 1> <Int 2>>' \
           , None \
           , [3]

    # 1 ? 2
    yield parsed_node('1 ? 2'), None, None, None, [1, 2]
    e = parsed_node('(1 ? 2) :: Int')
    yield inspect.fwd_chain_target(e), None, '<? <Int 1> <Int 2>>', None, [1, 2]

  @cytest.check_expressions()
  def test_reclet(self):
    e = parsed_node('''let a = True:b ; b = False:a in a''')
    yield e, '[True, False, ...]', '<_Fwd <: <True> <: <False> ...>>>'
    # A back reference below the top-level constructor gives the INodeAssign a
    # path of length two.  Both backends must index to the parent slot.
    M = curry.compile('data T = T Bool T Int', modulename='RecLetT')
    e = parsed_node('let a = T True (T False a 1) 2 in a', imports=[M])
    yield e, 'T True (T False ... 1) 2' \
           , '<_Fwd <T <True> <T <False> ... <Int 1>> <Int 2>>>'

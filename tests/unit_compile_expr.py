'''
The expressions that curry.compile builds: the exprtype argument and a
recursive let.  See unit_compile.py for the split of these tests.
'''
import cytest # from ./lib; must be first
import curry
from curry import inspect

class TestCompileExpr(cytest.TestCase):
  @cytest.check_expressions()
  def testExprType(self):
    '''Test the exprtype argument.'''
    # 1+2.  Without exprtype, the constraint Num a is defaulted to Int by the
    # table of the PAKCS REPL (unit_goals.py), and the body passes the
    # dictionary.
    yield curry.compile('1+2', mode='expr'), None, None, None, [3]
    # The C++ backend represents the single rewrite step taken by
    # curry.compile(..., 'expr') as a forward node at the root; the Python
    # backend rewrites the root in place.  Compare the forward target so one
    # expectation serves both backends.  The optimizer replaces the call of
    # the alias _impl#+#Prelude.Num#Prelude.Int by a call of plusInt.
    e = curry.compile('1+2', mode='expr', exprtype='Int')
    yield inspect.fwd_chain_target(e), None \
           , '<plusInt <Int 1> <Int 2>>' \
           , None \
           , [3]

    # 1 ? 2
    yield curry.compile('1 ? 2', mode='expr'), None, None, None, [1, 2]
    e = curry.compile('1 ? 2', mode='expr', exprtype='Int')
    yield inspect.fwd_chain_target(e), None, '<? <Int 1> <Int 2>>', None, [1, 2]

  @cytest.check_expressions()
  def test_reclet(self):
    e = curry.compile('''let a = True:b ; b = False:a in a''', 'expr')
    yield e, '[True, False, ...]', '<_Fwd <: <True> <: <False> ...>>>'
    # A back reference below the top-level constructor gives the INodeAssign a
    # path of length two.  Both backends must index to the parent slot.
    M = curry.compile('data T = T Bool T Int', modulename='RecLetT')
    e = curry.compile('let a = T True (T False a 1) 2 in a', 'expr', imports=M)
    yield e, 'T True (T False ... 1) 2' \
           , '<_Fwd <T <True> <T <False> ... <Int 1>> <Int 2>>>'

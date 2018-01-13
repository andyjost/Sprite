from curry.llvm import *
import curry.llvm as ll
from curry.llvm.types import *
import cytest
import itertools

class TestLLVMObjectLifetimes(cytest.TestCase):

  def testModule(self):
    '''Ensure modules are properly deleted.'''
    n = module._count_
    m = module('foo')
    self.assertEqual(n+1, module._count_)
    del m
    self.assertEqual(n, module._count_)

  def testGlobal(self):
    '''Ensure globals keep their module alive.'''
    m = module('foo')
    m_id = m.id
    x = m.def_('x', i32)
    del m
    self.assertEqual(x.parent.id, m_id)


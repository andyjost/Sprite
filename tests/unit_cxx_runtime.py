import cytest # from ./lib; must be first
from curry.backends.cxx import cyrtbindings as cyrt
from curry import common
import unittest

class TestCxxRuntime(cytest.TestCase):
  def testModuleCreation(self):
    count_modules = lambda: len(cyrt.Module.getall())
    self.assertEqual(count_modules(), 0)

    # Create.
    Hello = cyrt.Module.find_or_create('Hello')
    self.assertEqual(count_modules(), 1)
    self.assertIs(cyrt.Module.getall()['Hello'], Hello)

    # Attributes.
    self.assertEqual(Hello.name, 'Hello')

    # Recreate.
    Hello2 = cyrt.Module.find_or_create('Hello')
    self.assertIs(Hello, Hello2)

    # Delete
    del Hello, Hello2
    self.assertEqual(count_modules(), 0)

  def testTypeCreation(self):
    Hello = cyrt.Module.find_or_create('Hello')

    Cons = Hello.create_infotable(':', 2, common.T_CTOR  , common.F_LIST_TYPE)
    Nil = Hello.create_infotable('[]', 0, common.T_CTOR+1, common.F_LIST_TYPE)
    List = Hello.create_type('[]', [Cons, Nil], 0)

    self.assertEqual(Cons.arity, 2)
    self.assertEqual(Cons.flags, common.F_LIST_TYPE)
    self.assertEqual(Cons.format, 'pp')
    self.assertEqual(Cons.name, ':')
    self.assertEqual(Cons.tag, common.T_CTOR)
    # self.assertIs(Cons.step, None)
    # self.assertIs(Cons.typecheck, None)
    self.assertIs(Cons.typedef, List)

    self.assertIs(List.constructors[0], Cons)
    self.assertIs(List.constructors[1], Nil)


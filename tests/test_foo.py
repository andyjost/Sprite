from curry import compiler as cc
import cytest

GENERATE_GOLDENS = False

class TestCompileAPI(cytest.TestCase):
  def test_typeCreation(self):
    test_m = cc.Module('test')
    # list_ty = test_m.Data('List', [('Nil', 0), ('Cons', 2)])
    # bool_ty = test_m.Data('Bool', [('False', 0), ('True', 0)])

    # self.assertIs(test_m.datatypes['List'], list_ty)
    # self.assertIs(test_m.datatypes['Bool'], bool_ty)
    # self.assertEqual(str(list_ty), 'List')
    # self.assertEqual(str(bool_ty), 'Bool')


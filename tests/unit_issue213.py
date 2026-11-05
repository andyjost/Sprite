"""Constructor dispatch during normalization of a functional pattern (#213)."""
import cytest


class TestIssue213(cytest.TestCase):
  def test_normalized_pattern_pair(self):
    result = cytest.run_in_subprocess('''
import curry
module = curry.compile("""
import Control.Search.Unsafe (allValues)
match (xs ++ [x,y]) = x ++ y
goal :: [(String,Bool)]
goal = allValues (id $## (match ["a","b"], True))
""")
values = [curry.show(value) for value in curry.eval(module.goal)]
print(values, flush=True)
assert values == ['[("ab",True)]'], values
''', timeout=30, address_space=1 << 30)
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

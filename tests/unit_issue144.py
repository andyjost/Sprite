'''Issue #144: catch runs the handler and preserves the error value.'''
import cytest # from ./lib; must be first
import curry
import unittest

class TestCatch(cytest.TestCase):
  def test_error_and_ioerror(self):
    P = curry.import_('Prelude')
    M = curry.compile('handle e = return (show e)')
    for action, text in ((P.error('boom'), 'i/o error: boom'),
        (P.ioError(P.userError('u')), 'user error: u'),
        (P.readFile('/nosuch'), 'i/o error: No such file or directory: /nosuch')):
      self.assertEqual(curry.eval(P.catch(action, M.handle)).one(), text)
    for action, text in (('error "boom"', 'i/o error: boom'),
        ('ioError (userError "u")', 'user error: u')):
      goal = curry.parse('catch (%s) (\\e -> return (show e))' % action)
      self.assertEqual(curry.eval(goal).one(), text)

  def test_user_messages_do_not_select_error_classes(self):
    P = curry.import_('Prelude')
    for message in ('', 'division by zero: div 1 0', 'integer overflow: 1 + 2',
        'stack limit of 1 bytes exceeded',
        'i/o error: No such file or directory: /nosuch',
        'non-determinism in monadic actions occurred!'):
      with self.subTest(message=message):
        with self.assertRaises(curry.EvaluationError) as caught:
          next(curry.eval(P.error(message)))
        self.assertIs(type(caught.exception), curry.EvaluationError)
        self.assertEqual(str(caught.exception), message)
        with self.assertRaises(curry.CurryIOError) as caught:
          next(curry.eval(P.ioError(P.userError(message))))
        self.assertIs(type(caught.exception), curry.CurryIOError)

  def test_promotion_does_not_run_handler(self):
    goal = curry.parse('catch (return (show ((9223372036854775807 :: Int) + 1))) '
        '(\\e -> return (show e)) :: IO String')
    self.assertEqual(curry.eval(goal).one(), '9223372036854775808')

  def test_catch_arithmetic_error(self):
    goal = curry.parse('catch (print ((1 :: Int) `div` 0) '
        '>> return "") (\\e -> return (show e)) :: IO String')
    self.assertEqual(curry.eval(goal).one(),
        'i/o error: division by zero: div 1 0')

  def test_handler_can_raise(self):
    goal = curry.parse('catch (error "first") (\\_ -> ioError (userError "second"))')
    with self.assertRaises(curry.CurryIOError) as caught:
      next(curry.eval(goal))
    self.assertEqual(str(caught.exception), 'user error: second')

if __name__ == '__main__':
  unittest.main()

import collections, contextlib
from ..readcurry.show import show

TEMPLATE = \
'''%s

SPRITE RESULTS:
%s

ORACLE RESULTS:
%s
'''

@contextlib.contextmanager
def report_error(tc, a, b, formatobj=str):
  try:
    yield
  except BaseException as exc:
    message = TEMPLATE % (exc, formatobj(a), formatobj(b))
    tc.fail(message)

def format_counts(valueset):
  return '\n'.join(
      '%s (%s times)' % (show(value), count) if count != 1 else show(value)
          for value, count in valueset.items()
    )

def assertSameResultSet(
    tc, sprite_results, oracle_results, check_multiplicity=False
  ):
  from ..readcurry.parse import parse
  from ..readcurry.compare import compare

  # Ensure the results are in a bijection.
  s_count, o_count = (
      collections.Counter(r for r in results.split('\n') if r)
          for results in (sprite_results, oracle_results)
    )

  with report_error(tc, s_count, o_count, format_counts):
    # Each system should generate the same number of unique answers.
    tc.assertEqual(
        len(s_count), len(o_count)
      , 'the number of unique results does not match'
      )

    # Each answer in one matches an answer in the other.
    s_parsed, o_parsed = (
        {text: parse(text) for text in ab} for ab in (s_count, o_count)
      )
    for s_key, s_val in s_parsed.items():
      # Find a matching key in o_parsed, or fail.
      if s_key in o_parsed:
        o_key = s_key
      else:
        for o_key, o_val in o_parsed.items():
          if compare(s_val, o_val, modulo_variable_renaming=True):
            break
        else:
          tc.fail(
              'Sprite result %s not found in the Oracle result set'
                  % show(s_val)
            )

      # Check multiplicity, if requested.
      if check_multiplicity:
        tc.assertEqual(
            s_count[s_key], o_count[o_key]
          , '%s != %s; multiplicity of result %s does not match'
                % (s_count[s_key], o_count[o_key], show(s_val))
          )

def assertSameResultMultiset(tc, sprite_results, oracle_results):
  tc.assertSameResultSet(
      sprite_results, oracle_results, check_multiplicity=True
    )

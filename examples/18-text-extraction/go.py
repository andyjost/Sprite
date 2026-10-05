'''
Text extraction with functional patterns, compiled at run time.

The extraction rules are Curry text in this file.  The driver assembles them
into one module, compiles the module with curry.compile, applies each rule
to each line of a log file, and aggregates the matches with
collections.Counter.  Curry extracts, Python aggregates.

Usage: python go.py [--rule NAME BODY ...] [FILE]

Each --rule adds a function NAME :: String -> String with the equation
"NAME BODY" to the module.  For example:

    --rule path '(_ ++ "path=" ++ p ++ " " ++ _) = p'

The driver applies every rule to every line.  Like field, an extra rule sees
the line with one space appended, so the last field matches too.
'''
import argparse
import collections
import os
import sys
import curry

HERE = os.path.dirname(os.path.abspath(__file__))

# The default rules.  Each one is a Curry function with a functional pattern.
# A functional pattern matches every way to split the input.  A rule yields
# one value per match and no value when nothing matches.  The rules are text
# here, not a .curry file, because the driver compiles them at run time.
RULES = '''
-- The value of key k in a line of "key=value" fields.  The guard rejects the
-- longer matches that run on into the next field.
field :: String -> String -> String
field k (_ ++ k ++ "=" ++ v ++ " " ++ _) | ' ' `notElem` v = v

-- Every tag name in a line of markup.  The guard rejects the matches that
-- span from one tag into the next.
tag :: String -> String
tag (_ ++ "<" ++ t ++ ">" ++ _) | '<' `notElem` t && '>' `notElem` t = t
'''

# The keys that field reads from every line.
KEYS = ['status', 'host']

def matches(rule, *args):
  '''Every value of rule applied to args, as sorted Python strings.  The
  scheduler does not promise an order of the values, so sort them.  The
  converter turns each Curry String into a str, the empty String into ''.'''
  values = curry.eval(rule, *args, converter='topython')
  return sorted(values)

def compile_rules(extra):
  '''Assembles the default rules and the extra ones into one Curry module and
  compiles it.'''
  source = RULES
  for name, body in extra:
    source += '\n%s :: String -> String\n%s %s\n' % (name, name, body)
  return curry.compile(source, modulename='Rules')

def cell(values):
  return ','.join(values) if values else '-'

def totals(counter):
  '''The counts of one column, most frequent first, ties by name.'''
  if not counter:
    return 'none'
  items = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
  return ', '.join('%s (%d)' % item for item in items)

def main(argv):
  parser = argparse.ArgumentParser(
      description='Extracts fields and tags from the lines of a log file.')
  parser.add_argument('--rule', nargs=2, action='append', default=[],
      metavar=('NAME', 'BODY'),
      help='add the Curry rule "NAME BODY" of type String -> String')
  parser.add_argument('logfile', nargs='?',
      default=os.path.join(HERE, 'sample.log'))
  args = parser.parse_args(argv)

  # curry.CompileError derives from BaseException, so catch it by name.
  try:
    Rules = compile_rules(args.rule)
  except curry.CompileError as error:
    print('cannot compile the rules:', error, file=sys.stderr)
    return 1

  with open(args.logfile, encoding='utf-8') as stream:
    lines = [line.rstrip('\n') for line in stream]
  print('%d lines from %s' % (len(lines), os.path.basename(args.logfile)))

  extra = [name for name, _ in args.rule]
  columns = KEYS + ['tags'] + extra
  counters = {column: collections.Counter() for column in columns}
  rows = []
  for line in lines:
    row = {}
    for key in KEYS:
      # One space is appended so that the last field matches too.
      row[key] = matches(Rules.field, key, line + ' ')
    row['tags'] = matches(Rules.tag, line)
    for name in extra:
      row[name] = matches(getattr(Rules, name), line + ' ')
    for column in columns:
      counters[column].update(row[column])
    rows.append((line, row))

  # The per-line table.
  widths = {column: max([len(column)] + [len(cell(row[column])) for _, row in rows])
            for column in columns}
  linewidth = max([len('line')] + [len(line) for line in lines])
  print()
  print('  '.join(['line'.ljust(linewidth)] +
                  [column.ljust(widths[column]) for column in columns]).rstrip())
  for line, row in rows:
    print('  '.join([line.ljust(linewidth)] +
                    [cell(row[column]).ljust(widths[column]) for column in columns]).rstrip())

  # The totals.
  print()
  for column in columns:
    print('%s: %s' % (column, totals(counters[column])))
  return 0

if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))

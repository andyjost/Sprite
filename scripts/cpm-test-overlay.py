#!/usr/bin/env python3
"""Make a private CPM index copy for testing Sprite's PAKCS compatibility.

Never install this script or use its output as a user's package index.
"""
import argparse
from contextlib import closing, nullcontext
import json
import os
import re
from pathlib import Path
import shutil
import sqlite3
import tempfile


def overlay(source, destination):
  source, destination = Path(source).resolve(), Path(destination).resolve()
  if source == destination or source in destination.parents:
    raise ValueError('the overlay must be separate from the original index')
  validate_cache(source)
  shutil.copytree(source, destination, dirs_exist_ok=True,
                  ignore=shutil.ignore_patterns('REPOSITORY_CACHE*'))
  count = patch(destination)
  create_cache(destination, replace=True)
  for path in destination.glob('REPOSITORY_CACHE*'):
    if path.name != 'REPOSITORY_CACHE.db':
      path.unlink()
  return count


# Only CPM 3.3's escaped ReadShowTerm encoding and numeric versions are
# supported. Reject other encodings instead of guessing how to rewrite them.
QUOTE = r'\"'
SCHEMA = [
    ('Key', 'INTEGER', 0, 1), ('Name', 'string', 1, 0),
    ('Version', 'string', 1, 0), ('Dependencies', 'string', 0, 0),
    ('CompilerCompatibility', 'string', 0, 0), ('Synopsis', 'string', 0, 0),
    ('Category', 'string', 0, 0), ('SourceDirs', 'string', 0, 0),
    ('ExportedModules', 'string', 0, 0), ('ExecutableSpec', 'string', 0, 0)]


def unique_object(pairs):
  result = {}
  for key, value in pairs:
    if key in result:
      raise ValueError('duplicate JSON key: ' + key)
    result[key] = value
  return result


def read_package(path):
  return json.loads(path.read_text(), strict=False, object_pairs_hook=unique_object)


def version_term(version):
  if not isinstance(version, str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
    raise ValueError('unsupported repository version')
  return '(' + ','.join(str(int(n)) for n in version.split('.')) + ',Nothing)'


def constraint_term(constraint):
  operators = {'>=': 'VGte', '>': 'VGt', '<=': 'VLte', '<': 'VLt', '=': 'VExact', '^': 'VMajCompatible'}
  alternatives = []
  for alternative in constraint.split('||'):
    terms = []
    for part in alternative.split(','):
      match = re.fullmatch(r'\s*(>=|<=|>|<|=|\^)\s*([0-9]+\.[0-9]+\.[0-9]+)\s*', part)
      if match is None:
        raise ValueError('unsupported compiler constraint')
      op, version = match.groups()
      terms.append('(' + operators[op] + ' ' + version_term(version) + ')')
    alternatives.append('[' + ','.join(terms) + ']')
  return '[' + ','.join(alternatives) + ']'


def compatibility_terms(text):
  if not isinstance(text, str):
    raise ValueError('unsupported repository compatibility encoding')
  pattern = (r'\(CompilerCompatibility ' + re.escape(QUOTE) +
             r'([a-z][a-z0-9-]*)' + re.escape(QUOTE) + r' (\[.*?\])\)')
  matches = list(re.finditer(pattern, text))
  if '[' + ','.join(m.group(0) for m in matches) + ']' != text:
    raise ValueError('unsupported repository compatibility encoding')
  result = {m[1]: m[2] for m in matches}
  if len(result) != len(matches):
    raise ValueError('duplicate repository compiler')
  return result


def cache_rows(connection):
  schema = connection.execute('PRAGMA table_info(IndexEntry)').fetchall()
  if [(r[1], r[2], r[3], r[5]) for r in schema] != SCHEMA:
    raise ValueError('unsupported repository cache schema')
  return connection.execute(
      'SELECT * FROM IndexEntry').fetchall()


def validate_cache(root, connection=None):
  database = root / 'REPOSITORY_CACHE.db'
  if connection is None and not database.exists():
    return
  specifications = {}
  for path in root.rglob('package.json'):
    data = read_package(path)
    identity = (data['name'], version_term(data['version']))
    if identity in specifications:
      raise ValueError('duplicate repository package/version')
    specifications[identity] = package_row(data)
  with (closing(sqlite3.connect(database)) if connection is None else nullcontext(connection)) as connection:
    seen = set()
    for _, name, version, *fields in cache_rows(connection):
      identity = (name, version)
      if identity in seen or identity not in specifications:
        raise ValueError('repository package/version mismatch')
      seen.add(identity)
      expected = specifications[identity]
      if compatibility_terms(fields[1]) != compatibility_terms(expected[3]):
        raise ValueError('repository compatibility mismatch')
      for column, actual, wanted in zip([c[0] for c in SCHEMA][3:], fields, expected[2:]):
        if column != 'CompilerCompatibility' and actual != wanted:
          raise ValueError('repository field mismatch: ' + column)
    if seen != specifications.keys():
      raise ValueError('repository package/version mismatch')


def patch_cache(root):
  """Keep CPM on its indexed path with the overlay's compatibility data."""
  database = root / 'REPOSITORY_CACHE.db'
  if database.exists():
    entry = '(CompilerCompatibility ' + QUOTE + 'sprite' + QUOTE + ' [[(VGte (0,9,0,Nothing))]])'
    with closing(sqlite3.connect(database)) as connection, connection:
      for key, _, _, _, compatibility, *_ in cache_rows(connection):
        compilers = compatibility_terms(compatibility)
        if 'sprite' in compilers and compilers['sprite'] != constraint_term('>= 0.9.0'):
          raise ValueError('unexpected Sprite compatibility in repository cache')
        if 'pakcs' in compilers and 'sprite' not in compilers:
          compatibility = compatibility[:-1] + ',' + entry + ']'
          connection.execute(
              'UPDATE IndexEntry SET CompilerCompatibility = ? WHERE Key = ?',
              (compatibility, key))
      validate_cache(root, connection)
  for path in root.glob('REPOSITORY_CACHE*'):
    if path != database:
      path.unlink()


def sql_string(value):
  """The body of a Curry string, read by CDBI (not a JSON string)."""
  if not isinstance(value, str):
    raise ValueError('unsupported repository string')
  escapes = {'"': r'\"', '\\': r'\\', '\a': r'\a', '\b': r'\b',
             '\f': r'\f', '\n': r'\n', '\r': r'\r', '\t': r'\t', '\v': r'\v'}
  if any((ord(c) < 32 or ord(c) == 127) and c not in escapes for c in value):
    raise ValueError('unsupported repository control character')
  return ''.join(escapes.get(c, c) for c in value)


def string_term(value):
  return sql_string('"' + sql_string(value) + '"')


def list_term(values):
  return '[' + ','.join(values) + ']'


def package_row(data):
  """Encode the fields used by CPM.Repository.CacheDB.newEntry."""
  def constraints(field, constructor):
    return list_term('(' + constructor + ' ' + string_term(name) + ' ' +
                     constraint_term(value) + ')'
                     for name, value in data.get(field, {}).items())

  executables = ([data['executable']] if 'executable' in data else []) + data.get('executables', [])
  executable = 'Nothing'
  if executables:
    first = executables[0]
    options = list_term('(' + string_term(name) + ',' + string_term(value) + ')'
                        for name, value in first.get('options', {}).items())
    executable = ('(Just (PackageExecutable ' + string_term(first['name']) + ' ' +
                  string_term(first.get('main', 'Main')) + ' ' + options + '))')
  return (data['name'], version_term(data['version']),
          constraints('dependencies', 'Dependency'),
          constraints('compilerCompatibility', 'CompilerCompatibility'),
          sql_string(data.get('synopsis', '')),
          *(list_term(map(string_term, data.get(field, [])))
            for field in ('category', 'sourceDirs', 'exportedModules')),
          executable)


def create_cache(root, replace=False):
  """Avoid CPM 3.3's recursive JSON reader for indexes without a database."""
  database = root / 'REPOSITORY_CACHE.db'
  if database.exists() and not replace:
    return
  rows = [package_row(read_package(path))
          for path in sorted(root.rglob('package.json'))]
  descriptor, temporary = tempfile.mkstemp(prefix='.repository-', suffix='.db', dir=root)
  os.close(descriptor)
  temporary = Path(temporary)
  try:
    with closing(sqlite3.connect(temporary)) as connection, connection:
      columns = ', '.join(name + ' ' + kind +
          (' PRIMARY KEY' if primary else '') + (' NOT NULL' if required else '')
          for name, kind, required, primary in SCHEMA)
      connection.execute('CREATE TABLE IndexEntry (' + columns + ')')
      connection.executemany('INSERT INTO IndexEntry VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                             ((key, *row) for key, row in enumerate(rows, 1)))
      validate_cache(root, connection)
    os.replace(temporary, database)
  finally:
    temporary.unlink(missing_ok=True)


def patch(root):
  """Apply the overlay to metadata in a private index or downloaded copies."""
  count = 0
  for path in Path(root).rglob('package.json'):
    data = read_package(path)
    compilers = data.get('compilerCompatibility', {})
    if 'pakcs' in compilers and compilers.get('sprite') != '>= 0.9.0':
      compilers['sprite'] = '>= 0.9.0'
      path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + '\n')
      count += 1
  return count


def patch_downloads(roots):
  home = Path(os.environ['HOME']).resolve()
  count = 0
  for root in roots:
    if home not in Path(root).resolve().parents:
      raise ValueError('downloaded copies must be inside the scratch HOME')
    count += patch(root)
  return count


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('source', type=Path)
  parser.add_argument('destination', type=Path)
  parser.add_argument('--packages', nargs='*', type=Path, default=[],
                      help='downloaded package copies inside the scratch HOME')
  args = parser.parse_args()
  print('Updated %d package specifications' % overlay(args.source, args.destination))
  patch_downloads(args.packages)

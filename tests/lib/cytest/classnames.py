'''Spell operation-name expectations using the configured Prelude interface.'''
from curry import config
from curry.typecheck.sigtable import Interface
import curry, functools, os, re

@functools.lru_cache(None)
def _operations():
  iface = Interface.load(os.path.join(
      config.system_curry_path(), '.curry', config.intermediate_subdir()
    , 'Prelude.fint'))
  return tuple(iface.function_names())

def operation_names(text):
  '''Replace old unary names in expected text with their actual declarations.

  Names are resolved from their interfaces, including the encoded type
  arguments. A nullary head can also be spelled before its module is loaded.
  Prefix-only assertions (e.g. _inst#Prelude.Show#[]) keep their purpose.
  '''
  if config.frontend_version() < '3.0.0':
    return text
  pattern = r'_(?:inst#[^#\s]+|impl#[^#\s]+#[^#\s]+)#(?:\[\]|\(\)|\(,+\)|\(->\)|[A-Za-z0-9_.]+)'
  def replace(match):
    old = match.group()
    operations = list(_operations())
    # A user instance can belong to the class's or the type's module.
    modules = {part.rpartition('.')[0] for part in old.split('#')[1:]}
    interp = curry._interpreter_
    for module in modules - {'Prelude', ''}:
      if module in interp.modules:
        iface = interp.sigtable.interface(module)
        if iface is not None:
          operations.extend(iface.function_names())
    matches = {name for name in operations if name.startswith(old + '#')
        and name.endswith('#') and '._#' not in name}
    if len(matches) == 1:
      return matches.pop()
    if not matches:
      return old + '#'
    raise ValueError('ambiguous operation expectation: %s' % old)
  return re.sub(pattern, replace, text)

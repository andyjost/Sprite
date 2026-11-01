'''
Code for merging ICurry modules.
'''
import logging

_reported_externals = set()
from ..exceptions import CompileError

__all__ = [
    'copyExportedNames', 'mergebuiltins', 'mergemodule', 'mergesymbols'
  , 'validatemodule'
  ]


def mergebuiltins(tgt, backend, **kwds):
  '''
  Merge an IModule with its built-in content.

  Looks up built-in content from the backend, and, if any is found, invokes
  ``mergemodule``.

  Args:
    tgt:
        The module to merge content into.
    backend:
        An instance of ``IBackend`` used to locate built-in content.
    **kwds:
        Additional keywords passed to ``mergemodule``.
  '''
  mergekey = '%s.is_merged' % backend.backend_name
  if not tgt.metadata.get(mergekey, False):
    modspec = backend.lookup_builtin_module(tgt.fullname)
    if modspec is not None:
      mergemodule(tgt, modspec.extern(), modspec.exports(), modspec.aliases())
    tgt.update_metadata({mergekey: True})

def mergemodule(tgt, src=None, exports=None, aliases=None, **kwds):
  '''
  Merge content from IModule ``src`` into Imodule ``tgt`` with the specified content.

  Args:
    tgt:
        The module to merge content into.
    src:
        An instance if IModule to copy content from.
    exports:
        A list of symbol names indicating what to copy.
    exports:
        A list of aliases to add to add (via 'union') to ``tgt``.
    **kwds:
        Additional keywords to be passed to ``mergesymbols``.
  '''
  mergesymbols(tgt, src, **kwds)
  if exports is not None and src is not None:
    copyExportedNames(tgt, src, exports)
  if aliases is not None:
    tgt.aliases.update(aliases)

def copyExportedNames(tgt, src, exports):
  '''
  Copies exported functions and types, as specified in ``exports``, from
  ``src`` into this module.

  Args:
    tgt:
        The module to merge content into.
    src:
        An instance if IModule to copy content from.
    exports:
        A list of symbol names indicating what to copy.
  '''
  for name in exports:
    found = 0
    for to,from_ in zip(*[[m.types, m.functions] for m in [tgt, src]]):
      try:
        to[name] = from_[name]
      except KeyError:
        pass
      else:
        found += 1
    if not found:
      raise CompileError('cannot import %r from module %r' % (name, src.fullname))

def _isExternalType(itype):
  # The frontend translates an undefined type into a type with one constructor.
  # That constructor's name is something like '_Constr#A' (for type 'A').  This
  # function detects that oddball case.
  return not itype.constructors or \
      (len(itype.constructors) == 1 and
           itype.constructors[0].name.startswith('_Constr#')
         )

def mergesymbols(tgt, src, merge_metadata=True, resolve_externals=True):
  '''
  Merges metadata and external symbols from ``src`` to ``tgt``.

  Args:
    tgt:
        The module to merge content into.
    src:
        An instance if IModule to copy content from.
    merge_metadata:
        If specified, metadata for every symbol in ``src`` will be merged
        with the corresponding symbol (if any) in ``tgt``.
    resolve_externals:
        If specified, every external datatype and function in ``tgt`` is
        replaced with the corresponding object from ``src``.  If a source
        symbol is not found, the external remains unresolved.  An external datatype
        has no constructors or is explicitly marked 'external' in the source.
        An external function is marked 'external' in the source.
  '''
  from ..icurry import metadata
  if merge_metadata and src is not None:
    for itype in tgt.types.values():
      metadata.merge(itype, src)
  if resolve_externals:
    for itype in tgt.types.values():
      if _isExternalType(itype):
        if src is None or itype.name not in src.types:
          itype.constructors = []
        else:
          itype.constructors = src.types[itype.name].constructors
  for ifun in tgt.functions.values():
    if ifun.is_external and resolve_externals:
      if src is None or ifun.name not in src.functions:
        continue
      ifun.body = src.functions[ifun.name].body
    if merge_metadata:
      metadata.merge(ifun, src)

def validatemodule(imodule):
  mergemodule(imodule) # Implemented as merge with nothing.
  count = sum(f.is_external for f in imodule.functions.values())
  if count and imodule.fullname not in _reported_externals:
    logging.getLogger(__name__).info(
        'module %s: %d externals without a primitive raise when called',
        imodule.fullname, count)
    _reported_externals.add(imodule.fullname)


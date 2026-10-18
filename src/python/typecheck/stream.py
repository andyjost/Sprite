'''Recover the type carried by the printer of a stream element.'''

from . import terms, unify
from .builder import _follow, _partial_parts, symbol_map

def output_type(interp, printer):
  # The ordinary value walk skips dictionary arguments. Here those
  # arguments carry the type of an empty list or a polymorphic field.
  symbols = symbol_map(interp)
  arity = terms.type_arity(interp)

  def parts(node):
    node = _follow(node)
    return _partial_parts(node) if node.info.is_partial else (node.info, node.successors)

  def specialize(node, dictionary=False):
    head, stored = parts(node)
    if head.name == 'apply':
      if dictionary:
        # An instance dictionary applied to the unit token.
        return specialize(stored[0], True)
      function = terms.whnf(specialize(stored[0]), arity)
      return function.range
    scheme = symbols[id(head)].scheme
    mapping = {}
    kinds = dict(scheme.typevars)
    result = terms.instantiate(scheme.typeexpr, mapping, kinds)
    for predicate, arg in zip(scheme.context, stored):
      expected = terms.instantiate(predicate.typeexpr, mapping, kinds)
      unify.unify(expected, specialize(arg, True), arity)
    if dictionary:
      # Instance schemes end in () -> _Dict#Class t.
      return result.range.args[0]
    for _ in stored[scheme.ndicts:]:
      result = terms.whnf(result, arity).range
    return result

  printer_type = terms.whnf(specialize(printer), arity)
  return terms.zonk(printer_type.domain, arity=arity)

'''
Class predicates, context reduction and dictionary resolution.

A :class:`Pred` is a constraint ``C t`` on a term.  Reduction follows the
instance declarations: ``Show [a]`` is satisfied by the instance
``_inst#Prelude.Show#[]`` under the context ``Show a``, so the predicate is
replaced by ``Show a`` and remembers the instance.  A predicate on a type
variable stays until defaulting binds the variable.  Resolution turns a
reduced predicate into a :class:`DictTerm`: the instance function applied
to the dictionaries of its context, which the runtime passes as a partial
application with one missing argument.

The superclass relation comes from the selectors ``_super#C#S`` of the
loaded interfaces.  It simplifies a context the way the front end does:
``(Num a, Fractional a)`` is ``Fractional a``.
'''

from ..toolchain.flat2icurry import flatcurry as fc
from . import terms, unify
from .sigtable import PRELUDE, _is_tuple_name
from .terms import APPLY, Rigid, Var

__all__ = [
    'DATA_CLASS', 'DictTerm', 'InstanceEnv', 'NUM_CLASS', 'NoInstance', 'Pred'
  , 'SUPER_PREFIX'
  ]

DATA_CLASS = 'Prelude.Data'
NUM_CLASS = 'Prelude.Num'
SUPER_PREFIX = '_super#'
SPECIAL_TYPES = ('[]', '()', '(->)')

class Pred:
  '''
  A class constraint on a term.

  Attributes:
    classname:
        The qualified class name.
    term:
        The constrained term.
    spec:
        The spec that introduced the constraint: an application whose scheme
        has it in its context, a literal, or a free variable.
    parent:
        The predicate this one is a context predicate of, after reduction,
        or None for a predicate of a spec.
    instance:
        The instance that satisfies the predicate, once reduced, or None.
    subpreds:
        The context predicates of that instance.
    index:
        The position in the context of the scheme, for a predicate of an
        application.
  '''
  __slots__ = (
      'classname', 'term', 'spec', 'parent', 'instance', 'subpreds', 'index'
    )

  def __init__(self, classname, term, spec=None, parent=None, index=None):
    self.classname = classname
    self.term = term
    self.spec = spec
    self.parent = parent
    self.instance = None
    self.subpreds = ()
    self.index = index

  @property
  def shortname(self):
    return self.classname.rpartition('.')[2]

  def root(self):
    '''The predicate of a spec this one descends from.'''
    pred = self
    while pred.parent is not None:
      pred = pred.parent
    return pred

  def __repr__(self):
    return '<Pred %s %r>' % (self.classname, self.term)

class DictTerm:
  '''
  A dictionary: an instance function applied to the dictionaries of its
  context.  The runtime takes it as the partial application of
  ``_inst#Class#Type`` with one missing argument.
  '''
  __slots__ = ('instance', 'args')

  def __init__(self, instance, args=()):
    self.instance = instance
    self.args = tuple(args)

  @property
  def fullname(self):
    return self.instance.fullname

  def __eq__(self, rhs):
    return isinstance(rhs, DictTerm) and self.fullname == rhs.fullname \
        and self.args == rhs.args

  def __ne__(self, rhs):
    return not (self == rhs)

  def __hash__(self):
    return hash((self.fullname, self.args))

  def __str__(self):
    name = self.instance.name
    if not self.args:
      return name
    return '%s %s' % (name, ' '.join(
        str(arg) if not arg.args else '(%s)' % arg for arg in self.args
      ))

  def __repr__(self):
    return '<DictTerm %s>' % self

class NoInstance(Exception):
  '''No loaded module declares an instance for ``pred`` at ``term``.'''
  def __init__(self, pred, term):
    Exception.__init__(self, pred, term)
    self.pred = pred
    self.term = term

class InstanceEnv:
  '''The instances and classes of the loaded modules of one interpreter.'''

  def __init__(self, interp):
    self.interp = interp
    self.table = interp.sigtable
    self.arity = terms.type_arity(interp)
    self._super = None
    self._modules = None

  # Names
  # -----
  @staticmethod
  def typename(term):
    '''
    The key of the instance map for the head of a term: ``[]``, ``()``,
    ``(->)``, a tuple name, or ``M.T``; None for a term whose head is no
    constructor.
    '''
    if isinstance(term, fc.FuncType):
      return '(->)'
    if isinstance(term, fc.TCons) and term.name != APPLY:
      modulename, name = term.name
      if modulename == PRELUDE and (name in SPECIAL_TYPES or _is_tuple_name(name)):
        return name
      return '%s.%s' % term.name
    return None

  def instance(self, classname, typename):
    return self.table.instance(classname, typename)

  def has_instance(self, classname, typename):
    return self.table.instance(classname, typename) is not None

  # Superclasses
  # ------------
  def superclasses(self):
    '''
    A dict from a class to the set of all its superclasses, from the
    ``_super#C#S`` selectors of the loaded interfaces.  The map is built
    again when a module was loaded since the last call.
    '''
    modules = tuple(self.interp.modules)
    if self._super is None or self._modules != modules:
      direct = {}
      for modulename in modules:
        iface = self.table.interface(modulename)
        if iface is None:
          continue
        for name in iface.function_names():
          if name.startswith(SUPER_PREFIX) and '._#' not in name:
            parts = name.split('#')
            if len(parts) == 3:
              direct.setdefault(parts[1], set()).add(parts[2])
      closure = {}
      def close(cls):
        if cls not in closure:
          closure[cls] = set()
          for sup in direct.get(cls, ()):
            closure[cls].add(sup)
            closure[cls] |= close(sup)
        return closure[cls]
      for cls in list(direct):
        close(cls)
      self._super = closure
      self._modules = modules
    return self._super

  def entails(self, classname, other):
    '''Whether an instance of ``classname`` has an instance of ``other``.'''
    return classname == other or other in self.superclasses().get(classname, ())

  def is_numeric(self, classname):
    '''Whether ``Num`` is the class or one of its superclasses.'''
    return self.entails(classname, NUM_CLASS)

  def simplify(self, preds):
    '''
    The predicates without duplicates and without those a stronger predicate
    on the same type entails: ``(Num a, Fractional a)`` is ``Fractional a``.
    '''
    naming = terms.Naming()
    zonked = [terms.zonk(p.term, naming, self.arity) for p in preds]
    kept = []
    for i, pred in enumerate(preds):
      redundant = False
      for j, other in enumerate(preds):
        if i == j or zonked[i] != zonked[j]:
          continue
        if other.classname == pred.classname:
          # A duplicate: the first one stays.
          if j < i:
            redundant = True
            break
        elif self.entails(other.classname, pred.classname):
          redundant = True
          break
      if not redundant:
        kept.append(pred)
    return kept

  # Reduction
  # ---------
  def reduce(self, pred):
    '''
    Reduces a predicate through the instances.  Returns the residual
    predicates: those on a type variable, or on a variable applied to
    arguments, which wait for defaulting.  A reduced predicate records its
    instance and the context predicates it depends on.

    Raises:
      NoInstance:
          The head of a predicate is a constructor without an instance, or
          a rigid variable.
    '''
    residual = []
    work = [pred]
    while work:
      p = work.pop()
      t = terms.whnf(p.term, self.arity)
      if isinstance(t, Var):
        residual.append(p)
        continue
      if isinstance(t, fc.TCons) and t.name == APPLY:
        # A variable applied to arguments waits for the variable.  Any
        # other head of an Apply is a kind error: no instance fits.
        if isinstance(terms.whnf(t.args[0], self.arity), Var):
          residual.append(p)
          continue
        raise NoInstance(p, t)
      if isinstance(t, Rigid) or isinstance(t, fc.ForallType):
        raise NoInstance(p, t)
      typename = self.typename(t)
      inst = None if typename is None else self.instance(p.classname, typename)
      if inst is None:
        raise NoInstance(p, t)
      mapping = {}
      kinds = dict(inst.scheme.typevars)
      head = terms.instantiate(inst.head, mapping, kinds)
      try:
        unify.unify(head, t, self.arity)
      except unify.UnifyError:
        raise NoInstance(p, t)
      subpreds = [
          Pred(c.classname, terms.instantiate(c.typeexpr, mapping, kinds), p.spec, p)
              for c in inst.context
        ]
      p.instance = inst
      p.subpreds = tuple(subpreds)
      work.extend(reversed(subpreds))
    return residual

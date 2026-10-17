'''
The errors of the engine: the catalogue of section 7 of the design of the
typed boundary.

Every error is a :class:`CurryTypeError <curry.exceptions.CurryTypeError>`.
The first line of a message names the class of the error; the lines after it
name the symbol with its scheme, the argument path, and the types.  An error
carries the same facts as attributes, so a caller can build another message
from them.  The error of a goal the defaulting table cannot handle is
:class:`DefaultingError <curry.typecheck.defaulting.DefaultingError>`; the
engine raises it with the words of the oracle.
'''

from .. import exceptions
from .defaulting import ORACLE_SENTENCE

__all__ = [
    'AmbiguousTypeError', 'ArityError', 'ContextInExprTypeError'
  , 'ConversionError', 'DEFAULTS_HINT', 'ExprTypeError'
  , 'ExprTypeMismatchError', 'ExprTypeSyntaxError', 'FreeFunctionError'
  , 'KindError', 'MismatchError', 'NoInstanceError', 'TypeCheckError'
  , 'UnknownTypeConstructorError', 'ValueTooLargeError'
  ]

# The last line of an ambiguity error.
DEFAULTS_HINT = (
    'defaults exist for Num and Integral (Int), Fractional and Floating '
    "(Float), Monad (IO) and Data (Bool); pass exprtype, for example "
    "exprtype='Int'"
  )

TypeCheckError = exceptions.CurryTypeError

class MismatchError(TypeCheckError):
  '''
  Two arguments disagree, or an argument does not fit its parameter:
  ``type mismatch in argument N of S :: scheme``.
  '''

class ConversionError(TypeCheckError):
  '''
  A Python value under a type it cannot take: ``cannot convert 2.5 to Int at
  argument N of S``.  ``None`` is such a value under every type.
  '''

class AmbiguousTypeError(TypeCheckError):
  '''
  A class constraint that nothing fixes and the table cannot default:
  ``ambiguous type in S :: scheme``, with the sentence of the oracle.
  '''
  def __init__(self, what, scheme, detail=None, **kwds):
    lines = ['ambiguous type in %s :: %s' % (what, scheme)]
    if detail:
      lines.append('  ' + detail)
    lines.append('  ' + ORACLE_SENTENCE)
    lines.append('  ' + DEFAULTS_HINT)
    TypeCheckError.__init__(self, lines, **kwds)
    self.scheme = scheme

class NoInstanceError(TypeCheckError):
  '''``no instance for Show (a -> a) in argument 1 of Prelude.show``.'''
  def __init__(self, classname, typetext, where, **kwds):
    TypeCheckError.__init__(
        self, 'no instance for %s %s in %s' % (classname, typetext, where.split(' :: ', 1)[0])
      , where=where, **kwds
      )
    self.classname = classname

class FreeFunctionError(TypeCheckError):
  '''
  A free variable at a function type: ``free variable at argument N of S
  would have the function type T``.
  '''
  def __init__(self, where, typetext, **kwds):
    TypeCheckError.__init__(
        self
      , [ 'free variable at %s would have the function type %s'
              % (where, typetext)
        , '  Curry free variables must have a Data type'
        ]
      , where=where, **kwds
      )

class ArityError(TypeCheckError):
  '''``S :: scheme takes N arguments, M given``.'''
  def __init__(self, scheme, ntaken, ngiven, **kwds):
    TypeCheckError.__init__(
        self
      , '%s :: %s takes %d argument%s, %d given'
            % (scheme.fullname, scheme, ntaken, '' if ntaken == 1 else 's', ngiven)
      , symbol=scheme.fullname, **kwds
      )
    self.scheme = scheme
    self.ntaken = ntaken
    self.ngiven = ngiven

class ValueTooLargeError(TypeCheckError):
  '''
  The walk that types a Curry value stopped at its cap: ``the value at
  argument N of S has more than 100000 nodes; pass curry.term(node, type='T')``.
  With ``what='type of the value'`` the type of the value grew past the
  cap: a value that shares a node between the components of a pair at every
  level has a type exponential in its size.
  '''
  def __init__(self, where, cap, what='value', **kwds):
    TypeCheckError.__init__(
        self
      , "the %s at %s has more than %d nodes; pass curry.term(node, type='T')"
            % (what, where, cap)
      , where=where, **kwds
      )
    self.cap = cap
    self.what = what

# The errors of exprtype strings
# ==============================
class ExprTypeError(exceptions.TypeSyntaxError):
  '''A problem with an ``exprtype`` string or a ``expressions.typed`` annotation.'''
  def __init__(self, lines, text=None, **kwds):
    TypeCheckError.__init__(self, lines, **kwds)
    self.text = text

class ExprTypeSyntaxError(ExprTypeError):
  '''``cannot parse exprtype 'text': ... at column N``.'''
  def __init__(self, text, reason, column, **kwds):
    ExprTypeError.__init__(
        self
      , 'cannot parse exprtype %r: %s at column %d' % (text, reason, column)
      , text=text, **kwds
      )
    self.column = column

class ContextInExprTypeError(ExprTypeError):
  '''``exprtype takes a type without a context; the context is inferred``.'''
  def __init__(self, text, **kwds):
    ExprTypeError.__init__(
        self
      , 'exprtype takes a type without a context; the context is inferred'
        ' (exprtype %r)' % text
      , text=text, **kwds
      )

class UnknownTypeConstructorError(ExprTypeError):
  '''
  ``unknown type constructor T; searched the interfaces of M1, M2;
  curry.parse('expression :: T') checks the type with the front end``.
  '''
  def __init__(self, name, searched, text=None, detail=None, **kwds):
    searched = list(searched)
    where = ', '.join(searched) if searched else 'no loaded module'
    lines = [
        'unknown type constructor %s; searched the interfaces of %s; '
        "curry.parse('expression :: T') checks the type with the front end"
            % (name, where)
      ]
    if detail:
      lines.append('  ' + detail)
    ExprTypeError.__init__(self, lines, text=text, **kwds)
    self.name = name
    self.searched = searched

class KindError(ExprTypeError):
  '''A type constructor applied to the wrong number of arguments.'''
  def __init__(self, name, arity, ngiven, text, **kwds):
    ExprTypeError.__init__(
        self
      , '%s takes %d type argument%s, %d given in exprtype %r'
            % (name, arity, '' if arity == 1 else 's', ngiven, text)
      , text=text, **kwds
      )
    self.name = name
    self.arity = arity
    self.ngiven = ngiven

class ExprTypeMismatchError(MismatchError):
  '''``exprtype T does not match the inferred type U``.'''
  def __init__(self, text, inferred, detail=None, **kwds):
    lines = ['exprtype %s does not match the inferred type %s' % (text, inferred)]
    if detail:
      lines.append('  ' + detail)
    MismatchError.__init__(self, lines, **kwds)
    self.text = text
    self.inferred = inferred

'''
The ICurry data types, as in ``ICurry.Types`` of the Curry package
``icurry``.  A name is a triple ``(module, name, index)``.
'''

from .terms import Term, constructor

__all__ = [
    'IProg', 'IDataType', 'IFunction', 'Public', 'Private'
  , 'IExternal', 'IFuncBody', 'IBlock', 'IVarDecl', 'IFreeDecl'
  , 'IVarAssign', 'INodeAssign', 'IExempt', 'IReturn', 'ICaseCons', 'ICaseLit'
  , 'IConsBranch', 'ILitBranch', 'IVar', 'IVarAccess', 'ILit', 'IFCall'
  , 'ICCall', 'IFPCall', 'ICPCall', 'IOr', 'IInt', 'IChar', 'IFloat'
  , 'IExpr', 'IStatement', 'IAssign', 'IDecl', 'ILiteral', 'IVisibility'
  ]

class IVisibility(Term): __slots__ = ()
class IFuncBodyDecl(Term): __slots__ = ()
class IDecl(Term)      : __slots__ = ()
class IAssign(Term)    : __slots__ = ()
class IStatement(Term) : __slots__ = ()
class IExpr(Term)      : __slots__ = ()
class ILiteral(Term)   : __slots__ = ()

IProg       = constructor('IProg', 'name imports types functions')
IDataType   = constructor('IDataType', 'name constructors')
IFunction   = constructor('IFunction', 'name arity visibility demanded body')
Public      = constructor('Public', base=IVisibility)()
Private     = constructor('Private', base=IVisibility)()
IExternal   = constructor('IExternal', 'name', IFuncBodyDecl)
IFuncBody   = constructor('IFuncBody', 'block', IFuncBodyDecl)
IBlock      = constructor('IBlock', 'decls assigns statement')
IVarDecl    = constructor('IVarDecl', 'var', IDecl)
IFreeDecl   = constructor('IFreeDecl', 'var', IDecl)
IVarAssign  = constructor('IVarAssign', 'var expr', IAssign)
INodeAssign = constructor('INodeAssign', 'var path expr', IAssign)
IExempt     = constructor('IExempt', base=IStatement)()
IReturn     = constructor('IReturn', 'expr', IStatement)
ICaseCons   = constructor('ICaseCons', 'var branches', IStatement)
ICaseLit    = constructor('ICaseLit', 'var branches', IStatement)
IConsBranch = constructor('IConsBranch', 'name arity block')
ILitBranch  = constructor('ILitBranch', 'literal block')
IVar        = constructor('IVar', 'var', IExpr)
IVarAccess  = constructor('IVarAccess', 'var path', IExpr)
ILit        = constructor('ILit', 'literal', IExpr)
IFCall      = constructor('IFCall', 'name args', IExpr)
ICCall      = constructor('ICCall', 'name args', IExpr)
IFPCall     = constructor('IFPCall', 'name missing args', IExpr)
ICPCall     = constructor('ICPCall', 'name missing args', IExpr)
IOr         = constructor('IOr', 'lhs rhs', IExpr)
IInt        = constructor('IInt', 'value', ILiteral)
IChar       = constructor('IChar', 'value', ILiteral)
IFloat      = constructor('IFloat', 'value', ILiteral)

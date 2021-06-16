'''
Defines in pure ICurry a few simple modules designed for system testing.
'''
from curry.icurry import *
from curry.icurry.json import parse
from curry.utility import unboxed

# An arbitrary choice id.
_cid = 527
cid = unboxed.unboxed(_cid)

def blk(expr):
  return IBlock(vardecls=[], assigns=[], stmt=expr)

def retbody(expr):
  return IFuncBody(blk(IReturn(expr)))

def getbootstrap():
  return IModule(
      name='bootstrap'
    , imports=[]
    , types=[
          IType(
              name='bootstrap.NUM'
            , constructors=[
                  IConstructor('bootstrap.N', 0) # Nullary
                , IConstructor('bootstrap.M', 0) # A distinct nullary, to test choices.
                , IConstructor('bootstrap.U', 1) # Unary
                , IConstructor('bootstrap.B', 2) # Binary
                ]
            )
        ]
    , functions=[
        IFunction('bootstrap.ZN', 0, body=retbody(ICCall('bootstrap.N')))
      , IFunction('bootstrap.ZF', 0, body=retbody(ICCall('Prelude._Failure')))
      , IFunction('bootstrap.ZQ', 0, body=retbody(
            ICCall('Prelude._Choice', [_cid, ICCall('bootstrap.N'), ICCall('bootstrap.M')])
          ))
      #                                                       ^^^
      #  Not correctly typed, but three arguments are needed here.
      , IFunction('bootstrap.ZW', 0, body=retbody(ICCall('Prelude._Fwd', [ICCall('bootstrap.N')])))
        # Evaluates its argument and then returns a FWD node refering to it.
      , IFunction('bootstrap.Z' , 1, body=IFuncBody(IBlock(
            vardecls=[IVarDecl(1)]
          , assigns=[IVarAssign(1, IVarAccess(0, path=[0]))]
          , stmt=ICaseCons(
                1
              , branches=[
                    IConsBranch("bootstrap.N", 0, blk(IReturn(IVar(1))))
                  , IConsBranch("bootstrap.M", 0, blk(IReturn(IVar(1))))
                  , IConsBranch("bootstrap.U", 1, blk(IReturn(IFCall("Prelude.failed"))))
                  , IConsBranch("bootstrap.B", 2, blk(IReturn(IFCall("Prelude.failed"))))
                  ]
              )
          )))
      ]
    )

def getlist():
  return IModule(
      name='mylist', imports=[], functions=[]
    , types=[
          IType(
              name='mylist.List'
            , constructors=[
                IConstructor('mylist.Cons', 2)
              , IConstructor('mylist.Nil', 0) 
              ]
            )
        ]
    )

def getx():
  return IModule(
      name='X', imports=[], functions=[]
    , types=[
          IType(
              name='X.X'
            , constructors=[IConstructor('X.X', 1)]
            )
        ]
    )

def getexample():
  return parse(open('data/json/example.json', 'rb').read())


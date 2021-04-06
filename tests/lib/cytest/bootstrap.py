'''
Defines in pure ICurry a few simple modules designed for system testing.
'''
from curry.icurry import *
from curry.utility import unboxed

# An arbitrary choice id.
_cid = 527
cid = unboxed.unboxed(_cid)

def blk(expr):
  return IBlock(vardecls=[], assigns=[], stmt=IReturn(expr))

def ret(expr):
  return IFuncBody(blk(IReturn(expr)))

def getbootstrap():
  return IModule(
      name='bootstrap'
    , imports=[]
    , types=[
          IType(
              name='NUM'
            , constructors=[
                  IConstructor('N', 0) # Nullary
                , IConstructor('M', 0) # A distinct nullary, to test choices.
                , IConstructor('U', 1) # Unary
                , IConstructor('B', 2) # Binary
                ]
            )
        ]
    , functions=[
        IFunction('ZN', 0, body=ret(ICCall('bootstrap.N')))
      , IFunction('ZF', 0, body=ret(ICCall('Prelude._Failure')))
      , IFunction('ZQ', 0, body=ret(
            ICCall('Prelude._Choice', [_cid, ICCall('bootstrap.N'), ICCall('bootstrap.M')])
          ))
      #                                                       ^^^
      #  Not correctly typed, but three arguments are needed here.
      , IFunction('ZW', 0, body=ret(ICCall('Prelude._Fwd', [ICCall('bootstrap.N')])))
        # Evaluates its argument and then returns a FWD node refering to it.
      , IFunction('Z' , 1, body=IFuncBody(IBlock(
            vardecls=[IVarDecl(1)]
          , assigns=[IVarAssign(1, IVarAccess(0, path=[0]))]
          , stmt=ICaseCons(
                1
              , branches=[
                    IConsBranch("bootstrap.N", 0, blk(IReturn(IVar(1))))
                  , IConsBranch("bootstrap.M", 0, blk(IReturn(IVar(1))))
                  , IConsBranch("bootstrap.U", 1, blk(IReturn(IFCall("Prelude.failure"))))
                  , IConsBranch("bootstrap.B", 2, blk(IReturn(IFCall("Prelude.failure"))))
                  ]
              )
          )))
      ]
    )

def listformat(node):
  def gen():
    p = node
    while p.info.name == 'Cons':
      value = p.successors[0]
      yield value.info.show(value)
      p = p.successors[1]
  return '[' + ', '.join(gen()) + ']'

def getlist():
  return IModule(
      name='mylist', imports=[], functions=[]
    , types=[
          IType(
              name='List'
            , constructors=[
                IConstructor('Cons', 2, metadata={'py.format':listformat})
              , IConstructor('Nil', 0, metadata={'py.format':listformat})
              ]
            )
        ]
    )

def getx():
  return IModule(
      name='X', imports=[], functions=[]
    , types=[
          IType(
              name='X'
            , constructors=[IConstructor('X', 1)]
            )
        ]
    )

def getexample():
  return parse(open('data/json/example.json', 'rb').read())


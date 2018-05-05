'''
Defines in pure ICurry a few simple modules designed for system testing.
'''
from curry.icurry import *
import gzip

def getbootstrap():
  return IModule(
      name='bootstrap'
    , imports=['_System']
    , types=[
          IType(
              ident='NUM'
            , constructors=[
                  IConstructor('N', 0) # Nullary
                , IConstructor('M', 0) # A distinct nullary, to test choices.
                , IConstructor('U', 1) # Unary
                , IConstructor('B', 2) # Binary
                ]
            )
        ]
    , functions=[
        IFunction('ZN', 0, [Return(Applic('bootstrap.N'))])
      , IFunction('ZF', 0, [Return(Applic('_System.Failure'))])
      , IFunction('ZQ', 0, [Return(Applic('_System.Choice', [Applic('bootstrap.N'), Applic('bootstrap.M')]))])
      , IFunction('ZW', 0, [Return(Applic('_System.Fwd', [Applic('bootstrap.N')]))])
        # Evaluates its argument and then returns a FWD node refering to it.
      , IFunction('Z' , 1, [
            Declare(Variable(vid=1, scope=ILhs(index=["bootstrap.Z", 1])))
          , ATable(0, True, Reference(1)
              , [
                    ("bootstrap.N", [Return(Reference(1))])
                  , ("bootstrap.M", [Return(Reference(1))])
                    # U,B -> failure
                  ]
              )
          ])
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
              ident='List'
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
              ident='X'
            , constructors=[IConstructor('X', 1)]
            )
        ]
    )

def getexample():
  return parse(gzip.open('data/json/example.json.gz', 'rb').read())


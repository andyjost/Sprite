#!/home/andy/sprite4/install/bin/python
# ------------------------------------
# Python code for Curry module 'Peano'
# ------------------------------------

import curry
from curry.icurry import \
    IModule, IDataType, IConstructor, PUBLIC, PRIVATE

def cy_Nat(rts, _0):                    # Peano._inst#Prelude.Data#Peano.Nat
  _1 = None
  _1 = _0[0]
  _1.hnf(typedef=ty_Unit)
  selector = _1.tag
  _0.rewrite(ni_Data, rts.Node(ni__PartApplic, 2, rts.Node(ni_Nat, partial=True)), rts.Node(ni_Nat_0))

def cy_Nat_0(rts, _0):                  # Peano._impl#===#Prelude.Data#Peano.Nat
  _1 = None
  _2 = None
  _1 = _0[0]
  _2 = _0[1]
  _1.hnf(typedef=ty_Peano_Nat)
  selector = _1.tag
  if selector == 0:                     # Peano.O
    _0.rewrite(ni_Nat_CASE0, _2)
  else:                                 # Peano.S
    _4 = None
    _4 = _1[0]
    _0.rewrite(ni_Nat_CASE1, _2, _4)

def cy_Nat_CASE1(rts, _0):              # Peano._impl#===#Prelude.Data#Peano.Nat_CASE1
  _2 = None
  _4 = None
  _2 = _0[0]
  _4 = _0[1]
  _2.hnf(typedef=ty_Peano_Nat)
  selector = _2.tag
  if selector == 0:                     # Peano.O
    _0.rewrite(ni_False)
  else:                                 # Peano.S
    _5 = None
    _5 = _2[0]
    _0.rewrite(ni_Nat, _4, _5)

def cy_Nat_CASE0(rts, _0):              # Peano._impl#===#Prelude.Data#Peano.Nat_CASE0
  _2 = None
  _2 = _0[0]
  _2.hnf(typedef=ty_Peano_Nat)
  selector = _2.tag
  if selector == 0:                     # Peano.O
    _0.rewrite(ni_True)
  else:                                 # Peano.S
    _0.rewrite(ni_False)

def cy_Nat_1(rts, _0):                  # Peano._impl#aValue#Prelude.Data#Peano.Nat
  _0.rewrite(ni_Choice, rts.Node(ni_Peano_O), rts.Node(ni_Peano_S, rts.Node(ni_Nat_0)))

def cy_Peano_add(rts, _0):              # Peano.add
  _1 = None
  _2 = None
  _1 = _0[0]
  _2 = _0[1]
  _1.hnf(typedef=ty_Peano_Nat)
  selector = _1.tag
  if selector == 0:                     # Peano.O
    _0.rewrite(ni__Fwd, _2)
  else:                                 # Peano.S
    _3 = None
    _3 = _1[0]
    _0.rewrite(ni_Peano_S, rts.Node(ni_Peano_add, _3, _2))

def cy_Peano_main(rts, _0):             # Peano.main
  _0.rewrite(ni_Peano_add, rts.Node(ni_Peano_S, rts.Node(ni_Peano_O)), rts.Node(ni_Peano_S, rts.Node(ni_Peano_O)))


# Interface
# ---------
_icurry_ = IModule.fromBOM(
    fullname='Peano'
  , filename='/home/andy/sprite4/examples/Peano.curry'
  , imports=('Prelude',)
  , types=[
        IDataType('Peano.Nat', [
            IConstructor(fullname='Peano.O', arity=0)
          , IConstructor(fullname='Peano.S', arity=1)
          ])
      ]
  , functions=[
        ('Peano._inst#Prelude.Data#Peano.Nat', 1, PUBLIC , [0], cy_Nat)
      , ('Peano._impl#===#Prelude.Data#Peano.Nat', 2, PUBLIC , [0], cy_Nat_0)
      , ('Peano._impl#===#Prelude.Data#Peano.Nat_CASE1', 2, PRIVATE, [0], cy_Nat_CASE1)
      , ('Peano._impl#===#Prelude.Data#Peano.Nat_CASE0', 1, PRIVATE, [0], cy_Nat_CASE0)
      , ('Peano._impl#aValue#Prelude.Data#Peano.Nat', 0, PUBLIC , [] , cy_Nat_1)
      , ('Peano.add'                         , 2, PUBLIC , [0], cy_Peano_add)
      , ('Peano.main'                        , 0, PUBLIC , [] , cy_Peano_main)
      ]
  )

_module_ = curry.import_(_icurry_)


# Linking
# -------
ni_Peano_O     = curry.symbol('Peano.O')
ni_Peano_S     = curry.symbol('Peano.S')
ni_Nat         = curry.symbol('Peano._impl#===#Prelude.Data#Peano.Nat')
ni_Nat_CASE0   = curry.symbol('Peano._impl#===#Prelude.Data#Peano.Nat_CASE0')
ni_Nat_CASE1   = curry.symbol('Peano._impl#===#Prelude.Data#Peano.Nat_CASE1')
ni_Nat_0       = curry.symbol('Peano._impl#aValue#Prelude.Data#Peano.Nat')
ni_Peano_add   = curry.symbol('Peano.add')
ni_Choice      = curry.symbol('Prelude.?')
ni_False       = curry.symbol('Prelude.False')
ni_True        = curry.symbol('Prelude.True')
ni_Data        = curry.symbol('Prelude._Dict#Data')
ni__Fwd        = curry.symbol('Prelude._Fwd')
ni__PartApplic = curry.symbol('Prelude._PartApplic')
ty_Peano_Nat   = curry.type('Peano.Nat')
ty_Unit        = curry.type('Prelude.()')


if __name__ == '__main__':
  from curry import __main__
  __main__.moduleMain(__file__, 'Peano', goal='main')


#!/usr//bin/python

# This script generates the files named test<N>.curry.  The reason for doing it
# this way is simply that it is easier to maintain this script than work with
# scores of tiny files.

PROGRAMS = [
  # Constructors.
    'main = 0 =:= 0'
  , 'main = 0 =:= 1'
  , 'main = [0,0] =:= [0,0]'
  , 'main = [0,0] =:= [0,1]'
  # Functions.
  , 'f = True\n'
    'main = f =:= f'
  , 'f = True\n'
    'main = True =:= f'
  , 'f = True\n'
    'main = f =:= True'
  , 'f = True\n'
    'main = False =:= f'
  , 'f = True\n'
    'main = f =:= False'
  # Choices.
  , 'main = 0 =:= (0?1)'
  , 'main = (0?1) =:= 1'
  , 'main = (0?1) =:= (0?1)'
  # Failures.
  , 'main = 0 =:= failed'
  , 'main = failed =:= 1'
  , 'main = failed =:= (0?1)'
  # Free variables.
  # , 'main = x =:= 1 where x free'
  # , 'main = 0 =:= x where x free'
  , 'main = True =:= x where x free'
  , 'main = True == x where x free'
  # , 'f 0 1 = 1\n'
  #   'main = f 0 x where x free'
  # , 'f 0 True = True\n'
  #   'main = f 0 x where x free'
  , 'f True True = True\n'
    'main = f True x where x free'
  , 'main = x=:=y where x,y free'
  , 'main = (True:x)=:=(True:y) where x,y free'
  , 'main = (True:x)=:=(False:y) where x,y free'
  , 'main = (x:xs)=:=(y:ys) where x,y,xs,ys free'
  , 'main = (True:xs)=:=(y:ys) where y,xs,ys free'
  # , 'main = (0:xs)=:=(y:ys) where y,xs,ys free'
  # Forward nodes.
  , 'fwd x = x\n'               # fwd constructor
    'main = fwd True =:= True'
  , 'fwd x = x\n'
    'main = fwd True =:= False'
  , 'fwd x = x\n'
    'main = True =:= fwd True'
  , 'fwd x = x\n'
    'main = False =:= fwd True'
  , 'fwd x = x\n'               # fwd function
    'f = True\n'
    'main = fwd f =:= True'
  , 'fwd x = x\n'
    'f = True\n'
    'main = fwd f =:= False'
  , 'fwd x = x\n'
    'f = True\n'
    'main = True =:= fwd f'
  , 'fwd x = x\n'
    'f = True\n'
    'main = False =:= fwd f'
  , 'fwd x = x\n'               # fwd choice
    'f = True ? False\n'
    'main = fwd f =:= True'
  , 'fwd x = x\n'
    'f = True ? False\n'
    'main = fwd f =:= False'
  , 'fwd x = x\n'
    'f = True ? False\n'
    'main = True =:= fwd f'
  , 'fwd x = x\n'
    'f = True ? False\n'
    'main = False =:= fwd f'
  , 'fwd x = x\n'               # fwd free
    'main = fwd x =:= True where x free'
  , 'fwd x = x\n'
    'main = fwd x =:= False where x free'
  , 'fwd x = x\n'
    'main = True =:= fwd x where x free'
  , 'fwd x = x\n'
    'main = False =:= fwd x where x free'
  ]

for i, program_text in enumerate(PROGRAMS):
  filename = 'test{}.curry'.format(i)
  with open(filename, 'w') as out:
    out.write(program_text)

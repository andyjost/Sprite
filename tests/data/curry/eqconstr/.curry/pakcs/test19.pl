%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test19).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test19.main',main,0,'test19.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test19.main'(_G479006,_G479007,_G479008):-freeze(_G479007,'blocked_test19.main'(_G479006,_G479007,_G479008)).
'blocked_test19.main'(_G479297,_G479300,_G479303):-hnf('Prelude.=:='(['Prelude.True'|_G479042],['Prelude.True'|_G479051]),_G479297,_G479300,_G479303).

:-costCenters(['']).




%%%%% Number of shared variables: 0

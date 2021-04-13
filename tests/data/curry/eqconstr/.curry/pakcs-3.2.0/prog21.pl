%PAKCS3.2 swi8 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog21).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog21.main',main,0,'prog21.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog21.main'(_3588646,_3588648,_3588650):-freeze(_3588648,'blocked_prog21.main'(_3588646,_3588648,_3588650)).
'blocked_prog21.main'(_3589248,_3589254,_3589260):-hnf('Prelude.=:='([_3588718|_3588754],[_3588736|_3588772]),_3589248,_3589254,_3589260).

:-costCenters(['']).




%%%%% Number of shared variables: 0


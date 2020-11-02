%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test20).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test20.main',main,0,'test20.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test20.main'(_G479070,_G479071,_G479072):-freeze(_G479071,'blocked_test20.main'(_G479070,_G479071,_G479072)).
'blocked_test20.main'(_G479361,_G479364,_G479367):-hnf('Prelude.=:='(['Prelude.True'|_G479106],['Prelude.False'|_G479115]),_G479361,_G479364,_G479367).

:-costCenters(['']).




%%%%% Number of shared variables: 0

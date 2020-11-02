%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog20).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog20.main',main,0,'prog20.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog20.main'(_G479070,_G479071,_G479072):-freeze(_G479071,'blocked_prog20.main'(_G479070,_G479071,_G479072)).
'blocked_prog20.main'(_G479361,_G479364,_G479367):-hnf('Prelude.=:='(['Prelude.True'|_G479106],['Prelude.False'|_G479115]),_G479361,_G479364,_G479367).

:-costCenters(['']).




%%%%% Number of shared variables: 0

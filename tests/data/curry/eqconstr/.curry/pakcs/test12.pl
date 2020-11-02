%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test12).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test12.main',main,0,'test12.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test12.main'(_G475755,_G475756,_G475757):-freeze(_G475756,'blocked_test12.main'(_G475755,_G475756,_G475757)).
'blocked_test12.main'(_G475866,_G475869,_G475872):-hnf('Prelude.=:='(0,'Prelude.failed'),_G475866,_G475869,_G475872).

:-costCenters(['']).




%%%%% Number of shared variables: 0

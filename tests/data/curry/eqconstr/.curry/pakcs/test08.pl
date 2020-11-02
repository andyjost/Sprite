%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test08).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test08.f',f,0,'test08.f',nofix,'TCons'('Prelude.Bool',[])).
functiontype('test08.main',main,0,'test08.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test08.f'(_G486087,_G486088,_G486089):-freeze(_G486088,'blocked_test08.f'(_G486087,_G486088,_G486089)).
'blocked_test08.f'('Prelude.True',_G486128,_G486128).

'test08.main'(_G486502,_G486503,_G486504):-freeze(_G486503,'blocked_test08.main'(_G486502,_G486503,_G486504)).
'blocked_test08.main'(_G486620,_G486623,_G486626):-hnf('Prelude.=:='('test08.f','Prelude.False'),_G486620,_G486623,_G486626).

:-costCenters(['']).




%%%%% Number of shared variables: 0

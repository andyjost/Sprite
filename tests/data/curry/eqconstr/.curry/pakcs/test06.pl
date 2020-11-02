%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test06).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test06.f',f,0,'test06.f',nofix,'TCons'('Prelude.Bool',[])).
functiontype('test06.main',main,0,'test06.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test06.f'(_G486037,_G486038,_G486039):-freeze(_G486038,'blocked_test06.f'(_G486037,_G486038,_G486039)).
'blocked_test06.f'('Prelude.True',_G486078,_G486078).

'test06.main'(_G486452,_G486453,_G486454):-freeze(_G486453,'blocked_test06.main'(_G486452,_G486453,_G486454)).
'blocked_test06.main'(_G486570,_G486573,_G486576):-hnf('Prelude.=:='('test06.f','Prelude.True'),_G486570,_G486573,_G486576).

:-costCenters(['']).




%%%%% Number of shared variables: 0

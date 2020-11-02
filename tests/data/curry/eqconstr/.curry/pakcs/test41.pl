%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test41).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test41.main',main,0,'test41.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test41.main'(_G478153,_G478154,_G478155):-freeze(_G478154,'blocked_test41.main'(_G478153,_G478154,_G478155)).
'blocked_test41.main'(_G478425,_G478428,_G478431):-makeShare(_G478189,_G478463),hnf('Prelude.?'(_G478463,'Prelude.&>'('Prelude.=:='(_G478463,'Prelude.True'),_G478463)),_G478425,_G478428,_G478431).

:-costCenters(['']).




%%%%% Number of shared variables: 1

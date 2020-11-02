%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_001).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_001.main',main,0,'a0_001.main',nofix,'TCons'('a0_001.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_001.A','A',0,'A',0,'TCons'('a0_001.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_001.main'(_G478790,_G478791,_G478792):-freeze(_G478791,'blocked_a0_001.main'(_G478790,_G478791,_G478792)).
'blocked_a0_001.main'(_G478989,_G478992,_G478995):-makeShare(_G478826,_G479021),hnf('Prelude.&>'('Prelude.=:='('a0_001.A',_G479021),_G479021),_G478989,_G478992,_G478995).

:-costCenters(['']).




%%%%% Number of shared variables: 1

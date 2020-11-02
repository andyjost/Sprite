%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a2b1c0_004).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a2b1c0_004.main',main,0,'a2b1c0_004.main',nofix,'TCons'('a2b1c0_004.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a2b1c0_004.A','A',2,'A',0,'FuncType'('TCons'('a2b1c0_004.T',[]),'FuncType'('TCons'('a2b1c0_004.T',[]),'TCons'('a2b1c0_004.T',[]))),['a2b1c0_004.B'/1,'a2b1c0_004.C'/0]).
constructortype('a2b1c0_004.B','B',1,'B',1,'FuncType'('TCons'('a2b1c0_004.T',[]),'TCons'('a2b1c0_004.T',[])),['a2b1c0_004.A'/2,'a2b1c0_004.C'/0]).
constructortype('a2b1c0_004.C','C',0,'C',2,'TCons'('a2b1c0_004.T',[]),['a2b1c0_004.A'/2,'a2b1c0_004.B'/1]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a2b1c0_004.main'(_G495502,_G495503,_G495504):-freeze(_G495503,'blocked_a2b1c0_004.main'(_G495502,_G495503,_G495504)).
'blocked_a2b1c0_004.main'(_G495961,_G495964,_G495967):-makeShare(_G495538,_G496077),hnf('Prelude.&>'('Prelude.=:='(_G496077,'a2b1c0_004.A'('a2b1c0_004.A'(_G495547,_G495556),'a2b1c0_004.A'(_G495565,_G495574))),_G496077),_G495961,_G495964,_G495967).

:-costCenters(['']).




%%%%% Number of shared variables: 1

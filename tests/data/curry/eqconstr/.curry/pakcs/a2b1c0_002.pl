%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a2b1c0_002).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a2b1c0_002.main',main,0,'a2b1c0_002.main',nofix,'TCons'('a2b1c0_002.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a2b1c0_002.A','A',2,'A',0,'FuncType'('TCons'('a2b1c0_002.T',[]),'FuncType'('TCons'('a2b1c0_002.T',[]),'TCons'('a2b1c0_002.T',[]))),['a2b1c0_002.B'/1,'a2b1c0_002.C'/0]).
constructortype('a2b1c0_002.B','B',1,'B',1,'FuncType'('TCons'('a2b1c0_002.T',[]),'TCons'('a2b1c0_002.T',[])),['a2b1c0_002.A'/2,'a2b1c0_002.C'/0]).
constructortype('a2b1c0_002.C','C',0,'C',2,'TCons'('a2b1c0_002.T',[]),['a2b1c0_002.A'/2,'a2b1c0_002.B'/1]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a2b1c0_002.main'(_G491767,_G491768,_G491769):-freeze(_G491768,'blocked_a2b1c0_002.main'(_G491767,_G491768,_G491769)).
'blocked_a2b1c0_002.main'(_G491966,_G491969,_G491972):-makeShare(_G491803,_G491998),hnf('Prelude.&>'('Prelude.=:='(_G491998,'a2b1c0_002.C'),_G491998),_G491966,_G491969,_G491972).

:-costCenters(['']).




%%%%% Number of shared variables: 1

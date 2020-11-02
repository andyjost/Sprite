%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a2b1c0_000).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a2b1c0_000.main',main,0,'a2b1c0_000.main',nofix,'TCons'('a2b1c0_000.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a2b1c0_000.A','A',2,'A',0,'FuncType'('TCons'('a2b1c0_000.T',[]),'FuncType'('TCons'('a2b1c0_000.T',[]),'TCons'('a2b1c0_000.T',[]))),['a2b1c0_000.B'/1,'a2b1c0_000.C'/0]).
constructortype('a2b1c0_000.B','B',1,'B',1,'FuncType'('TCons'('a2b1c0_000.T',[]),'TCons'('a2b1c0_000.T',[])),['a2b1c0_000.A'/2,'a2b1c0_000.C'/0]).
constructortype('a2b1c0_000.C','C',0,'C',2,'TCons'('a2b1c0_000.T',[]),['a2b1c0_000.A'/2,'a2b1c0_000.B'/1]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a2b1c0_000.main'(_G492155,_G492156,_G492157):-freeze(_G492156,'blocked_a2b1c0_000.main'(_G492155,_G492156,_G492157)).
'blocked_a2b1c0_000.main'(_G492444,_G492447,_G492450):-makeShare(_G492191,_G492506),hnf('Prelude.&>'('Prelude.=:='(_G492506,'a2b1c0_000.A'(_G492200,_G492209)),_G492506),_G492444,_G492447,_G492450).

:-costCenters(['']).




%%%%% Number of shared variables: 1

%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a2b1c0_003).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a2b1c0_003.main',main,0,'a2b1c0_003.main',nofix,'TCons'('a2b1c0_003.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a2b1c0_003.A','A',2,'A',0,'FuncType'('TCons'('a2b1c0_003.T',[]),'FuncType'('TCons'('a2b1c0_003.T',[]),'TCons'('a2b1c0_003.T',[]))),['a2b1c0_003.B'/1,'a2b1c0_003.C'/0]).
constructortype('a2b1c0_003.B','B',1,'B',1,'FuncType'('TCons'('a2b1c0_003.T',[]),'TCons'('a2b1c0_003.T',[])),['a2b1c0_003.A'/2,'a2b1c0_003.C'/0]).
constructortype('a2b1c0_003.C','C',0,'C',2,'TCons'('a2b1c0_003.T',[]),['a2b1c0_003.A'/2,'a2b1c0_003.B'/1]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a2b1c0_003.main'(_G493836,_G493837,_G493838):-freeze(_G493837,'blocked_a2b1c0_003.main'(_G493836,_G493837,_G493838)).
'blocked_a2b1c0_003.main'(_G494210,_G494213,_G494216):-makeShare(_G493872,_G494296),hnf('Prelude.&>'('Prelude.=:='(_G494296,'a2b1c0_003.A'('a2b1c0_003.A'(_G493881,_G493890),_G493899)),_G494296),_G494210,_G494213,_G494216).

:-costCenters(['']).




%%%%% Number of shared variables: 1

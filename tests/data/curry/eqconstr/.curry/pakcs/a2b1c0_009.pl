%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a2b1c0_009).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a2b1c0_009.main',main,0,'a2b1c0_009.main',nofix,'TCons'('a2b1c0_009.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a2b1c0_009.A','A',2,'A',0,'FuncType'('TCons'('a2b1c0_009.T',[]),'FuncType'('TCons'('a2b1c0_009.T',[]),'TCons'('a2b1c0_009.T',[]))),['a2b1c0_009.B'/1,'a2b1c0_009.C'/0]).
constructortype('a2b1c0_009.B','B',1,'B',1,'FuncType'('TCons'('a2b1c0_009.T',[]),'TCons'('a2b1c0_009.T',[])),['a2b1c0_009.A'/2,'a2b1c0_009.C'/0]).
constructortype('a2b1c0_009.C','C',0,'C',2,'TCons'('a2b1c0_009.T',[]),['a2b1c0_009.A'/2,'a2b1c0_009.B'/1]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a2b1c0_009.main'(_G495105,_G495106,_G495107):-freeze(_G495106,'blocked_a2b1c0_009.main'(_G495105,_G495106,_G495107)).
'blocked_a2b1c0_009.main'(_G495474,_G495477,_G495480):-makeShare(_G495141,_G495536),hnf('Prelude.&>'('Prelude.=:='(_G495536,'a2b1c0_009.A'('a2b1c0_009.B'(_G495150),'a2b1c0_009.B'(_G495159))),_G495536),_G495474,_G495477,_G495480).

:-costCenters(['']).




%%%%% Number of shared variables: 1

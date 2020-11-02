%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a2b1c0_006).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a2b1c0_006.main',main,0,'a2b1c0_006.main',nofix,'TCons'('a2b1c0_006.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a2b1c0_006.A','A',2,'A',0,'FuncType'('TCons'('a2b1c0_006.T',[]),'FuncType'('TCons'('a2b1c0_006.T',[]),'TCons'('a2b1c0_006.T',[]))),['a2b1c0_006.B'/1,'a2b1c0_006.C'/0]).
constructortype('a2b1c0_006.B','B',1,'B',1,'FuncType'('TCons'('a2b1c0_006.T',[]),'TCons'('a2b1c0_006.T',[])),['a2b1c0_006.A'/2,'a2b1c0_006.C'/0]).
constructortype('a2b1c0_006.C','C',0,'C',2,'TCons'('a2b1c0_006.T',[]),['a2b1c0_006.A'/2,'a2b1c0_006.B'/1]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a2b1c0_006.main'(_G495108,_G495109,_G495110):-freeze(_G495109,'blocked_a2b1c0_006.main'(_G495108,_G495109,_G495110)).
'blocked_a2b1c0_006.main'(_G495477,_G495480,_G495483):-makeShare(_G495144,_G495539),hnf('Prelude.&>'('Prelude.=:='(_G495539,'a2b1c0_006.A'('a2b1c0_006.A'(_G495153,_G495162),'a2b1c0_006.C')),_G495539),_G495477,_G495480,_G495483).

:-costCenters(['']).




%%%%% Number of shared variables: 1

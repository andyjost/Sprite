%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a2b1c0_008).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a2b1c0_008.main',main,0,'a2b1c0_008.main',nofix,'TCons'('a2b1c0_008.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a2b1c0_008.A','A',2,'A',0,'FuncType'('TCons'('a2b1c0_008.T',[]),'FuncType'('TCons'('a2b1c0_008.T',[]),'TCons'('a2b1c0_008.T',[]))),['a2b1c0_008.B'/1,'a2b1c0_008.C'/0]).
constructortype('a2b1c0_008.B','B',1,'B',1,'FuncType'('TCons'('a2b1c0_008.T',[]),'TCons'('a2b1c0_008.T',[])),['a2b1c0_008.A'/2,'a2b1c0_008.C'/0]).
constructortype('a2b1c0_008.C','C',0,'C',2,'TCons'('a2b1c0_008.T',[]),['a2b1c0_008.A'/2,'a2b1c0_008.B'/1]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a2b1c0_008.main'(_G495284,_G495285,_G495286):-freeze(_G495285,'blocked_a2b1c0_008.main'(_G495284,_G495285,_G495286)).
'blocked_a2b1c0_008.main'(_G495698,_G495701,_G495704):-makeShare(_G495320,_G495784),hnf('Prelude.&>'('Prelude.=:='(_G495784,'a2b1c0_008.A'('a2b1c0_008.B'(_G495329),'a2b1c0_008.A'(_G495338,_G495347))),_G495784),_G495698,_G495701,_G495704).

:-costCenters(['']).




%%%%% Number of shared variables: 1

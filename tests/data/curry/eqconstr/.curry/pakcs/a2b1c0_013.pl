%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a2b1c0_013).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a2b1c0_013.main',main,0,'a2b1c0_013.main',nofix,'TCons'('a2b1c0_013.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a2b1c0_013.A','A',2,'A',0,'FuncType'('TCons'('a2b1c0_013.T',[]),'FuncType'('TCons'('a2b1c0_013.T',[]),'TCons'('a2b1c0_013.T',[]))),['a2b1c0_013.B'/1,'a2b1c0_013.C'/0]).
constructortype('a2b1c0_013.B','B',1,'B',1,'FuncType'('TCons'('a2b1c0_013.T',[]),'TCons'('a2b1c0_013.T',[])),['a2b1c0_013.A'/2,'a2b1c0_013.C'/0]).
constructortype('a2b1c0_013.C','C',0,'C',2,'TCons'('a2b1c0_013.T',[]),['a2b1c0_013.A'/2,'a2b1c0_013.B'/1]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a2b1c0_013.main'(_G494917,_G494918,_G494919):-freeze(_G494918,'blocked_a2b1c0_013.main'(_G494917,_G494918,_G494919)).
'blocked_a2b1c0_013.main'(_G495241,_G495244,_G495247):-makeShare(_G494953,_G495285),hnf('Prelude.&>'('Prelude.=:='(_G495285,'a2b1c0_013.A'('a2b1c0_013.C','a2b1c0_013.B'(_G494962))),_G495285),_G495241,_G495244,_G495247).

:-costCenters(['']).




%%%%% Number of shared variables: 1

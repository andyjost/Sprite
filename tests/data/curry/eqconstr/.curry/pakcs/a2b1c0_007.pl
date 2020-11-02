%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a2b1c0_007).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a2b1c0_007.main',main,0,'a2b1c0_007.main',nofix,'TCons'('a2b1c0_007.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a2b1c0_007.A','A',2,'A',0,'FuncType'('TCons'('a2b1c0_007.T',[]),'FuncType'('TCons'('a2b1c0_007.T',[]),'TCons'('a2b1c0_007.T',[]))),['a2b1c0_007.B'/1,'a2b1c0_007.C'/0]).
constructortype('a2b1c0_007.B','B',1,'B',1,'FuncType'('TCons'('a2b1c0_007.T',[]),'TCons'('a2b1c0_007.T',[])),['a2b1c0_007.A'/2,'a2b1c0_007.C'/0]).
constructortype('a2b1c0_007.C','C',0,'C',2,'TCons'('a2b1c0_007.T',[]),['a2b1c0_007.A'/2,'a2b1c0_007.B'/1]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a2b1c0_007.main'(_G493627,_G493628,_G493629):-freeze(_G493628,'blocked_a2b1c0_007.main'(_G493627,_G493628,_G493629)).
'blocked_a2b1c0_007.main'(_G493956,_G493959,_G493962):-makeShare(_G493663,_G494018),hnf('Prelude.&>'('Prelude.=:='(_G494018,'a2b1c0_007.A'('a2b1c0_007.B'(_G493672),_G493681)),_G494018),_G493956,_G493959,_G493962).

:-costCenters(['']).




%%%%% Number of shared variables: 1

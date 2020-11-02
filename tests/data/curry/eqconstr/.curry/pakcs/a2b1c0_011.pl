%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a2b1c0_011).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a2b1c0_011.main',main,0,'a2b1c0_011.main',nofix,'TCons'('a2b1c0_011.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a2b1c0_011.A','A',2,'A',0,'FuncType'('TCons'('a2b1c0_011.T',[]),'FuncType'('TCons'('a2b1c0_011.T',[]),'TCons'('a2b1c0_011.T',[]))),['a2b1c0_011.B'/1,'a2b1c0_011.C'/0]).
constructortype('a2b1c0_011.B','B',1,'B',1,'FuncType'('TCons'('a2b1c0_011.T',[]),'TCons'('a2b1c0_011.T',[])),['a2b1c0_011.A'/2,'a2b1c0_011.C'/0]).
constructortype('a2b1c0_011.C','C',0,'C',2,'TCons'('a2b1c0_011.T',[]),['a2b1c0_011.A'/2,'a2b1c0_011.B'/1]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a2b1c0_011.main'(_G493418,_G493419,_G493420):-freeze(_G493419,'blocked_a2b1c0_011.main'(_G493418,_G493419,_G493420)).
'blocked_a2b1c0_011.main'(_G493702,_G493705,_G493708):-makeShare(_G493454,_G493746),hnf('Prelude.&>'('Prelude.=:='(_G493746,'a2b1c0_011.A'('a2b1c0_011.C',_G493463)),_G493746),_G493702,_G493705,_G493708).

:-costCenters(['']).




%%%%% Number of shared variables: 1

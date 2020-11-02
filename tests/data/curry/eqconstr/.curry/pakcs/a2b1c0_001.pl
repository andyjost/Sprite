%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a2b1c0_001).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a2b1c0_001.main',main,0,'a2b1c0_001.main',nofix,'TCons'('a2b1c0_001.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a2b1c0_001.A','A',2,'A',0,'FuncType'('TCons'('a2b1c0_001.T',[]),'FuncType'('TCons'('a2b1c0_001.T',[]),'TCons'('a2b1c0_001.T',[]))),['a2b1c0_001.B'/1,'a2b1c0_001.C'/0]).
constructortype('a2b1c0_001.B','B',1,'B',1,'FuncType'('TCons'('a2b1c0_001.T',[]),'TCons'('a2b1c0_001.T',[])),['a2b1c0_001.A'/2,'a2b1c0_001.C'/0]).
constructortype('a2b1c0_001.C','C',0,'C',2,'TCons'('a2b1c0_001.T',[]),['a2b1c0_001.A'/2,'a2b1c0_001.B'/1]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a2b1c0_001.main'(_G491952,_G491953,_G491954):-freeze(_G491953,'blocked_a2b1c0_001.main'(_G491952,_G491953,_G491954)).
'blocked_a2b1c0_001.main'(_G492196,_G492199,_G492202):-makeShare(_G491988,_G492240),hnf('Prelude.&>'('Prelude.=:='(_G492240,'a2b1c0_001.B'(_G491997)),_G492240),_G492196,_G492199,_G492202).

:-costCenters(['']).




%%%%% Number of shared variables: 1

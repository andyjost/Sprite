%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a2b1c0_014).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a2b1c0_014.main',main,0,'a2b1c0_014.main',nofix,'TCons'('a2b1c0_014.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a2b1c0_014.A','A',2,'A',0,'FuncType'('TCons'('a2b1c0_014.T',[]),'FuncType'('TCons'('a2b1c0_014.T',[]),'TCons'('a2b1c0_014.T',[]))),['a2b1c0_014.B'/1,'a2b1c0_014.C'/0]).
constructortype('a2b1c0_014.B','B',1,'B',1,'FuncType'('TCons'('a2b1c0_014.T',[]),'TCons'('a2b1c0_014.T',[])),['a2b1c0_014.A'/2,'a2b1c0_014.C'/0]).
constructortype('a2b1c0_014.C','C',0,'C',2,'TCons'('a2b1c0_014.T',[]),['a2b1c0_014.A'/2,'a2b1c0_014.B'/1]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a2b1c0_014.main'(_G494693,_G494694,_G494695):-freeze(_G494694,'blocked_a2b1c0_014.main'(_G494693,_G494694,_G494695)).
'blocked_a2b1c0_014.main'(_G494972,_G494975,_G494978):-makeShare(_G494729,_G495004),hnf('Prelude.&>'('Prelude.=:='(_G495004,'a2b1c0_014.A'('a2b1c0_014.C','a2b1c0_014.C')),_G495004),_G494972,_G494975,_G494978).

:-costCenters(['']).




%%%%% Number of shared variables: 1

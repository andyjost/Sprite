%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0b0c0_012).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0b0c0_012.main',main,0,'a0b0c0_012.main',nofix,'TCons'('a0b0c0_012.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0b0c0_012.A','A',0,'A',0,'TCons'('a0b0c0_012.T',[]),['a0b0c0_012.B'/0,'a0b0c0_012.C'/0]).
constructortype('a0b0c0_012.B','B',0,'B',1,'TCons'('a0b0c0_012.T',[]),['a0b0c0_012.A'/0,'a0b0c0_012.C'/0]).
constructortype('a0b0c0_012.C','C',0,'C',2,'TCons'('a0b0c0_012.T',[]),['a0b0c0_012.A'/0,'a0b0c0_012.B'/0]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0b0c0_012.main'(_G490454,_G490455,_G490456):-freeze(_G490455,'blocked_a0b0c0_012.main'(_G490454,_G490455,_G490456)).
'blocked_a0b0c0_012.main'(_G490884,_G490887,_G490890):-makeShare(_G490490,_G490946),makeShare(_G490499,_G490956),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G490946,_G490956),'Prelude.=:='(_G490956,'a0b0c0_012.A')),_G490946),_G490946),_G490884,_G490887,_G490890).

:-costCenters(['']).




%%%%% Number of shared variables: 2

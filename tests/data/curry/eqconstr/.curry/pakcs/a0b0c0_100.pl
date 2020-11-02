%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0b0c0_100).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0b0c0_100.main',main,0,'a0b0c0_100.main',nofix,'TCons'('a0b0c0_100.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0b0c0_100.A','A',0,'A',0,'TCons'('a0b0c0_100.T',[]),['a0b0c0_100.B'/0,'a0b0c0_100.C'/0]).
constructortype('a0b0c0_100.B','B',0,'B',1,'TCons'('a0b0c0_100.T',[]),['a0b0c0_100.A'/0,'a0b0c0_100.C'/0]).
constructortype('a0b0c0_100.C','C',0,'C',2,'TCons'('a0b0c0_100.T',[]),['a0b0c0_100.A'/0,'a0b0c0_100.B'/0]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0b0c0_100.main'(_G490456,_G490457,_G490458):-freeze(_G490457,'blocked_a0b0c0_100.main'(_G490456,_G490457,_G490458)).
'blocked_a0b0c0_100.main'(_G490886,_G490889,_G490892):-makeShare(_G490501,_G490942),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('a0b0c0_100.B',_G490942),'Prelude.=:='(_G490492,_G490942)),_G490942),_G490942),_G490886,_G490889,_G490892).

:-costCenters(['']).




%%%%% Number of shared variables: 1

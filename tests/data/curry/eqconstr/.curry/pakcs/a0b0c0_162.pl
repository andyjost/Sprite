%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0b0c0_162).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0b0c0_162.main',main,0,'a0b0c0_162.main',nofix,'TCons'('a0b0c0_162.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0b0c0_162.A','A',0,'A',0,'TCons'('a0b0c0_162.T',[]),['a0b0c0_162.B'/0,'a0b0c0_162.C'/0]).
constructortype('a0b0c0_162.B','B',0,'B',1,'TCons'('a0b0c0_162.T',[]),['a0b0c0_162.A'/0,'a0b0c0_162.C'/0]).
constructortype('a0b0c0_162.C','C',0,'C',2,'TCons'('a0b0c0_162.T',[]),['a0b0c0_162.A'/0,'a0b0c0_162.B'/0]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0b0c0_162.main'(_G491670,_G491671,_G491672):-freeze(_G491671,'blocked_a0b0c0_162.main'(_G491670,_G491671,_G491672)).
'blocked_a0b0c0_162.main'(_G492173,_G492176,_G492179):-makeShare(_G491715,_G492247),makeShare(_G491706,_G492257),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G492247,_G492257),'Prelude.=:='(_G492247,'a0b0c0_162.A')),_G492257),'Prelude.?'(_G492247,_G492257)),_G492173,_G492176,_G492179).

:-costCenters(['']).




%%%%% Number of shared variables: 2
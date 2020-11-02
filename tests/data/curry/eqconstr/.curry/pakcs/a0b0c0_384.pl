%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0b0c0_384).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0b0c0_384.main',main,0,'a0b0c0_384.main',nofix,'TCons'('Prelude.(,)',['TCons'('a0b0c0_384.T',[]),'TCons'('a0b0c0_384.T',[])])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0b0c0_384.A','A',0,'A',0,'TCons'('a0b0c0_384.T',[]),['a0b0c0_384.B'/0,'a0b0c0_384.C'/0]).
constructortype('a0b0c0_384.B','B',0,'B',1,'TCons'('a0b0c0_384.T',[]),['a0b0c0_384.A'/0,'a0b0c0_384.C'/0]).
constructortype('a0b0c0_384.C','C',0,'C',2,'TCons'('a0b0c0_384.T',[]),['a0b0c0_384.A'/0,'a0b0c0_384.B'/0]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0b0c0_384.main'(_G500747,_G500748,_G500749):-freeze(_G500748,'blocked_a0b0c0_384.main'(_G500747,_G500748,_G500749)).
'blocked_a0b0c0_384.main'(_G501476,_G501479,_G501482):-makeShare(_G500783,_G501568),makeShare(_G500792,_G501578),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G501568,'a0b0c0_384.A'),'Prelude.&'('Prelude.=:='(_G501578,_G501568),'Prelude.=:='(_G501578,'a0b0c0_384.A'))),'Prelude.(,)'(_G501568,_G501578)),'Prelude.(,)'(_G501568,_G501578)),_G501476,_G501479,_G501482).

:-costCenters(['']).




%%%%% Number of shared variables: 2

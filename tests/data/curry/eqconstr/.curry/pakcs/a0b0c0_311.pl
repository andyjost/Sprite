%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0b0c0_311).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0b0c0_311.main',main,0,'a0b0c0_311.main',nofix,'TCons'('Prelude.(,)',['TCons'('a0b0c0_311.T',[]),'TCons'('a0b0c0_311.T',[])])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0b0c0_311.A','A',0,'A',0,'TCons'('a0b0c0_311.T',[]),['a0b0c0_311.B'/0,'a0b0c0_311.C'/0]).
constructortype('a0b0c0_311.B','B',0,'B',1,'TCons'('a0b0c0_311.T',[]),['a0b0c0_311.A'/0,'a0b0c0_311.C'/0]).
constructortype('a0b0c0_311.C','C',0,'C',2,'TCons'('a0b0c0_311.T',[]),['a0b0c0_311.A'/0,'a0b0c0_311.B'/0]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0b0c0_311.main'(_G500747,_G500748,_G500749):-freeze(_G500748,'blocked_a0b0c0_311.main'(_G500747,_G500748,_G500749)).
'blocked_a0b0c0_311.main'(_G501476,_G501479,_G501482):-makeShare(_G500783,_G501568),makeShare(_G500792,_G501578),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G501568,_G501578),'Prelude.&'('Prelude.=:='('a0b0c0_311.C',_G501568),'Prelude.=:='('a0b0c0_311.A',_G501578))),'Prelude.(,)'(_G501568,_G501578)),'Prelude.(,)'(_G501568,_G501578)),_G501476,_G501479,_G501482).

:-costCenters(['']).




%%%%% Number of shared variables: 2
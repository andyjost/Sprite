%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0b0c0_413).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0b0c0_413.main',main,0,'a0b0c0_413.main',nofix,'TCons'('Prelude.(,)',['TCons'('a0b0c0_413.T',[]),'TCons'('a0b0c0_413.T',[])])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0b0c0_413.A','A',0,'A',0,'TCons'('a0b0c0_413.T',[]),['a0b0c0_413.B'/0,'a0b0c0_413.C'/0]).
constructortype('a0b0c0_413.B','B',0,'B',1,'TCons'('a0b0c0_413.T',[]),['a0b0c0_413.A'/0,'a0b0c0_413.C'/0]).
constructortype('a0b0c0_413.C','C',0,'C',2,'TCons'('a0b0c0_413.T',[]),['a0b0c0_413.A'/0,'a0b0c0_413.B'/0]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0b0c0_413.main'(_G500747,_G500748,_G500749):-freeze(_G500748,'blocked_a0b0c0_413.main'(_G500747,_G500748,_G500749)).
'blocked_a0b0c0_413.main'(_G501476,_G501479,_G501482):-makeShare(_G500792,_G501568),makeShare(_G500783,_G501578),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('a0b0c0_413.A',_G501568),'Prelude.&'('Prelude.=:='(_G501578,'a0b0c0_413.C'),'Prelude.=:='(_G501568,_G501578))),'Prelude.(,)'(_G501578,_G501568)),'Prelude.(,)'(_G501578,_G501568)),_G501476,_G501479,_G501482).

:-costCenters(['']).




%%%%% Number of shared variables: 2
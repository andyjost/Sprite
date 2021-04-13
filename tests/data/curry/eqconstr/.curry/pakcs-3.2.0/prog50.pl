%PAKCS3.2 swi8 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog50).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog50.main',main,0,'prog50.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog50.main'(_3597306,_3597308,_3597310):-freeze(_3597308,'blocked_prog50.main'(_3597306,_3597308,_3597310)).
'blocked_prog50.main'(_3598156,_3598162,_3598168):-makeShare(_3597378,_3598244),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_3598244,'Prelude.True'),'Prelude.=:='(_3598244,'Prelude.False')),_3598244),_3598244),_3598156,_3598162,_3598168).

:-costCenters(['']).




%%%%% Number of shared variables: 1


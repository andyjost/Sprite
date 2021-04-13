%PAKCS3.2 swi8 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog45).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog45.main',main,0,'prog45.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog45.main'(_3597966,_3597968,_3597970):-freeze(_3597968,'blocked_prog45.main'(_3597966,_3597968,_3597970)).
'blocked_prog45.main'(_3599104,_3599110,_3599116):-makeShare(_3598038,_3599276),makeShare(_3598056,_3599296),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_3599276,_3599276),'Prelude.&'('Prelude.=:='(_3599296,_3599296),'Prelude.=:='(_3599276,_3599296))),_3599276),_3599276),_3599104,_3599110,_3599116).

:-costCenters(['']).




%%%%% Number of shared variables: 2


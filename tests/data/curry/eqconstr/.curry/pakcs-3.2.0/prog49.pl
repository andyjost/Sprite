%PAKCS3.2 swi8 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog49).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog49.main',main,0,'prog49.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog49.main'(_3597192,_3597194,_3597196):-freeze(_3597194,'blocked_prog49.main'(_3597192,_3597194,_3597196)).
'blocked_prog49.main'(_3598042,_3598048,_3598054):-makeShare(_3597264,_3598130),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_3598130,'Prelude.True'),'Prelude.=:='(_3598130,'Prelude.True')),_3598130),_3598130),_3598042,_3598048,_3598054).

:-costCenters(['']).




%%%%% Number of shared variables: 1


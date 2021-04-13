%PAKCS3.2 swi8 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog44).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog44.main',main,0,'prog44.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog44.main'(_3594382,_3594384,_3594386):-freeze(_3594384,'blocked_prog44.main'(_3594382,_3594384,_3594386)).
'blocked_prog44.main'(_3595228,_3595234,_3595240):-makeShare(_3594454,_3595364),makeShare(_3594472,_3595384),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_3595364,_3595364),'Prelude.=:='(_3595384,_3595384)),_3595364),_3595364),_3595228,_3595234,_3595240).

:-costCenters(['']).




%%%%% Number of shared variables: 2


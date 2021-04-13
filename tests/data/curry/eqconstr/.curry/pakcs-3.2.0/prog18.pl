%PAKCS3.2 swi8 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog18).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog18.main',main,0,'prog18.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog18.main'(_3583786,_3583788,_3583790):-freeze(_3583788,'blocked_prog18.main'(_3583786,_3583788,_3583790)).
'blocked_prog18.main'(_3584048,_3584054,_3584060):-hnf('Prelude.=:='(_3583858,_3583876),_3584048,_3584054,_3584060).

:-costCenters(['']).




%%%%% Number of shared variables: 0


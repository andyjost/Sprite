%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog09).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog09.main',main,0,'prog09.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog09.main'(_G475914,_G475915,_G475916):-freeze(_G475915,'blocked_prog09.main'(_G475914,_G475915,_G475916)).
'blocked_prog09.main'(_G476091,_G476094,_G476097):-hnf('Prelude.=:='(0,'Prelude.?'(0,1)),_G476091,_G476094,_G476097).

:-costCenters(['']).




%%%%% Number of shared variables: 0

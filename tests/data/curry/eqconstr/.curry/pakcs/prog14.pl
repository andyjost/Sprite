%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog14).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog14.main',main,0,'prog14.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog14.main'(_G477014,_G477015,_G477016):-freeze(_G477015,'blocked_prog14.main'(_G477014,_G477015,_G477016)).
'blocked_prog14.main'(_G477198,_G477201,_G477204):-hnf('Prelude.=:='('Prelude.failed','Prelude.?'(0,1)),_G477198,_G477201,_G477204).

:-costCenters(['']).




%%%%% Number of shared variables: 0

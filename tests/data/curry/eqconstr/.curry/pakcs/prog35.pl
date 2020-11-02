%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog35).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog35.fwd',fwd,1,'prog35.fwd',nofix,'FuncType'(_G471045,_G471045)).
functiontype('prog35.main',main,0,'prog35.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog35.fwd'(_G484248,_G484249,_G484250,_G484251):-freeze(_G484250,'blocked_prog35.fwd'(_G484248,_G484249,_G484250,_G484251)).
'blocked_prog35.fwd'(_G484286,_G484293,_G484296,_G484299):-hnf(_G484286,_G484293,_G484296,_G484299).

'prog35.main'(_G484679,_G484680,_G484681):-freeze(_G484680,'blocked_prog35.main'(_G484679,_G484680,_G484681)).
'blocked_prog35.main'(_G484845,_G484848,_G484851):-hnf('Prelude.=:='('prog35.fwd'(_G484715),'Prelude.True'),_G484845,_G484848,_G484851).

:-costCenters(['']).




%%%%% Number of shared variables: 0

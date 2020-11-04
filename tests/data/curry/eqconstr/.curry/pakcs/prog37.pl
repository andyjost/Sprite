%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog37).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog37.fwd',fwd,1,'prog37.fwd',nofix,'FuncType'(_G471045,_G471045)).
functiontype('prog37.main',main,0,'prog37.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog37.fwd'(_G484248,_G484249,_G484250,_G484251):-freeze(_G484250,'blocked_prog37.fwd'(_G484248,_G484249,_G484250,_G484251)).
'blocked_prog37.fwd'(_G484286,_G484293,_G484296,_G484299):-hnf(_G484286,_G484293,_G484296,_G484299).

'prog37.main'(_G484679,_G484680,_G484681):-freeze(_G484680,'blocked_prog37.main'(_G484679,_G484680,_G484681)).
'blocked_prog37.main'(_G484845,_G484848,_G484851):-hnf('Prelude.=:='('Prelude.True','prog37.fwd'(_G484715)),_G484845,_G484848,_G484851).

:-costCenters(['']).




%%%%% Number of shared variables: 0
%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog43).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog43.main',main,0,'prog43.main',nofix,_G468097).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog43.main'(_G475864,_G475865,_G475866):-freeze(_G475865,'blocked_prog43.main'(_G475864,_G475865,_G475866)).
'blocked_prog43.main'(_G476129,_G476132,_G476135):-makeShare(_G475900,_G476173),hnf('Prelude.?'('Prelude.&>'('Prelude.=:='(_G476173,_G476173),_G476173),_G476173),_G476129,_G476132,_G476135).

:-costCenters(['']).




%%%%% Number of shared variables: 1

%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog44).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog44.main',main,0,'prog44.main',nofix,_G470530).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog44.main'(_G478297,_G478298,_G478299):-freeze(_G478298,'blocked_prog44.main'(_G478297,_G478298,_G478299)).
'blocked_prog44.main'(_G478720,_G478723,_G478726):-makeShare(_G478333,_G478788),makeShare(_G478342,_G478798),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G478788,_G478788),'Prelude.=:='(_G478798,_G478798)),_G478788),_G478788),_G478720,_G478723,_G478726).

:-costCenters(['']).




%%%%% Number of shared variables: 2

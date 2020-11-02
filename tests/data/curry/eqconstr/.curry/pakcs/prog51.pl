%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog51).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog51.main',main,0,'prog51.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog51.main'(_G484277,_G484278,_G484279):-freeze(_G484278,'blocked_prog51.main'(_G484277,_G484278,_G484279)).
'blocked_prog51.main'(_G484860,_G484863,_G484866):-makeShare(_G484313,_G484928),makeShare(_G484322,_G484938),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G484928,'Prelude.True'),'Prelude.&'('Prelude.=:='(_G484938,_G484928),'Prelude.=:='(_G484938,'Prelude.True'))),_G484928),_G484928),_G484860,_G484863,_G484866).

:-costCenters(['']).




%%%%% Number of shared variables: 2

%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog100).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog100.main',main,0,'prog100.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog100.main'(_G483539,_G483540,_G483541):-freeze(_G483540,'blocked_prog100.main'(_G483539,_G483540,_G483541)).
'blocked_prog100.main'(_G484049,_G484052,_G484055):-makeShare(_G483584,_G484117),makeShare(_G483575,_G484127),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G484117,_G484127),'Prelude.&'('Prelude.=:='('Prelude.False',_G484117),'Prelude.=:='('Prelude.True',_G484127))),_G484127),_G484049,_G484052,_G484055).

:-costCenters(['']).




%%%%% Number of shared variables: 2

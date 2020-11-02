%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog47).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog47.main',main,0,'prog47.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog47.main'(_G485754,_G485755,_G485756):-freeze(_G485755,'blocked_prog47.main'(_G485754,_G485755,_G485756)).
'blocked_prog47.main'(_G486476,_G486479,_G486482):-makeShare(_G485799,_G486580),makeShare(_G485790,_G486590),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G486580,'Prelude.True'),'Prelude.&'('Prelude.=:='(_G486590,_G486590),'Prelude.&'('Prelude.=:='(_G486580,_G486580),'Prelude.=:='(_G486590,_G486580)))),_G486590),_G486590),_G486476,_G486479,_G486482).

:-costCenters(['']).




%%%%% Number of shared variables: 2

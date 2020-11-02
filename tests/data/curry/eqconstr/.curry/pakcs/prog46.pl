%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog46).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog46.main',main,0,'prog46.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog46.main'(_G485758,_G485759,_G485760):-freeze(_G485759,'blocked_prog46.main'(_G485758,_G485759,_G485760)).
'blocked_prog46.main'(_G486480,_G486483,_G486486):-makeShare(_G485794,_G486578),makeShare(_G485803,_G486588),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G486578,_G486578),'Prelude.&'('Prelude.=:='(_G486588,_G486588),'Prelude.&'('Prelude.=:='(_G486578,_G486588),'Prelude.=:='(_G486588,'Prelude.True')))),_G486578),_G486578),_G486480,_G486483,_G486486).

:-costCenters(['']).




%%%%% Number of shared variables: 2

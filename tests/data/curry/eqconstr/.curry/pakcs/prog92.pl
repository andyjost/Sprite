%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog92).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog92.main',main,0,'prog92.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog92.main'(_G483127,_G483128,_G483129):-freeze(_G483128,'blocked_prog92.main'(_G483127,_G483128,_G483129)).
'blocked_prog92.main'(_G483637,_G483640,_G483643):-makeShare(_G483172,_G483705),makeShare(_G483163,_G483715),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='('Prelude.False',_G483705),'Prelude.&'('Prelude.=:='(_G483705,_G483715),'Prelude.=:='('Prelude.True',_G483715))),_G483715),_G483637,_G483640,_G483643).

:-costCenters(['']).




%%%%% Number of shared variables: 2

%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog48).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog48.main',main,0,'prog48.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog48.main'(_G489416,_G489417,_G489418):-freeze(_G489417,'blocked_prog48.main'(_G489416,_G489417,_G489418)).
'blocked_prog48.main'(_G490291,_G490294,_G490297):-makeShare(_G489461,_G490401),makeShare(_G489452,_G490411),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G490401,'Prelude.True'),'Prelude.&'('Prelude.=:='(_G490411,_G490411),'Prelude.&'('Prelude.=:='(_G490401,_G490401),'Prelude.&'('Prelude.=:='(_G490411,_G490401),'Prelude.=:='(_G490401,'Prelude.True'))))),_G490411),_G490411),_G490291,_G490294,_G490297).

:-costCenters(['']).




%%%%% Number of shared variables: 2

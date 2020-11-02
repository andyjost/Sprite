%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog45).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog45.main',main,0,'prog45.main',nofix,_G473702).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog45.main'(_G481469,_G481470,_G481471):-freeze(_G481470,'blocked_prog45.main'(_G481469,_G481470,_G481471)).
'blocked_prog45.main'(_G482038,_G482041,_G482044):-makeShare(_G481505,_G482124),makeShare(_G481514,_G482134),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G482124,_G482124),'Prelude.&'('Prelude.=:='(_G482134,_G482134),'Prelude.=:='(_G482124,_G482134))),_G482124),_G482124),_G482038,_G482041,_G482044).

:-costCenters(['']).




%%%%% Number of shared variables: 2

%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test05).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test05.f',f,0,'test05.f',nofix,'TCons'('Prelude.Bool',[])).
functiontype('test05.main',main,0,'test05.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test05.f'(_G486031,_G486032,_G486033):-freeze(_G486032,'blocked_test05.f'(_G486031,_G486032,_G486033)).
'blocked_test05.f'('Prelude.True',_G486072,_G486072).

'test05.main'(_G486446,_G486447,_G486448):-freeze(_G486447,'blocked_test05.main'(_G486446,_G486447,_G486448)).
'blocked_test05.main'(_G486564,_G486567,_G486570):-hnf('Prelude.=:='('Prelude.True','test05.f'),_G486564,_G486567,_G486570).

:-costCenters(['']).




%%%%% Number of shared variables: 0

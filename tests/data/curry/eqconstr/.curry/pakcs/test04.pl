%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test04).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test04.f',f,0,'test04.f',nofix,'TCons'('Prelude.Bool',[])).
functiontype('test04.main',main,0,'test04.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test04.f'(_G485840,_G485841,_G485842):-freeze(_G485841,'blocked_test04.f'(_G485840,_G485841,_G485842)).
'blocked_test04.f'('Prelude.True',_G485881,_G485881).

'test04.main'(_G486255,_G486256,_G486257):-freeze(_G486256,'blocked_test04.main'(_G486255,_G486256,_G486257)).
'blocked_test04.main'(_G486373,_G486376,_G486379):-hnf('Prelude.=:='('test04.f','test04.f'),_G486373,_G486376,_G486379).

:-costCenters(['']).




%%%%% Number of shared variables: 0

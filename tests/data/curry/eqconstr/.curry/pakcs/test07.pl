%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test07).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test07.f',f,0,'test07.f',nofix,'TCons'('Prelude.Bool',[])).
functiontype('test07.main',main,0,'test07.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test07.f'(_G486090,_G486091,_G486092):-freeze(_G486091,'blocked_test07.f'(_G486090,_G486091,_G486092)).
'blocked_test07.f'('Prelude.True',_G486131,_G486131).

'test07.main'(_G486505,_G486506,_G486507):-freeze(_G486506,'blocked_test07.main'(_G486505,_G486506,_G486507)).
'blocked_test07.main'(_G486623,_G486626,_G486629):-hnf('Prelude.=:='('Prelude.False','test07.f'),_G486623,_G486626,_G486629).

:-costCenters(['']).




%%%%% Number of shared variables: 0

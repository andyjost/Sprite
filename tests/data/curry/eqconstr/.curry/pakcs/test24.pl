%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test24).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test24.fwd',fwd,1,'test24.fwd',nofix,'FuncType'(_G472863,_G472863)).
functiontype('test24.main',main,0,'test24.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test24.fwd'(_G486066,_G486067,_G486068,_G486069):-freeze(_G486068,'blocked_test24.fwd'(_G486066,_G486067,_G486068,_G486069)).
'blocked_test24.fwd'(_G486104,_G486111,_G486114,_G486117):-hnf(_G486104,_G486111,_G486114,_G486117).

'test24.main'(_G486497,_G486498,_G486499):-freeze(_G486498,'blocked_test24.main'(_G486497,_G486498,_G486499)).
'blocked_test24.main'(_G486655,_G486658,_G486661):-hnf('Prelude.=:='('test24.fwd'('Prelude.True'),'Prelude.False'),_G486655,_G486658,_G486661).

:-costCenters(['']).




%%%%% Number of shared variables: 0

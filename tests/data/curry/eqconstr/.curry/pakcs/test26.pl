%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test26).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test26.fwd',fwd,1,'test26.fwd',nofix,'FuncType'(_G472863,_G472863)).
functiontype('test26.main',main,0,'test26.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test26.fwd'(_G486066,_G486067,_G486068,_G486069):-freeze(_G486068,'blocked_test26.fwd'(_G486066,_G486067,_G486068,_G486069)).
'blocked_test26.fwd'(_G486104,_G486111,_G486114,_G486117):-hnf(_G486104,_G486111,_G486114,_G486117).

'test26.main'(_G486497,_G486498,_G486499):-freeze(_G486498,'blocked_test26.main'(_G486497,_G486498,_G486499)).
'blocked_test26.main'(_G486655,_G486658,_G486661):-hnf('Prelude.=:='('Prelude.False','test26.fwd'('Prelude.True')),_G486655,_G486658,_G486661).

:-costCenters(['']).




%%%%% Number of shared variables: 0

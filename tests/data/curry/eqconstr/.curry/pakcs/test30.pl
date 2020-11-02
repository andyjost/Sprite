%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test30).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test30.fwd',fwd,1,'test30.fwd',nofix,'FuncType'(_G476345,_G476345)).
functiontype('test30.f',f,0,'test30.f',nofix,'TCons'('Prelude.Bool',[])).
functiontype('test30.main',main,0,'test30.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test30.fwd'(_G495010,_G495011,_G495012,_G495013):-freeze(_G495012,'blocked_test30.fwd'(_G495010,_G495011,_G495012,_G495013)).
'blocked_test30.fwd'(_G495048,_G495055,_G495058,_G495061):-hnf(_G495048,_G495055,_G495058,_G495061).

'test30.f'(_G495387,_G495388,_G495389):-freeze(_G495388,'blocked_test30.f'(_G495387,_G495388,_G495389)).
'blocked_test30.f'('Prelude.True',_G495428,_G495428).

'test30.main'(_G495802,_G495803,_G495804):-freeze(_G495803,'blocked_test30.main'(_G495802,_G495803,_G495804)).
'blocked_test30.main'(_G495960,_G495963,_G495966):-hnf('Prelude.=:='('Prelude.False','test30.fwd'('test30.f')),_G495960,_G495963,_G495966).

:-costCenters(['']).




%%%%% Number of shared variables: 0

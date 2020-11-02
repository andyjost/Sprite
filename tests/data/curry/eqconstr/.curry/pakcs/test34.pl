%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test34).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test34.fwd',fwd,1,'test34.fwd',nofix,'FuncType'(_G478733,_G478733)).
functiontype('test34.f',f,0,'test34.f',nofix,'TCons'('Prelude.Bool',[])).
functiontype('test34.main',main,0,'test34.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test34.fwd'(_G497398,_G497399,_G497400,_G497401):-freeze(_G497400,'blocked_test34.fwd'(_G497398,_G497399,_G497400,_G497401)).
'blocked_test34.fwd'(_G497436,_G497443,_G497446,_G497449):-hnf(_G497436,_G497443,_G497446,_G497449).

'test34.f'(_G497775,_G497776,_G497777):-freeze(_G497776,'blocked_test34.f'(_G497775,_G497776,_G497777)).
'blocked_test34.f'(_G497893,_G497896,_G497899):-hnf('Prelude.?'('Prelude.True','Prelude.False'),_G497893,_G497896,_G497899).

'test34.main'(_G498459,_G498460,_G498461):-freeze(_G498460,'blocked_test34.main'(_G498459,_G498460,_G498461)).
'blocked_test34.main'(_G498617,_G498620,_G498623):-hnf('Prelude.=:='('Prelude.False','test34.fwd'('test34.f')),_G498617,_G498620,_G498623).

:-costCenters(['']).




%%%%% Number of shared variables: 0

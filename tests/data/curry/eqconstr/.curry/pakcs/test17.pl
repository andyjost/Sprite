%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test17).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test17.f',f,2,'test17.f',nofix,'FuncType'('TCons'('Prelude.Bool',[]),'FuncType'('TCons'('Prelude.Bool',[]),'TCons'('Prelude.Bool',[])))).
functiontype('test17.main',main,0,'test17.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test17.f'(_G491814,_G491815,_G491816,_G491817,_G491818):-freeze(_G491817,'blocked_test17.f'(_G491814,_G491815,_G491816,_G491817,_G491818)).
'blocked_test17.f'(_G491857,_G491866,_G492444,_G492447,_G492450):-hnf(_G491857,_G492786,_G492447,_G492774),'blocked_test17.f_1'(_G492786,_G491866,_G492444,_G492774,_G492450).

'blocked_test17.f_1'(_G492911,_G492912,_G492913,_G492914,_G492915):-freeze(_G492914,'blocked_blocked_test17.f_1'(_G492911,_G492912,_G492913,_G492914,_G492915)).
'blocked_blocked_test17.f_1'('Prelude.True',_G491866,_G493210,_G493213,_G493216):-!,hnf(_G491866,_G493921,_G493213,_G493912),'blocked_blocked_test17.f_1_Prelude.True_1'(_G493921,_G493210,_G493912,_G493216).

'blocked_blocked_test17.f_1_Prelude.True_1'(_G494123,_G494124,_G494125,_G494126):-freeze(_G494125,'blocked_blocked_blocked_test17.f_1_Prelude.True_1'(_G494123,_G494124,_G494125,_G494126)).
'blocked_blocked_blocked_test17.f_1_Prelude.True_1'('Prelude.True','Prelude.True',_G494334,_G494334):-!.
'blocked_blocked_blocked_test17.f_1_Prelude.True_1'('Prelude.False',_G494697,_G494700,_G494703):-!,hnf('Prelude.failure'('test17.f',['Prelude.False']),_G494697,_G494700,_G494703).
'blocked_blocked_blocked_test17.f_1_Prelude.True_1'('FAIL'(_G495204),'FAIL'(_G495204),_G495211,_G495211).
'blocked_blocked_test17.f_1'('Prelude.False',_G491866,_G495366,_G495369,_G495372):-!,hnf('Prelude.failure'('test17.f',['Prelude.False']),_G495366,_G495369,_G495372).
'blocked_blocked_test17.f_1'('FAIL'(_G495839),_G491866,'FAIL'(_G495839),_G495846,_G495846).

'test17.main'(_G496125,_G496126,_G496127):-freeze(_G496126,'blocked_test17.main'(_G496125,_G496126,_G496127)).
'blocked_test17.main'(_G496251,_G496254,_G496257):-hnf('test17.f'('Prelude.True',_G496161),_G496251,_G496254,_G496257).

:-costCenters(['']).




%%%%% Number of shared variables: 0

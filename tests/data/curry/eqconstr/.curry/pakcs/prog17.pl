%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog17).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog17.f',f,2,'prog17.f',nofix,'FuncType'('TCons'('Prelude.Bool',[]),'FuncType'('TCons'('Prelude.Bool',[]),'TCons'('Prelude.Bool',[])))).
functiontype('prog17.main',main,0,'prog17.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog17.f'(_G491812,_G491813,_G491814,_G491815,_G491816):-freeze(_G491815,'blocked_prog17.f'(_G491812,_G491813,_G491814,_G491815,_G491816)).
'blocked_prog17.f'(_G491855,_G491864,_G492442,_G492445,_G492448):-hnf(_G491855,_G492784,_G492445,_G492772),'blocked_prog17.f_1'(_G492784,_G491864,_G492442,_G492772,_G492448).

'blocked_prog17.f_1'(_G492909,_G492910,_G492911,_G492912,_G492913):-freeze(_G492912,'blocked_blocked_prog17.f_1'(_G492909,_G492910,_G492911,_G492912,_G492913)).
'blocked_blocked_prog17.f_1'('Prelude.True',_G491864,_G493208,_G493211,_G493214):-!,hnf(_G491864,_G493919,_G493211,_G493910),'blocked_blocked_prog17.f_1_Prelude.True_1'(_G493919,_G493208,_G493910,_G493214).

'blocked_blocked_prog17.f_1_Prelude.True_1'(_G494121,_G494122,_G494123,_G494124):-freeze(_G494123,'blocked_blocked_blocked_prog17.f_1_Prelude.True_1'(_G494121,_G494122,_G494123,_G494124)).
'blocked_blocked_blocked_prog17.f_1_Prelude.True_1'('Prelude.True','Prelude.True',_G494332,_G494332):-!.
'blocked_blocked_blocked_prog17.f_1_Prelude.True_1'('Prelude.False',_G494695,_G494698,_G494701):-!,hnf('Prelude.failure'('prog17.f',['Prelude.False']),_G494695,_G494698,_G494701).
'blocked_blocked_blocked_prog17.f_1_Prelude.True_1'('FAIL'(_G495202),'FAIL'(_G495202),_G495209,_G495209).
'blocked_blocked_prog17.f_1'('Prelude.False',_G491864,_G495364,_G495367,_G495370):-!,hnf('Prelude.failure'('prog17.f',['Prelude.False']),_G495364,_G495367,_G495370).
'blocked_blocked_prog17.f_1'('FAIL'(_G495837),_G491864,'FAIL'(_G495837),_G495844,_G495844).

'prog17.main'(_G496123,_G496124,_G496125):-freeze(_G496124,'blocked_prog17.main'(_G496123,_G496124,_G496125)).
'blocked_prog17.main'(_G496249,_G496252,_G496255):-hnf('prog17.f'('Prelude.True',_G496159),_G496249,_G496252,_G496255).

:-costCenters(['']).




%%%%% Number of shared variables: 0

%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(account).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('account.account',account,2,'account.account',nofix,'FuncType'('TCons'('Prelude.Int',[]),'FuncType'('TCons'([],['TCons'('account.Message',[])]),'TCons'('Prelude.Bool',[])))).
functiontype('account.make_account',make_account,1,'account.make_account',nofix,'FuncType'('TCons'([],['TCons'('account.Message',[])]),'TCons'('Prelude.Bool',[]))).
functiontype('account.goal1',goal1,1,'account.goal1',nofix,'FuncType'('TCons'('Prelude.Int',[]),'TCons'('Prelude.Bool',[]))).
functiontype('account.goal2',goal2,1,'account.goal2',nofix,'FuncType'('TCons'('Prelude.Int',[]),'TCons'('Prelude.Bool',[]))).
functiontype('account.sendMsg',sendMsg,2,'account.sendMsg',nofix,'FuncType'(_G671354,'FuncType'('TCons'([],[_G671354]),'TCons'([],[_G671354])))).
functiontype('account.client',client,1,'account.client',nofix,'FuncType'('TCons'([],['TCons'('account.Message',[])]),'TCons'('Prelude.Bool',[]))).
functiontype('account.goal3',goal3,1,'account.goal3',nofix,'FuncType'('TCons'([],['TCons'('account.Message',[])]),'TCons'('Prelude.Bool',[]))).
functiontype('account.sprite_goal1',sprite_goal1,0,'account.sprite_goal1',nofix,'TCons'('Prelude.Int',[])).
functiontype('account.sprite_goal2',sprite_goal2,0,'account.sprite_goal2',nofix,'TCons'('Prelude.Int',[])).
functiontype('account.sprite_goal3',sprite_goal3,0,'account.sprite_goal3',nofix,'TCons'([],['TCons'('account.Message',[])])).
functiontype('account.sendMsg._\'23caseor0','account.sendMsg._#caseor0',2,'account.sendMsg._\'23caseor0',nofix,'FuncType'('TCons'('Prelude.Bool',[]),'FuncType'(_G704924,_G704924))).
functiontype('account.client._\'23caseor0','account.client._#caseor0',3,'account.client._\'23caseor0',nofix,'FuncType'('TCons'('Prelude.Bool',[]),'FuncType'('TCons'('Prelude.Int',[]),'FuncType'('TCons'([],['TCons'('account.Message',[])]),'TCons'('Prelude.Bool',[]))))).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('account.Deposit','Deposit',1,'Deposit',0,'FuncType'('TCons'('Prelude.Int',[]),'TCons'('account.Message',[])),['account.Withdraw'/1,'account.Balance'/1]).
constructortype('account.Withdraw','Withdraw',1,'Withdraw',1,'FuncType'('TCons'('Prelude.Int',[]),'TCons'('account.Message',[])),['account.Deposit'/1,'account.Balance'/1]).
constructortype('account.Balance','Balance',1,'Balance',2,'FuncType'('TCons'('Prelude.Int',[]),'TCons'('account.Message',[])),['account.Deposit'/1,'account.Withdraw'/1]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'account.account'(_G719830,_G719831,_G719832,_G719833,_G719834):-freeze(_G719833,'blocked_account.account'(_G719830,_G719831,_G719832,_G719833,_G719834)).
'blocked_account.account'(_G719873,_G719882,_G720760,_G720763,_G720766):-hnf(_G719882,_G721228,_G720763,_G721216),'blocked_account.account_2'(_G721228,_G719873,_G720760,_G721216,_G720766).

'blocked_account.account_2'(_G721374,_G721375,_G721376,_G721377,_G721378):-freeze(_G721377,'blocked_blocked_account.account_2'(_G721374,_G721375,_G721376,_G721377,_G721378)).
'blocked_blocked_account.account_2'([],_G719873,_G721476,_G721479,_G721482):-hnf('Prelude.success',_G721476,_G721479,_G721482).
'blocked_blocked_account.account_2'([_G719982|_G719991],_G719873,_G721887,_G721890,_G721893):-!,hnf(_G719982,_G722601,_G721890,_G722586),'blocked_blocked_account.account_2_[|]_1'(_G722601,_G719991,_G719873,_G721887,_G722586,_G721893).

'blocked_blocked_account.account_2_[|]_1'(_G722799,_G722800,_G722801,_G722802,_G722803,_G722804):-freeze(_G722803,'blocked_blocked_blocked_account.account_2_[|]_1'(_G722799,_G722800,_G722801,_G722802,_G722803,_G722804)).
'blocked_blocked_blocked_account.account_2_[|]_1'('account.Deposit'(_G720051),_G719991,_G719873,_G722995,_G722998,_G723001):-hnf('account.account'('Prelude._impl\'23\'2B\'23Prelude.Num\'23Prelude.Int'(_G719873,_G720051),_G719991),_G722995,_G722998,_G723001).
'blocked_blocked_blocked_account.account_2_[|]_1'('account.Withdraw'(_G720248),_G719991,_G719873,_G723830,_G723833,_G723836):-hnf('account.account'('Prelude._impl\'23\'2D\'23Prelude.Num\'23Prelude.Int'(_G719873,_G720248),_G719991),_G723830,_G723833,_G723836).
'blocked_blocked_blocked_account.account_2_[|]_1'('account.Balance'(_G720445),_G719991,_G719873,_G724659,_G724662,_G724665):-!,makeShare(_G719873,_G724739),hnf('Prelude.&'('Prelude.=:='(_G720445,_G724739),'account.account'(_G724739,_G719991)),_G724659,_G724662,_G724665).
'blocked_blocked_blocked_account.account_2_[|]_1'('FAIL'(_G725536),_G719991,_G719873,'FAIL'(_G725536),_G725543,_G725543):-nonvar(_G725536).
'blocked_blocked_account.account_2'('FAIL'(_G725576),_G719873,'FAIL'(_G725576),_G725583,_G725583):-nonvar(_G725576).

'account.make_account'(_G726026,_G726027,_G726028,_G726029):-freeze(_G726028,'blocked_account.make_account'(_G726026,_G726027,_G726028,_G726029)).
'blocked_account.make_account'(_G726064,_G726184,_G726187,_G726190):-hnf('account.account'(0,'Prelude.ensureSpine'(_G726064)),_G726184,_G726187,_G726190).

'account.goal1'(_G726871,_G726872,_G726873,_G726874):-freeze(_G726873,'blocked_account.goal1'(_G726871,_G726872,_G726873,_G726874)).
'blocked_account.goal1'(_G726909,_G727463,_G727466,_G727469):-makeShare(_G726921,_G727511),hnf('Prelude.&'('account.make_account'(_G727511),'Prelude.=:='(_G727511,['account.Deposit'(200),'account.Deposit'(50),'account.Balance'(_G726909)])),_G727463,_G727466,_G727469).

'account.goal2'(_G729011,_G729012,_G729013,_G729014):-freeze(_G729013,'blocked_account.goal2'(_G729011,_G729012,_G729013,_G729014)).
'blocked_account.goal2'(_G729049,_G729716,_G729719,_G729722):-makeShare(_G729061,_G729764),hnf('Prelude.&'('account.make_account'(_G729764),'Prelude.=:='(_G729764,['account.Deposit'(200),'account.Withdraw'(100),'account.Deposit'(50),'account.Balance'(_G729049)])),_G729716,_G729719,_G729722).

'account.sendMsg'(_G731481,_G731482,_G731483,_G731484,_G731485):-freeze(_G731484,'blocked_account.sendMsg'(_G731481,_G731482,_G731483,_G731484,_G731485)).
'blocked_account.sendMsg'(_G731524,_G731533,_G731774,_G731777,_G731780):-makeShare(_G731545,_G731856),hnf('account.sendMsg._\'23caseor0'('Prelude.=:='(_G731533,[_G731524|_G731856]),_G731856),_G731774,_G731777,_G731780).

'account.client'(_G732881,_G732882,_G732883,_G732884):-freeze(_G732883,'blocked_account.client'(_G732881,_G732882,_G732883,_G732884)).
'blocked_account.client'(_G732919,_G733245,_G733248,_G733251):-makeShare(_G732931,_G733323),makeShare(_G732940,_G733333),hnf('account.client._\'23caseor0'('Prelude.=:='(_G733323,'account.sendMsg'('account.Balance'(_G733333),_G732919)),_G733333,_G733323),_G733245,_G733248,_G733251).

'account.goal3'(_G734609,_G734610,_G734611,_G734612):-freeze(_G734611,'blocked_account.goal3'(_G734609,_G734610,_G734611,_G734612)).
'blocked_account.goal3'(_G734647,_G734920,_G734923,_G734926):-makeShare(_G734647,_G734956),hnf('Prelude.&'('account.make_account'(_G734956),'account.client'('account.sendMsg'('account.Deposit'(100),_G734956))),_G734920,_G734923,_G734926).

'account.sprite_goal1'(_G736149,_G736150,_G736151):-freeze(_G736150,'blocked_account.sprite_goal1'(_G736149,_G736150,_G736151)).
'blocked_account.sprite_goal1'(_G736308,_G736311,_G736314):-makeShare(_G736185,_G736340),hnf('Prelude.&>'('account.goal1'(_G736340),_G736340),_G736308,_G736311,_G736314).

'account.sprite_goal2'(_G737242,_G737243,_G737244):-freeze(_G737243,'blocked_account.sprite_goal2'(_G737242,_G737243,_G737244)).
'blocked_account.sprite_goal2'(_G737401,_G737404,_G737407):-makeShare(_G737278,_G737433),hnf('Prelude.&>'('account.goal2'(_G737433),_G737433),_G737401,_G737404,_G737407).

'account.sprite_goal3'(_G738335,_G738336,_G738337):-freeze(_G738336,'blocked_account.sprite_goal3'(_G738335,_G738336,_G738337)).
'blocked_account.sprite_goal3'(_G738494,_G738497,_G738500):-makeShare(_G738371,_G738526),hnf('Prelude.&>'('account.goal3'(_G738526),_G738526),_G738494,_G738497,_G738500).

'account.sendMsg._\'23caseor0'(_G739530,_G739531,_G739532,_G739533,_G739534):-freeze(_G739533,'blocked_account.sendMsg._\'23caseor0'(_G739530,_G739531,_G739532,_G739533,_G739534)).
'blocked_account.sendMsg._\'23caseor0'(_G739573,_G739582,_G739956,_G739959,_G739962):-hnf(_G739573,_G740640,_G739959,_G740628),'blocked_account.sendMsg._\'23caseor0_1'(_G740640,_G739582,_G739956,_G740628,_G739962).

'blocked_account.sendMsg._\'23caseor0_1'(_G740825,_G740826,_G740827,_G740828,_G740829):-freeze(_G740828,freeze(_G740825,'blocked_blocked_account.sendMsg._\'23caseor0_1'(_G740825,_G740826,_G740827,_G740828,_G740829))).
'blocked_blocked_account.sendMsg._\'23caseor0_1'('Prelude.True',_G739582,_G740996,_G740999,_G741002):-hnf(_G739582,_G740996,_G740999,_G741002).
'blocked_blocked_account.sendMsg._\'23caseor0_1'('Prelude.False',_G739582,_G741347,_G741350,_G741353):-!,hnf('Prelude.failure'('account.sendMsg._\'23caseor0',['Prelude.False']),_G741347,_G741350,_G741353).
'blocked_blocked_account.sendMsg._\'23caseor0_1'('FAIL'(_G741934),_G739582,'FAIL'(_G741934),_G741941,_G741941).

'account.client._\'23caseor0'(_G742466,_G742467,_G742468,_G742469,_G742470,_G742471):-freeze(_G742470,'blocked_account.client._\'23caseor0'(_G742466,_G742467,_G742468,_G742469,_G742470,_G742471)).
'blocked_account.client._\'23caseor0'(_G742514,_G742523,_G742532,_G743689,_G743692,_G743695):-hnf(_G742514,_G744365,_G743692,_G744350),'blocked_account.client._\'23caseor0_1'(_G744365,_G742523,_G742532,_G743689,_G744350,_G743695).

'blocked_account.client._\'23caseor0_1'(_G744548,_G744549,_G744550,_G744551,_G744552,_G744553):-freeze(_G744552,freeze(_G744548,'blocked_blocked_account.client._\'23caseor0_1'(_G744548,_G744549,_G744550,_G744551,_G744552,_G744553))).
'blocked_blocked_account.client._\'23caseor0_1'('Prelude.True',_G742523,_G742532,_G745577,_G745580,_G745583):-makeShare(_G742523,_G744783),hnf('Prelude._impl\'23\'3D\'3D\'23Prelude.Eq\'23Prelude.Int'(_G744783,50),_G746652,_G745580,_G746637),'blocked_blocked_account.client._\'23caseor0_1_Prelude.True_ComplexCase'(_G746652,_G744783,_G742532,_G745577,_G746637,_G745583).

'blocked_blocked_account.client._\'23caseor0_1_Prelude.True_ComplexCase'(_G746940,_G746941,_G746942,_G746943,_G746944,_G746945):-freeze(_G746944,freeze(_G746940,'blocked_blocked_blocked_account.client._\'23caseor0_1_Prelude.True_ComplexCase'(_G746940,_G746941,_G746942,_G746943,_G746944,_G746945))).
'blocked_blocked_blocked_account.client._\'23caseor0_1_Prelude.True_ComplexCase'('Prelude.True',_G744783,_G742532,_G747116,_G747119,_G747122):-hnf('Prelude.=:='(_G742532,[]),_G747116,_G747119,_G747122).
'blocked_blocked_blocked_account.client._\'23caseor0_1_Prelude.True_ComplexCase'('Prelude.False',_G744783,_G742532,_G748641,_G748644,_G748647):-!,hnf('Prelude.apply'('Prelude.apply'('Prelude._impl\'23\'3E\'23Prelude.Ord\'23Prelude.Int',_G744783),50),_G750325,_G748644,_G750310),'blocked_blocked_blocked_account.client._\'23caseor0_1_Prelude.True_ComplexCase_Prelude.False_ComplexCase'(_G750325,_G744783,_G742532,_G748641,_G750310,_G748647).

'blocked_blocked_blocked_account.client._\'23caseor0_1_Prelude.True_ComplexCase_Prelude.False_ComplexCase'(_G750718,_G750719,_G750720,_G750721,_G750722,_G750723):-freeze(_G750722,freeze(_G750718,'blocked_blocked_blocked_blocked_account.client._\'23caseor0_1_Prelude.True_ComplexCase_Prelude.False_ComplexCase'(_G750718,_G750719,_G750720,_G750721,_G750722,_G750723))).
'blocked_blocked_blocked_blocked_account.client._\'23caseor0_1_Prelude.True_ComplexCase_Prelude.False_ComplexCase'('Prelude.True',_G744783,_G742532,_G750894,_G750897,_G750900):-hnf('account.client'('account.sendMsg'('account.Withdraw'(30),_G742532)),_G750894,_G750897,_G750900).
'blocked_blocked_blocked_blocked_account.client._\'23caseor0_1_Prelude.True_ComplexCase_Prelude.False_ComplexCase'('Prelude.False',_G744783,_G742532,_G751794,_G751797,_G751800):-!,hnf('account.client'('account.sendMsg'('account.Deposit'(70),_G742532)),_G751794,_G751797,_G751800).
'blocked_blocked_blocked_blocked_account.client._\'23caseor0_1_Prelude.True_ComplexCase_Prelude.False_ComplexCase'('FAIL'(_G752568),_G744783,_G742532,'FAIL'(_G752568),_G752575,_G752575).
'blocked_blocked_blocked_account.client._\'23caseor0_1_Prelude.True_ComplexCase'('FAIL'(_G752606),_G744783,_G742532,'FAIL'(_G752606),_G752613,_G752613).
'blocked_blocked_account.client._\'23caseor0_1'('Prelude.False',_G742523,_G742532,_G752776,_G752779,_G752782):-!,hnf('Prelude.failure'('account.client._\'23caseor0',['Prelude.False']),_G752776,_G752779,_G752782).
'blocked_blocked_account.client._\'23caseor0_1'('FAIL'(_G753392),_G742523,_G742532,'FAIL'(_G753392),_G753399,_G753399).

:-costCenters(['']).




%%%%% Number of shared variables: 11

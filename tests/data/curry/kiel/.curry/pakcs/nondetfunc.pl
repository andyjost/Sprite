%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(nondetfunc).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('nondetfunc.choose',choose,2,'nondetfunc.choose',nofix,'FuncType'(_G674342,'FuncType'(_G674342,_G674342))).
functiontype('nondetfunc.insert',insert,2,'nondetfunc.insert',nofix,'FuncType'(_G679948,'FuncType'('TCons'([],[_G679948]),'TCons'([],[_G679948])))).
functiontype('nondetfunc.permut',permut,1,'nondetfunc.permut',nofix,'FuncType'('TCons'([],[_G685572]),'TCons'([],[_G685572]))).
functiontype('nondetfunc.sort',sort,2,'nondetfunc.sort',nofix,'FuncType'('TCons'('Prelude._Dict\'23Ord',[_G691241]),'FuncType'('TCons'([],[_G691241]),'TCons'([],[_G691241])))).
functiontype('nondetfunc.rId',rId,2,'nondetfunc.rId',nofix,'FuncType'('FuncType'(_G696853,'TCons'('Prelude.Bool',[])),'FuncType'(_G696853,_G696853))).
functiontype('nondetfunc.wheresort',wheresort,2,'nondetfunc.wheresort',nofix,'FuncType'('TCons'('Prelude._Dict\'23Ord',[_G702573]),'FuncType'('TCons'([],[_G702573]),'TCons'([],[_G702573])))).
functiontype('nondetfunc.strictsort',strictsort,2,'nondetfunc.strictsort',nofix,'FuncType'('TCons'('Prelude._Dict\'23Ord',[_G708269]),'FuncType'('TCons'([],[_G708269]),'TCons'([],[_G708269])))).
functiontype('nondetfunc.sorted',sorted,2,'nondetfunc.sorted',nofix,'FuncType'('TCons'('Prelude._Dict\'23Ord',[_G713953]),'FuncType'('TCons'([],[_G713953]),'TCons'('Prelude.Bool',[])))).
functiontype('nondetfunc.goal1',goal1,0,'nondetfunc.goal1',nofix,'TCons'([],['TCons'('Prelude.Int',[])])).
functiontype('nondetfunc.goal2',goal2,0,'nondetfunc.goal2',nofix,'TCons'([],['TCons'('Prelude.Int',[])])).
functiontype('nondetfunc.goal3',goal3,0,'nondetfunc.goal3',nofix,'TCons'([],['TCons'('Prelude.Int',[])])).
functiontype('nondetfunc.coin',coin,0,'nondetfunc.coin',nofix,'TCons'('nondetfunc.Nat',[])).
functiontype('nondetfunc.add',add,2,'nondetfunc.add',nofix,'FuncType'('TCons'('nondetfunc.Nat',[]),'FuncType'('TCons'('nondetfunc.Nat',[]),'TCons'('nondetfunc.Nat',[])))).
functiontype('nondetfunc.double',double,1,'nondetfunc.double',nofix,'FuncType'('TCons'('nondetfunc.Nat',[]),'TCons'('nondetfunc.Nat',[]))).
functiontype('nondetfunc.goal4',goal4,0,'nondetfunc.goal4',nofix,'TCons'('nondetfunc.Nat',[])).
functiontype('nondetfunc.wheresort._\'23caseor0','nondetfunc.wheresort._#caseor0',2,'nondetfunc.wheresort._\'23caseor0',nofix,'FuncType'('TCons'('Prelude.Bool',[]),'FuncType'(_G759272,_G759272))).
functiontype('nondetfunc.strictsort._\'23caseor0','nondetfunc.strictsort._#caseor0',2,'nondetfunc.strictsort._\'23caseor0',nofix,'FuncType'('TCons'('Prelude.Bool',[]),'FuncType'(_G764932,_G764932))).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('nondetfunc.o',o,0,o,0,'TCons'('nondetfunc.Nat',[]),['nondetfunc.s'/1]).
constructortype('nondetfunc.s',s,1,s,1,'FuncType'('TCons'('nondetfunc.Nat',[]),'TCons'('nondetfunc.Nat',[])),['nondetfunc.o'/0]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'nondetfunc.choose'(_G773627,_G773628,_G773629,_G773630,_G773631):-freeze(_G773630,'blocked_nondetfunc.choose'(_G773627,_G773628,_G773629,_G773630,_G773631)).
'blocked_nondetfunc.choose'(_G773670,_G773679,_G773715,_G773718,_G773721):-hnf(_G773670,_G773715,_G773718,_G773721).
'blocked_nondetfunc.choose'(_G773670,_G773679,_G773902,_G773905,_G773908):-hnf(_G773679,_G773902,_G773905,_G773908).

'nondetfunc.insert'(_G774452,_G774453,_G774454,_G774455,_G774456):-freeze(_G774455,'blocked_nondetfunc.insert'(_G774452,_G774453,_G774454,_G774455,_G774456)).
'blocked_nondetfunc.insert'(_G774495,_G774504,_G775153,_G775156,_G775159):-hnf(_G774504,_G775657,_G775156,_G775645),'blocked_nondetfunc.insert_2'(_G775657,_G774495,_G775153,_G775645,_G775159).

'blocked_nondetfunc.insert_2'(_G775809,_G775810,_G775811,_G775812,_G775813):-freeze(_G775812,'blocked_blocked_nondetfunc.insert_2'(_G775809,_G775810,_G775811,_G775812,_G775813)).
'blocked_blocked_nondetfunc.insert_2'([],_G774495,[_G774495],_G775914,_G775914).
'blocked_blocked_nondetfunc.insert_2'([_G774677|_G774686],_G774495,_G776259,_G776262,_G776265):-!,makeShare(_G774495,_G776359),makeShare(_G774677,_G776369),makeShare(_G774686,_G776379),hnf('nondetfunc.choose'([_G776359,_G776369|_G776379],[_G776369|'nondetfunc.insert'(_G776359,_G776379)]),_G776259,_G776262,_G776265).
'blocked_blocked_nondetfunc.insert_2'('FAIL'(_G777451),_G774495,'FAIL'(_G777451),_G777458,_G777458):-nonvar(_G777451).

'nondetfunc.permut'(_G777847,_G777848,_G777849,_G777850):-freeze(_G777849,'blocked_nondetfunc.permut'(_G777847,_G777848,_G777849,_G777850)).
'blocked_nondetfunc.permut'(_G777885,_G778206,_G778209,_G778212):-hnf(_G777885,_G778700,_G778209,_G778691),'blocked_nondetfunc.permut_1'(_G778700,_G778206,_G778691,_G778212).

'blocked_nondetfunc.permut_1'(_G778851,_G778852,_G778853,_G778854):-freeze(_G778853,'blocked_blocked_nondetfunc.permut_1'(_G778851,_G778852,_G778853,_G778854)).
'blocked_blocked_nondetfunc.permut_1'([],[],_G778951,_G778951).
'blocked_blocked_nondetfunc.permut_1'([_G777985|_G777994],_G779170,_G779173,_G779176):-!,hnf('nondetfunc.insert'(_G777985,'nondetfunc.permut'(_G777994)),_G779170,_G779173,_G779176).
'blocked_blocked_nondetfunc.permut_1'('FAIL'(_G779642),'FAIL'(_G779642),_G779649,_G779649):-nonvar(_G779642).

'nondetfunc.sort'(_G779998,_G779999,_G780000,_G780001,_G780002):-freeze(_G780001,'blocked_nondetfunc.sort'(_G779998,_G779999,_G780000,_G780001,_G780002)).
'blocked_nondetfunc.sort'(_G780041,_G780050,_G780210,_G780213,_G780216):-hnf('nondetfunc.rId'(partcall(1,'nondetfunc.sorted',[_G780041]),'nondetfunc.permut'(_G780050)),_G780210,_G780213,_G780216).

'nondetfunc.rId'(_G781039,_G781040,_G781041,_G781042,_G781043):-freeze(_G781042,'blocked_nondetfunc.rId'(_G781039,_G781040,_G781041,_G781042,_G781043)).
'blocked_nondetfunc.rId'(_G781082,_G781091,_G781943,_G781946,_G781949):-makeShare(_G781091,_G781469),hnf('Prelude.apply'(_G781082,_G781469),_G782423,_G781946,_G782408),'blocked_nondetfunc.rId_ComplexCase'(_G782423,_G781082,_G781469,_G781943,_G782408,_G781949).

'blocked_nondetfunc.rId_ComplexCase'(_G782606,_G782607,_G782608,_G782609,_G782610,_G782611):-freeze(_G782610,freeze(_G782606,'blocked_blocked_nondetfunc.rId_ComplexCase'(_G782606,_G782607,_G782608,_G782609,_G782610,_G782611))).
'blocked_blocked_nondetfunc.rId_ComplexCase'('Prelude.True',_G781082,_G781469,_G782782,_G782785,_G782788):-hnf(_G781469,_G782782,_G782785,_G782788).
'blocked_blocked_nondetfunc.rId_ComplexCase'('Prelude.False',_G781082,_G781469,_G783159,_G783162,_G783165):-!,hnf('Prelude.failure'('nondetfunc.rId',['Prelude.False']),_G783159,_G783162,_G783165).
'blocked_blocked_nondetfunc.rId_ComplexCase'('FAIL'(_G783733),_G781082,_G781469,'FAIL'(_G783733),_G783740,_G783740).

'nondetfunc.wheresort'(_G784185,_G784186,_G784187,_G784188,_G784189):-freeze(_G784188,'blocked_nondetfunc.wheresort'(_G784185,_G784186,_G784187,_G784188,_G784189)).
'blocked_nondetfunc.wheresort'(_G784228,_G784237,_G784591,_G784594,_G784597):-makeShare(_G784249,_G784667),hnf('Prelude.cond'('Prelude.letrec'(_G784667,'nondetfunc.permut'(_G784237)),'nondetfunc.wheresort._\'23caseor0'('nondetfunc.sorted'(_G784228,_G784667),_G784667)),_G784591,_G784594,_G784597).

'nondetfunc.strictsort'(_G786086,_G786087,_G786088,_G786089,_G786090):-freeze(_G786089,'blocked_nondetfunc.strictsort'(_G786086,_G786087,_G786088,_G786089,_G786090)).
'blocked_nondetfunc.strictsort'(_G786129,_G786138,_G786572,_G786575,_G786578):-makeShare(_G786150,_G786648),hnf('nondetfunc.strictsort._\'23caseor0'('Prelude.&'('Prelude.=:='(_G786648,'nondetfunc.permut'(_G786138)),'Prelude.=:='('nondetfunc.sorted'(_G786129,_G786648),'Prelude.True')),_G786648),_G786572,_G786575,_G786578).

'nondetfunc.sorted'(_G788251,_G788252,_G788253,_G788254,_G788255):-freeze(_G788254,'blocked_nondetfunc.sorted'(_G788251,_G788252,_G788253,_G788254,_G788255)).
'blocked_nondetfunc.sorted'(_G788294,_G788303,_G789218,_G789221,_G789224):-hnf(_G788303,_G789722,_G789221,_G789710),'blocked_nondetfunc.sorted_2'(_G789722,_G788294,_G789218,_G789710,_G789224).

'blocked_nondetfunc.sorted_2'(_G789874,_G789875,_G789876,_G789877,_G789878):-freeze(_G789877,'blocked_blocked_nondetfunc.sorted_2'(_G789874,_G789875,_G789876,_G789877,_G789878)).
'blocked_blocked_nondetfunc.sorted_2'([],_G788294,'Prelude.True',_G789979,_G789979).
'blocked_blocked_nondetfunc.sorted_2'([_G788403|_G788412],_G788294,_G790385,_G790388,_G790391):-!,hnf(_G788412,_G791135,_G790388,_G791120),'blocked_blocked_nondetfunc.sorted_2_[|]_2'(_G791135,_G788403,_G788294,_G790385,_G791120,_G790391).

'blocked_blocked_nondetfunc.sorted_2_[|]_2'(_G791339,_G791340,_G791341,_G791342,_G791343,_G791344):-freeze(_G791343,'blocked_blocked_blocked_nondetfunc.sorted_2_[|]_2'(_G791339,_G791340,_G791341,_G791342,_G791343,_G791344)).
'blocked_blocked_blocked_nondetfunc.sorted_2_[|]_2'([],_G788403,_G788294,'Prelude.True',_G791449,_G791449).
'blocked_blocked_blocked_nondetfunc.sorted_2_[|]_2'([_G788518|_G788527],_G788403,_G788294,_G792898,_G792901,_G792904):-!,makeShare(_G788294,_G791917),makeShare(_G788518,_G791927),hnf('Prelude.apply'('Prelude.apply'('Prelude.<='(_G791917),_G788403),_G791927),_G793934,_G792901,_G793913),'blocked_blocked_blocked_nondetfunc.sorted_2_[|]_2_[|]_ComplexCase'(_G793934,_G791927,_G788527,_G788403,_G791917,_G792898,_G793913,_G792904).

'blocked_blocked_blocked_nondetfunc.sorted_2_[|]_2_[|]_ComplexCase'(_G794227,_G794228,_G794229,_G794230,_G794231,_G794232,_G794233,_G794234):-freeze(_G794233,freeze(_G794227,'blocked_blocked_blocked_blocked_nondetfunc.sorted_2_[|]_2_[|]_ComplexCase'(_G794227,_G794228,_G794229,_G794230,_G794231,_G794232,_G794233,_G794234))).
'blocked_blocked_blocked_blocked_nondetfunc.sorted_2_[|]_2_[|]_ComplexCase'('Prelude.True',_G791927,_G788527,_G788403,_G791917,_G794413,_G794416,_G794419):-hnf('nondetfunc.sorted'(_G791917,[_G791927|_G788527]),_G794413,_G794416,_G794419).
'blocked_blocked_blocked_blocked_nondetfunc.sorted_2_[|]_2_[|]_ComplexCase'('Prelude.False',_G791927,_G788527,_G788403,_G791917,_G795204,_G795207,_G795210):-!,hnf('Prelude.failure'('nondetfunc.sorted',['Prelude.False']),_G795204,_G795207,_G795210).
'blocked_blocked_blocked_blocked_nondetfunc.sorted_2_[|]_2_[|]_ComplexCase'('FAIL'(_G795950),_G791927,_G788527,_G788403,_G791917,'FAIL'(_G795950),_G795957,_G795957).
'blocked_blocked_blocked_nondetfunc.sorted_2_[|]_2'('FAIL'(_G795996),_G788403,_G788294,'FAIL'(_G795996),_G796003,_G796003):-nonvar(_G795996).
'blocked_blocked_nondetfunc.sorted_2'('FAIL'(_G796036),_G788294,'FAIL'(_G796036),_G796043,_G796043):-nonvar(_G796036).

'nondetfunc.goal1'(_G796414,_G796415,_G796416):-freeze(_G796415,'blocked_nondetfunc.goal1'(_G796414,_G796415,_G796416)).
'blocked_nondetfunc.goal1'(_G796824,_G796827,_G796830):-hnf('nondetfunc.sort'('Prelude._inst\'23Prelude.Ord\'23Prelude.Int',[4,3,2,1]),_G796824,_G796827,_G796830).

'nondetfunc.goal2'(_G797893,_G797894,_G797895):-freeze(_G797894,'blocked_nondetfunc.goal2'(_G797893,_G797894,_G797895)).
'blocked_nondetfunc.goal2'(_G798303,_G798306,_G798309):-hnf('nondetfunc.wheresort'('Prelude._inst\'23Prelude.Ord\'23Prelude.Int',[4,3,2,1]),_G798303,_G798306,_G798309).

'nondetfunc.goal3'(_G799387,_G799388,_G799389):-freeze(_G799388,'blocked_nondetfunc.goal3'(_G799387,_G799388,_G799389)).
'blocked_nondetfunc.goal3'(_G799797,_G799800,_G799803):-hnf('nondetfunc.strictsort'('Prelude._inst\'23Prelude.Ord\'23Prelude.Int',[4,3,2,1]),_G799797,_G799800,_G799803).

'nondetfunc.coin'(_G800866,_G800867,_G800868):-freeze(_G800867,'blocked_nondetfunc.coin'(_G800866,_G800867,_G800868)).
'blocked_nondetfunc.coin'('nondetfunc.o',_G800983,_G800983).
'blocked_nondetfunc.coin'('nondetfunc.s'('nondetfunc.o'),_G801126,_G801126).

'nondetfunc.add'(_G801659,_G801660,_G801661,_G801662,_G801663):-freeze(_G801662,'blocked_nondetfunc.add'(_G801659,_G801660,_G801661,_G801662,_G801663)).
'blocked_nondetfunc.add'(_G801702,_G801711,_G802004,_G802007,_G802010):-hnf(_G801702,_G802454,_G802007,_G802442),'blocked_nondetfunc.add_1'(_G802454,_G801711,_G802004,_G802442,_G802010).

'blocked_nondetfunc.add_1'(_G802597,_G802598,_G802599,_G802600,_G802601):-freeze(_G802600,'blocked_blocked_nondetfunc.add_1'(_G802597,_G802598,_G802599,_G802600,_G802601)).
'blocked_blocked_nondetfunc.add_1'('nondetfunc.o',_G801711,_G802765,_G802768,_G802771):-hnf(_G801711,_G802765,_G802768,_G802771).
'blocked_blocked_nondetfunc.add_1'('nondetfunc.s'(_G801804),_G801711,'nondetfunc.s'('nondetfunc.add'(_G801804,_G801711)),_G803079,_G803079):-!.
'blocked_blocked_nondetfunc.add_1'('FAIL'(_G803508),_G801711,'FAIL'(_G803508),_G803515,_G803515):-nonvar(_G803508).

'nondetfunc.double'(_G803904,_G803905,_G803906,_G803907):-freeze(_G803906,'blocked_nondetfunc.double'(_G803904,_G803905,_G803906,_G803907)).
'blocked_nondetfunc.double'(_G803942,_G804022,_G804025,_G804028):-makeShare(_G803942,_G804058),hnf('nondetfunc.add'(_G804058,_G804058),_G804022,_G804025,_G804028).

'nondetfunc.goal4'(_G804765,_G804766,_G804767):-freeze(_G804766,'blocked_nondetfunc.goal4'(_G804765,_G804766,_G804767)).
'blocked_nondetfunc.goal4'(_G804843,_G804846,_G804849):-hnf('nondetfunc.double'('nondetfunc.coin'),_G804843,_G804846,_G804849).

'nondetfunc.wheresort._\'23caseor0'(_G805714,_G805715,_G805716,_G805717,_G805718):-freeze(_G805717,'blocked_nondetfunc.wheresort._\'23caseor0'(_G805714,_G805715,_G805716,_G805717,_G805718)).
'blocked_nondetfunc.wheresort._\'23caseor0'(_G805757,_G805766,_G806155,_G806158,_G806161):-hnf(_G805757,_G806929,_G806158,_G806917),'blocked_nondetfunc.wheresort._\'23caseor0_1'(_G806929,_G805766,_G806155,_G806917,_G806161).

'blocked_nondetfunc.wheresort._\'23caseor0_1'(_G807129,_G807130,_G807131,_G807132,_G807133):-freeze(_G807132,freeze(_G807129,'blocked_blocked_nondetfunc.wheresort._\'23caseor0_1'(_G807129,_G807130,_G807131,_G807132,_G807133))).
'blocked_blocked_nondetfunc.wheresort._\'23caseor0_1'('Prelude.True',_G805766,_G807300,_G807303,_G807306):-hnf(_G805766,_G807300,_G807303,_G807306).
'blocked_blocked_nondetfunc.wheresort._\'23caseor0_1'('Prelude.False',_G805766,_G807666,_G807669,_G807672):-!,hnf('Prelude.failure'('nondetfunc.wheresort._\'23caseor0',['Prelude.False']),_G807666,_G807669,_G807672).
'blocked_blocked_nondetfunc.wheresort._\'23caseor0_1'('FAIL'(_G808283),_G805766,'FAIL'(_G808283),_G808290,_G808290).

'nondetfunc.strictsort._\'23caseor0'(_G808941,_G808942,_G808943,_G808944,_G808945):-freeze(_G808944,'blocked_nondetfunc.strictsort._\'23caseor0'(_G808941,_G808942,_G808943,_G808944,_G808945)).
'blocked_nondetfunc.strictsort._\'23caseor0'(_G808984,_G808993,_G809385,_G809388,_G809391):-hnf(_G808984,_G810177,_G809388,_G810165),'blocked_nondetfunc.strictsort._\'23caseor0_1'(_G810177,_G808993,_G809385,_G810165,_G809391).

'blocked_nondetfunc.strictsort._\'23caseor0_1'(_G810380,_G810381,_G810382,_G810383,_G810384):-freeze(_G810383,freeze(_G810380,'blocked_blocked_nondetfunc.strictsort._\'23caseor0_1'(_G810380,_G810381,_G810382,_G810383,_G810384))).
'blocked_blocked_nondetfunc.strictsort._\'23caseor0_1'('Prelude.True',_G808993,_G810551,_G810554,_G810557):-hnf(_G808993,_G810551,_G810554,_G810557).
'blocked_blocked_nondetfunc.strictsort._\'23caseor0_1'('Prelude.False',_G808993,_G810920,_G810923,_G810926):-!,hnf('Prelude.failure'('nondetfunc.strictsort._\'23caseor0',['Prelude.False']),_G810920,_G810923,_G810926).
'blocked_blocked_nondetfunc.strictsort._\'23caseor0_1'('FAIL'(_G811543),_G808993,'FAIL'(_G811543),_G811550,_G811550).

:-costCenters(['']).




%%%%% Number of shared variables: 9

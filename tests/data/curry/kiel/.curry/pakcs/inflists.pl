%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(inflists).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('inflists.from',from,2,'inflists.from',nofix,'FuncType'('TCons'('Prelude._Dict\'23Num',[_G698851]),'FuncType'(_G698851,'TCons'([],[_G698851])))).
functiontype('inflists.fibs',fibs,1,'inflists.fibs',nofix,'FuncType'('TCons'('Prelude._Dict\'23Num',[_G704451]),'TCons'([],[_G704451]))).
functiontype('inflists.fibgen',fibgen,3,'inflists.fibgen',nofix,'FuncType'('TCons'('Prelude._Dict\'23Num',[_G710054]),'FuncType'(_G710054,'FuncType'(_G710054,'TCons'([],[_G710054]))))).
functiontype('inflists.goal1',goal1,0,'inflists.goal1',nofix,'TCons'([],['TCons'('Prelude.Int',[])])).
functiontype('inflists.primes',primes,1,'inflists.primes',nofix,'FuncType'('TCons'('Prelude._Dict\'23Integral',[_G721239]),'TCons'([],[_G721239]))).
functiontype('inflists.sieve',sieve,2,'inflists.sieve',nofix,'FuncType'('TCons'('Prelude._Dict\'23Integral',[_G726854]),'FuncType'('TCons'([],[_G726854]),'TCons'([],[_G726854])))).
functiontype('inflists.sieve._\'23lambda1','inflists.sieve._#lambda1',3,'inflists.sieve._\'23lambda1',nofix,'FuncType'(_G732433,'FuncType'('TCons'('Prelude._Dict\'23Integral',[_G732433]),'FuncType'(_G732433,'TCons'('Prelude.Bool',[]))))).
functiontype('inflists.goal2',goal2,0,'inflists.goal2',nofix,'TCons'([],['TCons'('Prelude.Int',[])])).
functiontype('inflists.ordMerge',ordMerge,3,'inflists.ordMerge',nofix,'FuncType'('TCons'('Prelude._Dict\'23Ord',[_G743696]),'FuncType'('TCons'([],[_G743696]),'FuncType'('TCons'([],[_G743696]),'TCons'([],[_G743696]))))).
functiontype('inflists.hamming',hamming,2,'inflists.hamming',nofix,'FuncType'('TCons'('Prelude._Dict\'23Num',[_G749320]),'FuncType'('TCons'('Prelude._Dict\'23Ord',[_G749320]),'TCons'([],[_G749320])))).
functiontype('inflists.goal3',goal3,0,'inflists.goal3',nofix,'TCons'([],['TCons'('Prelude.Int',[])])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'inflists.from'(_G762892,_G762893,_G762894,_G762895,_G762896):-freeze(_G762895,'blocked_inflists.from'(_G762892,_G762893,_G762894,_G762895,_G762896)).
'blocked_inflists.from'(_G762935,_G762944,[_G763472|'inflists.from'(_G763482,'Prelude.apply'('Prelude.apply'('Prelude.+'(_G763482),_G763472),'Prelude.apply'('Prelude.fromInt'(_G763482),1)))],_G763399,_G763402):-makeShare(_G762944,_G763472),makeShare(_G762935,_G763482),_G763399=_G763402.

'inflists.fibs'(_G764897,_G764898,_G764899,_G764900):-freeze(_G764899,'blocked_inflists.fibs'(_G764897,_G764898,_G764899,_G764900)).
'blocked_inflists.fibs'(_G764935,_G765274,_G765277,_G765280):-makeShare(_G764935,_G765316),hnf('inflists.fibgen'(_G765316,'Prelude.apply'('Prelude.fromInt'(_G765316),1),'Prelude.apply'('Prelude.fromInt'(_G765316),1)),_G765274,_G765277,_G765280).

'inflists.fibgen'(_G766467,_G766468,_G766469,_G766470,_G766471,_G766472):-freeze(_G766471,'blocked_inflists.fibgen'(_G766467,_G766468,_G766469,_G766470,_G766471,_G766472)).
'blocked_inflists.fibgen'(_G766515,_G766524,_G766533,[_G767009|'inflists.fibgen'(_G767019,_G767029,'Prelude.apply'('Prelude.apply'('Prelude.+'(_G767019),_G767009),_G767029))],_G766908,_G766911):-makeShare(_G766524,_G767009),makeShare(_G766515,_G767019),makeShare(_G766533,_G767029),_G766908=_G766911.

'inflists.goal1'(_G768428,_G768429,_G768430):-freeze(_G768429,'blocked_inflists.goal1'(_G768428,_G768429,_G768430)).
'blocked_inflists.goal1'(_G768579,_G768582,_G768585):-hnf('Prelude.take'(10,'inflists.fibs'('Prelude._inst\'23Prelude.Num\'23Prelude.Int')),_G768579,_G768582,_G768585).

'inflists.primes'(_G769352,_G769353,_G769354,_G769355):-freeze(_G769354,'blocked_inflists.primes'(_G769352,_G769353,_G769354,_G769355)).
'blocked_inflists.primes'(_G769390,_G769816,_G769819,_G769822):-makeShare(_G769390,_G769858),hnf('inflists.sieve'(_G769858,'inflists.from'('Prelude._super\'23Prelude.Real\'23Prelude.Num'('Prelude._super\'23Prelude.Integral\'23Prelude.Real'(_G769858)),'Prelude.apply'('Prelude.fromInt'('Prelude._super\'23Prelude.Real\'23Prelude.Num'('Prelude._super\'23Prelude.Integral\'23Prelude.Real'(_G769858))),2))),_G769816,_G769819,_G769822).

'inflists.sieve'(_G771614,_G771615,_G771616,_G771617,_G771618):-freeze(_G771617,'blocked_inflists.sieve'(_G771614,_G771615,_G771616,_G771617,_G771618)).
'blocked_inflists.sieve'(_G771657,_G771666,_G772320,_G772323,_G772326):-hnf(_G771666,_G772770,_G772323,_G772758),'blocked_inflists.sieve_2'(_G772770,_G771657,_G772320,_G772758,_G772326).

'blocked_inflists.sieve_2'(_G772913,_G772914,_G772915,_G772916,_G772917):-freeze(_G772916,'blocked_blocked_inflists.sieve_2'(_G772913,_G772914,_G772915,_G772916,_G772917)).
'blocked_blocked_inflists.sieve_2'([_G771720|_G771729],_G771657,[_G773154|'inflists.sieve'(_G773164,'Prelude.filter'(partcall(1,'inflists.sieve._\'23lambda1',[_G773164,_G773154]),_G771729))],_G773075,_G773078):-!,makeShare(_G771720,_G773154),makeShare(_G771657,_G773164),_G773075=_G773078.
'blocked_blocked_inflists.sieve_2'([],_G771657,_G774161,_G774164,_G774167):-!,hnf('Prelude.failure'('inflists.sieve',[[]]),_G774161,_G774164,_G774167).
'blocked_blocked_inflists.sieve_2'('FAIL'(_G774631),_G771657,'FAIL'(_G774631),_G774638,_G774638).

'inflists.sieve._\'23lambda1'(_G775163,_G775164,_G775165,_G775166,_G775167,_G775168):-freeze(_G775167,'blocked_inflists.sieve._\'23lambda1'(_G775163,_G775164,_G775165,_G775166,_G775167,_G775168)).
'blocked_inflists.sieve._\'23lambda1'(_G775211,_G775220,_G775229,_G775881,_G775884,_G775887):-makeShare(_G775220,_G775961),hnf('Prelude.apply'('Prelude.apply'('Prelude.>'('Prelude._super\'23Prelude.Real\'23Prelude.Ord'('Prelude._super\'23Prelude.Integral\'23Prelude.Real'(_G775961))),'Prelude.apply'('Prelude.apply'('Prelude.mod'(_G775961),_G775229),_G775211)),'Prelude.apply'('Prelude.fromInt'('Prelude._super\'23Prelude.Real\'23Prelude.Num'('Prelude._super\'23Prelude.Integral\'23Prelude.Real'(_G775961))),0)),_G775881,_G775884,_G775887).

'inflists.goal2'(_G778233,_G778234,_G778235):-freeze(_G778234,'blocked_inflists.goal2'(_G778233,_G778234,_G778235)).
'blocked_inflists.goal2'(_G778384,_G778387,_G778390):-hnf('Prelude.take'(5,'inflists.primes'('Prelude._inst\'23Prelude.Integral\'23Prelude.Int')),_G778384,_G778387,_G778390).

'inflists.ordMerge'(_G779214,_G779215,_G779216,_G779217,_G779218,_G779219):-freeze(_G779218,'blocked_inflists.ordMerge'(_G779214,_G779215,_G779216,_G779217,_G779218,_G779219)).
'blocked_inflists.ordMerge'(_G779262,_G779271,_G779280,_G781638,_G781641,_G781644):-hnf(_G779271,_G782152,_G781641,_G782137),'blocked_inflists.ordMerge_2'(_G782152,_G779262,_G779280,_G781638,_G782137,_G781644).

'blocked_inflists.ordMerge_2'(_G782305,_G782306,_G782307,_G782308,_G782309,_G782310):-freeze(_G782309,'blocked_blocked_inflists.ordMerge_2'(_G782305,_G782306,_G782307,_G782308,_G782309,_G782310)).
'blocked_blocked_inflists.ordMerge_2'([_G779334|_G779343],_G779262,_G779280,_G782591,_G782594,_G782597):-!,hnf(_G779280,_G783351,_G782594,_G783333),'blocked_blocked_inflists.ordMerge_2_[|]_4'(_G783351,_G779334,_G779343,_G779262,_G782591,_G783333,_G782597).

'blocked_blocked_inflists.ordMerge_2_[|]_4'(_G783556,_G783557,_G783558,_G783559,_G783560,_G783561,_G783562):-freeze(_G783561,'blocked_blocked_blocked_inflists.ordMerge_2_[|]_4'(_G783556,_G783557,_G783558,_G783559,_G783560,_G783561,_G783562)).
'blocked_blocked_blocked_inflists.ordMerge_2_[|]_4'([_G779403|_G779412],_G779334,_G779343,_G779262,_G785706,_G785709,_G785712):-!,makeShare(_G779262,_G784102),makeShare(_G779334,_G784112),makeShare(_G779403,_G784122),hnf('Prelude.apply'('Prelude.apply'('Prelude.=='('Prelude._super\'23Prelude.Ord\'23Prelude.Eq'(_G784102)),_G784112),_G784122),_G786749,_G785709,_G786725),'blocked_blocked_blocked_inflists.ordMerge_2_[|]_4_[|]_ComplexCase'(_G786749,_G784122,_G779412,_G784112,_G779343,_G784102,_G785706,_G786725,_G785712).

'blocked_blocked_blocked_inflists.ordMerge_2_[|]_4_[|]_ComplexCase'(_G787049,_G787050,_G787051,_G787052,_G787053,_G787054,_G787055,_G787056,_G787057):-freeze(_G787056,freeze(_G787049,'blocked_blocked_blocked_blocked_inflists.ordMerge_2_[|]_4_[|]_ComplexCase'(_G787049,_G787050,_G787051,_G787052,_G787053,_G787054,_G787055,_G787056,_G787057))).
'blocked_blocked_blocked_blocked_inflists.ordMerge_2_[|]_4_[|]_ComplexCase'('Prelude.True',_G784122,_G779412,_G784112,_G779343,_G784102,[_G784112|'inflists.ordMerge'(_G784102,_G779343,_G779412)],_G787243,_G787243).
'blocked_blocked_blocked_blocked_inflists.ordMerge_2_[|]_4_[|]_ComplexCase'('Prelude.False',_G784122,_G779412,_G784112,_G779343,_G784102,_G789735,_G789738,_G789741):-!,makeShare(_G784102,_G788388),makeShare(_G784112,_G788398),makeShare(_G784122,_G788408),hnf('Prelude.apply'('Prelude.apply'('Prelude.<'(_G788388),_G788398),_G788408),_G791368,_G789738,_G791344),'blocked_blocked_blocked_blocked_inflists.ordMerge_2_[|]_4_[|]_ComplexCase_Prelude.False_ComplexCase'(_G791368,_G788408,_G779412,_G788398,_G779343,_G788388,_G789735,_G791344,_G789741).

'blocked_blocked_blocked_blocked_inflists.ordMerge_2_[|]_4_[|]_ComplexCase_Prelude.False_ComplexCase'(_G791770,_G791771,_G791772,_G791773,_G791774,_G791775,_G791776,_G791777,_G791778):-freeze(_G791777,freeze(_G791770,'blocked_blocked_blocked_blocked_blocked_inflists.ordMerge_2_[|]_4_[|]_ComplexCase_Prelude.False_ComplexCase'(_G791770,_G791771,_G791772,_G791773,_G791774,_G791775,_G791776,_G791777,_G791778))).
'blocked_blocked_blocked_blocked_blocked_inflists.ordMerge_2_[|]_4_[|]_ComplexCase_Prelude.False_ComplexCase'('Prelude.True',_G788408,_G779412,_G788398,_G779343,_G788388,[_G788398|'inflists.ordMerge'(_G788388,_G779343,[_G788408|_G779412])],_G791964,_G791964).
'blocked_blocked_blocked_blocked_blocked_inflists.ordMerge_2_[|]_4_[|]_ComplexCase_Prelude.False_ComplexCase'('Prelude.False',_G788408,_G779412,_G788398,_G779343,_G788388,_G794496,_G794499,_G794502):-!,makeShare(_G788388,_G793200),makeShare(_G788398,_G793210),makeShare(_G788408,_G793220),hnf('Prelude.apply'('Prelude.apply'('Prelude.>'(_G793200),_G793210),_G793220),_G796741,_G794499,_G796717),'blocked_blocked_blocked_blocked_blocked_inflists.ordMerge_2_[|]_4_[|]_ComplexCase_Prelude.False_ComplexCase_Prelude.False_ComplexCase'(_G796741,_G793220,_G779412,_G793210,_G779343,_G793200,_G794496,_G796717,_G794502).

'blocked_blocked_blocked_blocked_blocked_inflists.ordMerge_2_[|]_4_[|]_ComplexCase_Prelude.False_ComplexCase_Prelude.False_ComplexCase'(_G797245,_G797246,_G797247,_G797248,_G797249,_G797250,_G797251,_G797252,_G797253):-freeze(_G797252,freeze(_G797245,'blocked_blocked_blocked_blocked_blocked_blocked_inflists.ordMerge_2_[|]_4_[|]_ComplexCase_Prelude.False_ComplexCase_Prelude.False_ComplexCase'(_G797245,_G797246,_G797247,_G797248,_G797249,_G797250,_G797251,_G797252,_G797253))).
'blocked_blocked_blocked_blocked_blocked_blocked_inflists.ordMerge_2_[|]_4_[|]_ComplexCase_Prelude.False_ComplexCase_Prelude.False_ComplexCase'('Prelude.True',_G793220,_G779412,_G793210,_G779343,_G793200,[_G793220|'inflists.ordMerge'(_G793200,[_G793210|_G779343],_G779412)],_G797439,_G797439).
'blocked_blocked_blocked_blocked_blocked_blocked_inflists.ordMerge_2_[|]_4_[|]_ComplexCase_Prelude.False_ComplexCase_Prelude.False_ComplexCase'('Prelude.False',_G793220,_G779412,_G793210,_G779343,_G793200,_G798634,_G798637,_G798640):-!,hnf('Prelude.failure'('inflists.ordMerge',['Prelude.False']),_G798634,_G798637,_G798640).
'blocked_blocked_blocked_blocked_blocked_blocked_inflists.ordMerge_2_[|]_4_[|]_ComplexCase_Prelude.False_ComplexCase_Prelude.False_ComplexCase'('FAIL'(_G799619),_G793220,_G779412,_G793210,_G779343,_G793200,'FAIL'(_G799619),_G799626,_G799626).
'blocked_blocked_blocked_blocked_blocked_inflists.ordMerge_2_[|]_4_[|]_ComplexCase_Prelude.False_ComplexCase'('FAIL'(_G799669),_G788408,_G779412,_G788398,_G779343,_G788388,'FAIL'(_G799669),_G799676,_G799676).
'blocked_blocked_blocked_blocked_inflists.ordMerge_2_[|]_4_[|]_ComplexCase'('FAIL'(_G799719),_G784122,_G779412,_G784112,_G779343,_G784102,'FAIL'(_G799719),_G799726,_G799726).
'blocked_blocked_blocked_inflists.ordMerge_2_[|]_4'([],_G779334,_G779343,_G779262,_G799829,_G799832,_G799835):-!,hnf('Prelude.failure'('inflists.ordMerge',[[]]),_G799829,_G799832,_G799835).
'blocked_blocked_blocked_inflists.ordMerge_2_[|]_4'('FAIL'(_G800429),_G779334,_G779343,_G779262,'FAIL'(_G800429),_G800436,_G800436).
'blocked_blocked_inflists.ordMerge_2'([],_G779262,_G779280,_G800531,_G800534,_G800537):-!,hnf('Prelude.failure'('inflists.ordMerge',[[]]),_G800531,_G800534,_G800537).
'blocked_blocked_inflists.ordMerge_2'('FAIL'(_G801054),_G779262,_G779280,'FAIL'(_G801054),_G801061,_G801061).

'inflists.hamming'(_G801434,_G801435,_G801436,_G801437,_G801438):-freeze(_G801437,'blocked_inflists.hamming'(_G801434,_G801435,_G801436,_G801437,_G801438)).
'blocked_inflists.hamming'(_G801477,_G801486,['Prelude.apply'('Prelude.fromInt'(_G803155),1)|'inflists.ordMerge'(_G803165,'Prelude.map'(partcall(1,'Prelude.flip',['Prelude.apply'('Prelude.fromInt'(_G803155),2),'Prelude.*'(_G803155)]),'inflists.hamming'(_G803155,_G803165)),'inflists.ordMerge'(_G803165,'Prelude.map'(partcall(1,'Prelude.flip',['Prelude.apply'('Prelude.fromInt'(_G803155),3),'Prelude.*'(_G803155)]),'inflists.hamming'(_G803155,_G803165)),'Prelude.map'(partcall(1,'Prelude.flip',['Prelude.apply'('Prelude.fromInt'(_G803155),5),'Prelude.*'(_G803155)]),'inflists.hamming'(_G803155,_G803165))))],_G803010,_G803013):-makeShare(_G801477,_G803155),makeShare(_G801486,_G803165),_G803010=_G803013.

'inflists.goal3'(_G806550,_G806551,_G806552):-freeze(_G806551,'blocked_inflists.goal3'(_G806550,_G806551,_G806552)).
'blocked_inflists.goal3'(_G806741,_G806744,_G806747):-hnf('Prelude.take'(10,'inflists.hamming'('Prelude._inst\'23Prelude.Num\'23Prelude.Int','Prelude._inst\'23Prelude.Ord\'23Prelude.Int')),_G806741,_G806744,_G806747).

:-costCenters(['']).




%%%%% Number of shared variables: 21

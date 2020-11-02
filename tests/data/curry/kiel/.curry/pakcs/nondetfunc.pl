%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(nondetfunc).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('nondetfunc.choose',choose,2,'nondetfunc.choose',nofix,'FuncType'(_G1042308,'FuncType'(_G1042308,_G1042308))).
functiontype('nondetfunc.insert',insert,2,'nondetfunc.insert',nofix,'FuncType'(_G346431,'FuncType'('TCons'([],[_G346431]),'TCons'([],[_G346431])))).
functiontype('nondetfunc.permut',permut,1,'nondetfunc.permut',nofix,'FuncType'('TCons'([],[_G352022]),'TCons'([],[_G352022]))).
functiontype('nondetfunc.sort',sort,2,'nondetfunc.sort',nofix,'FuncType'('TCons'('Prelude._Dict\'23Ord',[_G357691]),'FuncType'('TCons'([],[_G357691]),'TCons'([],[_G357691])))).
functiontype('nondetfunc.rId',rId,2,'nondetfunc.rId',nofix,'FuncType'('FuncType'(_G363303,'TCons'('Prelude.Bool',[])),'FuncType'(_G363303,_G363303))).
functiontype('nondetfunc.wheresort',wheresort,2,'nondetfunc.wheresort',nofix,'FuncType'('TCons'('Prelude._Dict\'23Ord',[_G369023]),'FuncType'('TCons'([],[_G369023]),'TCons'([],[_G369023])))).
functiontype('nondetfunc.strictsort',strictsort,2,'nondetfunc.strictsort',nofix,'FuncType'('TCons'('Prelude._Dict\'23Ord',[_G374719]),'FuncType'('TCons'([],[_G374719]),'TCons'([],[_G374719])))).
functiontype('nondetfunc.sorted',sorted,2,'nondetfunc.sorted',nofix,'FuncType'('TCons'('Prelude._Dict\'23Ord',[_G380403]),'FuncType'('TCons'([],[_G380403]),'TCons'('Prelude.Bool',[])))).
functiontype('nondetfunc.goal1',goal1,2,'nondetfunc.goal1',nofix,'FuncType'('TCons'('Prelude._Dict\'23Num',[_G386117]),'FuncType'('TCons'('Prelude._Dict\'23Ord',[_G386117]),'TCons'([],[_G386117])))).
functiontype('nondetfunc.goal2',goal2,2,'nondetfunc.goal2',nofix,'FuncType'('TCons'('Prelude._Dict\'23Num',[_G391858]),'FuncType'('TCons'('Prelude._Dict\'23Ord',[_G391858]),'TCons'([],[_G391858])))).
functiontype('nondetfunc.goal3',goal3,2,'nondetfunc.goal3',nofix,'FuncType'('TCons'('Prelude._Dict\'23Num',[_G397599]),'FuncType'('TCons'('Prelude._Dict\'23Ord',[_G397599]),'TCons'([],[_G397599])))).
functiontype('nondetfunc.coin',coin,0,'nondetfunc.coin',nofix,'TCons'('nondetfunc.Nat',[])).
functiontype('nondetfunc.add',add,2,'nondetfunc.add',nofix,'FuncType'('TCons'('nondetfunc.Nat',[]),'FuncType'('TCons'('nondetfunc.Nat',[]),'TCons'('nondetfunc.Nat',[])))).
functiontype('nondetfunc.double',double,1,'nondetfunc.double',nofix,'FuncType'('TCons'('nondetfunc.Nat',[]),'TCons'('nondetfunc.Nat',[]))).
functiontype('nondetfunc.goal4',goal4,0,'nondetfunc.goal4',nofix,'TCons'('nondetfunc.Nat',[])).
functiontype('nondetfunc.wheresort._\'23caseor0','nondetfunc.wheresort._#caseor0',2,'nondetfunc.wheresort._\'23caseor0',nofix,'FuncType'('TCons'('Prelude.Bool',[]),'FuncType'(_G426046,_G426046))).
functiontype('nondetfunc.strictsort._\'23caseor0','nondetfunc.strictsort._#caseor0',2,'nondetfunc.strictsort._\'23caseor0',nofix,'FuncType'('TCons'('Prelude.Bool',[]),'FuncType'(_G431706,_G431706))).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('nondetfunc.o',o,0,o,0,'TCons'('nondetfunc.Nat',[]),['nondetfunc.s'/1]).
constructortype('nondetfunc.s',s,1,s,1,'FuncType'('TCons'('nondetfunc.Nat',[]),'TCons'('nondetfunc.Nat',[])),['nondetfunc.o'/0]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'nondetfunc.choose'(_G440401,_G440402,_G440403,_G440404,_G440405):-freeze(_G440404,'blocked_nondetfunc.choose'(_G440401,_G440402,_G440403,_G440404,_G440405)).
'blocked_nondetfunc.choose'(_G440444,_G440453,_G440489,_G440492,_G440495):-hnf(_G440444,_G440489,_G440492,_G440495).
'blocked_nondetfunc.choose'(_G440444,_G440453,_G440676,_G440679,_G440682):-hnf(_G440453,_G440676,_G440679,_G440682).

'nondetfunc.insert'(_G441226,_G441227,_G441228,_G441229,_G441230):-freeze(_G441229,'blocked_nondetfunc.insert'(_G441226,_G441227,_G441228,_G441229,_G441230)).
'blocked_nondetfunc.insert'(_G441269,_G441278,_G441927,_G441930,_G441933):-hnf(_G441278,_G442431,_G441930,_G442419),'blocked_nondetfunc.insert_2'(_G442431,_G441269,_G441927,_G442419,_G441933).

'blocked_nondetfunc.insert_2'(_G442583,_G442584,_G442585,_G442586,_G442587):-freeze(_G442586,'blocked_blocked_nondetfunc.insert_2'(_G442583,_G442584,_G442585,_G442586,_G442587)).
'blocked_blocked_nondetfunc.insert_2'([],_G441269,[_G441269],_G442688,_G442688).
'blocked_blocked_nondetfunc.insert_2'([_G441451|_G441460],_G441269,_G443033,_G443036,_G443039):-!,makeShare(_G441269,_G443133),makeShare(_G441451,_G443143),makeShare(_G441460,_G443153),hnf('nondetfunc.choose'([_G443133,_G443143|_G443153],[_G443143|'nondetfunc.insert'(_G443133,_G443153)]),_G443033,_G443036,_G443039).
'blocked_blocked_nondetfunc.insert_2'('FAIL'(_G444225),_G441269,'FAIL'(_G444225),_G444232,_G444232):-nonvar(_G444225).

'nondetfunc.permut'(_G444621,_G444622,_G444623,_G444624):-freeze(_G444623,'blocked_nondetfunc.permut'(_G444621,_G444622,_G444623,_G444624)).
'blocked_nondetfunc.permut'(_G444659,_G444980,_G444983,_G444986):-hnf(_G444659,_G445474,_G444983,_G445465),'blocked_nondetfunc.permut_1'(_G445474,_G444980,_G445465,_G444986).

'blocked_nondetfunc.permut_1'(_G445625,_G445626,_G445627,_G445628):-freeze(_G445627,'blocked_blocked_nondetfunc.permut_1'(_G445625,_G445626,_G445627,_G445628)).
'blocked_blocked_nondetfunc.permut_1'([],[],_G445725,_G445725).
'blocked_blocked_nondetfunc.permut_1'([_G444759|_G444768],_G445944,_G445947,_G445950):-!,hnf('nondetfunc.insert'(_G444759,'nondetfunc.permut'(_G444768)),_G445944,_G445947,_G445950).
'blocked_blocked_nondetfunc.permut_1'('FAIL'(_G446416),'FAIL'(_G446416),_G446423,_G446423):-nonvar(_G446416).

'nondetfunc.sort'(_G446772,_G446773,_G446774,_G446775,_G446776):-freeze(_G446775,'blocked_nondetfunc.sort'(_G446772,_G446773,_G446774,_G446775,_G446776)).
'blocked_nondetfunc.sort'(_G446815,_G446824,_G446984,_G446987,_G446990):-hnf('nondetfunc.rId'(partcall(1,'nondetfunc.sorted',[_G446815]),'nondetfunc.permut'(_G446824)),_G446984,_G446987,_G446990).

'nondetfunc.rId'(_G447813,_G447814,_G447815,_G447816,_G447817):-freeze(_G447816,'blocked_nondetfunc.rId'(_G447813,_G447814,_G447815,_G447816,_G447817)).
'blocked_nondetfunc.rId'(_G447856,_G447865,_G448717,_G448720,_G448723):-makeShare(_G447865,_G448243),hnf('Prelude.apply'(_G447856,_G448243),_G449197,_G448720,_G449182),'blocked_nondetfunc.rId_ComplexCase'(_G449197,_G447856,_G448243,_G448717,_G449182,_G448723).

'blocked_nondetfunc.rId_ComplexCase'(_G449380,_G449381,_G449382,_G449383,_G449384,_G449385):-freeze(_G449384,freeze(_G449380,'blocked_blocked_nondetfunc.rId_ComplexCase'(_G449380,_G449381,_G449382,_G449383,_G449384,_G449385))).
'blocked_blocked_nondetfunc.rId_ComplexCase'('Prelude.True',_G447856,_G448243,_G449556,_G449559,_G449562):-hnf(_G448243,_G449556,_G449559,_G449562).
'blocked_blocked_nondetfunc.rId_ComplexCase'('Prelude.False',_G447856,_G448243,_G449933,_G449936,_G449939):-!,hnf('Prelude.failure'('nondetfunc.rId',['Prelude.False']),_G449933,_G449936,_G449939).
'blocked_blocked_nondetfunc.rId_ComplexCase'('FAIL'(_G450507),_G447856,_G448243,'FAIL'(_G450507),_G450514,_G450514).

'nondetfunc.wheresort'(_G450959,_G450960,_G450961,_G450962,_G450963):-freeze(_G450962,'blocked_nondetfunc.wheresort'(_G450959,_G450960,_G450961,_G450962,_G450963)).
'blocked_nondetfunc.wheresort'(_G451002,_G451011,_G451365,_G451368,_G451371):-makeShare(_G451023,_G451441),hnf('Prelude.cond'('Prelude.letrec'(_G451441,'nondetfunc.permut'(_G451011)),'nondetfunc.wheresort._\'23caseor0'('nondetfunc.sorted'(_G451002,_G451441),_G451441)),_G451365,_G451368,_G451371).

'nondetfunc.strictsort'(_G452860,_G452861,_G452862,_G452863,_G452864):-freeze(_G452863,'blocked_nondetfunc.strictsort'(_G452860,_G452861,_G452862,_G452863,_G452864)).
'blocked_nondetfunc.strictsort'(_G452903,_G452912,_G453346,_G453349,_G453352):-makeShare(_G452924,_G453422),hnf('nondetfunc.strictsort._\'23caseor0'('Prelude.&'('Prelude.=:='(_G453422,'nondetfunc.permut'(_G452912)),'Prelude.=:='('nondetfunc.sorted'(_G452903,_G453422),'Prelude.True')),_G453422),_G453346,_G453349,_G453352).

'nondetfunc.sorted'(_G455025,_G455026,_G455027,_G455028,_G455029):-freeze(_G455028,'blocked_nondetfunc.sorted'(_G455025,_G455026,_G455027,_G455028,_G455029)).
'blocked_nondetfunc.sorted'(_G455068,_G455077,_G455992,_G455995,_G455998):-hnf(_G455077,_G456496,_G455995,_G456484),'blocked_nondetfunc.sorted_2'(_G456496,_G455068,_G455992,_G456484,_G455998).

'blocked_nondetfunc.sorted_2'(_G456648,_G456649,_G456650,_G456651,_G456652):-freeze(_G456651,'blocked_blocked_nondetfunc.sorted_2'(_G456648,_G456649,_G456650,_G456651,_G456652)).
'blocked_blocked_nondetfunc.sorted_2'([],_G455068,'Prelude.True',_G456753,_G456753).
'blocked_blocked_nondetfunc.sorted_2'([_G455177|_G455186],_G455068,_G457159,_G457162,_G457165):-!,hnf(_G455186,_G457909,_G457162,_G457894),'blocked_blocked_nondetfunc.sorted_2_[|]_2'(_G457909,_G455177,_G455068,_G457159,_G457894,_G457165).

'blocked_blocked_nondetfunc.sorted_2_[|]_2'(_G458113,_G458114,_G458115,_G458116,_G458117,_G458118):-freeze(_G458117,'blocked_blocked_blocked_nondetfunc.sorted_2_[|]_2'(_G458113,_G458114,_G458115,_G458116,_G458117,_G458118)).
'blocked_blocked_blocked_nondetfunc.sorted_2_[|]_2'([],_G455177,_G455068,'Prelude.True',_G458223,_G458223).
'blocked_blocked_blocked_nondetfunc.sorted_2_[|]_2'([_G455292|_G455301],_G455177,_G455068,_G459672,_G459675,_G459678):-!,makeShare(_G455068,_G458691),makeShare(_G455292,_G458701),hnf('Prelude.apply'('Prelude.apply'('Prelude.<='(_G458691),_G455177),_G458701),_G460708,_G459675,_G460687),'blocked_blocked_blocked_nondetfunc.sorted_2_[|]_2_[|]_ComplexCase'(_G460708,_G458701,_G455301,_G455177,_G458691,_G459672,_G460687,_G459678).

'blocked_blocked_blocked_nondetfunc.sorted_2_[|]_2_[|]_ComplexCase'(_G461001,_G461002,_G461003,_G461004,_G461005,_G461006,_G461007,_G461008):-freeze(_G461007,freeze(_G461001,'blocked_blocked_blocked_blocked_nondetfunc.sorted_2_[|]_2_[|]_ComplexCase'(_G461001,_G461002,_G461003,_G461004,_G461005,_G461006,_G461007,_G461008))).
'blocked_blocked_blocked_blocked_nondetfunc.sorted_2_[|]_2_[|]_ComplexCase'('Prelude.True',_G458701,_G455301,_G455177,_G458691,_G461187,_G461190,_G461193):-hnf('nondetfunc.sorted'(_G458691,[_G458701|_G455301]),_G461187,_G461190,_G461193).
'blocked_blocked_blocked_blocked_nondetfunc.sorted_2_[|]_2_[|]_ComplexCase'('Prelude.False',_G458701,_G455301,_G455177,_G458691,_G461978,_G461981,_G461984):-!,hnf('Prelude.failure'('nondetfunc.sorted',['Prelude.False']),_G461978,_G461981,_G461984).
'blocked_blocked_blocked_blocked_nondetfunc.sorted_2_[|]_2_[|]_ComplexCase'('FAIL'(_G462724),_G458701,_G455301,_G455177,_G458691,'FAIL'(_G462724),_G462731,_G462731).
'blocked_blocked_blocked_nondetfunc.sorted_2_[|]_2'('FAIL'(_G462770),_G455177,_G455068,'FAIL'(_G462770),_G462777,_G462777):-nonvar(_G462770).
'blocked_blocked_nondetfunc.sorted_2'('FAIL'(_G462810),_G455068,'FAIL'(_G462810),_G462817,_G462817):-nonvar(_G462810).

'nondetfunc.goal1'(_G463188,_G463189,_G463190,_G463191,_G463192):-freeze(_G463191,'blocked_nondetfunc.goal1'(_G463188,_G463189,_G463190,_G463191,_G463192)).
'blocked_nondetfunc.goal1'(_G463231,_G463240,_G464071,_G464074,_G464077):-makeShare(_G463231,_G464153),hnf('nondetfunc.sort'(_G463240,['Prelude.apply'('Prelude.fromInt'(_G464153),4),'Prelude.apply'('Prelude.fromInt'(_G464153),3),'Prelude.apply'('Prelude.fromInt'(_G464153),2),'Prelude.apply'('Prelude.fromInt'(_G464153),1)]),_G464071,_G464074,_G464077).

'nondetfunc.goal2'(_G466109,_G466110,_G466111,_G466112,_G466113):-freeze(_G466112,'blocked_nondetfunc.goal2'(_G466109,_G466110,_G466111,_G466112,_G466113)).
'blocked_nondetfunc.goal2'(_G466152,_G466161,_G466992,_G466995,_G466998):-makeShare(_G466152,_G467074),hnf('nondetfunc.wheresort'(_G466161,['Prelude.apply'('Prelude.fromInt'(_G467074),4),'Prelude.apply'('Prelude.fromInt'(_G467074),3),'Prelude.apply'('Prelude.fromInt'(_G467074),2),'Prelude.apply'('Prelude.fromInt'(_G467074),1)]),_G466992,_G466995,_G466998).

'nondetfunc.goal3'(_G469045,_G469046,_G469047,_G469048,_G469049):-freeze(_G469048,'blocked_nondetfunc.goal3'(_G469045,_G469046,_G469047,_G469048,_G469049)).
'blocked_nondetfunc.goal3'(_G469088,_G469097,_G469928,_G469931,_G469934):-makeShare(_G469088,_G470010),hnf('nondetfunc.strictsort'(_G469097,['Prelude.apply'('Prelude.fromInt'(_G470010),4),'Prelude.apply'('Prelude.fromInt'(_G470010),3),'Prelude.apply'('Prelude.fromInt'(_G470010),2),'Prelude.apply'('Prelude.fromInt'(_G470010),1)]),_G469928,_G469931,_G469934).

'nondetfunc.coin'(_G471966,_G471967,_G471968):-freeze(_G471967,'blocked_nondetfunc.coin'(_G471966,_G471967,_G471968)).
'blocked_nondetfunc.coin'('nondetfunc.o',_G472083,_G472083).
'blocked_nondetfunc.coin'('nondetfunc.s'('nondetfunc.o'),_G472226,_G472226).

'nondetfunc.add'(_G472759,_G472760,_G472761,_G472762,_G472763):-freeze(_G472762,'blocked_nondetfunc.add'(_G472759,_G472760,_G472761,_G472762,_G472763)).
'blocked_nondetfunc.add'(_G472802,_G472811,_G473104,_G473107,_G473110):-hnf(_G472802,_G473554,_G473107,_G473542),'blocked_nondetfunc.add_1'(_G473554,_G472811,_G473104,_G473542,_G473110).

'blocked_nondetfunc.add_1'(_G473697,_G473698,_G473699,_G473700,_G473701):-freeze(_G473700,'blocked_blocked_nondetfunc.add_1'(_G473697,_G473698,_G473699,_G473700,_G473701)).
'blocked_blocked_nondetfunc.add_1'('nondetfunc.o',_G472811,_G473865,_G473868,_G473871):-hnf(_G472811,_G473865,_G473868,_G473871).
'blocked_blocked_nondetfunc.add_1'('nondetfunc.s'(_G472904),_G472811,'nondetfunc.s'('nondetfunc.add'(_G472904,_G472811)),_G474179,_G474179):-!.
'blocked_blocked_nondetfunc.add_1'('FAIL'(_G474608),_G472811,'FAIL'(_G474608),_G474615,_G474615):-nonvar(_G474608).

'nondetfunc.double'(_G475004,_G475005,_G475006,_G475007):-freeze(_G475006,'blocked_nondetfunc.double'(_G475004,_G475005,_G475006,_G475007)).
'blocked_nondetfunc.double'(_G475042,_G475122,_G475125,_G475128):-makeShare(_G475042,_G475158),hnf('nondetfunc.add'(_G475158,_G475158),_G475122,_G475125,_G475128).

'nondetfunc.goal4'(_G475865,_G475866,_G475867):-freeze(_G475866,'blocked_nondetfunc.goal4'(_G475865,_G475866,_G475867)).
'blocked_nondetfunc.goal4'(_G475943,_G475946,_G475949):-hnf('nondetfunc.double'('nondetfunc.coin'),_G475943,_G475946,_G475949).

'nondetfunc.wheresort._\'23caseor0'(_G476814,_G476815,_G476816,_G476817,_G476818):-freeze(_G476817,'blocked_nondetfunc.wheresort._\'23caseor0'(_G476814,_G476815,_G476816,_G476817,_G476818)).
'blocked_nondetfunc.wheresort._\'23caseor0'(_G476857,_G476866,_G477255,_G477258,_G477261):-hnf(_G476857,_G478029,_G477258,_G478017),'blocked_nondetfunc.wheresort._\'23caseor0_1'(_G478029,_G476866,_G477255,_G478017,_G477261).

'blocked_nondetfunc.wheresort._\'23caseor0_1'(_G478229,_G478230,_G478231,_G478232,_G478233):-freeze(_G478232,freeze(_G478229,'blocked_blocked_nondetfunc.wheresort._\'23caseor0_1'(_G478229,_G478230,_G478231,_G478232,_G478233))).
'blocked_blocked_nondetfunc.wheresort._\'23caseor0_1'('Prelude.True',_G476866,_G478400,_G478403,_G478406):-hnf(_G476866,_G478400,_G478403,_G478406).
'blocked_blocked_nondetfunc.wheresort._\'23caseor0_1'('Prelude.False',_G476866,_G478766,_G478769,_G478772):-!,hnf('Prelude.failure'('nondetfunc.wheresort._\'23caseor0',['Prelude.False']),_G478766,_G478769,_G478772).
'blocked_blocked_nondetfunc.wheresort._\'23caseor0_1'('FAIL'(_G479383),_G476866,'FAIL'(_G479383),_G479390,_G479390).

'nondetfunc.strictsort._\'23caseor0'(_G480041,_G480042,_G480043,_G480044,_G480045):-freeze(_G480044,'blocked_nondetfunc.strictsort._\'23caseor0'(_G480041,_G480042,_G480043,_G480044,_G480045)).
'blocked_nondetfunc.strictsort._\'23caseor0'(_G480084,_G480093,_G480485,_G480488,_G480491):-hnf(_G480084,_G481277,_G480488,_G481265),'blocked_nondetfunc.strictsort._\'23caseor0_1'(_G481277,_G480093,_G480485,_G481265,_G480491).

'blocked_nondetfunc.strictsort._\'23caseor0_1'(_G481480,_G481481,_G481482,_G481483,_G481484):-freeze(_G481483,freeze(_G481480,'blocked_blocked_nondetfunc.strictsort._\'23caseor0_1'(_G481480,_G481481,_G481482,_G481483,_G481484))).
'blocked_blocked_nondetfunc.strictsort._\'23caseor0_1'('Prelude.True',_G480093,_G481651,_G481654,_G481657):-hnf(_G480093,_G481651,_G481654,_G481657).
'blocked_blocked_nondetfunc.strictsort._\'23caseor0_1'('Prelude.False',_G480093,_G482020,_G482023,_G482026):-!,hnf('Prelude.failure'('nondetfunc.strictsort._\'23caseor0',['Prelude.False']),_G482020,_G482023,_G482026).
'blocked_blocked_nondetfunc.strictsort._\'23caseor0_1'('FAIL'(_G482643),_G480093,'FAIL'(_G482643),_G482650,_G482650).

:-costCenters(['']).




%%%%% Number of shared variables: 12

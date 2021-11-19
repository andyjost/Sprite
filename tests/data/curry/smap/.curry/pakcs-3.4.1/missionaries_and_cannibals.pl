%PAKCS3.4 swi8 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(missionaries_and_cannibals).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('missionaries_and_cannibals._inst\'23Prelude.Data\'23missionaries_and_cannibals.State','_inst#Prelude.Data#missionaries_and_cannibals.State',1,'missionaries_and_cannibals._inst\'23Prelude.Data\'23missionaries_and_cannibals.State',nofix,notype).
functiontype('missionaries_and_cannibals._impl\'23\'3D\'3D\'3D\'23Prelude.Data\'23missionaries_and_cannibals.State','_impl#===#Prelude.Data#missionaries_and_cannibals.State',2,'missionaries_and_cannibals._impl\'23\'3D\'3D\'3D\'23Prelude.Data\'23missionaries_and_cannibals.State',nofix,notype).
functiontype('missionaries_and_cannibals._impl\'23aValue\'23Prelude.Data\'23missionaries_and_cannibals.State','_impl#aValue#Prelude.Data#missionaries_and_cannibals.State',0,'missionaries_and_cannibals._impl\'23aValue\'23Prelude.Data\'23missionaries_and_cannibals.State',nofix,notype).
functiontype('missionaries_and_cannibals._inst\'23Prelude.Eq\'23missionaries_and_cannibals.State','_inst#Prelude.Eq#missionaries_and_cannibals.State',1,'missionaries_and_cannibals._inst\'23Prelude.Eq\'23missionaries_and_cannibals.State',nofix,notype).
functiontype('missionaries_and_cannibals._impl\'23\'3D\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State','_impl#==#Prelude.Eq#missionaries_and_cannibals.State',2,'missionaries_and_cannibals._impl\'23\'3D\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State',nofix,notype).
functiontype('missionaries_and_cannibals._impl\'23\'2F\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State','_impl#/=#Prelude.Eq#missionaries_and_cannibals.State',0,'missionaries_and_cannibals._impl\'23\'2F\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State',nofix,notype).
functiontype('missionaries_and_cannibals.M','M',1,'missionaries_and_cannibals.M',nofix,notype).
functiontype('missionaries_and_cannibals.C','C',1,'missionaries_and_cannibals.C',nofix,notype).
functiontype('missionaries_and_cannibals.makeState',makeState,3,'missionaries_and_cannibals.makeState',nofix,notype).
functiontype('missionaries_and_cannibals.start',start,0,'missionaries_and_cannibals.start',nofix,notype).
functiontype('missionaries_and_cannibals.end',end,0,'missionaries_and_cannibals.end',nofix,notype).
functiontype('missionaries_and_cannibals.move',move,1,'missionaries_and_cannibals.move',nofix,notype).
functiontype('missionaries_and_cannibals.makePath',makePath,2,'missionaries_and_cannibals.makePath',nofix,notype).
functiontype('missionaries_and_cannibals.extend',extend,1,'missionaries_and_cannibals.extend',nofix,notype).
functiontype('missionaries_and_cannibals.main',main,0,'missionaries_and_cannibals.main',nofix,notype).
functiontype('missionaries_and_cannibals.makeState._\'23caseor0','missionaries_and_cannibals.makeState._#caseor0',4,'missionaries_and_cannibals.makeState._\'23caseor0',nofix,notype).
functiontype('missionaries_and_cannibals.makePath._\'23caseor0','missionaries_and_cannibals.makePath._#caseor0',1,'missionaries_and_cannibals.makePath._\'23caseor0',nofix,notype).
functiontype('missionaries_and_cannibals.makePath._\'23caseor0._\'23caseor0','missionaries_and_cannibals.makePath._#caseor0._#caseor0',3,'missionaries_and_cannibals.makePath._\'23caseor0._\'23caseor0',nofix,notype).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('missionaries_and_cannibals.State','State',3,'State',0,notype,[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'missionaries_and_cannibals._inst\'23Prelude.Data\'23missionaries_and_cannibals.State'(_1164598,_1164600,_1164602,_1164604):-freeze(_1164602,'blocked_missionaries_and_cannibals._inst\'23Prelude.Data\'23missionaries_and_cannibals.State'(_1164598,_1164600,_1164602,_1164604)).
'blocked_missionaries_and_cannibals._inst\'23Prelude.Data\'23missionaries_and_cannibals.State'(_1164674,_1165514,_1165520,_1165526):-hnf(_1164674,_1168842,_1165520,_1168824),'blocked_missionaries_and_cannibals._inst\'23Prelude.Data\'23missionaries_and_cannibals.State_1'(_1168842,_1165514,_1168824,_1165526).

'blocked_missionaries_and_cannibals._inst\'23Prelude.Data\'23missionaries_and_cannibals.State_1'(_1169534,_1169536,_1169538,_1169540):-freeze(_1169538,'blocked_blocked_missionaries_and_cannibals._inst\'23Prelude.Data\'23missionaries_and_cannibals.State_1'(_1169534,_1169536,_1169538,_1169540)).
'blocked_blocked_missionaries_and_cannibals._inst\'23Prelude.Data\'23missionaries_and_cannibals.State_1'('Prelude.()','Prelude._Dict\'23Data'(partcall(2,'missionaries_and_cannibals._impl\'23\'3D\'3D\'3D\'23Prelude.Data\'23missionaries_and_cannibals.State',[]),'missionaries_and_cannibals._impl\'23aValue\'23Prelude.Data\'23missionaries_and_cannibals.State'),_1169836,_1169836):-!.
'blocked_blocked_missionaries_and_cannibals._inst\'23Prelude.Data\'23missionaries_and_cannibals.State_1'('FAIL'(_1171972),'FAIL'(_1171972),_1171986,_1171986):-nonvar(_1171972).

'missionaries_and_cannibals._impl\'23\'3D\'3D\'3D\'23Prelude.Data\'23missionaries_and_cannibals.State'(_1175246,_1175248,_1175250,_1175252,_1175254):-freeze(_1175252,'blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'3D\'23Prelude.Data\'23missionaries_and_cannibals.State'(_1175246,_1175248,_1175250,_1175252,_1175254)).
'blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'3D\'23Prelude.Data\'23missionaries_and_cannibals.State'(_1175332,_1175350,_1177378,_1177384,_1177390):-hnf(_1175332,_1181158,_1177384,_1181134),'blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'3D\'23Prelude.Data\'23missionaries_and_cannibals.State_1'(_1181158,_1175350,_1177378,_1181134,_1177390).

'blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'3D\'23Prelude.Data\'23missionaries_and_cannibals.State_1'(_1181924,_1181926,_1181928,_1181930,_1181932):-freeze(_1181930,'blocked_blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'3D\'23Prelude.Data\'23missionaries_and_cannibals.State_1'(_1181924,_1181926,_1181928,_1181930,_1181932)).
'blocked_blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'3D\'23Prelude.Data\'23missionaries_and_cannibals.State_1'('missionaries_and_cannibals.State'(_1175458,_1175476,_1175494),_1175350,_1183232,_1183238,_1183244):-!,hnf(_1175350,_1188386,_1183238,_1188350),'blocked_blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'3D\'23Prelude.Data\'23missionaries_and_cannibals.State_1_missionaries_and_cannibals.State_4'(_1188386,_1175458,_1175476,_1175494,_1183232,_1188350,_1183244).

'blocked_blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'3D\'23Prelude.Data\'23missionaries_and_cannibals.State_1_missionaries_and_cannibals.State_4'(_1189432,_1189434,_1189436,_1189438,_1189440,_1189442,_1189444):-freeze(_1189442,'blocked_blocked_blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'3D\'23Prelude.Data\'23missionaries_and_cannibals.State_1_missionaries_and_cannibals.State_4'(_1189432,_1189434,_1189436,_1189438,_1189440,_1189442,_1189444)).
'blocked_blocked_blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'3D\'23Prelude.Data\'23missionaries_and_cannibals.State_1_missionaries_and_cannibals.State_4'('missionaries_and_cannibals.State'(_1175620,_1175638,_1175656),_1175458,_1175476,_1175494,_1190054,_1190060,_1190066):-!,hnf('Prelude.&&'('Prelude.&&'('Prelude.apply'('Prelude.apply'('Prelude._impl\'23\'3D\'3D\'3D\'23Prelude.Data\'23Prelude.Int',_1175458),_1175620),'Prelude.apply'('Prelude.apply'('Prelude._impl\'23\'3D\'3D\'3D\'23Prelude.Data\'23Prelude.Int',_1175476),_1175638)),'Prelude._impl\'23\'3D\'3D\'3D\'23Prelude.Data\'23Prelude.Bool'(_1175494,_1175656)),_1190054,_1190060,_1190066).
'blocked_blocked_blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'3D\'23Prelude.Data\'23missionaries_and_cannibals.State_1_missionaries_and_cannibals.State_4'('FAIL'(_1194518),_1175458,_1175476,_1175494,'FAIL'(_1194518),_1194532,_1194532):-nonvar(_1194518).
'blocked_blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'3D\'23Prelude.Data\'23missionaries_and_cannibals.State_1'('FAIL'(_1194606),_1175350,'FAIL'(_1194606),_1194620,_1194620):-nonvar(_1194606).

'missionaries_and_cannibals._impl\'23aValue\'23Prelude.Data\'23missionaries_and_cannibals.State'(_1197924,_1197926,_1197928):-freeze(_1197926,'blocked_missionaries_and_cannibals._impl\'23aValue\'23Prelude.Data\'23missionaries_and_cannibals.State'(_1197924,_1197926,_1197928)).
'blocked_missionaries_and_cannibals._impl\'23aValue\'23Prelude.Data\'23missionaries_and_cannibals.State'('missionaries_and_cannibals.State'('Prelude._impl\'23aValue\'23Prelude.Data\'23Prelude.Int','Prelude._impl\'23aValue\'23Prelude.Data\'23Prelude.Int','Prelude._impl\'23aValue\'23Prelude.Data\'23Prelude.Bool'),_1198246,_1198246).

'missionaries_and_cannibals._inst\'23Prelude.Eq\'23missionaries_and_cannibals.State'(_1203232,_1203234,_1203236,_1203238):-freeze(_1203236,'blocked_missionaries_and_cannibals._inst\'23Prelude.Eq\'23missionaries_and_cannibals.State'(_1203232,_1203234,_1203236,_1203238)).
'blocked_missionaries_and_cannibals._inst\'23Prelude.Eq\'23missionaries_and_cannibals.State'(_1203308,_1204136,_1204142,_1204148):-hnf(_1203308,_1207392,_1204142,_1207374),'blocked_missionaries_and_cannibals._inst\'23Prelude.Eq\'23missionaries_and_cannibals.State_1'(_1207392,_1204136,_1207374,_1204148).

'blocked_missionaries_and_cannibals._inst\'23Prelude.Eq\'23missionaries_and_cannibals.State_1'(_1208072,_1208074,_1208076,_1208078):-freeze(_1208076,'blocked_blocked_missionaries_and_cannibals._inst\'23Prelude.Eq\'23missionaries_and_cannibals.State_1'(_1208072,_1208074,_1208076,_1208078)).
'blocked_blocked_missionaries_and_cannibals._inst\'23Prelude.Eq\'23missionaries_and_cannibals.State_1'('Prelude.()','Prelude._Dict\'23Eq'(partcall(2,'missionaries_and_cannibals._impl\'23\'3D\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State',[]),'missionaries_and_cannibals._impl\'23\'2F\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State'),_1208374,_1208374):-!.
'blocked_blocked_missionaries_and_cannibals._inst\'23Prelude.Eq\'23missionaries_and_cannibals.State_1'('FAIL'(_1210444),'FAIL'(_1210444),_1210458,_1210458):-nonvar(_1210444).

'missionaries_and_cannibals._impl\'23\'3D\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State'(_1213586,_1213588,_1213590,_1213592,_1213594):-freeze(_1213592,'blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State'(_1213586,_1213588,_1213590,_1213592,_1213594)).
'blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State'(_1213672,_1213690,_1215368,_1215374,_1215380):-hnf(_1213672,_1218968,_1215374,_1218944),'blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State_1'(_1218968,_1213690,_1215368,_1218944,_1215380).

'blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State_1'(_1219704,_1219706,_1219708,_1219710,_1219712):-freeze(_1219710,'blocked_blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State_1'(_1219704,_1219706,_1219708,_1219710,_1219712)).
'blocked_blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State_1'('missionaries_and_cannibals.State'(_1213798,_1213816,_1213834),_1213690,_1220982,_1220988,_1220994):-!,hnf(_1213690,_1225956,_1220988,_1225920),'blocked_blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State_1_missionaries_and_cannibals.State_4'(_1225956,_1213798,_1213816,_1213834,_1220982,_1225920,_1220994).

'blocked_blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State_1_missionaries_and_cannibals.State_4'(_1226972,_1226974,_1226976,_1226978,_1226980,_1226982,_1226984):-freeze(_1226982,'blocked_blocked_blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State_1_missionaries_and_cannibals.State_4'(_1226972,_1226974,_1226976,_1226978,_1226980,_1226982,_1226984)).
'blocked_blocked_blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State_1_missionaries_and_cannibals.State_4'('missionaries_and_cannibals.State'(_1213960,_1213978,_1213996),_1213798,_1213816,_1213834,_1227594,_1227600,_1227606):-!,hnf('Prelude.&&'('Prelude.&&'('Prelude._impl\'23\'3D\'3D\'23Prelude.Eq\'23Prelude.Int'(_1213798,_1213960),'Prelude._impl\'23\'3D\'3D\'23Prelude.Eq\'23Prelude.Int'(_1213816,_1213978)),'Prelude._impl\'23\'3D\'3D\'23Prelude.Eq\'23Prelude.Bool'(_1213834,_1213996)),_1227594,_1227600,_1227606).
'blocked_blocked_blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State_1_missionaries_and_cannibals.State_4'('FAIL'(_1231246),_1213798,_1213816,_1213834,'FAIL'(_1231246),_1231260,_1231260):-nonvar(_1231246).
'blocked_blocked_missionaries_and_cannibals._impl\'23\'3D\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State_1'('FAIL'(_1231334),_1213690,'FAIL'(_1231334),_1231348,_1231348):-nonvar(_1231334).

'missionaries_and_cannibals._impl\'23\'2F\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State'(_1234484,_1234486,_1234488):-freeze(_1234486,'blocked_missionaries_and_cannibals._impl\'23\'2F\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State'(_1234484,_1234486,_1234488)).
'blocked_missionaries_and_cannibals._impl\'23\'2F\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State'(_1234640,_1234646,_1234652):-hnf(partcall(2,'Prelude._def\'23\'2F\'3D\'23Prelude.Eq',[partcall(1,'missionaries_and_cannibals._inst\'23Prelude.Eq\'23missionaries_and_cannibals.State',[])]),_1234640,_1234646,_1234652).

'missionaries_and_cannibals.M'(_1237234,_1237236,_1237238,_1237240):-freeze(_1237238,'blocked_missionaries_and_cannibals.M'(_1237234,_1237236,_1237238,_1237240)).
'blocked_missionaries_and_cannibals.M'(_1237310,_1237550,_1237556,_1237562):-hnf('Prelude.apply'('Prelude.fromInt'(_1237310),2),_1237550,_1237556,_1237562).

'missionaries_and_cannibals.C'(_1239476,_1239478,_1239480,_1239482):-freeze(_1239480,'blocked_missionaries_and_cannibals.C'(_1239476,_1239478,_1239480,_1239482)).
'blocked_missionaries_and_cannibals.C'(_1239552,_1239792,_1239798,_1239804):-hnf('Prelude.apply'('Prelude.fromInt'(_1239552),1),_1239792,_1239798,_1239804).

'missionaries_and_cannibals.makeState'(_1242006,_1242008,_1242010,_1242012,_1242014,_1242016):-freeze(_1242014,'blocked_missionaries_and_cannibals.makeState'(_1242006,_1242008,_1242010,_1242012,_1242014,_1242016)).
'blocked_missionaries_and_cannibals.makeState'(_1242102,_1242120,_1242138,_1245342,_1245348,_1245354):-makeShare(_1242162,_1245886),makeShare(_1242102,_1245906),makeShare(_1242120,_1245926),makeShare(_1242180,_1245946),hnf('Prelude.cond'('Prelude.letrec'(_1245886,'Prelude.&&'('Prelude._impl\'23\'3C\'3D\'23Prelude.Ord\'23Prelude.Int'(0,_1245906),'Prelude.&&'('Prelude._impl\'23\'3C\'3D\'23Prelude.Ord\'23Prelude.Int'(_1245906,'missionaries_and_cannibals.M'(partcall(1,'Prelude._inst\'23Prelude.Num\'23Prelude.Int',[]))),'Prelude.&&'('Prelude._impl\'23\'3C\'3D\'23Prelude.Ord\'23Prelude.Int'(0,_1245926),'Prelude._impl\'23\'3C\'3D\'23Prelude.Ord\'23Prelude.Int'(_1245926,'missionaries_and_cannibals.C'(partcall(1,'Prelude._inst\'23Prelude.Num\'23Prelude.Int',[]))))))),'Prelude.cond'('Prelude.letrec'(_1245946,'Prelude.&&'('Prelude._impl\'23\'3C\'3D\'23Prelude.Ord\'23Prelude.Int'(_1245926,_1245906),'Prelude._impl\'23\'3C\'3D\'23Prelude.Ord\'23Prelude.Int'('Prelude._impl\'23\'2D\'23Prelude.Num\'23Prelude.Int'('missionaries_and_cannibals.C'(partcall(1,'Prelude._inst\'23Prelude.Num\'23Prelude.Int',[])),_1245926),'Prelude._impl\'23\'2D\'23Prelude.Num\'23Prelude.Int'('missionaries_and_cannibals.M'(partcall(1,'Prelude._inst\'23Prelude.Num\'23Prelude.Int',[])),_1245906)))),'missionaries_and_cannibals.makeState._\'23caseor0'('Prelude.&&'(_1245886,_1245946),_1245906,_1245926,_1242138))),_1245342,_1245348,_1245354).

'missionaries_and_cannibals.start'(_1257678,_1257680,_1257682):-freeze(_1257680,'blocked_missionaries_and_cannibals.start'(_1257678,_1257680,_1257682)).
'blocked_missionaries_and_cannibals.start'(_1258154,_1258160,_1258166):-hnf('missionaries_and_cannibals.makeState'('missionaries_and_cannibals.M'(partcall(1,'Prelude._inst\'23Prelude.Num\'23Prelude.Int',[])),'missionaries_and_cannibals.C'(partcall(1,'Prelude._inst\'23Prelude.Num\'23Prelude.Int',[])),'Prelude.True'),_1258154,_1258160,_1258166).

'missionaries_and_cannibals.end'(_1261288,_1261290,_1261292):-freeze(_1261290,'blocked_missionaries_and_cannibals.end'(_1261288,_1261290,_1261292)).
'blocked_missionaries_and_cannibals.end'(_1261576,_1261582,_1261588):-hnf('missionaries_and_cannibals.makeState'(0,0,'Prelude.False'),_1261576,_1261582,_1261588).

'missionaries_and_cannibals.move'(_1263664,_1263666,_1263668,_1263670):-freeze(_1263668,'blocked_missionaries_and_cannibals.move'(_1263664,_1263666,_1263668,_1263670)).
'blocked_missionaries_and_cannibals.move'(_1263740,_1269526,_1269532,_1269538):-hnf(_1263740,_1271018,_1269532,_1271000),'blocked_missionaries_and_cannibals.move_1'(_1271018,_1269526,_1271000,_1269538).

'blocked_missionaries_and_cannibals.move_1'(_1271404,_1271406,_1271408,_1271410):-freeze(_1271408,'blocked_blocked_missionaries_and_cannibals.move_1'(_1271404,_1271406,_1271408,_1271410)).
'blocked_blocked_missionaries_and_cannibals.move_1'('missionaries_and_cannibals.State'(_1263848,_1263866,_1263884),_1272318,_1272324,_1272330):-!,hnf(_1263884,_1275184,_1272324,_1275154),'blocked_blocked_missionaries_and_cannibals.move_1_missionaries_and_cannibals.State_3'(_1275184,_1263848,_1263866,_1272318,_1275154,_1272330).

'blocked_blocked_missionaries_and_cannibals.move_1_missionaries_and_cannibals.State_3'(_1275850,_1275852,_1275854,_1275856,_1275858,_1275860):-freeze(_1275858,'blocked_blocked_blocked_missionaries_and_cannibals.move_1_missionaries_and_cannibals.State_3'(_1275850,_1275852,_1275854,_1275856,_1275858,_1275860)).
'blocked_blocked_blocked_missionaries_and_cannibals.move_1_missionaries_and_cannibals.State_3'('Prelude.True',_1263848,_1263866,_1276196,_1276202,_1276208):-makeShare(_1263848,_1276440),makeShare(_1263866,_1276460),hnf('Prelude.?'('missionaries_and_cannibals.makeState'('Prelude._impl\'23\'2D\'23Prelude.Num\'23Prelude.Int'(_1276440,1),_1276460,'Prelude.False'),'Prelude.?'('missionaries_and_cannibals.makeState'('Prelude._impl\'23\'2D\'23Prelude.Num\'23Prelude.Int'(_1276440,2),_1276460,'Prelude.False'),'Prelude.?'('missionaries_and_cannibals.makeState'(_1276440,'Prelude._impl\'23\'2D\'23Prelude.Num\'23Prelude.Int'(_1276460,1),'Prelude.False'),'Prelude.?'('missionaries_and_cannibals.makeState'(_1276440,'Prelude._impl\'23\'2D\'23Prelude.Num\'23Prelude.Int'(_1276460,2),'Prelude.False'),'missionaries_and_cannibals.makeState'('Prelude._impl\'23\'2D\'23Prelude.Num\'23Prelude.Int'(_1276440,1),'Prelude._impl\'23\'2D\'23Prelude.Num\'23Prelude.Int'(_1276460,1),'Prelude.False'))))),_1276196,_1276202,_1276208).
'blocked_blocked_blocked_missionaries_and_cannibals.move_1_missionaries_and_cannibals.State_3'('Prelude.False',_1263848,_1263866,_1284464,_1284470,_1284476):-!,makeShare(_1263848,_1284708),makeShare(_1263866,_1284728),hnf('Prelude.?'('missionaries_and_cannibals.makeState'('Prelude._impl\'23\'2B\'23Prelude.Num\'23Prelude.Int'(_1284708,1),_1284728,'Prelude.True'),'Prelude.?'('missionaries_and_cannibals.makeState'('Prelude._impl\'23\'2B\'23Prelude.Num\'23Prelude.Int'(_1284708,2),_1284728,'Prelude.True'),'Prelude.?'('missionaries_and_cannibals.makeState'(_1284708,'Prelude._impl\'23\'2B\'23Prelude.Num\'23Prelude.Int'(_1284728,1),'Prelude.True'),'Prelude.?'('missionaries_and_cannibals.makeState'(_1284708,'Prelude._impl\'23\'2B\'23Prelude.Num\'23Prelude.Int'(_1284728,2),'Prelude.True'),'missionaries_and_cannibals.makeState'('Prelude._impl\'23\'2B\'23Prelude.Num\'23Prelude.Int'(_1284708,1),'Prelude._impl\'23\'2B\'23Prelude.Num\'23Prelude.Int'(_1284728,1),'Prelude.True'))))),_1284464,_1284470,_1284476).
'blocked_blocked_blocked_missionaries_and_cannibals.move_1_missionaries_and_cannibals.State_3'('FAIL'(_1292456),_1263848,_1263866,'FAIL'(_1292456),_1292470,_1292470):-nonvar(_1292456).
'blocked_blocked_missionaries_and_cannibals.move_1'('FAIL'(_1292536),'FAIL'(_1292536),_1292550,_1292550):-nonvar(_1292536).

'missionaries_and_cannibals.makePath'(_1293968,_1293970,_1293972,_1293974,_1293976):-freeze(_1293974,'blocked_missionaries_and_cannibals.makePath'(_1293968,_1293970,_1293972,_1293974,_1293976)).
'blocked_missionaries_and_cannibals.makePath'(_1294054,_1294072,_1295934,_1295940,_1295946):-makeShare(_1294096,_1296290),makeShare(_1294054,_1296310),makeShare(_1294072,_1296330),makeShare(_1294114,_1296350),hnf('Prelude.cond'('Prelude.letrec'(_1296290,'missionaries_and_cannibals.makePath._\'23caseor0'('Prelude.=:='(partcall(1,'missionaries_and_cannibals._inst\'23Prelude.Data\'23missionaries_and_cannibals.State',[]),_1296310,'missionaries_and_cannibals.move'('Prelude.head'(_1296330))))),'Prelude.cond'('Prelude.letrec'(_1296350,'Prelude.apply'('Prelude.all'('Prelude.apply'('missionaries_and_cannibals._impl\'23\'2F\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State',_1296310)),_1296330)),'missionaries_and_cannibals.makePath._\'23caseor0._\'23caseor0'('Prelude.&&'(_1296290,_1296350),_1296310,_1296330))),_1295934,_1295940,_1295946).

'missionaries_and_cannibals.extend'(_1303904,_1303906,_1303908,_1303910):-freeze(_1303908,'blocked_missionaries_and_cannibals.extend'(_1303904,_1303906,_1303908,_1303910)).
'blocked_missionaries_and_cannibals.extend'(_1303980,_1306612,_1306618,_1306624):-makeShare(_1303980,_1304786),hnf('missionaries_and_cannibals._impl\'23\'3D\'3D\'23Prelude.Eq\'23missionaries_and_cannibals.State'('Prelude.head'(_1304786),'missionaries_and_cannibals.end'),_1308242,_1306618,_1308218),'blocked_missionaries_and_cannibals.extend_ComplexCase'(_1308242,_1304786,_1306612,_1308218,_1306624).

'blocked_missionaries_and_cannibals.extend_ComplexCase'(_1308720,_1308722,_1308724,_1308726,_1308728):-freeze(_1308726,freeze(_1308720,'blocked_blocked_missionaries_and_cannibals.extend_ComplexCase'(_1308720,_1308722,_1308724,_1308726,_1308728))).
'blocked_blocked_missionaries_and_cannibals.extend_ComplexCase'('Prelude.True',_1304786,_1309062,_1309068,_1309074):-hnf(_1304786,_1309062,_1309068,_1309074).
'blocked_blocked_missionaries_and_cannibals.extend_ComplexCase'('Prelude.False',_1304786,_1309860,_1309866,_1309872):-!,hnf('missionaries_and_cannibals.extend'('missionaries_and_cannibals.makePath'('Prelude.unknown'(partcall(1,'missionaries_and_cannibals._inst\'23Prelude.Data\'23missionaries_and_cannibals.State',[])),_1304786)),_1309860,_1309866,_1309872).
'blocked_blocked_missionaries_and_cannibals.extend_ComplexCase'('FAIL'(_1311792),_1304786,'FAIL'(_1311792),_1311806,_1311806).

'missionaries_and_cannibals.main'(_1313084,_1313086,_1313088):-freeze(_1313086,'blocked_missionaries_and_cannibals.main'(_1313084,_1313086,_1313088)).
'blocked_missionaries_and_cannibals.main'(_1313400,_1313406,_1313412):-hnf('missionaries_and_cannibals.extend'(['missionaries_and_cannibals.start']),_1313400,_1313406,_1313412).

'missionaries_and_cannibals.makeState._\'23caseor0'(_1316196,_1316198,_1316200,_1316202,_1316204,_1316206,_1316208):-freeze(_1316206,'blocked_missionaries_and_cannibals.makeState._\'23caseor0'(_1316196,_1316198,_1316200,_1316202,_1316204,_1316206,_1316208)).
'blocked_missionaries_and_cannibals.makeState._\'23caseor0'(_1316302,_1316320,_1316338,_1316356,_1317442,_1317448,_1317454):-hnf(_1316302,_1319606,_1317448,_1319570),'blocked_missionaries_and_cannibals.makeState._\'23caseor0_1'(_1319606,_1316320,_1316338,_1316356,_1317442,_1319570,_1317454).

'blocked_missionaries_and_cannibals.makeState._\'23caseor0_1'(_1320106,_1320108,_1320110,_1320112,_1320114,_1320116,_1320118):-freeze(_1320116,freeze(_1320106,'blocked_blocked_missionaries_and_cannibals.makeState._\'23caseor0_1'(_1320106,_1320108,_1320110,_1320112,_1320114,_1320116,_1320118))).
'blocked_blocked_missionaries_and_cannibals.makeState._\'23caseor0_1'('Prelude.True',_1316320,_1316338,_1316356,'missionaries_and_cannibals.State'(_1316320,_1316338,_1316356),_1320474,_1320474).
'blocked_blocked_missionaries_and_cannibals.makeState._\'23caseor0_1'('Prelude.False',_1316320,_1316338,_1316356,_1321916,_1321922,_1321928):-!,hnf('Prelude.failure'('missionaries_and_cannibals.makeState._\'23caseor0',['Prelude.False']),_1321916,_1321922,_1321928).
'blocked_blocked_missionaries_and_cannibals.makeState._\'23caseor0_1'('FAIL'(_1323482),_1316320,_1316338,_1316356,'FAIL'(_1323482),_1323496,_1323496).

'missionaries_and_cannibals.makePath._\'23caseor0'(_1325318,_1325320,_1325322,_1325324):-freeze(_1325322,'blocked_missionaries_and_cannibals.makePath._\'23caseor0'(_1325318,_1325320,_1325322,_1325324)).
'blocked_missionaries_and_cannibals.makePath._\'23caseor0'(_1325394,_1326276,_1326282,_1326288):-hnf(_1325394,_1328344,_1326282,_1328326),'blocked_missionaries_and_cannibals.makePath._\'23caseor0_1'(_1328344,_1326276,_1328326,_1326288).

'blocked_missionaries_and_cannibals.makePath._\'23caseor0_1'(_1328832,_1328834,_1328836,_1328838):-freeze(_1328836,freeze(_1328832,'blocked_blocked_missionaries_and_cannibals.makePath._\'23caseor0_1'(_1328832,_1328834,_1328836,_1328838))).
'blocked_blocked_missionaries_and_cannibals.makePath._\'23caseor0_1'('Prelude.True','Prelude.True',_1329170,_1329170).
'blocked_blocked_missionaries_and_cannibals.makePath._\'23caseor0_1'('Prelude.False',_1329980,_1329986,_1329992):-!,hnf('Prelude.failure'('missionaries_and_cannibals.makePath._\'23caseor0',['Prelude.False']),_1329980,_1329986,_1329992).
'blocked_blocked_missionaries_and_cannibals.makePath._\'23caseor0_1'('FAIL'(_1331324),'FAIL'(_1331324),_1331338,_1331338).

'missionaries_and_cannibals.makePath._\'23caseor0._\'23caseor0'(_1333520,_1333522,_1333524,_1333526,_1333528,_1333530):-freeze(_1333528,'blocked_missionaries_and_cannibals.makePath._\'23caseor0._\'23caseor0'(_1333520,_1333522,_1333524,_1333526,_1333528,_1333530)).
'blocked_missionaries_and_cannibals.makePath._\'23caseor0._\'23caseor0'(_1333616,_1333634,_1333652,_1334738,_1334744,_1334750):-hnf(_1333616,_1337278,_1334744,_1337248),'blocked_missionaries_and_cannibals.makePath._\'23caseor0._\'23caseor0_1'(_1337278,_1333634,_1333652,_1334738,_1337248,_1334750).

'blocked_missionaries_and_cannibals.makePath._\'23caseor0._\'23caseor0_1'(_1337842,_1337844,_1337846,_1337848,_1337850,_1337852):-freeze(_1337850,freeze(_1337842,'blocked_blocked_missionaries_and_cannibals.makePath._\'23caseor0._\'23caseor0_1'(_1337842,_1337844,_1337846,_1337848,_1337850,_1337852))).
'blocked_blocked_missionaries_and_cannibals.makePath._\'23caseor0._\'23caseor0_1'('Prelude.True',_1333634,_1333652,[_1333634|_1333652],_1338200,_1338200).
'blocked_blocked_missionaries_and_cannibals.makePath._\'23caseor0._\'23caseor0_1'('Prelude.False',_1333634,_1333652,_1339336,_1339342,_1339348):-!,hnf('Prelude.failure'('missionaries_and_cannibals.makePath._\'23caseor0._\'23caseor0',['Prelude.False']),_1339336,_1339342,_1339348).
'blocked_blocked_missionaries_and_cannibals.makePath._\'23caseor0._\'23caseor0_1'('FAIL'(_1340964),_1333634,_1333652,'FAIL'(_1340964),_1340978,_1340978).

:-costCenters(['']).




%%%%% Number of shared variables: 13


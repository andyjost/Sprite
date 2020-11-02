%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(qsortlet).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('qsortlet.split',split,3,'qsortlet.split',nofix,'FuncType'('TCons'('Prelude._Dict\'23Ord',[_G595286]),'FuncType'(_G595286,'FuncType'('TCons'([],[_G595286]),'TCons'('Prelude.(,)',['TCons'([],[_G595286]),'TCons'([],[_G595286])]))))).
functiontype('qsortlet.split._\'23selFP2\'23l','qsortlet.split._#selFP2#l',1,'qsortlet.split._\'23selFP2\'23l',nofix,'FuncType'('TCons'('Prelude.(,)',['TCons'([],[_G600916]),'TCons'([],[_G600916])]),'TCons'([],[_G600916]))).
functiontype('qsortlet.split._\'23selFP3\'23r','qsortlet.split._#selFP3#r',1,'qsortlet.split._\'23selFP3\'23r',nofix,'FuncType'('TCons'('Prelude.(,)',['TCons'([],[_G606474]),'TCons'([],[_G606474])]),'TCons'([],[_G606474]))).
functiontype('qsortlet.qsort',qsort,2,'qsortlet.qsort',nofix,'FuncType'('TCons'('Prelude._Dict\'23Ord',[_G612014]),'FuncType'('TCons'([],[_G612014]),'TCons'([],[_G612014])))).
functiontype('qsortlet.qsort._\'23selFP5\'23l','qsortlet.qsort._#selFP5#l',1,'qsortlet.qsort._\'23selFP5\'23l',nofix,'FuncType'('TCons'('Prelude.(,)',['TCons'([],[_G617599]),'TCons'([],[_G617599])]),'TCons'([],[_G617599]))).
functiontype('qsortlet.qsort._\'23selFP6\'23r','qsortlet.qsort._#selFP6#r',1,'qsortlet.qsort._\'23selFP6\'23r',nofix,'FuncType'('TCons'('Prelude.(,)',['TCons'([],[_G623157]),'TCons'([],[_G623157])]),'TCons'([],[_G623157]))).
functiontype('qsortlet.goal',goal,0,'qsortlet.goal',nofix,'TCons'([],['TCons'('Prelude.Int',[])])).
functiontype('qsortlet.split._\'23caseor0','qsortlet.split._#caseor0',6,'qsortlet.split._\'23caseor0',nofix,'FuncType'('TCons'('Prelude.Bool',[]),'FuncType'('TCons'('Prelude._Dict\'23Ord',[_G634291]),'FuncType'(_G634291,'FuncType'('TCons'([],[_G634291]),'FuncType'(_G634291,'FuncType'('TCons'([],[_G634291]),'TCons'('Prelude.(,)',['TCons'([],[_G634291]),'TCons'([],[_G634291])])))))))).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'qsortlet.split'(_G642248,_G642249,_G642250,_G642251,_G642252,_G642253):-freeze(_G642252,'blocked_qsortlet.split'(_G642248,_G642249,_G642250,_G642251,_G642252,_G642253)).
'blocked_qsortlet.split'(_G642296,_G642305,_G642314,_G643653,_G643656,_G643659):-hnf(_G642314,_G644113,_G643656,_G644098),'blocked_qsortlet.split_3'(_G644113,_G642296,_G642305,_G643653,_G644098,_G643659).

'blocked_qsortlet.split_3'(_G644257,_G644258,_G644259,_G644260,_G644261,_G644262):-freeze(_G644261,'blocked_blocked_qsortlet.split_3'(_G644257,_G644258,_G644259,_G644260,_G644261,_G644262)).
'blocked_blocked_qsortlet.split_3'([],_G642296,_G642305,'Prelude.(,)'([],[]),_G644367,_G644367).
'blocked_blocked_qsortlet.split_3'([_G642494|_G642503],_G642296,_G642305,_G644769,_G644772,_G644775):-!,makeShare(_G642521,_G645149),makeShare(_G642296,_G645159),makeShare(_G642305,_G645169),makeShare(_G642530,_G645179),makeShare(_G642539,_G645189),makeShare(_G642494,_G645199),hnf('Prelude.cond'('Prelude.letrec'(_G645149,'qsortlet.split'(_G645159,_G645169,_G642503)),'Prelude.cond'('Prelude.letrec'(_G645179,'qsortlet.split._\'23selFP2\'23l'(_G645149)),'Prelude.cond'('Prelude.letrec'(_G645189,'qsortlet.split._\'23selFP3\'23r'(_G645149)),'qsortlet.split._\'23caseor0'('Prelude.apply'('Prelude.apply'('Prelude.>='(_G645159),_G645169),_G645199),_G645159,_G645169,_G645179,_G645199,_G645189)))),_G644769,_G644772,_G644775).
'blocked_blocked_qsortlet.split_3'('FAIL'(_G648034),_G642296,_G642305,'FAIL'(_G648034),_G648041,_G648041):-nonvar(_G648034).

'qsortlet.split._\'23selFP2\'23l'(_G648608,_G648609,_G648610,_G648611):-freeze(_G648610,'blocked_qsortlet.split._\'23selFP2\'23l'(_G648608,_G648609,_G648610,_G648611)).
'blocked_qsortlet.split._\'23selFP2\'23l'(_G648646,_G648844,_G648847,_G648850):-hnf(_G648646,_G649554,_G648847,_G649545),'blocked_qsortlet.split._\'23selFP2\'23l_1'(_G649554,_G648844,_G649545,_G648850).

'blocked_qsortlet.split._\'23selFP2\'23l_1'(_G649741,_G649742,_G649743,_G649744):-freeze(_G649743,'blocked_blocked_qsortlet.split._\'23selFP2\'23l_1'(_G649741,_G649742,_G649743,_G649744)).
'blocked_blocked_qsortlet.split._\'23selFP2\'23l_1'('Prelude.(,)'(_G648700,_G648709),_G649901,_G649904,_G649907):-!,hnf(_G648700,_G649901,_G649904,_G649907).
'blocked_blocked_qsortlet.split._\'23selFP2\'23l_1'('FAIL'(_G650162),'FAIL'(_G650162),_G650169,_G650169):-nonvar(_G650162).

'qsortlet.split._\'23selFP3\'23r'(_G650728,_G650729,_G650730,_G650731):-freeze(_G650730,'blocked_qsortlet.split._\'23selFP3\'23r'(_G650728,_G650729,_G650730,_G650731)).
'blocked_qsortlet.split._\'23selFP3\'23r'(_G650766,_G650964,_G650967,_G650970):-hnf(_G650766,_G651674,_G650967,_G651665),'blocked_qsortlet.split._\'23selFP3\'23r_1'(_G651674,_G650964,_G651665,_G650970).

'blocked_qsortlet.split._\'23selFP3\'23r_1'(_G651861,_G651862,_G651863,_G651864):-freeze(_G651863,'blocked_blocked_qsortlet.split._\'23selFP3\'23r_1'(_G651861,_G651862,_G651863,_G651864)).
'blocked_blocked_qsortlet.split._\'23selFP3\'23r_1'('Prelude.(,)'(_G650820,_G650829),_G652021,_G652024,_G652027):-!,hnf(_G650829,_G652021,_G652024,_G652027).
'blocked_blocked_qsortlet.split._\'23selFP3\'23r_1'('FAIL'(_G652282),'FAIL'(_G652282),_G652289,_G652289):-nonvar(_G652282).

'qsortlet.qsort'(_G652620,_G652621,_G652622,_G652623,_G652624):-freeze(_G652623,'blocked_qsortlet.qsort'(_G652620,_G652621,_G652622,_G652623,_G652624)).
'blocked_qsortlet.qsort'(_G652663,_G652672,_G653829,_G653832,_G653835):-hnf(_G652672,_G654279,_G653832,_G654267),'blocked_qsortlet.qsort_2'(_G654279,_G652663,_G653829,_G654267,_G653835).

'blocked_qsortlet.qsort_2'(_G654422,_G654423,_G654424,_G654425,_G654426):-freeze(_G654425,'blocked_blocked_qsortlet.qsort_2'(_G654422,_G654423,_G654424,_G654425,_G654426)).
'blocked_blocked_qsortlet.qsort_2'([],_G652663,[],_G654527,_G654527).
'blocked_blocked_qsortlet.qsort_2'([_G652772|_G652781],_G652663,_G654772,_G654775,_G654778):-!,makeShare(_G652799,_G655046),makeShare(_G652663,_G655056),makeShare(_G652772,_G655066),makeShare(_G652808,_G655076),makeShare(_G652817,_G655086),hnf('Prelude.cond'('Prelude.letrec'(_G655046,'qsortlet.split'(_G655056,_G655066,_G652781)),'Prelude.cond'('Prelude.letrec'(_G655076,'qsortlet.qsort._\'23selFP5\'23l'(_G655046)),'Prelude.cond'('Prelude.letrec'(_G655086,'qsortlet.qsort._\'23selFP6\'23r'(_G655046)),'Prelude.++'('qsortlet.qsort'(_G655056,_G655076),[_G655066|'qsortlet.qsort'(_G655056,_G655086)])))),_G654772,_G654775,_G654778).
'blocked_blocked_qsortlet.qsort_2'('FAIL'(_G657601),_G652663,'FAIL'(_G657601),_G657608,_G657608):-nonvar(_G657601).

'qsortlet.qsort._\'23selFP5\'23l'(_G658171,_G658172,_G658173,_G658174):-freeze(_G658173,'blocked_qsortlet.qsort._\'23selFP5\'23l'(_G658171,_G658172,_G658173,_G658174)).
'blocked_qsortlet.qsort._\'23selFP5\'23l'(_G658209,_G658407,_G658410,_G658413):-hnf(_G658209,_G659117,_G658410,_G659108),'blocked_qsortlet.qsort._\'23selFP5\'23l_1'(_G659117,_G658407,_G659108,_G658413).

'blocked_qsortlet.qsort._\'23selFP5\'23l_1'(_G659304,_G659305,_G659306,_G659307):-freeze(_G659306,'blocked_blocked_qsortlet.qsort._\'23selFP5\'23l_1'(_G659304,_G659305,_G659306,_G659307)).
'blocked_blocked_qsortlet.qsort._\'23selFP5\'23l_1'('Prelude.(,)'(_G658263,_G658272),_G659464,_G659467,_G659470):-!,hnf(_G658263,_G659464,_G659467,_G659470).
'blocked_blocked_qsortlet.qsort._\'23selFP5\'23l_1'('FAIL'(_G659725),'FAIL'(_G659725),_G659732,_G659732):-nonvar(_G659725).

'qsortlet.qsort._\'23selFP6\'23r'(_G660291,_G660292,_G660293,_G660294):-freeze(_G660293,'blocked_qsortlet.qsort._\'23selFP6\'23r'(_G660291,_G660292,_G660293,_G660294)).
'blocked_qsortlet.qsort._\'23selFP6\'23r'(_G660329,_G660527,_G660530,_G660533):-hnf(_G660329,_G661237,_G660530,_G661228),'blocked_qsortlet.qsort._\'23selFP6\'23r_1'(_G661237,_G660527,_G661228,_G660533).

'blocked_qsortlet.qsort._\'23selFP6\'23r_1'(_G661424,_G661425,_G661426,_G661427):-freeze(_G661426,'blocked_blocked_qsortlet.qsort._\'23selFP6\'23r_1'(_G661424,_G661425,_G661426,_G661427)).
'blocked_blocked_qsortlet.qsort._\'23selFP6\'23r_1'('Prelude.(,)'(_G660383,_G660392),_G661584,_G661587,_G661590):-!,hnf(_G660392,_G661584,_G661587,_G661590).
'blocked_blocked_qsortlet.qsort._\'23selFP6\'23r_1'('FAIL'(_G661845),'FAIL'(_G661845),_G661852,_G661852):-nonvar(_G661845).

'qsortlet.goal'(_G662165,_G662166,_G662167):-freeze(_G662166,'blocked_qsortlet.goal'(_G662165,_G662166,_G662167)).
'blocked_qsortlet.goal'(_G662867,_G662870,_G662873):-hnf('qsortlet.qsort'('Prelude._inst\'23Prelude.Ord\'23Prelude.Int',[8,6,7,5,4,2,3,1]),_G662867,_G662870,_G662873).

'qsortlet.split._\'23caseor0'(_G664420,_G664421,_G664422,_G664423,_G664424,_G664425,_G664426,_G664427,_G664428):-freeze(_G664427,'blocked_qsortlet.split._\'23caseor0'(_G664420,_G664421,_G664422,_G664423,_G664424,_G664425,_G664426,_G664427,_G664428)).
'blocked_qsortlet.split._\'23caseor0'(_G664483,_G664492,_G664501,_G664510,_G664519,_G664528,_G665464,_G665467,_G665470):-hnf(_G664483,_G666170,_G665467,_G666146),'blocked_qsortlet.split._\'23caseor0_1'(_G666170,_G664492,_G664501,_G664510,_G664519,_G664528,_G665464,_G666146,_G665470).

'blocked_qsortlet.split._\'23caseor0_1'(_G666356,_G666357,_G666358,_G666359,_G666360,_G666361,_G666362,_G666363,_G666364):-freeze(_G666363,freeze(_G666356,'blocked_blocked_qsortlet.split._\'23caseor0_1'(_G666356,_G666357,_G666358,_G666359,_G666360,_G666361,_G666362,_G666363,_G666364))).
'blocked_blocked_qsortlet.split._\'23caseor0_1'('Prelude.True',_G664492,_G664501,_G664510,_G664519,_G664528,'Prelude.(,)'([_G664519|_G664510],_G664528),_G666550,_G666550).
'blocked_blocked_qsortlet.split._\'23caseor0_1'('Prelude.False',_G664492,_G664501,_G664510,_G664519,_G664528,_G668255,_G668258,_G668261):-!,makeShare(_G664519,_G667379),hnf('Prelude.apply'('Prelude.apply'('Prelude.<'(_G664492),_G664501),_G667379),_G669366,_G668258,_G669342),'blocked_blocked_qsortlet.split._\'23caseor0_1_Prelude.False_ComplexCase'(_G669366,_G664492,_G664501,_G664510,_G667379,_G664528,_G668255,_G669342,_G668261).

'blocked_blocked_qsortlet.split._\'23caseor0_1_Prelude.False_ComplexCase'(_G669669,_G669670,_G669671,_G669672,_G669673,_G669674,_G669675,_G669676,_G669677):-freeze(_G669676,freeze(_G669669,'blocked_blocked_blocked_qsortlet.split._\'23caseor0_1_Prelude.False_ComplexCase'(_G669669,_G669670,_G669671,_G669672,_G669673,_G669674,_G669675,_G669676,_G669677))).
'blocked_blocked_blocked_qsortlet.split._\'23caseor0_1_Prelude.False_ComplexCase'('Prelude.True',_G664492,_G664501,_G664510,_G667379,_G664528,'Prelude.(,)'(_G664510,[_G667379|_G664528]),_G669863,_G669863).
'blocked_blocked_blocked_qsortlet.split._\'23caseor0_1_Prelude.False_ComplexCase'('Prelude.False',_G664492,_G664501,_G664510,_G667379,_G664528,_G670669,_G670672,_G670675):-!,hnf('Prelude.failure'('qsortlet.split._\'23caseor0',['Prelude.False']),_G670669,_G670672,_G670675).
'blocked_blocked_blocked_qsortlet.split._\'23caseor0_1_Prelude.False_ComplexCase'('FAIL'(_G671492),_G664492,_G664501,_G664510,_G667379,_G664528,'FAIL'(_G671492),_G671499,_G671499).
'blocked_blocked_qsortlet.split._\'23caseor0_1'('FAIL'(_G671542),_G664492,_G664501,_G664510,_G664519,_G664528,'FAIL'(_G671542),_G671549,_G671549).

:-costCenters(['']).




%%%%% Number of shared variables: 12

%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(multgen).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('multgen.pairs',pairs,2,'multgen.pairs',nofix,'FuncType'('TCons'([],[_G358328]),'FuncType'('TCons'([],[_G358343]),'TCons'([],['TCons'('Prelude.(,)',[_G358328,_G358343])])))).
functiontype('multgen.pairs._\'23lambda1','multgen.pairs._#lambda1',2,'multgen.pairs._\'23lambda1',nofix,'FuncType'('TCons'([],[_G363973]),'FuncType'(_G363982,'TCons'([],['TCons'('Prelude.(,)',[_G363982,_G363973])])))).
functiontype('multgen.pairs._\'23lambda1._\'23lambda2','multgen.pairs._#lambda1._#lambda2',2,'multgen.pairs._\'23lambda1._\'23lambda2',nofix,'FuncType'(_G369618,'FuncType'(_G369627,'TCons'('Prelude.(,)',[_G369618,_G369627])))).
functiontype('multgen.goal1',goal1,0,'multgen.goal1',nofix,'TCons'([],['TCons'('Prelude.(,)',['TCons'('Prelude.Int',[]),'TCons'('Prelude.Int',[])])])).
functiontype('multgen.triangle',triangle,1,'multgen.triangle',nofix,'FuncType'('TCons'('Prelude.Int',[]),'TCons'([],['TCons'('Prelude.(,)',['TCons'('Prelude.Int',[]),'TCons'('Prelude.Int',[])])]))).
functiontype('multgen.triangle._\'23lambda3','multgen.triangle._#lambda3',1,'multgen.triangle._\'23lambda3',nofix,'FuncType'('TCons'('Prelude.Int',[]),'TCons'([],['TCons'('Prelude.(,)',['TCons'('Prelude.Int',[]),'TCons'('Prelude.Int',[])])]))).
functiontype('multgen.triangle._\'23lambda3._\'23lambda4','multgen.triangle._#lambda3._#lambda4',2,'multgen.triangle._\'23lambda3._\'23lambda4',nofix,'FuncType'('TCons'('Prelude.Int',[]),'FuncType'('TCons'('Prelude.Int',[]),'TCons'('Prelude.(,)',['TCons'('Prelude.Int',[]),'TCons'('Prelude.Int',[])])))).
functiontype('multgen.goal2',goal2,0,'multgen.goal2',nofix,'TCons'([],['TCons'('Prelude.(,)',['TCons'('Prelude.Int',[]),'TCons'('Prelude.Int',[])])])).
functiontype('multgen.pyTriple',pyTriple,4,'multgen.pyTriple',nofix,'FuncType'('TCons'('Prelude._Dict\'23Enum',[_G403755]),'FuncType'('TCons'('Prelude._Dict\'23Eq',[_G403755]),'FuncType'('TCons'('Prelude._Dict\'23Num',[_G403755]),'FuncType'(_G403755,'TCons'([],['TCons'('Prelude.(,,)',[_G403755,_G403755,_G403755])])))))).
functiontype('multgen.pyTriple._\'23lambda5','multgen.pyTriple._#lambda5',5,'multgen.pyTriple._\'23lambda5',nofix,'FuncType'(_G409529,'FuncType'('TCons'('Prelude._Dict\'23Enum',[_G409529]),'FuncType'('TCons'('Prelude._Dict\'23Eq',[_G409529]),'FuncType'('TCons'('Prelude._Dict\'23Num',[_G409529]),'FuncType'(_G409529,'TCons'([],['TCons'('Prelude.(,,)',[_G409529,_G409529,_G409529])]))))))).
functiontype('multgen.pyTriple._\'23lambda5._\'23lambda6','multgen.pyTriple._#lambda5._#lambda6',6,'multgen.pyTriple._\'23lambda5._\'23lambda6',nofix,'FuncType'(_G415387,'FuncType'(_G415387,'FuncType'('TCons'('Prelude._Dict\'23Enum',[_G415387]),'FuncType'('TCons'('Prelude._Dict\'23Eq',[_G415387]),'FuncType'('TCons'('Prelude._Dict\'23Num',[_G415387]),'FuncType'(_G415387,'TCons'([],['TCons'('Prelude.(,,)',[_G415387,_G415387,_G415387])])))))))).
functiontype('multgen.pyTriple._\'23lambda5._\'23lambda6._\'23lambda7','multgen.pyTriple._#lambda5._#lambda6._#lambda7',5,'multgen.pyTriple._\'23lambda5._\'23lambda6._\'23lambda7',nofix,'FuncType'(_G421284,'FuncType'(_G421284,'FuncType'('TCons'('Prelude._Dict\'23Eq',[_G421284]),'FuncType'('TCons'('Prelude._Dict\'23Num',[_G421284]),'FuncType'(_G421284,'TCons'([],['TCons'('Prelude.(,,)',[_G421284,_G421284,_G421284])]))))))).
functiontype('multgen.goal3',goal3,0,'multgen.goal3',nofix,'TCons'([],['TCons'('Prelude.(,,)',['TCons'('Prelude.Int',[]),'TCons'('Prelude.Int',[]),'TCons'('Prelude.Int',[])])])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'multgen.pairs'(_G435093,_G435094,_G435095,_G435096,_G435097):-freeze(_G435096,'blocked_multgen.pairs'(_G435093,_G435094,_G435095,_G435096,_G435097)).
'blocked_multgen.pairs'(_G435136,_G435145,_G435305,_G435308,_G435311):-hnf('Prelude.apply'('Prelude.concatMap'(partcall(1,'multgen.pairs._\'23lambda1',[_G435145])),_G435136),_G435305,_G435308,_G435311).

'multgen.pairs._\'23lambda1'(_G436323,_G436324,_G436325,_G436326,_G436327):-freeze(_G436326,'blocked_multgen.pairs._\'23lambda1'(_G436323,_G436324,_G436325,_G436326,_G436327)).
'blocked_multgen.pairs._\'23lambda1'(_G436366,_G436375,_G436495,_G436498,_G436501):-hnf('Prelude.map'(partcall(1,'multgen.pairs._\'23lambda1._\'23lambda2',[_G436375]),_G436366),_G436495,_G436498,_G436501).

'multgen.pairs._\'23lambda1._\'23lambda2'(_G437672,_G437673,_G437674,_G437675,_G437676):-freeze(_G437675,'blocked_multgen.pairs._\'23lambda1._\'23lambda2'(_G437672,_G437673,_G437674,_G437675,_G437676)).
'blocked_multgen.pairs._\'23lambda1._\'23lambda2'(_G437715,_G437724,'Prelude.(,)'(_G437715,_G437724),_G437807,_G437807).

'multgen.goal1'(_G438458,_G438459,_G438460):-freeze(_G438459,'blocked_multgen.goal1'(_G438458,_G438459,_G438460)).
'blocked_multgen.goal1'(_G438941,_G438944,_G438947):-hnf('multgen.pairs'([1,2,3],[4,5]),_G438941,_G438944,_G438947).

'multgen.triangle'(_G439954,_G439955,_G439956,_G439957):-freeze(_G439956,'blocked_multgen.triangle'(_G439954,_G439955,_G439956,_G439957)).
'blocked_multgen.triangle'(_G439992,_G440272,_G440275,_G440278):-hnf('Prelude.apply'('Prelude.concatMap'(partcall(1,'multgen.triangle._\'23lambda3',[])),'Prelude.apply'('Prelude.apply'('Prelude._impl\'23enumFromTo\'23Prelude.Enum\'23Prelude.Int',1),_G439992)),_G440272,_G440275,_G440278).

'multgen.triangle._\'23lambda3'(_G441702,_G441703,_G441704,_G441705):-freeze(_G441704,'blocked_multgen.triangle._\'23lambda3'(_G441702,_G441703,_G441704,_G441705)).
'blocked_multgen.triangle._\'23lambda3'(_G441740,_G442013,_G442016,_G442019):-makeShare(_G441740,_G442049),hnf('Prelude.map'(partcall(1,'multgen.triangle._\'23lambda3._\'23lambda4',[_G442049]),'Prelude.apply'('Prelude.apply'('Prelude._impl\'23enumFromTo\'23Prelude.Enum\'23Prelude.Int',1),_G442049)),_G442013,_G442016,_G442019).

'multgen.triangle._\'23lambda3._\'23lambda4'(_G443760,_G443761,_G443762,_G443763,_G443764):-freeze(_G443763,'blocked_multgen.triangle._\'23lambda3._\'23lambda4'(_G443760,_G443761,_G443762,_G443763,_G443764)).
'blocked_multgen.triangle._\'23lambda3._\'23lambda4'(_G443803,_G443812,'Prelude.(,)'(_G443803,_G443812),_G443895,_G443895).

'multgen.goal2'(_G444555,_G444556,_G444557):-freeze(_G444556,'blocked_multgen.goal2'(_G444555,_G444556,_G444557)).
'blocked_multgen.goal2'(_G444626,_G444629,_G444632):-hnf('multgen.triangle'(3),_G444626,_G444629,_G444632).

'multgen.pyTriple'(_G445166,_G445167,_G445168,_G445169,_G445170,_G445171,_G445172):-freeze(_G445171,'blocked_multgen.pyTriple'(_G445166,_G445167,_G445168,_G445169,_G445170,_G445171,_G445172)).
'blocked_multgen.pyTriple'(_G445219,_G445228,_G445237,_G445246,_G445804,_G445807,_G445810):-makeShare(_G445246,_G445942),makeShare(_G445219,_G445952),makeShare(_G445237,_G445962),hnf('Prelude.apply'('Prelude.concatMap'(partcall(1,'multgen.pyTriple._\'23lambda5',[_G445962,_G445228,_G445952,_G445942])),'Prelude.apply'('Prelude.apply'('Prelude.enumFromTo'(_G445952),'Prelude.apply'('Prelude.fromInt'(_G445962),2)),_G445942)),_G445804,_G445807,_G445810).

'multgen.pyTriple._\'23lambda5'(_G448071,_G448072,_G448073,_G448074,_G448075,_G448076,_G448077,_G448078):-freeze(_G448077,'blocked_multgen.pyTriple._\'23lambda5'(_G448071,_G448072,_G448073,_G448074,_G448075,_G448076,_G448077,_G448078)).
'blocked_multgen.pyTriple._\'23lambda5'(_G448129,_G448138,_G448147,_G448156,_G448165,_G448942,_G448945,_G448948):-makeShare(_G448129,_G449168),makeShare(_G448165,_G449178),makeShare(_G448138,_G449188),makeShare(_G448156,_G449198),hnf('Prelude.apply'('Prelude.concatMap'(partcall(1,'multgen.pyTriple._\'23lambda5._\'23lambda6',[_G449198,_G448147,_G449188,_G449178,_G449168])),'Prelude.apply'('Prelude.apply'('Prelude.enumFromTo'(_G449188),'Prelude.apply'('Prelude.apply'('Prelude.+'(_G449198),_G449178),'Prelude.apply'('Prelude.fromInt'(_G449198),1))),_G449168)),_G448942,_G448945,_G448948).

'multgen.pyTriple._\'23lambda5._\'23lambda6'(_G452087,_G452088,_G452089,_G452090,_G452091,_G452092,_G452093,_G452094,_G452095):-freeze(_G452094,'blocked_multgen.pyTriple._\'23lambda5._\'23lambda6'(_G452087,_G452088,_G452089,_G452090,_G452091,_G452092,_G452093,_G452094,_G452095)).
'blocked_multgen.pyTriple._\'23lambda5._\'23lambda6'(_G452150,_G452159,_G452168,_G452177,_G452186,_G452195,_G452939,_G452942,_G452945):-makeShare(_G452195,_G453169),makeShare(_G452186,_G453179),hnf('Prelude.apply'('Prelude.concatMap'(partcall(1,'multgen.pyTriple._\'23lambda5._\'23lambda6._\'23lambda7',[_G453179,_G452177,_G453169,_G452159])),'Prelude.apply'('Prelude.apply'('Prelude.enumFromTo'(_G452168),'Prelude.apply'('Prelude.apply'('Prelude.+'(_G453179),_G453169),'Prelude.apply'('Prelude.fromInt'(_G453179),1))),_G452150)),_G452939,_G452942,_G452945).

'multgen.pyTriple._\'23lambda5._\'23lambda6._\'23lambda7'(_G456118,_G456119,_G456120,_G456121,_G456122,_G456123,_G456124,_G456125):-freeze(_G456124,'blocked_multgen.pyTriple._\'23lambda5._\'23lambda6._\'23lambda7'(_G456118,_G456119,_G456120,_G456121,_G456122,_G456123,_G456124,_G456125)).
'blocked_multgen.pyTriple._\'23lambda5._\'23lambda6._\'23lambda7'(_G456176,_G456185,_G456194,_G456203,_G456212,_G460332,_G460335,_G460338):-makeShare(_G456203,_G457722),makeShare(_G456176,_G457732),makeShare(_G456185,_G457742),makeShare(_G456212,_G457752),hnf('Prelude.apply'('Prelude.apply'('Prelude.=='(_G456194),'Prelude.apply'('Prelude.apply'('Prelude.+'(_G457722),'Prelude.apply'('Prelude.apply'('Prelude.*'(_G457722),_G457732),_G457732)),'Prelude.apply'('Prelude.apply'('Prelude.*'(_G457722),_G457742),_G457742))),'Prelude.apply'('Prelude.apply'('Prelude.*'(_G457722),_G457752),_G457752)),_G461517,_G460335,_G461493),'blocked_multgen.pyTriple._\'23lambda5._\'23lambda6._\'23lambda7_ComplexCase'(_G461517,_G457732,_G457742,_G456194,_G457722,_G457752,_G460332,_G461493,_G460338).

'blocked_multgen.pyTriple._\'23lambda5._\'23lambda6._\'23lambda7_ComplexCase'(_G461835,_G461836,_G461837,_G461838,_G461839,_G461840,_G461841,_G461842,_G461843):-freeze(_G461842,freeze(_G461835,'blocked_blocked_multgen.pyTriple._\'23lambda5._\'23lambda6._\'23lambda7_ComplexCase'(_G461835,_G461836,_G461837,_G461838,_G461839,_G461840,_G461841,_G461842,_G461843))).
'blocked_blocked_multgen.pyTriple._\'23lambda5._\'23lambda6._\'23lambda7_ComplexCase'('Prelude.True',_G457732,_G457742,_G456194,_G457722,_G457752,['Prelude.(,,)'(_G457732,_G457742,_G457752)],_G462029,_G462029).
'blocked_blocked_multgen.pyTriple._\'23lambda5._\'23lambda6._\'23lambda7_ComplexCase'('Prelude.False',_G457732,_G457742,_G456194,_G457722,_G457752,[],_G462891,_G462891):-!.
'blocked_blocked_multgen.pyTriple._\'23lambda5._\'23lambda6._\'23lambda7_ComplexCase'('FAIL'(_G463354),_G457732,_G457742,_G456194,_G457722,_G457752,'FAIL'(_G463354),_G463361,_G463361).

'multgen.goal3'(_G463692,_G463693,_G463694):-freeze(_G463693,'blocked_multgen.goal3'(_G463692,_G463693,_G463694)).
'blocked_multgen.goal3'(_G463883,_G463886,_G463889):-hnf('multgen.pyTriple'('Prelude._inst\'23Prelude.Enum\'23Prelude.Int','Prelude._inst\'23Prelude.Eq\'23Prelude.Int','Prelude._inst\'23Prelude.Num\'23Prelude.Int',20),_G463883,_G463886,_G463889).

:-costCenters(['']).




%%%%% Number of shared variables: 14

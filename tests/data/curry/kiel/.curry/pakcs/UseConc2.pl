%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('ModConc').
:-importModule('Prelude').

:-curryModule('UseConc2').


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('UseConc2.main1',main1,0,'UseConc2.main1',nofix,'TCons'([],['TCons'('Prelude.Int',[])])).
functiontype('UseConc2.main2',main2,0,'UseConc2.main2',nofix,'TCons'([],['TCons'('Prelude.Int',[])])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'UseConc2.main1'(_G521884,_G521885,_G521886):-freeze(_G521885,'blocked_UseConc2.main1'(_G521884,_G521885,_G521886)).
'blocked_UseConc2.main1'(_G522221,_G522224,_G522227):-hnf('ModConc..+.'([1],['Prelude._impl\'23\'2B\'23Prelude.Num\'23Prelude.Int'(1,1)]),_G522221,_G522224,_G522227).

'UseConc2.main2'(_G523211,_G523212,_G523213):-freeze(_G523212,'blocked_UseConc2.main2'(_G523211,_G523212,_G523213)).
'blocked_UseConc2.main2'(_G523555,_G523558,_G523561):-hnf('Prelude.apply'('Prelude.apply'('ModConc.conc',[1]),[2]),_G523555,_G523558,_G523561).

:-costCenters(['']).




%%%%% Number of shared variables: 0

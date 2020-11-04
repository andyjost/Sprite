%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('ModConc').
:-importModule('Prelude').

:-curryModule('UseConc1').


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('UseConc1.goal1',goal1,0,'UseConc1.goal1',nofix,'TCons'([],['TCons'('Prelude.Int',[])])).
functiontype('UseConc1.goal2',goal2,0,'UseConc1.goal2',nofix,'TCons'([],['TCons'('Prelude.Int',[])])).
functiontype('UseConc1.goal3',goal3,0,'UseConc1.goal3',nofix,'TCons'([],['TCons'('Prelude.Int',[])])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'UseConc1.goal1'(_G537692,_G537693,_G537694):-freeze(_G537693,'blocked_UseConc1.goal1'(_G537692,_G537693,_G537694)).
'blocked_UseConc1.goal1'(_G538029,_G538032,_G538035):-hnf('ModConc..+.'([1],['Prelude._impl\'23\'2B\'23Prelude.Num\'23Prelude.Int'(1,1)]),_G538029,_G538032,_G538035).

'UseConc1.goal2'(_G539019,_G539020,_G539021):-freeze(_G539020,'blocked_UseConc1.goal2'(_G539019,_G539020,_G539021)).
'blocked_UseConc1.goal2'(_G539356,_G539359,_G539362):-hnf('ModConc..+.'([1],['Prelude._impl\'23\'2B\'23Prelude.Num\'23Prelude.Int'(1,1)]),_G539356,_G539359,_G539362).

'UseConc1.goal3'(_G540346,_G540347,_G540348):-freeze(_G540347,'blocked_UseConc1.goal3'(_G540346,_G540347,_G540348)).
'blocked_UseConc1.goal3'(_G540690,_G540693,_G540696):-hnf('Prelude.apply'('Prelude.apply'('ModConc.conc',[1]),[2]),_G540690,_G540693,_G540696).

:-costCenters(['']).




%%%%% Number of shared variables: 0

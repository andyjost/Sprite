%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule('ModConc').


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('ModConc.+',+,2,'ModConc.+',infixr(5),'FuncType'('TCons'([],[_G501157]),'FuncType'('TCons'([],[_G501157]),'TCons'([],[_G501157])))).
functiontype('ModConc..+.',.+.,2,'ModConc..+.',infixr(5),'FuncType'('TCons'([],[_G506697]),'FuncType'('TCons'([],[_G506697]),'TCons'([],[_G506697])))).
functiontype('ModConc.conc',conc,0,'ModConc.conc',nofix,'FuncType'('TCons'([],[_G512204]),'FuncType'('TCons'([],[_G512204]),'TCons'([],[_G512204])))).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'ModConc.+'(_G520028,_G520029,_G520030,_G520031,_G520032):-freeze(_G520031,'blocked_ModConc.+'(_G520028,_G520029,_G520030,_G520031,_G520032)).
'blocked_ModConc.+'(_G520071,_G520080,_G520160,_G520163,_G520166):-hnf('Prelude.++'(_G520071,_G520080),_G520160,_G520163,_G520166).

'ModConc..+.'(_G520778,_G520779,_G520780,_G520781,_G520782):-freeze(_G520781,'blocked_ModConc..+.'(_G520778,_G520779,_G520780,_G520781,_G520782)).
'blocked_ModConc..+.'(_G520821,_G520830,_G520910,_G520913,_G520916):-hnf('ModConc.+'(_G520821,_G520830),_G520910,_G520913,_G520916).

'ModConc.conc'(_G521496,_G521497,_G521498):-freeze(_G521497,'blocked_ModConc.conc'(_G521496,_G521497,_G521498)).
'blocked_ModConc.conc'(_G521534,_G521537,_G521540):-hnf(partcall(2,'ModConc.+',[]),_G521534,_G521537,_G521540).

:-costCenters(['']).




%%%%% Number of shared variables: 0

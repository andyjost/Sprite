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
functiontype('UseConc1.goal1',goal1,1,'UseConc1.goal1',nofix,'FuncType'('TCons'('Prelude._Dict\'23Num',[_G766593]),'TCons'([],[_G766593]))).
functiontype('UseConc1.goal2',goal2,1,'UseConc1.goal2',nofix,'FuncType'('TCons'('Prelude._Dict\'23Num',[_G772127]),'TCons'([],[_G772127]))).
functiontype('UseConc1.goal3',goal3,1,'UseConc1.goal3',nofix,'FuncType'('TCons'('Prelude._Dict\'23Num',[_G777661]),'TCons'([],[_G777661]))).
functiontype('UseConc1.main',main,0,'UseConc1.main',nofix,'TCons'('Prelude.(,,)',['TCons'([],['TCons'('Prelude.Int',[])]),'TCons'([],['TCons'('Prelude.Int',[])]),'TCons'([],['TCons'('Prelude.Int',[])])])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'UseConc1.goal1'(_G791170,_G791171,_G791172,_G791173):-freeze(_G791172,'blocked_UseConc1.goal1'(_G791170,_G791171,_G791172,_G791173)).
'blocked_UseConc1.goal1'(_G791208,_G791973,_G791976,_G791979):-makeShare(_G791208,_G792021),hnf('ModConc..+.'(['Prelude.apply'('Prelude.fromInt'(_G792021),1)],['Prelude.apply'('Prelude.apply'('Prelude.+'(_G792021),'Prelude.apply'('Prelude.fromInt'(_G792021),1)),'Prelude.apply'('Prelude.fromInt'(_G792021),1))]),_G791973,_G791976,_G791979).

'UseConc1.goal2'(_G793900,_G793901,_G793902,_G793903):-freeze(_G793902,'blocked_UseConc1.goal2'(_G793900,_G793901,_G793902,_G793903)).
'blocked_UseConc1.goal2'(_G793938,_G794703,_G794706,_G794709):-makeShare(_G793938,_G794751),hnf('ModConc..+.'(['Prelude.apply'('Prelude.fromInt'(_G794751),1)],['Prelude.apply'('Prelude.apply'('Prelude.+'(_G794751),'Prelude.apply'('Prelude.fromInt'(_G794751),1)),'Prelude.apply'('Prelude.fromInt'(_G794751),1))]),_G794703,_G794706,_G794709).

'UseConc1.goal3'(_G796630,_G796631,_G796632,_G796633):-freeze(_G796632,'blocked_UseConc1.goal3'(_G796630,_G796631,_G796632,_G796633)).
'blocked_UseConc1.goal3'(_G796668,_G797214,_G797217,_G797220):-makeShare(_G796668,_G797250),hnf('Prelude.apply'('Prelude.apply'('ModConc.conc',['Prelude.apply'('Prelude.fromInt'(_G797250),1)]),['Prelude.apply'('Prelude.fromInt'(_G797250),2)]),_G797214,_G797217,_G797220).

'UseConc1.main'(_G798685,_G798686,_G798687):-freeze(_G798686,'blocked_UseConc1.main'(_G798685,_G798686,_G798687)).
'blocked_UseConc1.main'('Prelude.(,,)'('UseConc1.goal1'('Prelude._inst\'23Prelude.Num\'23Prelude.Int'),'UseConc1.goal2'('Prelude._inst\'23Prelude.Num\'23Prelude.Int'),'UseConc1.goal3'('Prelude._inst\'23Prelude.Num\'23Prelude.Int')),_G798966,_G798966).

:-costCenters(['']).




%%%%% Number of shared variables: 3

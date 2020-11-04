%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(family_nd).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('family_nd.female',female,0,'family_nd.female',nofix,'TCons'('family_nd.Person',[])).
functiontype('family_nd.male',male,0,'family_nd.male',nofix,'TCons'('family_nd.Person',[])).
functiontype('family_nd.husband',husband,1,'family_nd.husband',nofix,'FuncType'('TCons'('family_nd.Person',[]),'TCons'('family_nd.Person',[]))).
functiontype('family_nd.mother',mother,1,'family_nd.mother',nofix,'FuncType'('TCons'('family_nd.Person',[]),'TCons'('family_nd.Person',[]))).
functiontype('family_nd.father',father,1,'family_nd.father',nofix,'FuncType'('TCons'('family_nd.Person',[]),'TCons'('family_nd.Person',[]))).
functiontype('family_nd.grandfather',grandfather,1,'family_nd.grandfather',nofix,'FuncType'('TCons'('family_nd.Person',[]),'TCons'('family_nd.Person',[]))).
functiontype('family_nd.ancestor',ancestor,1,'family_nd.ancestor',nofix,'FuncType'('TCons'('family_nd.Person',[]),'TCons'('family_nd.Person',[]))).
functiontype('family_nd.goal1',goal1,0,'family_nd.goal1',nofix,'TCons'('family_nd.Person',[])).
functiontype('family_nd.goal2',goal2,1,'family_nd.goal2',nofix,'FuncType'('TCons'('family_nd.Person',[]),'TCons'('family_nd.Person',[]))).
functiontype('family_nd.main2',main2,0,'family_nd.main2',nofix,'TCons'('Prelude.(,)',['TCons'('family_nd.Person',[]),'TCons'('family_nd.Person',[])])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('family_nd.Christine','Christine',0,'Christine',0,'TCons'('family_nd.Person',[]),['family_nd.Maria'/0,'family_nd.Monica'/0,'family_nd.Alice'/0,'family_nd.Susan'/0,'family_nd.Antony'/0,'family_nd.Bill'/0,'family_nd.John'/0,'family_nd.Frank'/0,'family_nd.Peter'/0,'family_nd.Andrew'/0]).
constructortype('family_nd.Maria','Maria',0,'Maria',1,'TCons'('family_nd.Person',[]),['family_nd.Christine'/0,'family_nd.Monica'/0,'family_nd.Alice'/0,'family_nd.Susan'/0,'family_nd.Antony'/0,'family_nd.Bill'/0,'family_nd.John'/0,'family_nd.Frank'/0,'family_nd.Peter'/0,'family_nd.Andrew'/0]).
constructortype('family_nd.Monica','Monica',0,'Monica',2,'TCons'('family_nd.Person',[]),['family_nd.Christine'/0,'family_nd.Maria'/0,'family_nd.Alice'/0,'family_nd.Susan'/0,'family_nd.Antony'/0,'family_nd.Bill'/0,'family_nd.John'/0,'family_nd.Frank'/0,'family_nd.Peter'/0,'family_nd.Andrew'/0]).
constructortype('family_nd.Alice','Alice',0,'Alice',3,'TCons'('family_nd.Person',[]),['family_nd.Christine'/0,'family_nd.Maria'/0,'family_nd.Monica'/0,'family_nd.Susan'/0,'family_nd.Antony'/0,'family_nd.Bill'/0,'family_nd.John'/0,'family_nd.Frank'/0,'family_nd.Peter'/0,'family_nd.Andrew'/0]).
constructortype('family_nd.Susan','Susan',0,'Susan',4,'TCons'('family_nd.Person',[]),['family_nd.Christine'/0,'family_nd.Maria'/0,'family_nd.Monica'/0,'family_nd.Alice'/0,'family_nd.Antony'/0,'family_nd.Bill'/0,'family_nd.John'/0,'family_nd.Frank'/0,'family_nd.Peter'/0,'family_nd.Andrew'/0]).
constructortype('family_nd.Antony','Antony',0,'Antony',5,'TCons'('family_nd.Person',[]),['family_nd.Christine'/0,'family_nd.Maria'/0,'family_nd.Monica'/0,'family_nd.Alice'/0,'family_nd.Susan'/0,'family_nd.Bill'/0,'family_nd.John'/0,'family_nd.Frank'/0,'family_nd.Peter'/0,'family_nd.Andrew'/0]).
constructortype('family_nd.Bill','Bill',0,'Bill',6,'TCons'('family_nd.Person',[]),['family_nd.Christine'/0,'family_nd.Maria'/0,'family_nd.Monica'/0,'family_nd.Alice'/0,'family_nd.Susan'/0,'family_nd.Antony'/0,'family_nd.John'/0,'family_nd.Frank'/0,'family_nd.Peter'/0,'family_nd.Andrew'/0]).
constructortype('family_nd.John','John',0,'John',7,'TCons'('family_nd.Person',[]),['family_nd.Christine'/0,'family_nd.Maria'/0,'family_nd.Monica'/0,'family_nd.Alice'/0,'family_nd.Susan'/0,'family_nd.Antony'/0,'family_nd.Bill'/0,'family_nd.Frank'/0,'family_nd.Peter'/0,'family_nd.Andrew'/0]).
constructortype('family_nd.Frank','Frank',0,'Frank',8,'TCons'('family_nd.Person',[]),['family_nd.Christine'/0,'family_nd.Maria'/0,'family_nd.Monica'/0,'family_nd.Alice'/0,'family_nd.Susan'/0,'family_nd.Antony'/0,'family_nd.Bill'/0,'family_nd.John'/0,'family_nd.Peter'/0,'family_nd.Andrew'/0]).
constructortype('family_nd.Peter','Peter',0,'Peter',9,'TCons'('family_nd.Person',[]),['family_nd.Christine'/0,'family_nd.Maria'/0,'family_nd.Monica'/0,'family_nd.Alice'/0,'family_nd.Susan'/0,'family_nd.Antony'/0,'family_nd.Bill'/0,'family_nd.John'/0,'family_nd.Frank'/0,'family_nd.Andrew'/0]).
constructortype('family_nd.Andrew','Andrew',0,'Andrew',10,'TCons'('family_nd.Person',[]),['family_nd.Christine'/0,'family_nd.Maria'/0,'family_nd.Monica'/0,'family_nd.Alice'/0,'family_nd.Susan'/0,'family_nd.Antony'/0,'family_nd.Bill'/0,'family_nd.John'/0,'family_nd.Frank'/0,'family_nd.Peter'/0]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'family_nd.female'(_G688294,_G688295,_G688296):-freeze(_G688295,'blocked_family_nd.female'(_G688294,_G688295,_G688296)).
'blocked_family_nd.female'('family_nd.Christine',_G688767,_G688767).
'blocked_family_nd.female'('family_nd.Maria',_G688934,_G688934).
'blocked_family_nd.female'('family_nd.Monica',_G689089,_G689089).
'blocked_family_nd.female'('family_nd.Alice',_G689247,_G689247).
'blocked_family_nd.female'('family_nd.Susan',_G689402,_G689402).

'family_nd.male'(_G689863,_G689864,_G689865):-freeze(_G689864,'blocked_family_nd.male'(_G689863,_G689864,_G689865)).
'blocked_family_nd.male'('family_nd.Antony',_G690564,_G690564).
'blocked_family_nd.male'('family_nd.Bill',_G690716,_G690716).
'blocked_family_nd.male'('family_nd.John',_G690862,_G690862).
'blocked_family_nd.male'('family_nd.Frank',_G691008,_G691008).
'blocked_family_nd.male'('family_nd.Peter',_G691157,_G691157).
'blocked_family_nd.male'('family_nd.Andrew',_G691306,_G691306).

'family_nd.husband'(_G691818,_G691819,_G691820,_G691821):-freeze(_G691820,'blocked_family_nd.husband'(_G691818,_G691819,_G691820,_G691821)).
'blocked_family_nd.husband'(_G691856,_G693581,_G693584,_G693587):-hnf(_G691856,_G694075,_G693584,_G694066),'blocked_family_nd.husband_1'(_G694075,_G693581,_G694066,_G693587).

'blocked_family_nd.husband_1'(_G694226,_G694227,_G694228,_G694229):-freeze(_G694228,'blocked_blocked_family_nd.husband_1'(_G694226,_G694227,_G694228,_G694229)).
'blocked_blocked_family_nd.husband_1'('family_nd.Christine','family_nd.Antony',_G694434,_G694434).
'blocked_blocked_family_nd.husband_1'('family_nd.Maria','family_nd.Bill',_G694776,_G694776).
'blocked_blocked_family_nd.husband_1'('family_nd.Monica','family_nd.John',_G695118,_G695118).
'blocked_blocked_family_nd.husband_1'('family_nd.Alice','family_nd.Frank',_G695499,_G695499):-!.
'blocked_blocked_family_nd.husband_1'('family_nd.Susan',_G695886,_G695889,_G695892):-!,hnf('Prelude.failure'('family_nd.husband',['family_nd.Susan']),_G695886,_G695889,_G695892).
'blocked_blocked_family_nd.husband_1'('family_nd.Antony',_G696534,_G696537,_G696540):-hnf('Prelude.failure'('family_nd.husband',['family_nd.Antony']),_G696534,_G696537,_G696540).
'blocked_blocked_family_nd.husband_1'('family_nd.Bill',_G697164,_G697167,_G697170):-hnf('Prelude.failure'('family_nd.husband',['family_nd.Bill']),_G697164,_G697167,_G697170).
'blocked_blocked_family_nd.husband_1'('family_nd.John',_G697788,_G697791,_G697794):-hnf('Prelude.failure'('family_nd.husband',['family_nd.John']),_G697788,_G697791,_G697794).
'blocked_blocked_family_nd.husband_1'('family_nd.Frank',_G698418,_G698421,_G698424):-hnf('Prelude.failure'('family_nd.husband',['family_nd.Frank']),_G698418,_G698421,_G698424).
'blocked_blocked_family_nd.husband_1'('family_nd.Peter',_G699051,_G699054,_G699057):-hnf('Prelude.failure'('family_nd.husband',['family_nd.Peter']),_G699051,_G699054,_G699057).
'blocked_blocked_family_nd.husband_1'('family_nd.Andrew',_G699690,_G699693,_G699696):-!,hnf('Prelude.failure'('family_nd.husband',['family_nd.Andrew']),_G699690,_G699693,_G699696).
'blocked_blocked_family_nd.husband_1'('FAIL'(_G700191),'FAIL'(_G700191),_G700198,_G700198).

'family_nd.mother'(_G700563,_G700564,_G700565,_G700566):-freeze(_G700565,'blocked_family_nd.mother'(_G700563,_G700564,_G700565,_G700566)).
'blocked_family_nd.mother'(_G700601,_G702003,_G702006,_G702009):-hnf(_G700601,_G702479,_G702006,_G702470),'blocked_family_nd.mother_1'(_G702479,_G702003,_G702470,_G702009).

'blocked_family_nd.mother_1'(_G702627,_G702628,_G702629,_G702630):-freeze(_G702629,'blocked_blocked_family_nd.mother_1'(_G702627,_G702628,_G702629,_G702630)).
'blocked_blocked_family_nd.mother_1'('family_nd.John','family_nd.Christine',_G702805,_G702805).
'blocked_blocked_family_nd.mother_1'('family_nd.Alice','family_nd.Christine',_G703153,_G703153).
'blocked_blocked_family_nd.mother_1'('family_nd.Frank','family_nd.Maria',_G703501,_G703501).
'blocked_blocked_family_nd.mother_1'('family_nd.Susan','family_nd.Monica',_G703837,_G703837).
'blocked_blocked_family_nd.mother_1'('family_nd.Peter','family_nd.Monica',_G704176,_G704176).
'blocked_blocked_family_nd.mother_1'('family_nd.Andrew','family_nd.Alice',_G704566,_G704566):-!.
'blocked_blocked_family_nd.mother_1'('family_nd.Christine',_G704974,_G704977,_G704980):-!,hnf('Prelude.failure'('family_nd.mother',['family_nd.Christine']),_G704974,_G704977,_G704980).
'blocked_blocked_family_nd.mother_1'('family_nd.Maria',_G705622,_G705625,_G705628):-hnf('Prelude.failure'('family_nd.mother',['family_nd.Maria']),_G705622,_G705625,_G705628).
'blocked_blocked_family_nd.mother_1'('family_nd.Monica',_G706255,_G706258,_G706261):-hnf('Prelude.failure'('family_nd.mother',['family_nd.Monica']),_G706255,_G706258,_G706261).
'blocked_blocked_family_nd.mother_1'('family_nd.Antony',_G706891,_G706894,_G706897):-hnf('Prelude.failure'('family_nd.mother',['family_nd.Antony']),_G706891,_G706894,_G706897).
'blocked_blocked_family_nd.mother_1'('family_nd.Bill',_G707515,_G707518,_G707521):-!,hnf('Prelude.failure'('family_nd.mother',['family_nd.Bill']),_G707515,_G707518,_G707521).
'blocked_blocked_family_nd.mother_1'('FAIL'(_G708004),'FAIL'(_G708004),_G708011,_G708011).

'family_nd.father'(_G708376,_G708377,_G708378,_G708379):-freeze(_G708378,'blocked_family_nd.father'(_G708376,_G708377,_G708378,_G708379)).
'blocked_family_nd.father'(_G708414,_G708501,_G708504,_G708507):-hnf('family_nd.husband'('family_nd.mother'(_G708414)),_G708501,_G708504,_G708507).

'family_nd.grandfather'(_G709280,_G709281,_G709282,_G709283):-freeze(_G709282,'blocked_family_nd.grandfather'(_G709280,_G709281,_G709282,_G709283)).
'blocked_family_nd.grandfather'(_G709318,_G709514,_G709517,_G709520):-hnf('family_nd.father'('family_nd.father'(_G709318)),_G709514,_G709517,_G709520).
'blocked_family_nd.grandfather'(_G709318,_G709870,_G709873,_G709876):-hnf('family_nd.father'('family_nd.mother'(_G709318)),_G709870,_G709873,_G709876).

'family_nd.ancestor'(_G710607,_G710608,_G710609,_G710610):-freeze(_G710609,'blocked_family_nd.ancestor'(_G710607,_G710608,_G710609,_G710610)).
'blocked_family_nd.ancestor'(_G710645,_G711123,_G711126,_G711129):-hnf('family_nd.father'(_G710645),_G711123,_G711126,_G711129).
'blocked_family_nd.ancestor'(_G710645,_G711374,_G711377,_G711380):-hnf('family_nd.mother'(_G710645),_G711374,_G711377,_G711380).
'blocked_family_nd.ancestor'(_G710645,_G711625,_G711628,_G711631):-hnf('family_nd.father'('family_nd.ancestor'(_G710645)),_G711625,_G711628,_G711631).
'blocked_family_nd.ancestor'(_G710645,_G711978,_G711981,_G711984):-hnf('family_nd.mother'('family_nd.ancestor'(_G710645)),_G711978,_G711981,_G711984).

'family_nd.goal1'(_G712658,_G712659,_G712660):-freeze(_G712659,'blocked_family_nd.goal1'(_G712658,_G712659,_G712660)).
'blocked_family_nd.goal1'(_G712736,_G712739,_G712742):-hnf('family_nd.father'('family_nd.John'),_G712736,_G712739,_G712742).

'family_nd.goal2'(_G713316,_G713317,_G713318,_G713319):-freeze(_G713318,'blocked_family_nd.goal2'(_G713316,_G713317,_G713318,_G713319)).
'blocked_family_nd.goal2'(_G713354,_G713401,_G713404,_G713407):-hnf('family_nd.grandfather'(_G713354),_G713401,_G713404,_G713407).

'family_nd.main2'(_G713985,_G713986,_G713987):-freeze(_G713986,'blocked_family_nd.main2'(_G713985,_G713986,_G713987)).
'blocked_family_nd.main2'('Prelude.(,)'('family_nd.grandfather'(_G714176),_G714176),_G714147,_G714150):-makeShare(_G714021,_G714176),_G714147=_G714150.

:-costCenters(['']).




%%%%% Number of shared variables: 1

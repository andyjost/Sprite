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
functiontype('family_nd.goal3',goal3,0,'family_nd.goal3',nofix,'TCons'('family_nd.Person',[])).

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
'family_nd.female'(_G684152,_G684153,_G684154):-freeze(_G684153,'blocked_family_nd.female'(_G684152,_G684153,_G684154)).
'blocked_family_nd.female'('family_nd.Christine',_G684625,_G684625).
'blocked_family_nd.female'('family_nd.Maria',_G684792,_G684792).
'blocked_family_nd.female'('family_nd.Monica',_G684947,_G684947).
'blocked_family_nd.female'('family_nd.Alice',_G685105,_G685105).
'blocked_family_nd.female'('family_nd.Susan',_G685260,_G685260).

'family_nd.male'(_G685721,_G685722,_G685723):-freeze(_G685722,'blocked_family_nd.male'(_G685721,_G685722,_G685723)).
'blocked_family_nd.male'('family_nd.Antony',_G686422,_G686422).
'blocked_family_nd.male'('family_nd.Bill',_G686574,_G686574).
'blocked_family_nd.male'('family_nd.John',_G686720,_G686720).
'blocked_family_nd.male'('family_nd.Frank',_G686866,_G686866).
'blocked_family_nd.male'('family_nd.Peter',_G687015,_G687015).
'blocked_family_nd.male'('family_nd.Andrew',_G687164,_G687164).

'family_nd.husband'(_G687676,_G687677,_G687678,_G687679):-freeze(_G687678,'blocked_family_nd.husband'(_G687676,_G687677,_G687678,_G687679)).
'blocked_family_nd.husband'(_G687714,_G689439,_G689442,_G689445):-hnf(_G687714,_G689933,_G689442,_G689924),'blocked_family_nd.husband_1'(_G689933,_G689439,_G689924,_G689445).

'blocked_family_nd.husband_1'(_G690084,_G690085,_G690086,_G690087):-freeze(_G690086,'blocked_blocked_family_nd.husband_1'(_G690084,_G690085,_G690086,_G690087)).
'blocked_blocked_family_nd.husband_1'('family_nd.Christine','family_nd.Antony',_G690292,_G690292).
'blocked_blocked_family_nd.husband_1'('family_nd.Maria','family_nd.Bill',_G690634,_G690634).
'blocked_blocked_family_nd.husband_1'('family_nd.Monica','family_nd.John',_G690976,_G690976).
'blocked_blocked_family_nd.husband_1'('family_nd.Alice','family_nd.Frank',_G691357,_G691357):-!.
'blocked_blocked_family_nd.husband_1'('family_nd.Susan',_G691744,_G691747,_G691750):-!,hnf('Prelude.failure'('family_nd.husband',['family_nd.Susan']),_G691744,_G691747,_G691750).
'blocked_blocked_family_nd.husband_1'('family_nd.Antony',_G692392,_G692395,_G692398):-hnf('Prelude.failure'('family_nd.husband',['family_nd.Antony']),_G692392,_G692395,_G692398).
'blocked_blocked_family_nd.husband_1'('family_nd.Bill',_G693022,_G693025,_G693028):-hnf('Prelude.failure'('family_nd.husband',['family_nd.Bill']),_G693022,_G693025,_G693028).
'blocked_blocked_family_nd.husband_1'('family_nd.John',_G693646,_G693649,_G693652):-hnf('Prelude.failure'('family_nd.husband',['family_nd.John']),_G693646,_G693649,_G693652).
'blocked_blocked_family_nd.husband_1'('family_nd.Frank',_G694276,_G694279,_G694282):-hnf('Prelude.failure'('family_nd.husband',['family_nd.Frank']),_G694276,_G694279,_G694282).
'blocked_blocked_family_nd.husband_1'('family_nd.Peter',_G694909,_G694912,_G694915):-hnf('Prelude.failure'('family_nd.husband',['family_nd.Peter']),_G694909,_G694912,_G694915).
'blocked_blocked_family_nd.husband_1'('family_nd.Andrew',_G695548,_G695551,_G695554):-!,hnf('Prelude.failure'('family_nd.husband',['family_nd.Andrew']),_G695548,_G695551,_G695554).
'blocked_blocked_family_nd.husband_1'('FAIL'(_G696049),'FAIL'(_G696049),_G696056,_G696056).

'family_nd.mother'(_G696421,_G696422,_G696423,_G696424):-freeze(_G696423,'blocked_family_nd.mother'(_G696421,_G696422,_G696423,_G696424)).
'blocked_family_nd.mother'(_G696459,_G697861,_G697864,_G697867):-hnf(_G696459,_G698337,_G697864,_G698328),'blocked_family_nd.mother_1'(_G698337,_G697861,_G698328,_G697867).

'blocked_family_nd.mother_1'(_G698485,_G698486,_G698487,_G698488):-freeze(_G698487,'blocked_blocked_family_nd.mother_1'(_G698485,_G698486,_G698487,_G698488)).
'blocked_blocked_family_nd.mother_1'('family_nd.John','family_nd.Christine',_G698663,_G698663).
'blocked_blocked_family_nd.mother_1'('family_nd.Alice','family_nd.Christine',_G699011,_G699011).
'blocked_blocked_family_nd.mother_1'('family_nd.Frank','family_nd.Maria',_G699359,_G699359).
'blocked_blocked_family_nd.mother_1'('family_nd.Susan','family_nd.Monica',_G699695,_G699695).
'blocked_blocked_family_nd.mother_1'('family_nd.Peter','family_nd.Monica',_G700034,_G700034).
'blocked_blocked_family_nd.mother_1'('family_nd.Andrew','family_nd.Alice',_G700424,_G700424):-!.
'blocked_blocked_family_nd.mother_1'('family_nd.Christine',_G700832,_G700835,_G700838):-!,hnf('Prelude.failure'('family_nd.mother',['family_nd.Christine']),_G700832,_G700835,_G700838).
'blocked_blocked_family_nd.mother_1'('family_nd.Maria',_G701480,_G701483,_G701486):-hnf('Prelude.failure'('family_nd.mother',['family_nd.Maria']),_G701480,_G701483,_G701486).
'blocked_blocked_family_nd.mother_1'('family_nd.Monica',_G702113,_G702116,_G702119):-hnf('Prelude.failure'('family_nd.mother',['family_nd.Monica']),_G702113,_G702116,_G702119).
'blocked_blocked_family_nd.mother_1'('family_nd.Antony',_G702749,_G702752,_G702755):-hnf('Prelude.failure'('family_nd.mother',['family_nd.Antony']),_G702749,_G702752,_G702755).
'blocked_blocked_family_nd.mother_1'('family_nd.Bill',_G703373,_G703376,_G703379):-!,hnf('Prelude.failure'('family_nd.mother',['family_nd.Bill']),_G703373,_G703376,_G703379).
'blocked_blocked_family_nd.mother_1'('FAIL'(_G703862),'FAIL'(_G703862),_G703869,_G703869).

'family_nd.father'(_G704234,_G704235,_G704236,_G704237):-freeze(_G704236,'blocked_family_nd.father'(_G704234,_G704235,_G704236,_G704237)).
'blocked_family_nd.father'(_G704272,_G704359,_G704362,_G704365):-hnf('family_nd.husband'('family_nd.mother'(_G704272)),_G704359,_G704362,_G704365).

'family_nd.grandfather'(_G705138,_G705139,_G705140,_G705141):-freeze(_G705140,'blocked_family_nd.grandfather'(_G705138,_G705139,_G705140,_G705141)).
'blocked_family_nd.grandfather'(_G705176,_G705372,_G705375,_G705378):-hnf('family_nd.father'('family_nd.father'(_G705176)),_G705372,_G705375,_G705378).
'blocked_family_nd.grandfather'(_G705176,_G705728,_G705731,_G705734):-hnf('family_nd.father'('family_nd.mother'(_G705176)),_G705728,_G705731,_G705734).

'family_nd.ancestor'(_G706465,_G706466,_G706467,_G706468):-freeze(_G706467,'blocked_family_nd.ancestor'(_G706465,_G706466,_G706467,_G706468)).
'blocked_family_nd.ancestor'(_G706503,_G706981,_G706984,_G706987):-hnf('family_nd.father'(_G706503),_G706981,_G706984,_G706987).
'blocked_family_nd.ancestor'(_G706503,_G707232,_G707235,_G707238):-hnf('family_nd.mother'(_G706503),_G707232,_G707235,_G707238).
'blocked_family_nd.ancestor'(_G706503,_G707483,_G707486,_G707489):-hnf('family_nd.father'('family_nd.ancestor'(_G706503)),_G707483,_G707486,_G707489).
'blocked_family_nd.ancestor'(_G706503,_G707836,_G707839,_G707842):-hnf('family_nd.mother'('family_nd.ancestor'(_G706503)),_G707836,_G707839,_G707842).

'family_nd.goal1'(_G708516,_G708517,_G708518):-freeze(_G708517,'blocked_family_nd.goal1'(_G708516,_G708517,_G708518)).
'blocked_family_nd.goal1'(_G708594,_G708597,_G708600):-hnf('family_nd.father'('family_nd.John'),_G708594,_G708597,_G708600).

'family_nd.goal2'(_G709174,_G709175,_G709176,_G709177):-freeze(_G709176,'blocked_family_nd.goal2'(_G709174,_G709175,_G709176,_G709177)).
'blocked_family_nd.goal2'(_G709212,_G709259,_G709262,_G709265):-hnf('family_nd.grandfather'(_G709212),_G709259,_G709262,_G709265).

'family_nd.goal3'(_G709843,_G709844,_G709845):-freeze(_G709844,'blocked_family_nd.goal3'(_G709843,_G709844,_G709845)).
'blocked_family_nd.goal3'(_G709921,_G709924,_G709927):-hnf('family_nd.ancestor'('family_nd.Andrew'),_G709921,_G709924,_G709927).

:-costCenters(['']).




%%%%% Number of shared variables: 0

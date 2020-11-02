%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(rev).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('rev.append',append,2,'rev.append',nofix,'FuncType'('TCons'([],[_G528832]),'FuncType'('TCons'([],[_G528832]),'TCons'([],[_G528832])))).
functiontype('rev.rev',rev,1,'rev.rev',nofix,'FuncType'('TCons'([],[_G534273]),'TCons'([],[_G534273]))).
functiontype('rev.goal1',goal1,0,'rev.goal1',nofix,'TCons'([],['TCons'('Prelude.Int',[])])).
functiontype('rev.goal2',goal2,0,'rev.goal2',nofix,'TCons'([],['TCons'('Prelude.Int',[])])).
functiontype('rev.goal3',goal3,0,'rev.goal3',nofix,'TCons'([],['TCons'('Prelude.Int',[])])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'rev.append'(_G558451,_G558452,_G558453,_G558454,_G558455):-freeze(_G558454,'blocked_rev.append'(_G558451,_G558452,_G558453,_G558454,_G558455)).
'blocked_rev.append'(_G558494,_G558503,_G558829,_G558832,_G558835):-hnf(_G558494,_G559207,_G558832,_G559195),'blocked_rev.append_1'(_G559207,_G558503,_G558829,_G559195,_G558835).

'blocked_rev.append_1'(_G559338,_G559339,_G559340,_G559341,_G559342):-freeze(_G559341,'blocked_blocked_rev.append_1'(_G559338,_G559339,_G559340,_G559341,_G559342)).
'blocked_blocked_rev.append_1'([],_G558503,_G559440,_G559443,_G559446):-hnf(_G558503,_G559440,_G559443,_G559446).
'blocked_blocked_rev.append_1'([_G558596|_G558605],_G558503,[_G558596|'rev.append'(_G558605,_G558503)],_G559683,_G559683):-!.
'blocked_blocked_rev.append_1'('FAIL'(_G560138),_G558503,'FAIL'(_G560138),_G560145,_G560145):-nonvar(_G560138).

'rev.rev'(_G560354,_G560355,_G560356,_G560357):-freeze(_G560356,'blocked_rev.rev'(_G560354,_G560355,_G560356,_G560357)).
'blocked_rev.rev'(_G560392,_G560763,_G560766,_G560769):-hnf(_G560392,_G561077,_G560766,_G561068),'blocked_rev.rev_1'(_G561077,_G560763,_G561068,_G560769).

'blocked_rev.rev_1'(_G561198,_G561199,_G561200,_G561201):-freeze(_G561200,'blocked_blocked_rev.rev_1'(_G561198,_G561199,_G561200,_G561201)).
'blocked_blocked_rev.rev_1'([],[],_G561298,_G561298).
'blocked_blocked_rev.rev_1'([_G560492|_G560501],_G561487,_G561490,_G561493):-!,hnf('rev.append'('rev.rev'(_G560501),[_G560492]),_G561487,_G561490,_G561493).
'blocked_blocked_rev.rev_1'('FAIL'(_G561973),'FAIL'(_G561973),_G561980,_G561980):-nonvar(_G561973).

'rev.goal1'(_G562221,_G562222,_G562223):-freeze(_G562222,'blocked_rev.goal1'(_G562221,_G562222,_G562223)).
'blocked_rev.goal1'(_G562631,_G562634,_G562637):-hnf('rev.append'([1,2],[3,4]),_G562631,_G562634,_G562637).

'rev.goal2'(_G563412,_G563413,_G563414):-freeze(_G563413,'blocked_rev.goal2'(_G563412,_G563413,_G563414)).
'blocked_rev.goal2'(_G563782,_G563785,_G563788):-hnf('rev.rev'([1,2,3,4]),_G563782,_G563785,_G563788).

'rev.goal3'(_G564507,_G564508,_G564509):-freeze(_G564508,'blocked_rev.goal3'(_G564507,_G564508,_G564509)).
'blocked_rev.goal3'(_G565315,_G565318,_G565321):-hnf('rev.rev'([1,2,3,4,5,6,7,8,9,10]),_G565315,_G565318,_G565321).

:-costCenters(['']).




%%%%% Number of shared variables: 0

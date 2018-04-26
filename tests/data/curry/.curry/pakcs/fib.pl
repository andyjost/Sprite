%PAKCS1.15 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(fib).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('fib.fib',fib,1,'fib.fib',nofix,'FuncType'('TCons'('Prelude.Int',[]),'TCons'('Prelude.Int',[]))).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'fib.fib'(_G36502,_G36503,_G36504,_G36505):-freeze(_G36504,'blocked_fib.fib'(_G36502,_G36503,_G36504,_G36505)).
'blocked_fib.fib'(_G36540,_G37859,_G37862,_G37865):-makeShare(_G36540,_G37296),hnf('Prelude.<'(_G37296,2),_G38206,_G37862,_G38194),'blocked_fib.fib_ComplexCase'(_G38206,_G37296,_G37859,_G38194,_G37865).

'blocked_fib.fib_ComplexCase'(_G38367,_G38368,_G38369,_G38370,_G38371):-freeze(_G38370,freeze(_G38367,'blocked_blocked_fib.fib_ComplexCase'(_G38367,_G38368,_G38369,_G38370,_G38371))).
'blocked_blocked_fib.fib_ComplexCase'('Prelude.True',_G37296,1,_G38541,_G38541).
'blocked_blocked_fib.fib_ComplexCase'('Prelude.False',_G37296,_G39227,_G39230,_G39233):-!,hnf('Prelude.otherwise',_G40148,_G39230,_G40136),'blocked_blocked_fib.fib_ComplexCase_Prelude.False_ComplexCase'(_G40148,_G37296,_G39227,_G40136,_G39233).

'blocked_blocked_fib.fib_ComplexCase_Prelude.False_ComplexCase'(_G40414,_G40415,_G40416,_G40417,_G40418):-freeze(_G40417,freeze(_G40414,'blocked_blocked_blocked_fib.fib_ComplexCase_Prelude.False_ComplexCase'(_G40414,_G40415,_G40416,_G40417,_G40418))).
'blocked_blocked_blocked_fib.fib_ComplexCase_Prelude.False_ComplexCase'('Prelude.True',_G37296,_G40585,_G40588,_G40591):-makeShare(_G37296,_G40625),hnf('Prelude.+'('fib.fib'('Prelude.-'(_G40625,1)),'fib.fib'('Prelude.-'(_G40625,2))),_G40585,_G40588,_G40591).
'blocked_blocked_blocked_fib.fib_ComplexCase_Prelude.False_ComplexCase'('Prelude.False',_G37296,_G41661,_G41664,_G41667):-!,hnf('Prelude.failure'('fib.fib',['Prelude.False']),_G41661,_G41664,_G41667).
'blocked_blocked_blocked_fib.fib_ComplexCase_Prelude.False_ComplexCase'('FAIL'(_G42260),_G37296,'FAIL'(_G42260),_G42267,_G42267).
'blocked_blocked_fib.fib_ComplexCase'('FAIL'(_G42294),_G37296,'FAIL'(_G42294),_G42301,_G42301).

:-costCenters(['']).




%%%%% Number of shared variables: 2

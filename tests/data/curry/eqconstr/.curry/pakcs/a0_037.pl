%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_037).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_037.main',main,0,'a0_037.main',nofix,'TCons'('a0_037.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_037.A','A',0,'A',0,'TCons'('a0_037.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_037.main'(_G482825,_G482826,_G482827):-freeze(_G482826,'blocked_a0_037.main'(_G482825,_G482826,_G482827)).
'blocked_a0_037.main'(_G483255,_G483258,_G483261):-makeShare(_G482870,_G483329),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G482861,_G483329),'Prelude.=:='(_G483329,'a0_037.A')),_G483329),_G483329),_G483255,_G483258,_G483261).

:-costCenters(['']).




%%%%% Number of shared variables: 1

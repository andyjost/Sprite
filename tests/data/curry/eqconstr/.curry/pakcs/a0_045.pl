%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_045).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_045.main',main,0,'a0_045.main',nofix,'TCons'('a0_045.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_045.A','A',0,'A',0,'TCons'('a0_045.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_045.main'(_G482825,_G482826,_G482827):-freeze(_G482826,'blocked_a0_045.main'(_G482825,_G482826,_G482827)).
'blocked_a0_045.main'(_G483255,_G483258,_G483261):-makeShare(_G482870,_G483311),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G483311,'a0_045.A'),'Prelude.=:='(_G482861,_G483311)),_G483311),_G483311),_G483255,_G483258,_G483261).

:-costCenters(['']).




%%%%% Number of shared variables: 1

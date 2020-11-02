%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_002).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_002.main',main,0,'a0_002.main',nofix,'TCons'('a0_002.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_002.A','A',0,'A',0,'TCons'('a0_002.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_002.main'(_G480587,_G480588,_G480589):-freeze(_G480588,'blocked_a0_002.main'(_G480587,_G480588,_G480589)).
'blocked_a0_002.main'(_G480859,_G480862,_G480865):-makeShare(_G480623,_G480897),hnf('Prelude.?'('Prelude.&>'('Prelude.=:='(_G480897,'a0_002.A'),_G480897),_G480897),_G480859,_G480862,_G480865).

:-costCenters(['']).




%%%%% Number of shared variables: 1

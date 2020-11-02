%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_003).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_003.main',main,0,'a0_003.main',nofix,'TCons'('a0_003.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_003.A','A',0,'A',0,'TCons'('a0_003.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_003.main'(_G480587,_G480588,_G480589):-freeze(_G480588,'blocked_a0_003.main'(_G480587,_G480588,_G480589)).
'blocked_a0_003.main'(_G480859,_G480862,_G480865):-makeShare(_G480623,_G480897),hnf('Prelude.?'('Prelude.&>'('Prelude.=:='('a0_003.A',_G480897),_G480897),_G480897),_G480859,_G480862,_G480865).

:-costCenters(['']).




%%%%% Number of shared variables: 1

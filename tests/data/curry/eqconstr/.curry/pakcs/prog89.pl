%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog89).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog89.main',main,0,'prog89.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog89.main'(_G483125,_G483126,_G483127):-freeze(_G483126,'blocked_prog89.main'(_G483125,_G483126,_G483127)).
'blocked_prog89.main'(_G483635,_G483638,_G483641):-makeShare(_G483170,_G483703),makeShare(_G483161,_G483713),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G483703,'Prelude.False'),'Prelude.&'('Prelude.=:='(_G483703,_G483713),'Prelude.=:='(_G483713,'Prelude.True'))),_G483713),_G483635,_G483638,_G483641).

:-costCenters(['']).




%%%%% Number of shared variables: 2
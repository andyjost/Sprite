import abc
from .... import icurry

class ModuleSpecification(abc.ABC):
  TYPE_METADATA = {}
  CONSTRUCTOR_METADATA = {}
  FUNCTION_METADATA = {}

  def aliases(self):
    return []

  def exports(self):
    return []

  def extern(self):
    return icurry.IModule(
          name=self.NAME
        , imports=self.IMPORTS
        , types=self.types()
        , functions=self.functions()
        )

  def types(self):
    for (typename, constructors) in self.TYPES:
      yield icurry.IDataType(
          '%s.%s' % (self.NAME, typename)
        , [ icurry.IConstructor(
                '%s.%s' % (self.NAME, ctorname)
              , arity
              , metadata=dict(md, **self.CONSTRUCTOR_METADATA.get((typename, i), {}))
              )
              for i,(ctorname, arity, md) in enumerate(constructors)
            ]
        , modulename=self.NAME
        , metadata=self.TYPE_METADATA.get(typename, {})
        )

  def functions(self):
    for name, arity, md in self.FUNCTIONS:
      yield icurry.IFunction(
          '%s.%s' % (self.NAME, name)
        , arity
        , modulename=self.NAME
        , metadata=dict(md, **self.FUNCTION_METADATA.get(name, {}))
        , body=icurry.IBuiltin()
        )


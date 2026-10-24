'''Defines the step-limit flow-control exception.'''

__all__ = ['RuntimeFlowException', 'E_TERMINATE']

class RuntimeFlowException(BaseException):
  '''The base class for runtime flow-control exceptions.'''
  pass

class E_TERMINATE(RuntimeFlowException):
  '''Raised to terminate evaluation.'''

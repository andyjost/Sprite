import os
import subprocess
import tempfile
import curry

HERE = os.path.dirname(os.path.abspath(__file__))
curry.path.insert(0, os.path.join(HERE, '..', '01-run-with-python'))
Hello = curry.import_('Hello')
print(curry.eval(Hello.greet('session')).one())
curry.wait(Hello)  # join the background compiler before resetting
print('background compilation finished')
M = curry.compile('answer :: Int\nanswer = 41', name='Session')
old = M.answer
print(curry.eval(old).one())
curry.reload(M, text='answer :: Int\nanswer = 42')
try:
  curry.eval(old).one()
except curry.StaleError as error:
  print(type(error).__name__, error)
print(curry.eval(M.answer).one())
with tempfile.TemporaryDirectory() as work:
  product = os.path.join(work, 'Session.object')
  program = os.path.join(work, 'answer.exe')
  curry.save(M, product)
  curry.save(M, program, main=M.answer)
  curry.reset()
  print('after reset:', sorted(curry.modules))
  M = curry.load(product)
  print('loaded:', curry.eval(M.answer).one())
  print('same load:', curry.load(product) is M)
  run = subprocess.run([program], check=True, capture_output=True, text=True)
  print('saved program:', run.stdout.strip())

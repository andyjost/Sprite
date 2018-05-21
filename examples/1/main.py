import curry
code = curry.compile(
  '''
  fib n | n < 3 = 1
        | True  = (fib (n-1)) + (fib (n-2))
  '''
  )
fib = code.fib
print next(curry.eval([fib, 7])) # 13


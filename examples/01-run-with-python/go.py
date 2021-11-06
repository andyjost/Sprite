import curry

### Load and run rev.curry.

# Since rev.curry is in this directory, we should add it to curry.path.
curry.path.insert(0, '.')

# Import module rev
rev = curry.import_('rev')

# Evaluate rev.main and print the values.
for value in curry.eval(rev.main):
  print value


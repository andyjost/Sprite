'''Issue #138: old products that postdate an edit are still stale.'''
import cytest # from ./lib; must be first
import curry
import os
from pathlib import Path
import tempfile
import time
import unittest


class TestIssue138(cytest.TestCase):
  def test_newer_products_of_old_source_are_refused(self):
    self.check_products()

  def test_source_digest_is_checked_without_icurry(self):
    self.check_products(remove_icurry=True)

  def test_products_without_a_source_stamp_are_not_trusted(self):
    self.check_products(remove_stamp=True)

  def test_new_import_reads_the_interface_after_a_cached_edit(self):
    with tempfile.TemporaryDirectory() as work:
      source = Path(work) / 'EdTyped.curry'
      def write(type_, value):
        source.write_text('module EdTyped where\nf :: %s\nf = %s\n' % (type_, value))
      # Warm the frontend cache with the text the final edit restores.
      write('Bool', 'True')
      curry.import_(source)
      curry.wait()
      curry.reset()
      write('Int', '1')
      curry.import_(source)
      curry.wait()
      write('Bool', 'True')
      stamp = time.time_ns() + 1000000000
      for product in (Path(work) / '.curry').rglob('*'):
        if product.is_file():
          os.utime(product, ns=(stamp, stamp))
      curry.reset()
      module = curry.import_(source)
      consumer = curry.compile('g = f', imports=[module])
      self.assertEqual(curry.typeof(consumer.g), 'Bool')
      self.assertIs(curry.eval(consumer.g).one(), True)
      curry.wait()

  def check_products(self, remove_icurry=False, remove_stamp=False):
    with tempfile.TemporaryDirectory() as work:
      source = Path(work) / 'Ed.curry'
      source.write_text('module Ed where\nf :: Int\nf = 1\n')
      first = curry.import_(source)
      self.assertEqual(curry.eval(first.f).one(), 1)
      curry.wait()
      source.write_text('module Ed where\nf :: Int\nf = 2\n')
      # Pin the race without depending on compiler speed: every product
      # of the old text is newer than the edit.
      stamp = time.time_ns() + 1000000000
      for product in (Path(work) / '.curry').rglob('*'):
        if product.is_file():
          os.utime(product, ns=(stamp, stamp))
      if remove_icurry:
        for product in (Path(work) / '.curry').rglob('*.icy'):
          product.unlink()
      if remove_stamp:
        for product in (Path(work) / '.curry').rglob('*.icy.source'):
          product.unlink()
      curry.reset()
      second = curry.import_(source)
      self.assertEqual(curry.eval(second.f).one(), 2)
      with self.assertRaises(curry.StaleError):
        first.f
      curry.wait()


if __name__ == '__main__':
  unittest.main()

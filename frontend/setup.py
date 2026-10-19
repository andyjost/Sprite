'''The payload is native code, though the Python launcher has no extension.'''
from setuptools import Distribution, setup
from wheel.bdist_wheel import bdist_wheel
from sysconfig import get_platform


class PlatformWheel(bdist_wheel):
  def finalize_options(self):
    super().finalize_options()
    self.root_is_pure = False

  def get_tag(self):
    return 'py3', 'none', get_platform().replace('-', '_').replace('.', '_')


class NativePayload(Distribution):
  def has_ext_modules(self):
    # Install the native payload in platlib, without a CPython ABI tag.
    return True


setup(cmdclass={'bdist_wheel': PlatformWheel}, distclass=NativePayload)

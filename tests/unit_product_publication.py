'''Faults at product publication boundaries and same-size corruption.'''
import cytest # from ./lib; must be first
from curry import cache, config
from curry.toolchain import _productcache, _productlock, _makecurry
from curry.backends.cxx import toolchain, llvmjit
from unittest import mock
import hashlib, json, os, pathlib, tempfile, time, zlib


class TestPublication(cytest.TestCase):
  def setUp(self):
    self.work = tempfile.TemporaryDirectory()
    self.addCleanup(self.work.cleanup)
    self.base = pathlib.Path(self.work.name)

  def products(self):
    source = self.base / ('M' + config.module_object_suffix())
    source.write_bytes(b'complete object')
    root = str(self.base / 'cache')
    entry = _productcache.store('runtime', 'key', [str(source)], root)
    dest = self.base / 'dest'
    dest.mkdir()
    return source, root, pathlib.Path(entry) / source.name, dest

  def test_restore_invalidates_stamp_before_object(self):
    source, root, entry, dest = self.products()
    stamp = dest / (source.name + '.abi')
    stamp.write_text('old runtime\n')
    place = _productcache._place
    def interrupted(*args, **kwargs):
      place(*args, **kwargs)
      raise RuntimeError('interrupted after rename')
    with mock.patch.object(_productcache, '_place', side_effect=interrupted):
      with self.assertRaisesRegex(RuntimeError, 'interrupted'):
        _productcache.restore('runtime', 'key', str(dest), [source.name], root)
    self.assertFalse(stamp.exists(), 'old stamp survived object replacement')

  def test_corrupt_cache_entry_misses(self):
    source, root, entry, dest = self.products()
    for data in (b'truncated', b'X' * len(source.read_bytes())):
      with self.subTest(data=data):
        stamp = entry.stat()
        entry.write_bytes(data)
        os.utime(entry, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        self.assertIsNone(_productcache.restore(
            'runtime', 'key', str(dest), [source.name], root))
        self.assertFalse((dest / source.name).exists())
    cache.write_file(str(source), b'rebuilt object')
    _productcache.store('runtime', 'key', [str(source)], root)
    self.assertIsNotNone(_productcache.restore(
        'runtime', 'key', str(dest), [source.name], root))
    self.assertEqual((dest / source.name).read_bytes(), b'rebuilt object')

  def test_export_replaces_inode(self):
    source = self.base / 'source.cpp'
    target = self.base / 'target.cpp'
    alias = self.base / 'alias.cpp'
    source.write_bytes(b'new complete output')
    target.write_bytes(b'previous output')
    os.link(target, alias)
    with _makecurry.ToolchainContext(str(source), output=str(target)):
      pass
    self.assertEqual(alias.read_bytes(), b'previous output')
    self.assertEqual(target.read_bytes(), source.read_bytes())

  def test_export_interrupted_copy_keeps_destination(self):
    source = self.base / 'source.cpp'
    target = self.base / 'target.cpp'
    source.write_bytes(b'new complete output')
    target.write_bytes(b'previous output')
    def interrupt(source, target, **kwargs):
      pathlib.Path(target).write_bytes(b'partial')
      raise OSError('interrupted copy')
    with mock.patch.object(_productcache.shutil, 'copyfile', side_effect=interrupt):
      with self.assertRaisesRegex(OSError, 'interrupted copy'):
        with _makecurry.ToolchainContext(str(source), output=str(target)):
          pass
    self.assertEqual(target.read_bytes(), b'previous output')

  def test_export_accepts_arbitrary_output_name(self):
    source = self.base / 'source.cpp'
    target = self.base / 'output'
    source.write_bytes(b'complete output')
    with _makecurry.ToolchainContext(str(source), output=str(target)):
      pass
    self.assertEqual(target.read_bytes(), source.read_bytes())

  def test_canonical_stamp_binds_object_bytes(self):
    source = self.base / ('M' + config.module_object_suffix())
    source.write_bytes(b'complete object')
    stamp = pathlib.Path(str(source) + '.abi')
    stamp.write_text('runtime\ninstallation\n' + json.dumps(dict(
        version=1, imports={}, input={}, object=hashlib.sha256(source.read_bytes()).hexdigest())))
    self.assertEqual(toolchain.Cpp2So._read_stamp_records(str(source))[0], 'runtime')
    stamp = source.stat()
    source.write_bytes(b'X' * len(source.read_bytes()))
    os.utime(source, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    self.assertIsNone(toolchain.Cpp2So._read_stamp_records(str(source))[0])

  def test_import_comments_between_tokens(self):
    info = cache.SourceInfo('M.curry', b'import {- outer {- inner -} -} qualified\n'
        b'-- line comment\n B.C\nimport {- comment -} D\n')
    self.assertEqual(info.imports, ['B.C', 'D'])

  def test_private_library_snapshot_has_completion_receipt(self):
    import curry
    from curry.backends.cxx import tiered
    from curry.objects.handle import getHandle
    from curry.toolchain import _curry2icurry, _filenames
    curry.reset(interpret='all', jit='off')
    module = curry.import_('Prelude')
    copied, _ = tiered._private_copy(getHandle(module).icurry)
    self.assertTrue(_curry2icurry.source_matches(copied, _filenames.icurryfilename(copied)),
        'a verified library snapshot unnecessarily invalidated its translation')

  def test_pch_content_change_with_preserved_time(self):
    header = self.base / 'header.hpp'
    header.write_text('old layout')
    stamp = header.stat()
    with mock.patch.object(toolchain.PrecompiledHeader, 'header_files',
        return_value=[str(header)]):
      old = toolchain.PrecompiledHeader(str(self.base), 'c++', ['-O3'])
      os.makedirs(old.directory)
      pathlib.Path(old.filename).write_bytes(b'old precompiled header')
      header.write_text('new layout')
      os.utime(header, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
      new = toolchain.PrecompiledHeader(str(self.base), 'c++', ['-O3'])
      self.assertFalse(new.is_current(), 'changed headers accepted old PCH')

  def test_lock_open_failure_refuses_publication(self):
    with mock.patch.object(_productlock, '_open', return_value=None):
      with self.assertRaises(OSError):
        with _productlock.locked(str(self.base / 'M.icy')):
          self.fail('publication entered without a lock')

  @cytest.posix_only('advisory flock failure')
  def test_advisory_lock_failure_refuses_publication(self):
    with mock.patch.object(_productlock.fcntl, 'flock', side_effect=OSError('lock refused')):
      with self.assertRaises(OSError):
        with _productlock.locked(str(self.base / 'M.icy')):
          self.fail('publication entered without exclusion')

  def test_jit_index_same_size_corruption(self):
    payload = zlib.compress(b'valid object bytes')
    stamp = (time.time_ns() // 2000000000) * 2000000000
    index = dict(key='key', objects=[dict(functions=[['M.f', 's0', []]],
        size=len(payload), digest=hashlib.sha256(payload).hexdigest())], size=0, mtime_ns=stamp)
    # Use the current writer's prefix, retaining the checksum if present.
    while True:
      encoded = json.dumps(index, sort_keys=True, separators=(',', ':')).encode('ascii')
      size = llvmjit._CACHE_PREFIX.size + len(encoded) + len(payload)
      if size == index['size']:
        break
      index['size'] = size
    fields = [llvmjit._CACHE_MAGIC, len(encoded)]
    if llvmjit._CACHE_PREFIX.size > 12:
      fields.append(hashlib.sha256(encoded).digest())
    data = llvmjit._CACHE_PREFIX.pack(*fields) + encoded + payload
    path = self.base / 'M.jit'
    path.write_bytes(data)
    os.utime(path, ns=(stamp, stamp))
    intact = llvmjit._read_cache(str(path), 'key')
    intact.close()
    path.write_bytes(data.replace(b'M.f', b'M.g'))
    os.utime(path, ns=(stamp, stamp))
    with self.assertRaises(ValueError):
      found = llvmjit._read_cache(str(path), 'key')
      found.close()

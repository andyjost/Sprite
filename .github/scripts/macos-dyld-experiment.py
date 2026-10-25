#!/usr/bin/env python3
'''
An experiment on a macOS runner for issue #162, step 2: which link forms let
a shim of absolute symbols stand in for the tables of a loaded object, as
the shim of the tiered mode does on ELF.  A host program holds a "live"
table, writes a shim that names the table's symbol at the live address,
loads the shim and then an object that defines the same symbol, and checks
where the object's references and its dynamic initializer went.  The object
is built in several forms; the shim in two.  Every result is printed; the
script never fails the job.
'''
import os, subprocess, sys, tempfile, textwrap

HOST = r'''
#include <dlfcn.h>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
struct Table { int step; int flags; Table(int s, int f); };
__attribute__((noinline)) Table::Table(int s, int f) : step(s), flags(f) {}
Table live{7, 0};
int main(int argc, char ** argv)
{
  std::string shim = argv[1], object = argv[2], marker = argv[3];
  std::string second = argc > 4 ? argv[4] : "";
  {
    std::ofstream s(shim + ".s");
    s << ".globl _tbl\n_tbl = 0x" << std::hex << (unsigned long) &live << "\n";
    if(marker == "marker")
      s << ".section __DATA,__data\n.globl _shim_marker\n.weak_definition _shim_marker\n_shim_marker:\n.quad 0\n";
  }
  // Apple's linker refuses a dylib without the system library (-nostdlib).
  std::string cmd = "c++ -shared -x assembler " + shim + ".s -o " + shim + " 2>&1";
  if(int status = system(cmd.c_str())) { printf("  shim link failed (%d)\n", status); return 0; }
  void * sh = dlopen(shim.c_str(), RTLD_NOW | RTLD_GLOBAL);
  if(!sh) { printf("  shim load failed: %s\n", dlerror()); return 0; }
  void * found = dlsym(sh, "tbl");
  printf("  dlsym(shim, tbl) %s the live table (%p vs %p)\n", found == &live ? "is" : "IS NOT", found, (void *) &live);
  void * a = dlopen(object.c_str(), RTLD_LAZY | RTLD_GLOBAL);
  if(!a) { printf("  object load failed: %s\n", dlerror()); return 0; }
  auto addr = (Table const * (*)()) dlsym(a, "a_table_address");
  auto use = (int (*)()) dlsym(a, "a_uses_table");
  printf("  the object's &tbl %s the live table; live.step = %d (42: the initializer wrote the live table; 7: it did not); the object reads step %d\n",
         addr() == &live ? "IS" : "IS NOT", live.step, use());
  if(!second.empty())
  {
    void * b = dlopen(second.c_str(), RTLD_LAZY | RTLD_GLOBAL);
    if(!b) { printf("  second object load failed: %s\n", dlerror()); return 0; }
    auto baddr = (Table const * (*)()) dlsym(b, "b_table_address");
    printf("  the second object's &tbl %s the live table\n", baddr() == &live ? "IS" : "IS NOT");
  }
  return 0;
}
'''
A_WEAK = r'''
struct Table { int step; int flags; Table(int s, int f); };
__attribute__((noinline)) Table::Table(int s, int f) : step(s), flags(f) {}
extern "C" { extern Table const tbl; }
extern "C" { __attribute__((weak)) Table const tbl{42, 1}; }
extern "C" Table const * a_table_address() { return &tbl; }
extern "C" int a_uses_table() { return tbl.step; }
'''
A_STRONG = A_WEAK.replace('__attribute__((weak)) ', '')
B = r'''
struct Table { int step; int flags; };
extern "C" { extern Table const tbl; }
extern "C" Table const * b_table_address() { return &tbl; }
'''

def run(cmd, cwd):
  proc = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True)
  return proc.returncode, (proc.stdout + proc.stderr).strip()

def main():
  tmp = tempfile.mkdtemp(prefix='dyld-experiment-')
  for name, text in [('host.cpp', HOST), ('a_weak.cpp', A_WEAK), ('a_strong.cpp', A_STRONG), ('b.cpp', B)]:
    with open(os.path.join(tmp, name), 'w') as stream:
      stream.write(textwrap.dedent(text))
  status, out = run('c++ -std=c++17 host.cpp -o host', tmp)
  print('host build:', status, out)
  variants = [
      ('weak definitions, two-level namespace', 'a_weak.cpp', '-Wl,-install_name,sprite-A.so.14'),
      ('weak definitions, flat namespace', 'a_weak.cpp', '-Wl,-flat_namespace -Wl,-install_name,sprite-A.so.14'),
      ('strong definitions, two-level namespace', 'a_strong.cpp', '-Wl,-install_name,sprite-A.so.14'),
      ('strong definitions, flat namespace, interposable', 'a_strong.cpp', '-Wl,-flat_namespace -Wl,-interposable -Wl,-install_name,sprite-A.so.14'),
    ]
  for index, (title, source, flags) in enumerate(variants):
    print('== %s' % title)
    so = 'a%d.so' % index
    status, out = run('c++ -std=c++17 -O2 -shared %s %s -o %s' % (flags, source, so), tmp)
    print('  object link:', status, out[:400])
    if status:
      continue
    bso = 'b%d.so' % index
    status, out = run('c++ -std=c++17 -O2 -shared -Wl,-undefined,dynamic_lookup -Wl,-install_name,sprite-B.so.14 -Wl,-weak_library,%s b.cpp -o %s' % (so, bso), tmp)
    print('  second object link (-weak_library, -undefined dynamic_lookup):', status, out[:400])
    second = bso if status == 0 else ''
    for marker in ('plain', 'marker'):
      print(' shim %s:' % marker)
      status, out = run('./host shim-%d-%s.dylib %s %s %s' % (index, marker, so, marker, second), tmp)
      print(textwrap.indent(out, '  '))
  print('== the load commands of the second object')
  status, out = run('otool -L b0.so; otool -l b0.so | grep -A3 LC_LOAD_WEAK_DYLIB | head -8', tmp)
  print(out)
  print('== ld version')
  status, out = run('ld -v 2>&1 | head -2', tmp)
  print(out)

if __name__ == '__main__':
  main()

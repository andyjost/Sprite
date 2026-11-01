#pragma once
// Compare runtime function addresses only inside the runtime library: a
// Windows DLL consumer can see its own import thunk instead of the function.
// Consumers must ask a runtime predicate; stores of these addresses also
// belong in the runtime library.
// The data symbols of the runtime library that other objects read: the info
// tables of the built-in types, the singletons, the allocation runs and the
// caches of small values.  On Windows a DLL exports its functions through the
// definition file that CMake writes (WINDOWS_EXPORT_ALL_SYMBOLS), and a
// consumer calls them through the import library without a declaration; a
// data symbol needs an explicit export: the generated definition file can
// omit const tables in read-only sections.  Its reader must declare the
// import, or the linker looks for the symbol itself instead of its import
// thunk.  CURRYRT_DATA marks every such declaration: export when building
// the runtime library, import in its consumers, nothing on other platforms.
#if defined(_WIN32)
#  if defined(CURRYRT_BUILDING)
#    define CURRYRT_DATA __declspec(dllexport)
#  else
#    define CURRYRT_DATA __declspec(dllimport)
#  endif
#else
#  define CURRYRT_DATA
#endif

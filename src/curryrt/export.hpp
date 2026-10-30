#pragma once
// The data symbols of the runtime library that other objects read: the info
// tables of the built-in types, the singletons, the allocation runs and the
// caches of small values.  On Windows a DLL exports its functions through the
// definition file that CMake writes (WINDOWS_EXPORT_ALL_SYMBOLS), and a
// consumer calls them through the import library without a declaration; a
// data symbol is exported the same way, but its reader must declare the
// import, or the linker looks for the symbol itself instead of its import
// thunk.  CURRYRT_DATA marks every such declaration: nothing when the
// runtime library itself is built (CURRYRT_BUILDING) and on every other
// platform, the import declaration in the objects that read the library.
#if defined(_WIN32) && !defined(CURRYRT_BUILDING)
#  define CURRYRT_DATA __declspec(dllimport)
#else
#  define CURRYRT_DATA
#endif

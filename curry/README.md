This directory contains the Curry system libraries.  The Curry, ICY, and JSON
files are copied into the installation.

Since compiling the library is slow, there is a pre-build mechanism.  The
products can be checked in to the repository to streamline installation.


Pre-building Libraries for a New PAKCS
======================================

The precompiled libraries are stored in subdirectories named after the PAKCS
version.  When an unknown version of PAKCS is used, the Makefile will
automatically create a new version-specific subdirectory and copy the Prelude.

To pre-build ICY and JSON files, first perform a regular build and install.
You might issue the following commands from the project root:

    % make all
    % make install

This will prepare the Curry source files belonging to the system library and
install them.  Sprite is installed at this point, but the first time it is used
to run a Curry program, the Prelude will need to be compiled.  This raises two
problems.  First, it is very slow and might be unexpected by a user of Sprite.
Second, if that user does not have the same privileges as the installer, the
compilation could fail.  Instead, it is preferable to pre-build the system
libraries during installation.  This can be done by issuing the following
command in this directory:

    % make currylib

This compiles the Curry source code to Flat curry and then ICurry.  This step
could take longer than 30 minutes.  Verify that the system libraries were built
correctly by inspecting the subdirectory named after the current PAKCS version.

To install, issue the following command:

    % make uninstall install

This copies files to $(PREFIX)/curry.  Test the installation.  If everything
looks OK, check in the new files under this directory.


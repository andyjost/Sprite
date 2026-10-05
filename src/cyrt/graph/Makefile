SUBMODULES=
INSTALL_DIR= # no installation from this directory.
# The collector is selected in memory.cpp: the block heap and the
# mark-and-sweep collector of gc/ by default, the Memory Pool System with
# make GC=mps.  The MPS build compiles the library of the submodule
# extern/mps as one C object: mpsgc.c includes mps.c.  The hot variety is the
# production build of MPS (assertions on, the checks of the cool variety
# off).
SRCS := $(wildcard *.cpp)
ifeq ($(GC),mps)
  SRCS += mpsgc.c
endif
include Make.include
ifeq ($(GC),mps)
# The flags of the release flavor of the runtime, less the C++ warnings.
$(OBJECT_DIR)/mpsgc.o: CFLAGS := -O2 -fPIC -fno-stack-protector -fno-plt \
                                 -DCONFIG_VAR_HOT -I$(ROOT_DIR)/extern/mps/code
else
# A build without MPS after one with it: the member stays in the archive
# otherwise, and the whole-archive link would carry the dead code.
libs::
	-@$(AR) dP $(LIB_OUT) $(OBJECT_DIR)/mpsgc.o 2>/dev/null
endif

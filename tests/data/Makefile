# Gets Curry examples and converts them to JSON.
.PHONY : all clean

all : Makefile2
	$(MAKE) -k -f Makefile2

# This file is a proxy for downloading the Curry examples.  To get the latest
# examples, delete it and then re-make.
index.py : scripts/get-curry-examples.py
	(cd scripts && ./get-curry-examples.py)
	# Remove unsupported Curry files that use findall.
	grep -l findall curry/*.curry | xargs rm

Makefile2 : scripts/write-makefile2.py index.py
	(cd scripts && ./write-makefile2.py)

clean :
	$(MAKE) clean -f Makefile2
	rm -rf index.py Makefile2 curry/.curry curry/*.curry curry/robots*


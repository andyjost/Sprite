# Gets Curry examples and converts them to JSON.
.PHONY : all

all : Makefile.json
	$(MAKE) -k -f Makefile.json

# This file is a proxy for downloading the Curry examples.
index.py : scripts/get-curry-examples.py
	(cd scripts && ./get-curry-examples.py)

Makefile.json : scripts/write-makefile-json.py index.py
	(cd scripts && ./write-makefile-json.py)


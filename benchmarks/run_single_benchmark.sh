#! /bin/bash

# Default values.  Customize in ~/.vialoisrc if appropriate
KICS2=kics2
PAKCS=pakcs
MCCCYC=cyc
VIALOIS=vialois.sh
SPRITE=sprite

if [ -e ~/.vialoisrc ]; then
  source ~/.vialoisrc
fi

function removeCurry {
    echo $(dirname $1)/$(basename $1 ".curry")
}

function make_sprite {
    SRC=$1
    OUTPUT=$(removeCurry $SRC)
    BIN=$(removeCurry $SRC).sprite
    $SPRITE $(removeCurry $SRC)
    mv $OUTPUT $BIN
}

function make_KiCS2 {
    SRC=$1
    OUTPUT=$(removeCurry $SRC)
    BIN=$(removeCurry $SRC).kics2
    $KICS2 ":load $SRC" ":save" ":q"
    mv $OUTPUT $BIN
}

function make_PAKCS {
    SRC=$1
    TMPBASE=/tmp/$(basename $SRC ".curry")
    INPUT=$TMPBASE.curry
    OUTPUT=$TMPBASE.state
    BIN=$(removeCurry $SRC).pakcs
    
    sed 's/main[\t ]*=/mainFun =/' $SRC > $INPUT
    echo "" >> $INPUT
    echo "-- IO Main" >> $INPUT
    echo "main = putStrLn (show (findall (=:= mainFun)))" >> $INPUT
    
    (cd /tmp; $PAKCS -s "$INPUT") && rm $INPUT
    mv $OUTPUT $BIN
}

function make_ViaLOIS {
    SRC=$1
    OUTPUT=$(removeCurry $SRC).ocamlopt
    BIN=$(removeCurry $SRC).vialois
    echo $VIALOIS 
    $VIALOIS --opt $SRC
    mv $OUTPUT $BIN 
    TMP=$(removeCurry $SRC)
    rm -f $TMP.cmi $TMP.cmx $TMP.o $TMP.ml
}

function make_MCC {
    SRC=$1
    TMPBASE=/tmp/$(basename $SRC ".curry")
    INPUT=$TMPBASE.curry
    BIN=$(removeCurry $SRC).mcc
    
    echo "import AllSolutions" > $INPUT
    sed 's/main[\t ]*=/mainFun =/' $SRC >> $INPUT
    echo "" >> $INPUT
    echo "-- IO Main" >> $INPUT
    echo "
main = do
  l <- getAllValues mainFun
  putStrLn (show l)
" >> $INPUT
    
    $MCCCYC $INPUT -o $BIN && rm $INPUT
}

SRC=$1
BASE=$(removeCurry $SRC)

echo "============ Benchmarking $SRC ============"

echo "Building..."
echo "sprite"
make_sprite "$SRC" > /dev/null # 2>&1
echo "ViaLOIS"
make_ViaLOIS "$SRC" > /dev/null # 2>&1
echo "KiCS2"
make_KiCS2 "$SRC" > /dev/null # 2>&1
echo "PAKCS"
make_PAKCS "$SRC" > /dev/null # 2>&1
echo "MCC"
make_MCC "$SRC"
echo "Done."

if [ -z "$MAXTIME" ]; then 
    TIMEOUT=45
else    
    TIMEOUT=$MAXTIME
fi
if [ -z "$NRUNS" ]; then 
    NRUNS=1
fi

function run {
    ulimit -s unlimited
    for i in $(seq $NRUNS); do
    #env -i timeout 10 $@
	\time -f "'$1',time,%e,%U,%S,mem,%K,%M" timeout $TIMEOUT bash -c "ulimit -s unlimited; $1 > /dev/null" 2>&1 | grep -v "SICStus" | tee -a benchmark.log
	if [ "$?" -ne "0" ]; then
	    echo "ERROR: Run of '$*' failed"
	fi
    done
}

export OCAMLRUNPARAM="s=4M,i=16M"
#export GHCRTS="-A4m -H16m"
ulimit -s unlimited

echo "sprite:"
run $BASE.sprite
echo "ViaLOIS:"
run $BASE.vialois
echo "KiCS2:"
run $BASE.kics2
echo "MCC:"
run "$BASE.mcc +RTS -h100m -k8m"
echo "PAKCS:"
run $BASE.pakcs


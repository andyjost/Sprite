#!/bin/bash

CFLAGS="-I$HOME/build/dmain/3rdparty/boost_1_42/ -I. -Wall -O0 -ggdb"
#CFLAGS="-I$HOME/build/dmain/3rdparty/boost/1_46_0 -I. -Wall -O0 -ggdb"

g++ -c sprite/builtins.cpp -o obj/builtins.o $CFLAGS &
g++ -c sprite/exec.cpp -o obj/exec.o $CFLAGS &

g++ -c sprite/tests/int.cpp -o obj/test_int.o $CFLAGS &
g++ -c sprite/tests/io.cpp -o obj/test_io.o $CFLAGS &
g++ -c sprite/tests/concat.cpp -o obj/test_concat.o $CFLAGS &

wait

if [ $? -eq 0 ]; then

  rm obj/sprite.a
  ar -r obj/sprite.a obj/builtins.o obj/exec.o
  
  g++ obj/test_int.o obj/sprite.a -o bin/test_int &
  g++ obj/test_io.o obj/sprite.a -o bin/test_io &
  g++ obj/test_concat.o obj/sprite.a -o bin/test_concat &
  
  wait
fi

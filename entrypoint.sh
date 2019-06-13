#!/bin/sh

if  [ $# -ne 2 ]; then
    # TODO: print usage
    python /app/main.py
else
    python $1
fi


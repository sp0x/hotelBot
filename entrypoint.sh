#!/bin/sh


if  [ $# -eq 0 ]; then
    # TODO: print usage
    python /app/main.py
else
    python $1 $2
fi


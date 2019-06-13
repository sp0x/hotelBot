#!/bin/env python
from iface import run_bots
from chatbots import get_bots

if __name__ == '__main__':
    b = get_bots()
    run_bots(b)

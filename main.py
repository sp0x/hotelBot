#!/bin/env python
from nlp import DialogFlow
import json
import chatbot
from iface import run_bots, Viber

if __name__ == '__main__':
    bots = [Viber(web_config=('0.0.0.0', 8080))]
    run_bots(bots)

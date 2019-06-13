#!/usr/bin/env python
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--train', dest='train', action='store_true',
                        default=False,
                        help='Run training')

    args = parser.parse_args()
    if args.train:
        from dialog.nlp import train_intent
        train_intent()

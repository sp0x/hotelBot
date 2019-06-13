from nlp import DialogFlow
import json


def get_dialogflow():
    script = {}
    with open('script.dialog', 'r') as f:
        script = json.load(f)
    d = DialogFlow(script)
    return d


if __name__ == '__main__':
    script = {}
    with open('script.dialog', 'r') as f:
        script = json.load(f)
    d = DialogFlow(script)
    r = d.greet()
    done = d.is_done()
    print(r)
    while not done:
        m = input("\nYou: ")
        done, replies = d.process_message(m)
        for r in replies:
            print("\nReply: ", r)
    print("Done")

import spacy
from api import get_recommendation_for_location
from rasa_nlu.training_data import load_data
from rasa_nlu.config import RasaNLUModelConfig
from rasa_nlu.model import Trainer, Metadata, Interpreter
from rasa_nlu import config
import logging
import api
import os

logging.basicConfig(format='[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

model_directory = "D:/Dev/Projects/Other/dora/model/default/model_20190503-153134"
model_directory_env = os.environ.get("MODEL_DIR")
model_directory = model_directory_env if (model_directory_env is not None and len(model_directory_env)>0)\
    else "./model/default/model_20190614-070915"

nlp = spacy.load('en_core_web_md')
interpreter = Interpreter.load(model_directory) if os.path.isdir(model_directory) else None
place_intents = ['hotel']

class DialogNlp:

    def __init__(self, interest_intents):
        self.interest_intents = interest_intents


    def parse_intent(self, text):
        intent_data = interpreter.parse(text)
        # print(intent_data)
        intent = intent_data['intent']['name']
        entities = {}
        doc = nlp(text)
        for ent in doc.ents:
            m = entities.get(ent.label_, [])
            m.append(ent.text)
            entities[ent.label_] = m
        for e in intent_data['entities']:
            m = entities.get(e['entity'], [])
            m.append(e['value'])
            entities[e['entity']] = m
        # if intent not in ['affirm', 'greet', 'reject', 'goodbye', 'end', 'change_form']:
        #     entities[intent] = intent

        if self.present_already(text):
            intent = "visit"
            entities = {'DATE': ['Today']}
        elif intent in self.interest_intents:  # Handle interests without entities
            if len(entities) == 0:
                entities['interest'] = [intent]

        return intent, entities

    def present_already(self, msg):
        lower = msg.lower()
        return (("here" in lower) and "already" in lower) or \
               ("there" in lower and "now" in lower)


def flatten(f):
    import itertools
    flat = list(itertools.chain(*f))
    return flat


def boxes_have_data(boxes):
    for b in boxes:
        if b.has_data():
            return True
    return False


def train_intent():
    train_data = load_data('./conf/rasa_dataset.json')
    trainer = Trainer(config.load("./conf/config_spacy.yaml"))
    trainer.train(train_data)
    global model_directory
    model_directory = trainer.persist('./model/')




if __name__ == "__main__":
    train_intent()

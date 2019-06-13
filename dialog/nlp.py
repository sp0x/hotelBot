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
model_directory = "./model/default/model_20190613-175915"

nlp = spacy.load('en_core_web_md')
interpreter = Interpreter.load(model_directory) if os.path.isdir(model_directory) else None
place_intents = ['hotel']

folloup_radius = 2000
default_radius = 3600
max_radius = 5000

initial_suggestion_count = 8


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
    train_data = load_data('conf/rasa_dataset.json')
    trainer = Trainer(config.load("conf/config_spacy.yaml"))
    trainer.train(train_data)
    global model_directory
    model_directory = trainer.persist('./model/')


def format_box_question(box, form):
    """
    Formats a box into a question
    :param box:
    :param form:
    :return:
    """
    # question = box.question.format(**form)
    question = format_form_message(form, box.question)
    if box.is_yes_no() and box.has_data():
        place_ = box.data['place']
        output_reply = box_place_reply(box, question + " - " + place_.formatted_address)
    elif box.has_entity('interest'):
        output_reply = box_interest_reply(box, question)
    else:
        output_reply = msg_reply(question)
    return output_reply


def create_places_link(places):
    url_base = "https://www.google.com/maps/dir"
    for p in places:
        location = p.geo_location
        lat = float(location['lat'])
        lng = float(location['lng'])
        url_base += "/{0},{1}".format(lat, lng)
    return url_base


def format_form_message(form, msg):
    printable_form = form.copy()
    for k in printable_form:
        if k == "selected_items":
            continue
        item = printable_form[k]
        f = item
        # if isinstance(f, list): f = f[0]
        if isinstance(f, DialogBox):
            continue
        logging.info("Form field: %s , %s", k, f)
        printable_form[k] = f.capitalize()
    return msg.format(**printable_form)


suggestion_attr = "selected_items"

if __name__ == "__main__":
    train_intent()

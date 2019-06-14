import json
from copy import deepcopy
import random
import numpy as np
import logging

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S',
                    level=logging.DEBUG)

from dialog.nlp import DialogNlp

import api


class DialogBox:
    def __init__(self, params):
        self.intent = params.get('intent', [])
        self.entities = params.get('entities', '')
        self.accepted = params.get('accepted', '')
        self.question = params.get('question', '')
        self.rejected = params.get('rejected', '')
        self.attribute = params.get('attribute', '')
        # The data from the locations API
        self.data = params.get('data', [])
        self.finished = False
        self.answer_intent = None

    def finish(self, intent):
        self.finished = True
        self.answer_intent = intent

    def has_entity(self, entity_name):
        return entity_name in self.entities

    def validate_answer(self, intent, ents):
        """

        :param intent:
        :param ents:
        :return: bool, str, list
        """
        valid = intent in self.intent if self.intent else True
        matches = []
        for e in ents:
            if e in self.entities:
                matches.append(ents[e])
        valid = len(matches) > 0 if self.entities else valid
        return valid, self.accepted if valid else self.rejected, matches

    def is_suggestion(self):
        return self.attribute == 'selected_items'

    def has_data(self):
        return self.data is not None and len(self.data) > 0

    def is_yes_no(self):
        return 'reject' in self.intent and 'confirm' in self.intent

    def __str__(self) -> str:
        return "Dialogbox {4}:{0} {3} - ents {1} - Answer: {2}  ".format(self.intent, self.entities, self.answer_intent,
                                                                         self.question,
                                                                         'Done' if self.finished else 'NotDone')


class DialogFlow:
    def __init__(self, script):
        self.index = 0
        self.script = script
        self.opener, self.closer, self.boxes = self.__build_flow__(script)
        self.terminating = False
        self.form = {}
        self.box = self.boxes[0]
        self.needed_fields = ['city', 'date', 'interests', 'selected_items']
        self.callback_on_searching = None
        self.callback_on_search_done = lambda: None
        self.last_affirmed_place = None
        self.last_interest = None
        self.probs = [1.0 / len(api.query_examples)] * len(api.query_examples)
        self.interest_intents = script['interests']
        self.nlp = DialogNlp(self.interest_intents)
        self.initialized_suggestions = False
        self.suggestion_box_attr = "selected_items"
        self.autoreset_on_done = True
        self.initial_suggestion_count = 8

    def reset(self):
        self.opener, self.closer, self.boxes = self.__build_flow__(self.script)
        self.terminating = False
        self.index = 0
        self.form = {}
        self.box = self.boxes[0]
        self.last_affirmed_place = None
        self.last_interest = None
        logging.info("Reset dialog.")

    # ______________________________________ Callback setters __________________________________

    def on_searching(self, callback):
        self.callback_on_searching = callback

    def on_search_resolved(self, callback):
        self.callback_on_search_done = callback

    def __build_flow__(self, script):
        obj = deepcopy(script)
        boxes = []
        for i in obj['conversation']:
            boxes.append(DialogBox(i))
        return obj['opener'], obj['closer'], boxes

    def confirm(self):
        return self.process_intent('affirm', [])

    def reject(self):
        return self.process_intent('reject', [])

    def end(self):
        return self.process_intent('end', [])

    def is_done(self):
        incomplete_boxes = list(filter(lambda x: not x.finished, self.boxes))
        done = len(self.form.keys()) > 0 and all(list(map(lambda x: x in self.form, self.needed_fields)))
        return done and len(incomplete_boxes) == 0

    def greet(self):
        return [random.choice(self.opener), self.boxes[0].question]

    def start(self):
        """
        Starts of the dialog. Gets the response the first time you subscribe with the bot.
        :return:
        """
        self.reset()
        r = reply(self.script['greeting'])
        return r

    def fetch_initial_city_suggestions(self):
        location = self.form['city']
        if location is None or len(location)==0:
            raise Exception('City form field is needed.')

        if self.callback_on_searching is not None:
            self.callback_on_searching({
                'location': api.location_name(location),
                'type': ""
            })
        query = api.PlaceQuery("", [], None)
        query.types = ['establishment']
        recs = api.get_random_locations(location, query, self.initial_suggestion_count, probs=self.probs,
                                        radius=api.max_radius)
        logging.info("Found suggestions for search: %s", [x['title'] for x in recs])
        self.initialized_suggestions = True
        for i in range(len(recs)):
            params = {
                'intent': ['confirm', 'reject'],
                'attribute': self.suggestion_box_attr,
                'question': recs[i]['title'],
                'data': recs[i]
            }
            self.boxes.append(DialogBox(params))
        return recs

    def add_suggestions(self, is_folloup_suggestion=True, exclusions=None, query=None, custom_radius=None, cnt=None):
        """
        Gets recommendations for a location and adds it to the Boxes
        :param custom_radius:
        :param query:
        :param exclusions:
        :param is_folloup_suggestion:
        :return:
        """
        if query is None:
            query = self.get_suggestion_query()
        location = self.form['city']
        if self.last_affirmed_place is not None:
            location = self.last_affirmed_place
        count = 1
        radius = default_radius
        if is_folloup_suggestion:
            count = 3
            radius = folloup_radius
        if custom_radius is not None:
            radius = custom_radius
        if cnt is not None:
            count = cnt

        # location = location[0]
        logging.info("Searching for `%s` at `%s`. Excluding %s", query, location, exclusions)

        if self.callback_on_searching is not None and not is_folloup_suggestion:
            self.callback_on_searching({
                'location': api.location_name(location),
                'type': query.capitalize()
            })
        if query.is_random:
            query.types = ['establishment']
            recs = api.get_random_locations(location, query, self.initial_suggestion_count, self.probs, api.max_radius)
        else:
            recs = api.get_recommendation_for_location(location, query, count, radius, exclusions)

        logging.info("Found suggestions for search: %s", [x['title'] for x in recs])
        for i in range(len(recs)):
            params = {
                'intent': ['confirm', 'reject'],
                'attribute': self.suggestion_box_attr,
                'question': recs[i]['title'],
                'data': recs[i]
            }
            self.boxes.append(DialogBox(params))
        return recs

    def create_itinerary(self):
        first_city = self.form['city']
        if isinstance(first_city, list): first_city = first_city[0]
        city = first_city.capitalize()
        date = self.form['date']

        if isinstance(date, list): date = date[0]
        if isinstance(date, list): date = date[0]

        selected_boxes = self.form['selected_items'] if 'selected_items' in self.form else []
        locations = []
        url = create_places_link([box.data['place'] for box in selected_boxes])

        for box in selected_boxes:
            place = box.data['place']
            loc = "[{0}]({1}) - {2}".format(place.name, place.url, place.formatted_address)
            locations.append({
                'text': loc,
                'location': place.geo_location  # Dict with `lat`, `lng`
            })

        if date.lower() == 'tomorrow':
            text = 'Your trip to {0} Tomorrow will include the following places: '.format(city)
        else:
            text = 'Your trip to {0} on {1} will include the following places: '.format(city, date)
        text += " [Map](" + url + ")"
        rep = Reply(None, 'place_list', text)
        rep.data = locations
        return rep
        # selected_destinations = ' '.join(self.form['selected_items'])
        # return 'Your trip to {0} on {1} will include the following places: {2}'.format(
        #     city, date, selected_destinations)

    def get_suggestion_boxes(self):
        """
        Gets the suggestion boxes
        :return:
        """
        items = filter(lambda x: x.attribute == self.suggestion_box_attr, self.boxes)
        return list(items)

    def has_suggestions(self):
        items = filter(lambda x: x.attribute == self.suggestion_box_attr, self.boxes)
        return len(list(items)) > 0

    def has_finished_all_suggestions(self):
        """
        Has suggestions and they're all finished
        :return:
        """
        has_suggestion = False
        for x in self.boxes:
            if x.attribute != self.suggestion_box_attr: continue
            has_suggestion = True
            if not x.finished:
                return False
        return has_suggestion

    def __affirm_suggestion(self, box):
        self.last_affirmed_place = box.data['place']

    def next(self):
        """
        Goes to the next dialog box.
        Fetches suggestions if enough data is present
        :return:
        """
        # If we don't have any more boxes
        remaining_boxes = list(filter(lambda x: not x.finished, self.boxes))
        if len(remaining_boxes) == 0:
            if self.has_finished_all_suggestions():
                logging.info("Fetching next suggestions")
                exclusions = [x.data['place'] for x in
                              list(filter(lambda x: x.finished and x.attribute == "selected_items", self.boxes))]
                # Fetch similar suggestions
                similar_suggestion_query = self.get_suggestion_query()
                next_similar_suggestions = self.add_suggestions(True, exclusions, similar_suggestion_query, cnt=5)
                # Fetch random suggestions
                next_random_query = api.PlaceQuery("", [], None)
                next_random_query.is_random = True
                next_random_suggestions = self.add_suggestions(True, exclusions, next_random_query,
                                                               custom_radius=api.max_radius, cnt=3)
                total_new_suggestions = len(next_similar_suggestions) + len(next_random_suggestions)

                if total_new_suggestions == 0:
                    # logging.info("No boxes remainging and suggestions have been added. Finishing up.")
                    # logging.info(self.boxes)
                    itinerary_reply = self.create_itinerary()
                    itinerary_reply.prepend("I have all the information I need. Here's your itinerary ")
                    # self.reset()
                    return [itinerary_reply]
                else:
                    return self.next()  # [format_box_question(self.box, self.form)]  # [itinerary_reply]
            elif not self.initialized_suggestions:
                # type = self.form['interests']
                logging.info("Fetching first suggestions.")
                self.fetch_initial_city_suggestions()
                return self.next()
            else:
                itinerary_reply = self.create_itinerary()
                itinerary_reply.prepend("I have all the information I need. Here's your itinerary ")
                # self.reset()
                # logging.info("Creating itinerary")
                return [itinerary_reply]
        else:
            # Go to next unfinished box
            for i in range(len(self.boxes)):
                if not self.boxes[i].finished:
                    self.box = self.boxes[i]
                    self.index = i  # Update index
                    # logging.info("Progressed to box[%d] %s", self.index, self.box)
                    break

        reply = format_box_question(self.box, self.form)
        return [reply]

    def match_all_intents(self, intent, ents):
        """
        Go over unfinished boxes and try to validate them, stuffing replies from each one.
        This is skipped if the dialog is done.
        :param intent:
        :param ents:
        :return:
        """
        boxes = list(filter(lambda x: not x.finished and x.attribute != 'selected_item', self.boxes))
        reply = []
        matched_boxes = []
        if self.is_done():
            return reply, matched_boxes

        logging.info("Boxes left: ")
        for b in boxes: logging.info(b)

        for b in boxes:
            # logging.info("Non finished boxes: %s", b)
            valid, _, matches = b.validate_answer(intent, ents)
            if valid and not b.finished:
                self.set_form_matches(b, matches)
                logging.info("Set attribute: %s to %s", b.attribute, matches)
                b.finished = True
                logging.info("Finished box: %s", b)
                reply = self.next()
                # logging.info("Finished box: %s\nWith reply: %s", b, reply)
                matched_boxes.append(b)

        return reply, matched_boxes

    def set_intent(self, intent, entitites):
        self.last_interest = intent
        return []

    def get_suggestion_query(self):
        """

        :return: string The last interest
        """
        import operator
        softmax = lambda x: np.exp(x) / sum(np.exp(x))
        if self.last_interest is not None and len(self.last_interest) > 0:
            return api.PlaceQuery(self.last_interest, [], None)
        else:
            # Get the best matching query based on the current suggestions
            suggestions = filter(lambda x: x.attribute == self.suggestion_box_attr and x.finished, self.boxes)
            types = {}
            for s in [x for x in suggestions]:
                place = s.data['place']
                for t in place.types:
                    if t not in types:
                        types[t] = 1
                        self.probs[api.query_examples.index(t)] -= 2.0
                    else:
                        types[t] += 1
                        self.probs[api.query_examples.index(t)] += 1.0
                logging.info(s.data['place'].types)
                logging.info(s.data['place'].vicinity)
                logging.info(s.data['place'].name)
            sorted_x = sorted(types.items(), key=operator.itemgetter(1))
            sorted_x.reverse()
            self.probs = list(softmax(np.array(self.probs)))
            # Get the 2 most liked types and use them in the search
            return api.PlaceQuery("", [t[0] for t in sorted_x[:2]], None)

    def set_form_matches(self, box, matches):
        if isinstance(matches, list) and not isinstance(matches, str): matches = matches[0]
        if isinstance(matches, list) and not isinstance(matches, str): matches = matches[0]
        self.form[box.attribute] = matches

    def edit_form(self, ents):
        changes = ""

        for e in ents:
            logging.info("Setting %s to form with value `%s`", e, ents[e])
            if e == 'DATE':
                if 'date' not in self.form:
                    self.form['date'] = ''
                ent = ents[e]
                if isinstance(ent, list): ent = ents[e][0]
                changes += " date from {0} to {1}".format(self.form['date'], ent)
                self.form['date'] = ent
            elif e in ['GPE', 'location']:
                if 'city' not in self.form:
                    self.form['city'] = ''
                ent = ents[e]
                if isinstance(ent, list): ent = ents[e][0]
                changes += " destination from {0} to {1}".format(self.form['city'], ent)
                logging.info("Setting city to: %s", ent)
                self.form['city'] = ent
            elif e in ["museum", "coffee", "bar", "restaurant"]:
                if 'interests' not in self.form:
                    self.form['interests'] = ''
                ent = ents[e]
                if isinstance(ent, list): ent = ents[e][0]
                changes += " sites from {0} to {1}".format(self.form['interests'], ent)
                self.form['interests'] = ent
        # print("Form: ", self.form)
        if len(changes) > 0:
            changes = "Changing the " + changes
        return changes

    def terminate(self):
        self.terminating = True
        replies = [self.create_itinerary()]
        self.reset()
        return replies

    def process_intent(self, intent, ents):
        box = self.box
        initial_has_suggestions = self.has_suggestions()
        logging.info("Parsed intent %s", intent)
        logging.info("Entity %s", ents)
        logging.info("Current box: %s", box)

        # 2.1 check if intent matches greeting
        if intent == 'greet' and not 'DATE' in ents:
            self.reset()
            return False, [msg_reply(self.greet())]

        # 2.2 check if intent matches end
        replies = []
        if intent == 'end' and self.terminating:
            self.terminating = False
            return False, self.terminate()  # [format_box_question(self.box, self.form)]
        if intent == 'end':
            # replies = ["Are you sure you want to end your trip planning here?"]
            self.terminating = True
            replies = self.terminate()
            # return False, [msg_reply(replies)]
        elif intent == 'goodbye' and self.has_suggestions():
            # replies = ["Are you sure you want to end your trip planning here?"]
            self.terminating = True
            return False, self.terminate()  # [msg_reply(replies)]
        elif intent == 'goodbye':
            replies = ["Goodbye!"]
            self.terminating = True
            return False, self.terminate()  # [msg_reply(replies)]

        # 2.3 check if intent is reject/affirm
        if intent in ['reject', 'affirm']:
            # If answering a suggestion, load more like it, if  needed
            if self.terminating and intent == "affirm":
                logging.info("Terminating")
                replies = self.terminate()
                return True, replies
            elif self.terminating and intent == "reject":
                self.terminating = False
                return False, self.terminate()  # [format_box_question(self.box, self.form)]
            elif box.attribute == self.suggestion_box_attr:
                if intent == 'affirm':
                    items = self.form.get('selected_items', [])
                    items.append(box)
                    self.form['selected_items'] = items
                    self.__affirm_suggestion(box)
                self.boxes[self.index].finish(intent)
                logging.info("Finished box: %s", self.boxes[self.index])
                replies.extend(self.next())
                # elif len(replies)==0:
                return self.is_done(), replies  # msg_replies(replies)
        elif intent in self.interest_intents:
            replies = self.set_intent(intent, ents)

        # Intent to update the form
        if intent == 'change_form' and ents:
            replies = [self.edit_form(ents)]

        # 2.4 check if intent matches current box
        current_box_validated, reply, matches = box.validate_answer(intent, ents)
        current_matched_boxes = []
        if current_box_validated:
            self.set_form_matches(box, matches)
            self.box.finished = True
            self.box.answer_intent = intent
            # logging.info("Finished box: %s", self.boxes[self.index])
            next_replies = self.next()
            replies.extend(next_replies)
            current_matched_boxes.append(box)
            logging.info("Current box validated. Dialog is done: %s", self.is_done())

        # 3. check if intent matches other boxes
        rep, itents_matched_boxes = self.match_all_intents(intent, ents)
        logging.info("Matched all intents: %s", rep)
        current_matched_boxes.extend(itents_matched_boxes)

        # logging.info("Parsed intent: %s %s", str(intent), str(ents))
        # logging.info("Current box %s", self.box)
        if len(rep) > 0:
            replies = rep
        if reply:
            str_reply = format_form_message(self.form, reply)
            if len(replies) > 0:
                replies[0].prepend(str_reply)
            else:
                replies.append(msg_reply(str_reply))

        logging.info("Message marked these boxes as finished: ")
        for b in current_matched_boxes:
            logging.info(b)
        if len(replies) == 0:
            replies = [msg_reply("I can't answer that. Do you want to start over? If so just say `stop`.")]
        logging.info("Resulting replies: %s", replies[0])

        if not initial_has_suggestions and self.has_suggestions() and self.callback_on_search_done is not None:
            self.callback_on_search_done()
        logging.info("Form: %s", self.form)

        is_done = self.is_done()
        if is_done and self.autoreset_on_done:
            self.reset()
        return is_done, replies

    def process_message(self, message):
        """
        Parse intent and process it and it's entities
        :param message:
        :return: bool, Reply|None
        """
        logging.info("Got message: %s", message)
        intent, ents = self.nlp.parse_intent(message)
        return self.process_intent(intent, ents)


class Reply:

    def __init__(self, box, type, text):
        if isinstance(text, list) and not isinstance(text, str):
            text = '. '.join(text)
        data = box.data if box is not None else None
        self.type = type
        self.data = box.data if box is not None else None
        self.text = text
        self.img = data['img'] if (data is not None and 'img' in data) else None

    def str(self):
        text = self.text
        if isinstance(text, list) and not isinstance(text, str):
            text = '. '.join(text)
        return text

    def prepend(self, prefix):
        self.text = prefix + self.text

    def __str__(self) -> str:
        return self.text


def box_place_reply(box, question):
    output = Reply(box, 'place', question)
    return output


def box_interest_reply(box, question):
    output = Reply(box, 'interest_question', question)
    output.data = box.intent
    return output


def msg_reply(replies):
    """

    :param replies: String list or single string
    :return:
    """
    output = Reply(None, 'text', replies)
    return output


# Dialog creation and loading
#
def create_empty():
    d = load_dialog('conf/script.dialog')
    return d


def load_dialog(file):
    script = {}
    with open(file, 'r') as f:
        script = json.load(f)
    df = DialogFlow(script)
    return df


def reply(r):
    """
    Formats a reply into a string
    :param r:
    :return:
    """
    dunno = 'I dont know how to answer that'
    # print("Reply type: ", type(r))
    if isinstance(r, dict):
        if r['type'] == 'text':
            replies = r['replies']
            return '. '.join(replies)
    elif isinstance(r, list) and not isinstance(r, str):
        if len(r) == 0: r = [dunno]
        return '. '.join(r)
    else:
        if r == '': r = dunno
        return r


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

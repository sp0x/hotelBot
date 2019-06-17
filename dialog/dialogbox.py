# format_box_question
import logging

from dialog.reply import Reply

class DialogBox:
    def __init__(self, params):
        self.intent = params.get('intent', [])
        self.entities = params.get('entities', '')
        self.accepted = params.get('accepted', '')
        self.question = params.get('question', '')
        self.rejected = params.get('rejected', '')
        self.attribute = params.get('attribute', '')
        self.buttons = params.get('buttons', [])
        self.role = params.get('role', '')
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

    def format_box_question(self, form) -> Reply:
        """
        Formats a box into a question
        :param box:
        :param form:
        :return:
        """
        # question = box.question.format(**form)
        box = self
        question = format_form_message(form, box.question)
        if box.is_yes_no() and box.has_data():
            place_ = box.data['place']
            txt = question + " - " + place_.formatted_address
            output_reply = box_place_reply(box, txt)
        elif box.has_entity('interest'):
            output_reply = box_interest_reply(box, question)
        else:
            output_reply = msg_reply(question)
        if len(box.buttons) > 0:
            output_reply.buttons = box.buttons

        return output_reply

    def __str__(self) -> str:
        return "Dialogbox {4}:{0} {3} - ents {1} - Answer: {2}  ".format(self.intent, self.entities, self.answer_intent,
                                                                         self.question,
                                                                         'Done' if self.finished else 'NotDone')


def msg_reply(replies):
    """

    :param replies: String list or single string
    :return:
    """
    output = Reply(None, 'text', replies)
    return output


def box_place_reply(box, question):
    output = Reply(box, 'place', question)
    return output


def box_interest_reply(box, question):
    output = Reply(box, 'interest_question', question)
    output.data = box.intent
    return output


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
        # logging.info("Form field: %s , %s", k, f)
        printable_form[k] = f.capitalize()
    return msg.format(**printable_form)

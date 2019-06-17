import os
import threading
import traceback

from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.messages.text_message import TextMessage
from viberbot.api.messages.keyboard_message import KeyboardMessage
from viberbot.api.messages.picture_message import PictureMessage
from viberbot.api.messages.location_message import LocationMessage

from viberbot.api.viber_requests import ViberConversationStartedRequest
from viberbot.api.viber_requests import ViberFailedRequest
from viberbot.api.viber_requests import ViberMessageRequest
from viberbot.api.viber_requests import ViberSubscribedRequest
from viberbot.api.viber_requests import ViberUnsubscribedRequest
from viberbot.api.viber_requests.viber_seen_request import ViberSeenRequest
from viberbot.api.viber_requests.viber_delivered_request import ViberDeliveredRequest

from flask import Flask, request, Response
from iface import ChatIface
import logging
import time
import dialog


class Viber(ChatIface):

    def __init__(self, web_url, web_config=('0.0.0.0', 8080)):
        super().__init__()

        self.thread = None
        self.token = os.environ.get('VIBER_TOKEN')
        if self.token is None:
            raise Exception('VIBER_TOKEN env variable is nil.')
        self.bot_configuration = BotConfiguration(
            name=os.environ.get('VIBER_NAME'),
            avatar='https://static.thenounproject.com/png/363639-200.png',
            auth_token=self.token
        )
        self.api = None
        self.app = Flask(__name__)
        self.web_config = web_config
        self.web_url = web_url
        self.setup_routes()
        self.last_message = None

    def run(self):
        web_config = self.web_config
        self.thread = threading.Thread(target=self.start)
        self.thread.start()
        self.api = Api(self.bot_configuration)
        logging.info("Setting viber hook to: %s", self.web_url)
        evtypes = self.api.set_webhook(self.web_url)
        viber_account = self.api.get_account_info()
        logging.info("Registered ev types: %s", evtypes)
        logging.info("Account info: %s", viber_account)

    def start(self):
        web_config = self.web_config
        self.app.run(host=web_config[0], port=web_config[1], debug=True, use_reloader=False)

    #  Message handlers
    #

    # Conversation start allows only 1 message before a subscription
    def _on_start(self, user_id):
        viber = self.api
        d = self.get_dialog(user_id)
        g = d.start()
        d.on_searching(lambda details: self._callback_on_searching(user_id, details))
        keyboard_msg = self.get_initial_keyboard(user_id)._keyboard
        viber.send_messages(user_id, [
            TextMessage(text=g, keyboard=keyboard_msg),
        ])

    def _on_message(self, user_id, message):
        # Make sure our dialog is setup.
        d = self.get_dialog(user_id)
        d.on_searching(lambda details: self._callback_on_searching(user_id, details))
        try:
            # Process the message
            is_done, r = self.process_message(user_id, message)
            # Send replies
            self.send_replies(user_id, r)
        except Exception as ex:
            tb = traceback.format_exc()
            logging.info(tb)
            logging.info(ex)
            self.send_replies(user_id, "Sorry can you try a different phrase?")

    def _callback_on_searching(self, user_id, details):
        viber = self.api
        logging.info("Starting search at %s", details)
        place = details['location'].capitalize()
        t = details['type']
        if len(t) == 0:
            txtmsg = TextMessage(text="Great. Here are a few places for you to stay in {0}..".format(place))
            viber.send_messages(user_id, [txtmsg])
        else:
            txtmsg = TextMessage(text="Great. I'll start searching for {0} in {1}..".format('placest to stay', place))
            viber.send_messages(user_id, [txtmsg])

    def send_img(self, user_id, rep: dialog.dialog.Reply, keyboard: KeyboardMessage = None):
        viber = self.api
        imglist = rep.img
        if not isinstance(imglist, list):
            imglist = [imglist]
        img = imglist[0]
        if img is None:
            return
        img_url = img['url']
        k = None
        if keyboard is not None:
            k = keyboard._keyboard
        pmsg = PictureMessage(text=rep.text, media=img_url, tracking_data=user_id, keyboard=k)
        viber.send_messages(user_id, [pmsg])

    def send_keyboard(self, user_id, keyboard):
        viber = self.api
        viber.send_messages(user_id, [
            keyboard
        ])

    def send_replies(self, user_id, replies):
        viber = self.api

        if not isinstance(replies, list): replies = [replies]
        for rep in replies:
            if isinstance(rep, str):
                rep = dialog.dialog.msg_reply(rep)
            reply_text = rep.str()
            if reply_text == "": reply_text = "Can you try again with a different phrase?"
            logging.info("REPL[%s]: %s", rep.type, rep)
            self.send_reply(rep, reply_text, user_id)

    def send_reply(self, rep, reply_text, user_id):
        viber = self.api
        if rep.type == 'place':
            # Send the image and a button for the user to confirm or reject
            kbd = self.get_place_keyboard(user_id, rep.buttons)
            if rep.img:
                self.send_img(user_id, rep, keyboard=kbd)
            else:
                self.send_keyboard(reply_text, kbd)
        elif rep.type == 'place_list':
            logging.info("Reply itinerary: %s", reply_text)
            txtmsg = TextMessage(text=str(reply_text), keyboard=buttons_to_keyboard(rep.buttons))
            viber.send_messages(user_id, [txtmsg])
        elif rep.type == 'interest_question':
            txtmsg = TextMessage(text=str(reply_text), keyboard=buttons_to_keyboard(rep.buttons))
            viber.send_messages(user_id, [txtmsg])
        else:
            txtmsg = TextMessage(text=str(reply_text), keyboard=buttons_to_keyboard(rep.buttons))
            viber.send_messages(user_id, [txtmsg])

    def setup_routes(self):
        app = self.app

        @app.route('/', methods=['POST'])
        def incoming():
            import json
            viber = self.api
            data = request.get_data()
            logging.info("received request. post data: {0}".format(data))
            # every viber message is signed, you can verify the signature using this method
            if not viber.verify_signature(request.get_data(), request.headers.get('X-Viber-Content-Signature')):
                return Response(status=403)
            request_dict = json.loads(data)
            # this library supplies a simple way to receive a request object
            viber_request = viber.parse_request(data)

            if isinstance(viber_request, ViberConversationStartedRequest):
                user_id = viber_request.user.id
                self._on_start(user_id)
            elif isinstance(viber_request, ViberSeenRequest):
                pass
            elif isinstance(viber_request, ViberDeliveredRequest):
                pass
            elif isinstance(viber_request, ViberMessageRequest):
                sender_id = viber_request.sender.id
                message = viber_request.message
                # We need unique messages
                if isinstance(message, TextMessage):
                    ts = int(request_dict['timestamp'])
                    is_old = (self.last_message is not None and
                              self.last_message[2] == ts and
                              self.last_message[1] == sender_id)
                    cr_pair = (message.text, sender_id, ts)
                    logging.info("MSG DUMP: %s", cr_pair)
                    logging.info("LAST DUMP: %s", self.last_message)
                    logging.info("DUP: %s", is_old)
                    if not is_old:
                        self._on_message(sender_id, message.text)
                        self.last_message = cr_pair

            elif isinstance(viber_request, ViberFailedRequest):
                logging.warn("client failed receiving message. failure: {0}".format(viber_request))

            return Response(status=200)

        @app.route('/incoming', methods=['POST'])
        def incomingUrl():
            logging.debug("received request. post data: {0}".format(request.get_data()))
            # handle the request here
            return Response(status=200)

        @app.route('/health-check', methods=['GET'])
        def health():
            logging.debug("Health-check")
            # handle the request here
            return Response(status=200)

    def get_place_keyboard(self, user_id, additional_buttons=None):
        import json
        buttons = [{
            "Columns": 2,
            "Rows": 2,
            "Text": "<font color=\"#494E67\">Confirm</font>",
            "TextSize": "medium",
            "TextHAlign": "center",
            "TextVAlign": "bottom",
            "ActionType": "reply",
            "ActionBody": "Yes",
            "BgColor": "#f7bb3f",
        }, {
            "Columns": 2,
            "Rows": 2,
            "Text": "<font color=\"#494E67\">Reject</font>",
            "TextSize": "medium",
            "TextHAlign": "center",
            "TextVAlign": "bottom",
            "ActionType": "reply",
            "ActionBody": "No",
            "BgColor": "#f6f7f9",
        },
            {
                "Columns": 2,
                "Rows": 2,
                "Text": "<font color=\"#494E67\">Stop</font>",
                "TextSize": "medium",
                "TextHAlign": "center",
                "TextVAlign": "middle",
                "ActionType": "reply",
                "ActionBody": "Stop",
                "BgColor": "#f6f7f9",
            }
        ]
        if additional_buttons:
            buttons.extend([{
                "Columns": 2,
                "Rows": 2,
                "Text": "<font color=\"#494E67\">" + b + "</font>",
                "ActionBody": b,
            } for b in additional_buttons])
        keyboard = {
            "DefaultHeight": True,
            "BgColor": "#FFFFFF",
            "Type": "keyboard",
            "Buttons": buttons
        }
        msg = KeyboardMessage(keyboard=keyboard)
        return msg

    def get_initial_keyboard(self, user_id):
        keyboard = {
            "Type": "keyboard",
            "Buttons": [{
                "Columns": 6,
                "ActionType": "reply",
                "Rows": 1,
                "Text": "<font color=\"#494E67\">I want to book a hotel</font>",
                "TextSize": "medium",
                "TextHAlign": "center",
                "TextVAlign": "middle",
                "ActionBody": "I want to book a hotel",
            }
            ]
        }
        msg = KeyboardMessage(keyboard=keyboard)
        return msg


def buttons_to_keyboard(buttons):
    if buttons is None or len(buttons) == 0:
        return None
    bs = []
    total_cols = 6
    bl = len(buttons)
    bcol = 12
    if bl == 1:
        bcol = 6
    elif bl == 2:
        bcol = 3
    elif bl == 3:
        bcol = 2
    elif bl == 4:
        bcol = 2
    else:
        bcol = 1

    bs.extend([{
        "Columns": bcol,
        "Rows": 1,
        "Text": "" + b + "",
        "TextSize": "medium",
        "ActionBody": b,
        "ActionType": "reply",
        "TextHAlign": "center",
        "TextVAlign": "middle",
    } for b in buttons])
    keyboard = {
        "DefaultHeight": True,
        "Type": "keyboard",
        "Buttons": bs
    }
    return keyboard

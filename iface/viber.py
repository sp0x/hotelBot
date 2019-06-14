import os
import threading
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.messages.text_message import TextMessage
from viberbot.api.messages.keyboard_message import KeyboardMessage
from viberbot.api.messages.picture_message import PictureMessage
from viberbot.api.viber_requests import ViberConversationStartedRequest
from viberbot.api.viber_requests import ViberFailedRequest
from viberbot.api.viber_requests import ViberMessageRequest
from viberbot.api.viber_requests import ViberSubscribedRequest
from viberbot.api.viber_requests import ViberUnsubscribedRequest

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
            name='NetlytTestBot',
            avatar='https://static.thenounproject.com/png/363639-200.png',
            auth_token=self.token
        )
        self.api = None
        self.app = Flask(__name__)
        self.web_config = web_config
        self.web_url = web_url
        self.setup_routes()

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

    def _on_start(self, user_id):
        viber = self.api
        d = self.get_dialog(user_id)
        g = d.start()
        d.on_searching(lambda details: self._callback_on_searching(user_id, details))
        viber.send_messages(user_id, [
            TextMessage(text=g)
        ])

    def _on_message(self, user_id, message):
        viber = self.api
        is_done, r = self.process_message(user_id, message)
        viber.send_messages(user_id, [
            r
        ])

    def _callback_on_searching(self, user_id, details):
        viber = self.api
        logging.info("Starting search at %s", details)
        place = details['location'].capitalize()
        t = details['type']
        if len(t) == 0:
            viber.send_messages(user_id, [
                "Great. Here are a few places for you to stay in {0}..".format(place)
            ])
        else:
            viber.send_messages(user_id, [
                "Great. I'll start searching for {0} in {1}..".format('placest to stay', place)
            ])

    def send_img(self, user_id, rep: dialog.dialog.Reply):
        viber = self.api
        imglist = rep.img
        if not isinstance(imglist, list):
            imglist = [imglist]
        img = imglist[0]
        if img is None:
            return
        img_url = img['url']
        pmsg = PictureMessage(media=img_url)
        viber.send_message(user_id, message=pmsg)

    def send_keyboard(self, user_id, keyboard):
        viber = self.api
        viber.send_messages(user_id, [
            keyboard
        ])

    def send_message(self, user_id, replies):
        viber = self.api

        if not isinstance(replies, list): replies = [replies]
        for rep in replies:
            if isinstance(rep, str):
                rep = dialog.dialog.msg_reply(rep)
            reply_text = rep.str()
            if reply_text == "": reply_text = "Can you try again with a different phrase?"
            if rep.type == 'place':
                # Send the image and a button for the user to confirm or reject
                if rep.img:
                    self.send_img(user_id, rep)
                self.send_keyboard(reply_text, self.get_place_keyboard(user_id))
            elif rep.type == 'place_list':
                logging.info("Reply itinerary: %s", reply_text)
                viber.send_messages(user_id, [reply_text])
                # for place in rep.data:
                #     place_text = place['text']
                #     place_loc = place['location']
                #     # bot.send_location(chat_id, latitude=float(place_loc['lat']), longitude=float(place_loc['lng']))
                #     # update.message.reply_text(place_text, parse_mode=telegram.ParseMode.MARKDOWN)
            elif rep.type == 'interest_question':
                # update.message.reply_text(reply_text, parse_mode=telegram.ParseMode.MARKDOWN)
                interests = rep.data
                # custom_keyboard = [[x.capitalize()] for x in interests]
                # reply_markup = ReplyKeyboardMarkup(custom_keyboard, one_time_keyboard=True)
                # reply_markup = None
                # bot.send_message(chat_id=chat_id, text=reply_text, reply_markup=reply_markup)
                viber.send_message(user_id, reply_text)
            else:
                viber.send_message(user_id, reply_text)

    def setup_routes(self):
        app = self.app

        @app.route('/', methods=['POST'])
        def incoming():
            viber = self.api
            logging.debug("received request. post data: {0}".format(request.get_data()))
            # every viber message is signed, you can verify the signature using this method
            if not viber.verify_signature(request.get_data(), request.headers.get('X-Viber-Content-Signature')):
                return Response(status=403)

            # this library supplies a simple way to receive a request object
            viber_request = viber.parse_request(request.get_data())
            sender_id = viber_request.sender.id

            if isinstance(viber_request, ViberConversationStartedRequest):
                self._on_start(sender_id)

            elif isinstance(viber_request, ViberMessageRequest):
                message = viber_request.message
                self._on_message(sender_id, message)
            elif isinstance(viber_request, ViberSubscribedRequest):
                viber.send_messages(sender_id, [
                    TextMessage(text="thanks for subscribing!")
                ])
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

    def get_place_keyboard(self, user_id):
        import json
        keyboard = json.dumps({
            "Buttons": [{
                "Columns": 2,
                "Rows": 2,
                "Text": "<font color=\"#494E67\">Confirm 😃</font><br><br>",
                "TextSize": "medium",
                "TextHAlign": "center",
                "TextVAlign": "bottom",
                "ActionType": "reply",
                "ActionBody": "Confirm 😃",
                "BgColor": "#f7bb3f",
            }, {
                "Columns": 2,
                "Rows": 2,
                "Text": "<font color=\"#494E67\">Reject</font><br><br>",
                "TextSize": "medium",
                "TextHAlign": "center",
                "TextVAlign": "bottom",
                "ActionType": "reply",
                "ActionBody": "Reject",
                "BgColor": "# f6f7f9",
            },
                {
                    "Columns": 2,
                    "Rows": 2,
                    "Text": "<font color=\"#494E67\">Stop</font><br><br>",
                    "TextSize": "medium",
                    "TextHAlign": "center",
                    "TextVAlign": "bottom",
                    "ActionType": "reply",
                    "ActionBody": "Stop",
                    "BgColor": "# f6f7f9",
                }
            ]
        })
        msg = KeyboardMessage(tracking_data=user_id, keyboard=keyboard)
        return msg

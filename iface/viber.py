import os
import threading
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.messages.text_message import TextMessage
from viberbot.api.viber_requests import ViberConversationStartedRequest
from viberbot.api.viber_requests import ViberFailedRequest
from viberbot.api.viber_requests import ViberMessageRequest
from viberbot.api.viber_requests import ViberSubscribedRequest
from viberbot.api.viber_requests import ViberUnsubscribedRequest

from flask import Flask, request, Response
from iface import ChatIface
import logging
import time


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

    def on_start(self, user_id):
        viber = self.api
        d = self.get_dialog(user_id)
        g = d.start()
        viber.send_messages(user_id, [
            TextMessage(text=g)
        ])

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

            if isinstance(viber_request, ViberConversationStartedRequest):
                self.on_start(viber_request.get_user().get_id())

            elif isinstance(viber_request, ViberMessageRequest):
                message = viber_request.message
                # lets echo back
                viber.send_messages(viber_request.sender.id, [
                    message
                ])
            elif isinstance(viber_request, ViberSubscribedRequest):
                viber.send_messages(viber_request.get_user().id, [
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

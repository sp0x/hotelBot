import os
import threading
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from flask import Flask, request, Response
import logging
import time


class Viber:

    def __init__(self, web_config=('0.0.0.0', 8080)):
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
        self.setup_routes()


    def run(self):
        web_config = self.web_config
        self.app.run(host=web_config[0], port=web_config[1], debug=True, use_reloader=False)
        self.thread = threading.Thread(target=self.start)
        self.thread.start()

    def start(self):
        self.api = Api(self.bot_configuration)


    def setup_routes(self):
        app = self.app

        @app.route('/incoming', methods=['POST'])
        def incoming():
            logging.debug("received request. post data: {0}".format(request.get_data()))
            # handle the request here
            return Response(status=200)

        @app.route('/health-check', methods=['GET'])
        def health():
            logging.debug("Health-check")
            # handle the request here
            return Response(status=200)

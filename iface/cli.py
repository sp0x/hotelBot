import threading
import logging

from iface import ChatIface


class Cli(ChatIface):

    def __init__(self):
        super().__init__()
        self.thread = threading.Thread(target=self.start)

    def run(self):
        self.thread.start()

    def start(self):
        pass

    def on_start(self, user_id):
        d = self.get_dialog(user_id)
        r = d.start()
        d.on_searching(lambda details: self._callback_on_searching(user_id, details))
        return r

    def _callback_on_searching(self, user_id, details):
        logging.info("Starting search at %s", details)
        place = details['location'].capitalize()
        t = details['type']
        if len(t) == 0:
            logging.info("Great. Here are a few places for you to stay in {0}..".format(place))
        else:
            logging.info("Great. I'll start searching for {0} in {1}..".format('placest to stay', place))

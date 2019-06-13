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
        dialog = self.get_dialog(user_id)
        r = dialog.start()
        logging.info('Text: %s', r)




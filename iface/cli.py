import threading
import logging
import dialog
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

    def send_img(self, user_id, rep: dialog.dialog.Reply):
        imglist = rep.img
        if not isinstance(imglist, list):
            imglist = [imglist]
        img = imglist[0]
        if img is None:
            return
        img_url = img['url']
        logging.info("MSG_IMG: %s", img_url)

    def send_message(self, user_id, replies):
        if not isinstance(replies, list): replies = [replies]
        for rep in replies:
            if isinstance(rep, str):
                rep = dialog.dialog.msg_reply(rep)
            reply_text = rep.str()
            if reply_text == "": reply_text = "Can you try again with a different phrase?"
            logging.info("Sending msg[%s]", rep.type)
            if rep.type == 'place':
                if rep.img:
                    self.send_img(user_id, rep)
                logging.info("MSG: %s", reply_text)
                logging.info("KB: Confirm, Reject, End")
            elif rep.type == 'place_list':
                pass
            elif rep.type == 'interest_question':
                pass
            else:
                logging.info("MSG: %s", reply_text)



    def _callback_on_searching(self, user_id, details):
        logging.info("Starting search at %s", details)
        place = details['location'].capitalize()
        t = details['type']
        if len(t) == 0:
            logging.info("ONSEARCH: Great. Here are a few places for you to stay in {0}..".format(place))
        else:
            logging.info("ONSEARCH: Great. I'll start searching for {0} in {1}..".format('placest to stay', place))

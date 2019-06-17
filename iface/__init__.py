import logging
import dialog


def run_bots(ifaces):
    for iface in ifaces:
        iface.run()
        logging.info("Running inface: %s", iface)


def _wrap_dialog(ifc):
    outp = {
        'flow': dialog.create_empty(),
        'iface': ifc
    }
    return outp


class ChatIface:

    def __init__(self):
        self.dialogs = {}

    def is_done(self, uid):
        d = self.get_dialog(uid)
        return d.is_done()

    def get_dialog(self, session_id) -> dialog.dialog.DialogFlow:
        if session_id not in self.dialogs:
            self.dialogs[session_id] = _wrap_dialog(self)
            # self.dialogs[session_id]['flow'].on_searching(
            #     lambda details: send_searching_action(details, dialogs[id]['bot'], dialogs[id]['update']))
            # self.dialogs[session_id]['flow'].on_search_resolved(
            #     lambda: send_searching_update(id, dialogs[id]['bot'], dialogs[id]['update']))
        return self.dialogs[session_id]['flow']

    def process_message(self, uid, msg):
        d = self.get_dialog(uid)
        if msg.lower() == "single":
            msg = "Single rooms"
        elif msg.lower() == "double":
            msg = "Double rooms"
        elif msg.lower() == "triple":
            msg = "Triple rooms"
        done, replies = d.process_message(msg)
        return done, replies

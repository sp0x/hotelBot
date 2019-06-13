from dialog import create_empty
from iface.cli import Cli
import logging


if __name__ == '__main__':
    c = Cli()
    uid = "user1"
    c.run()
    r = c.on_start(uid)
    done = c.is_done(uid)
    logging.info("Greet: %s", r)
    while not done:
        m = input("\nYou: ")
        d = c.get_dialog(uid)
        done, replies = d.process_message(m)
        for r in replies:
            logging.info("\nReply: %s", r)
    logging.info("Done")

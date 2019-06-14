from dialog import create_empty
from iface.cli import Cli
import logging


if __name__ == '__main__':
    c = Cli()
    uid = "user1"
    c.run()
    r = c.on_start(uid)
    done = c.is_done(uid)
    logging.info("Greet[%s]: %s", type(r), r)
    while not done:
        m = input("\nYou: ")
        done, replies = c.process_message(uid, m)
        for r in replies:
            logging.info("\nReply[%s]: %s", type(r), r)
    logging.info("Done")

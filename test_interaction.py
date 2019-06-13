from dialog import create_empty
import logging


if __name__ == '__main__':
    d = create_empty()
    r = d.start()
    done = d.is_done()
    logging.info("Greet: %s", r)
    while not done:
        m = input("\nYou: ")
        done, replies = d.process_message(m)
        for r in replies:
            logging.info("\nReply: %s", r)
    logging.info("Done")

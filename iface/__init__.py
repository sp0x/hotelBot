from iface.viber import Viber
import logging


def run_bots(ifaces):
    for iface in ifaces:
        iface.run()
        logging.info("Running inface: %s", iface)

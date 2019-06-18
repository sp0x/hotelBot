from dialog import create_empty
from iface.cli import Cli
import logging
import api

if __name__ == '__main__':
    query = api.PlaceQuery("hotel", [], None)
    query.types = ['establishment']
    location = 'Barcelona'
    recs = api.get_random_locations(location, query, 8, probs=[], radius=api.max_radius)
    logging.info("Found suggestions for search: %s", [x['title'] for x in recs])
from googleplaces import GooglePlaces, types, lang, Place
import os
import random
import logging
import numpy as np

logging.basicConfig(format='[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

google_places = GooglePlaces(os.environ.get('GOOGLE_TOKEN'))
folloup_radius = 2000
default_radius = 3600
max_radius = 5000


def __fetch_photo(p):
    if p is not None:
        p.get(maxheight=300, maxwidth=300)
    photo_data = p.data if p else None
    return photo_data


nphotos = 3
place_types = [
    'geocode',
    'address',
    'establishment',
    'point_of_interest',
    'lodging',
    'political',
    'locality',
    'cafe',
    'store',
    'food',
    'bar',
    'restaurant'
]

query_examples = [
    'museum', 'bar', 'restaurant', 'coffee', 'shop', 'gallery', 'landmark', 'gym', 'hotel',
    'night club', 'beer place', 'monuments', 'sights', 'festivals'
]


def location_name(loc_or_str):
    if isinstance(loc_or_str, str):
        return loc_or_str
    else:
        return loc_or_str.name


def get_random_locations(location, query, count, probs, radius=3200, exclusions=None):
    cnt = random.randint(1, len(query_examples))
    all_results = []
    for c in range(cnt):
        if not query.has_query_keywords():
            keyword = np.random.choice(query_examples, p=probs)
            query.set_query_keywords(keyword)

        keywords = query.capitalize()
        types = query.types
        if isinstance(location, Place):
            query_result = google_places.nearby_search(lat_lng=location.geo_location, keyword=keywords, radius=radius,
                                                       types=types)
        else:
            query_result = google_places.nearby_search(location=location, keyword=keywords, radius=radius, types=types)
        all_results.extend(list(query_result.places))
    randoms = random.choices(all_results, k=count)
    output = format_places(randoms, exclusions)
    return output


def get_recommendation_for_location(location, query, count=1, radius=3200, exclusions=None):
    """

    :param location:
    :param PlaceQuery query:
    :param count:
    :param radius:
    :param exclusions:
    :return:
    """
    print("Looking for {0} in {1} ({2},{3})".format(query, location, type(location), type(query)))
    keywords = query.capitalize()
    types = query.types
    if isinstance(location, Place):
        query_result = google_places.nearby_search(lat_lng=location.geo_location, keyword=keywords, radius=radius,
                                                   types=types)
    else:
        query_result = google_places.nearby_search(location=location, keyword=keywords, radius=radius, types=types)
    places = list(query_result.places)[:count]
    output = format_places(places, exclusions)
    return output


def format_places(places, exclusions):
    output = []
    for place in places:
        if exclusions is not None:
            logging.info("Place filters: %s", exclusions)
            is_filtered = next(filter(lambda p: p.name == place.name, exclusions), None) is not None
            if is_filtered: continue

        # print(place.place_id)
        place.get_details()
        photos = place.photos[:nphotos]
        imgs = []
        for p in photos:
            imgs.append({
                'fetcher': __fetch_photo,
                'obj': p
            })
        output.append({
            'title': place.name,
            'img': imgs,
            'place': place
        })
    return output


class PlaceQuery:

    def __init__(self, query_string, types, place):
        self.query_string = query_string
        self.types = types if types is not None else []
        self.place = place
        self.is_random = False

    def capitalize(self):
        return (self.query_string if self.query_string is not None else "").capitalize()

    def __str__(self) -> str:
        return "%s: %s" % (self.types, self.query_string)

    def set_query_keywords(self, strx):
        self.query_string = strx

    def has_query_keywords(self):
        return self.query_string is not None and len(self.query_string) > 0

# -*- coding: UTF-8 -*-
"""
Yelp v3 API see: https://www.yelp.com/developers/documentation/v3/
Adapted from https://pypi.python.org/pypi/yelp3/1.0.1 """

import json
import urllib

import six

from errors import ErrorHandler

API_HOST = 'api.yelp.com'
AUTH_URL = "https://api.yelp.com/oauth2/token"

BUSINESS_SEARCH_PATH = '/v3/businesses/search'
PHONE_SEARCH_PATH = '/v3/businesses/search/phone'
TRANSACTION_SEARCH_PATH = '/v3/transactions/{transaction_type}/search'
BUSINESS_PATH = '/v3/businesses/{id}'
REVIEWS_PATH = '/v3/businesses/{id}/reviews'
AUTOCOMPLETE_PATH = '/v3/autocomplete'


class Client(object):
    """Yelp fusion (v3) API client."""
    def __init__(self, app_id, app_secret, debug=False):
        self.access_token = self.get_access_token(app_id, app_secret)
        self._error_handler = ErrorHandler()
        self.debug = debug

    @staticmethod
    def get_access_token(app_id, app_secret):
        data = urllib.urlencode({
            "grant_type": "client_credentials",
            "client_id": app_id,
            "client_secret": app_secret
        })
        return json.loads(urllib.urlopen(AUTH_URL, data).read())["access_token"]

    # Query endpoints

    def business_search(self, **url_params):
        return self._make_request(
            path=BUSINESS_SEARCH_PATH,
            url_params=dict(**url_params)
        )

    def phone_search(self, **url_params):
        return self._make_request(
            path=PHONE_SEARCH_PATH,
            url_params=dict(**url_params)
        )

    def transaction_search(self, transaction_type, **url_params):
        return self._make_request(
            path=TRANSACTION_SEARCH_PATH.format(
                transaction_type=transaction_type
            ),
            url_params=dict(**url_params)
        )

    def business(self, _id, **url_params):
        return self._make_request(
            path=BUSINESS_PATH.format(
                id=_id
            ),
            url_params=dict(**url_params)
        )

    def review(self, _id, **url_params):
        return self._make_request(
            path=REVIEWS_PATH.format(
                id=_id
            ),
            url_params=dict(**url_params)
        )

    def autocomplete(self, **url_params):
        return self._make_request(
            path=AUTOCOMPLETE_PATH,
            url_params=dict(**url_params)
        )

    # Wrapper for the search query checking the location type
    def search_query(self, query, location):
        num_bizs_to_display = 5
        params = {
            "term": query,
            "lang": "en",
            "limit": num_bizs_to_display
        }
        if location["type"] == "lat_long":
            print "Searching for '{}' using lat_long position".format(query)
            latitude, longitude = location["value"]["value"]
            return self.business_search(latitude=latitude, longitude=longitude, **params)
        elif location["type"] == "location_string":
            print "Searching for '{}' in {}".format(query, location["value"]["value"])
            return self.business_search(location=location["value"]["value"], **params)
        return

    @staticmethod
    def _filter_dict(old_dict, cb):
        """ Returns a filtered dictionary based on the result of `cb(key)`. """
        return {k: v for k, v in old_dict.items() if cb(k)}

    def _make_request(self, path, url_params={}):

        # filter out parameters that equal None
        url_params = Client._filter_dict(url_params, lambda k: url_params[k] is not None)

        url = 'https://{0}{1}?'.format(
            API_HOST,
            six.moves.urllib.parse.quote(path.encode('utf-8'))
        ) + six.moves.urllib.parse.urlencode(url_params)

        request = six.moves.urllib.request.Request(
            url,
            headers={
                "Authorization": "Bearer {0}".format(self.access_token)
            }
        )

        try:
            conn = six.moves.urllib.request.urlopen(request)
        except six.moves.urllib.error.HTTPError as error:
            self._error_handler.raise_error(error)

        try:
            data = conn.read()
            response = json.loads(data.decode('utf-8'))

            if self.debug:
                print("\n> " + request.get_full_url())
                print("")
                print(str(conn.info()))

        finally:
            conn.close()

        return response

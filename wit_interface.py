# -*- coding: UTF-8 -*-
import wit

from messenger_actions import post_search_carousel
from messenger_actions import request_location
from messenger_actions import send_message


class WitInterface:
    """Wrapper over the wit client to be able to pass yelp API client and FB token."""

    def __init__(self, yelp_client, wit_token, fb_token):
        self.yelp_client = yelp_client
        self.fb_token = fb_token
        actions = {
            "search": self.yelp_search_and_display_action,
            "send": self.send_action,
            "requestLocation": self.request_location_action,
            "setContext": self.set_context_action,
        }
        self.wit_client = wit.Wit(access_token=wit_token, actions=actions)

    def yelp_search_and_display_action(self, request):
        """Call the yelp API to search for businesses, and display the results."""
        context = request['context']
        # This is a workaround since wit's model often fails to follow a single story correctly
        context = self.set_context_action(request)
        location = context["location"]
        print "Location dict: {}".format(location)
        query = context["local_search_query"]["value"]
        print "local search query: {}".format(query)
        search_response = self.yelp_client.search_query(query=query, location=location)
        context["search_response"] = search_response
        sender_id = request['session_id']
        post_search_carousel(self.fb_token, sender_id, context["search_response"])
        return context

    def request_location_action(self, request):
        """Request the user's location."""
        context = request['context']
        sender_id = request['session_id']
        request_location(self.fb_token, sender_id)
        return context

    def send_action(self, request, response):
        """Send a text message"""
        text = response["text"]
        fb_id = request["session_id"]
        send_message(self.fb_token, recipient=fb_id, text=text)

    @staticmethod
    def set_context_action(request):
        """Update the context with extracted entities"""
        context = request['context']
        entities = request['entities']
        if entities:
            for entity, values in entities.iteritems():
                if entity == "location":
                    # we differentiate with lat_long type locations
                    context[entity] = {"value": values[0], "type": "location_string"}
                else:
                    context[entity] = values[0]
        print "Context is set to {}".format(context.keys())
        return context


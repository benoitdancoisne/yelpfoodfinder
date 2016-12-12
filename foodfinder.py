# -*- coding: UTF-8 -*-
import json
from collections import defaultdict

from flask import Flask, request

from messenger_actions import post_biz_details
from messenger_actions import post_review_details
from messenger_actions import request_location
from messenger_actions import send_message
from wit_interface import WitInterface
from yelp3.client import Client

app = Flask(__name__)

# Time (in s) after which we forget the context for a given user
CONTEXT_LIFESPAN = 90

# Load credentials
with open("keys.json", "r") as fi:
    keys = json.load(fi)
fb_token = keys["facebook_messenger"]["page_access_token"]

# Setup Yelp fusion API client
app_id = keys["yelp_fusion"]["app_id"]
app_secret = keys["yelp_fusion"]["app_secret"]
yelp_client = Client(app_id, app_secret)

# Setup Wit API client
wit_interface = WitInterface(yelp_client, keys["wit"]["server_side_token"], fb_token)

# Setup user_to_current_context dictionary
user_to_current_context = defaultdict(dict)
user_to_last_message = defaultdict(int)


def extract_messages_payload(payload):
    """Generate dictionaries of input data from the
    provided payload.
    """
    data = json.loads(payload)
    events = data["entry"][0]["messaging"]
    timestamp = data["entry"][0]["time"]
    for event in events:
        if "message" in event:
            yield {
                "sender": event["sender"]["id"],
                "timestamp": event["timestamp"],
                "text": event["message"].get("text"),
                "attachments": event["message"].get("attachments"),
            }
        elif "postback" in event:
            yield {
                "sender": event["sender"]["id"],
                "timestamp": event["timestamp"],
                "postback": event["postback"].get("payload"),
            }


@app.route('/', methods=['GET'])
def handle_verification():
    """Handles verification call to bind an app."""
    # Heroku tails stdout by default
    print "Handling Verification."
    if request.args.get('hub.verify_token', '') == keys["facebook_messenger"]["verify_token"]:
        print "Verification successful!"
        return request.args.get('hub.challenge', '')
    else:
        print "Verification failed!"
        return 'Error, wrong validation token'


@app.route('/', methods=['POST'])
def handle_messages():
    """Handles incoming messages."""
    print "Handling Messages"
    payload = request.get_data()
    print "Payload: {}".format(payload)

    for input_data in extract_messages_payload(payload):
        sender = input_data["sender"]
        timestamp = input_data["timestamp"]
        context = user_to_current_context[sender]
        print "Stored context: {}".format(context.keys())
        # look at last message and possibly clear context if it is too old
        last_message = user_to_last_message[sender]
        if timestamp - last_message > CONTEXT_LIFESPAN*1e3:
            print "Last message from {} received more than {}s ago, clearing context".format(sender, CONTEXT_LIFESPAN)
            context = {}
        user_to_last_message[sender] = timestamp
        # decodes eventual text
        if input_data.get("text"):
            text = input_data["text"].encode('unicode_escape')
        # handle attachments
        if input_data.get("attachments"):
            print "Handling attachments"
            attachment = input_data["attachments"][0]
            print attachment
            # disregard images
            if attachment["type"] == "image":
                send_message(fb_token, sender, "Nice image!")
            # put gps location in the context and send updated context to wit using an empty message
            # this is a workaround to make wit understand a key has been updated even with no text message
            elif attachment["type"] == "location":
                latitude = attachment["payload"]["coordinates"]["lat"]
                longitude = attachment["payload"]["coordinates"]["long"]
                context["location"] = {"type": "lat_long", "value": {
                    "suggested": False, "value": (latitude, longitude), "confidence": 1, "type": "value"
                }}
                context = wit_interface.wit_client.run_actions(session_id=sender, message="", context=context)
        elif input_data.get("postback"):
            print "Handling postback"
            postback_data = json.loads(input_data["postback"])
            print postback_data
            # handle button clicks
            if "details" in postback_data:
                biz_id = postback_data["details"].encode('unicode_escape')
                print "Details postback for business {}".format(biz_id)
                context["business_response"] = yelp_client.business(biz_id)
                post_biz_details(fb_token, sender, context["business_response"])
            elif "reviews" in postback_data:
                biz_id = postback_data["reviews"].encode('unicode_escape')
                print "Reviews postback for business {}".format(biz_id)
                review_response = yelp_client.review(biz_id)
                post_review_details(fb_token, sender, review_response)
            elif "update_location" in postback_data:
                request_location(fb_token, sender)

        else:
            print text
            if text == "Debug":
                # keyword to catch wit errors without having to tail logs
                send_message(fb_token, sender, "query: {}".format(context.get("local_search_query")))
                send_message(fb_token, sender, "location: {}".format(context.get("location")))
            else:
                print "Sending message to wit client"
                # we get text back, so we send it to Wit
                print "Context keys before wit: {}".format(context.keys())
                context = wit_interface.wit_client.run_actions(session_id=sender, message=text, context=context)
                user_to_current_context[sender] = context
                print "Context keys after wit: {}".format(context.keys())
    return "ok"


if __name__ == '__main__':
    app.run()

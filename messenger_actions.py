# -*- coding: UTF-8 -*-
import datetime
import json

import requests


def send_message(token, recipient, text):
    """Send the message text to the recipient using messenger API."""
    r = requests.post(
      "https://graph.facebook.com/v2.6/me/messages",
      params={"access_token": token},
      data=json.dumps(
        {
          "recipient": {"id": recipient},
          "message": {"text": text.decode('unicode_escape')}
         }
      ),
      headers={'Content-type': 'application/json'}
    )
    if r.status_code != requests.codes.ok:
        print r.text


def request_user_info(token, user_id):
    """Looks up facebook user infos."""
    r = requests.get(
      "https://graph.facebook.com/v2.6/{}".format(user_id),
      params={"access_token": token,
              "fields": "first_name,last_name,profile_pic,locale,timezone,gender"},
      headers={'Content-type': 'application/json'}
    )
    if r.status_code != requests.codes.ok:
        print r.text
    return r.json()


def post_search_carousel(token, recipient, yelp_response):
    """Show a carousel with search results from Yelp."""
    print "Got back {} bizs from yelp api".format(len(yelp_response["businesses"]))
    elements = []
    for i in range(len(yelp_response["businesses"])):
        biz = yelp_response["businesses"][i]
        if not biz["is_closed"]:
            elements.append(
                {
                    "title": biz["name"],
                    "item_url": biz["url"],
                    "image_url": biz["image_url"],
                    "subtitle": "Rated {:g}* stars out of {} Yelp reviews".format(float(biz["rating"]), biz["review_count"]),
                    "buttons": [
                        {
                            "type": "postback",
                            "title": "More details",
                            "payload": json.dumps({"details": biz["id"]}),
                        },
                        {
                            "type": "element_share"
                        }
                    ]
                }
            )
    r = requests.post(
        "https://graph.facebook.com/v2.6/me/messages",
        params={"access_token": token},
        data=json.dumps(
            {
                "recipient": {"id": recipient},
                "message": {
                    "attachment": {
                        "type": "template",
                        "payload": {
                            "template_type": "generic",
                            "elements": elements,
                        }
                    }
                },
            }
        ),
        headers={'Content-type': 'application/json'}
    )
    if r.status_code != requests.codes.ok:
        print r.text
    print "Sent carousel"


def post_biz_details(token, recipient, yelp_response):
    """Show a list of yelp reviews for a given business."""
    print "Showing details for {}".format(yelp_response["id"])
    location = yelp_response["location"]
    display_address = location["address1"] + "\n" + location["city"]
    if yelp_response.get("hours") and yelp_response.get("hours")[0]["is_open_now"]:
        display_address += "\n[Open now!]"
    else:
        hours, minutes = find_next_open_time(yelp_response.get("hours"))
        display_address += "\n[Opens at {}:{}]".format(hours, minutes)
    elements = [
                {
                    "title": yelp_response["name"]+" ({})".format(yelp_response["price"]),
                    "image_url": yelp_response["image_url"],
                    "subtitle": ", ".join(cat["title"] for cat in yelp_response["categories"]),
                    "buttons": [
                        {
                            "type": "web_url",
                            "url": yelp_response["url"],
                            "title": "View on Yelp",
                            "webview_height_ratio": "tall",
                        }
                    ]
                },
                {
                    "title": display_address,
                    "buttons": [
                        {
                            "type": "web_url",
                            # This is mainly to cater for iphones, but it will redirect to Google maps on WWW
                            "url": "http://maps.apple.com/maps?q={},{}".format(
                                yelp_response["coordinates"]["latitude"],
                                yelp_response["coordinates"]["longitude"]
                            ),
                            "title": "Go there",
                        }
                    ]
                },
                {
                    "title": "Rated {:g}* on Yelp".format(float(yelp_response["rating"])),
                    "subtitle": "{} reviews".format(yelp_response["review_count"]),
                    "buttons": [
                        {
                            "type": "postback",
                            "title": "See reviews",
                            "payload": json.dumps({"reviews": yelp_response["id"]}),
                        }
                    ]
                }
        ]
    if yelp_response.get("photos") and len(yelp_response.get("photos")) > 1:
        elements[2]["image_url"] = yelp_response["photos"][1]

    r = requests.post(
        "https://graph.facebook.com/v2.6/me/messages",
        params={"access_token": token},
        data=json.dumps(
            {
                "recipient": {"id": recipient},
                "message": {
                    "attachment": {
                        "type": "template",
                        "payload": {
                            "template_type": "list",
                            "elements": elements
                        }
                    }
                },
            }
        ),
        headers={'Content-type': 'application/json'}
    )
    if r.status_code != requests.codes.ok:
        print r.text


def post_review_details(token, recipient, yelp_response):
    elements = []
    for review in yelp_response["reviews"]:
        elements.append(
            {
                "title": "{} stars review by {}".format(review["rating"], review["user"]["name"]),
                "image_url": review["user"]["image_url"],
                "subtitle": review["text"],
                "buttons": [
                    {
                        "type": "web_url",
                        "url": review["url"],
                        "title": "Read more",
                        "webview_height_ratio": "tall",
                    }
                ]
            }
        )
    if len(elements):
        r = requests.post(
            "https://graph.facebook.com/v2.6/me/messages",
            params={"access_token": token},
            data=json.dumps(
                {
                    "recipient": {"id": recipient},
                    "message": {
                        "attachment": {
                            "type": "template",
                            "payload": {
                                "template_type": "list",
                                "top_element_style": "compact",
                                "elements": elements
                            }
                        }
                    },
                }
            ),
            headers={'Content-type': 'application/json'}
        )
        if r.status_code != requests.codes.ok:
            print r.text


def request_location(token, recipient):
    """Request the user's location by showing a "send location" button."""
    r = requests.post(
      "https://graph.facebook.com/v2.6/me/messages",
      params={"access_token": token},
      data=json.dumps(
        {
          "recipient": {"id": recipient},
          "message": {
              "text": "Where do you want me to search? "
                      "You can type a location or send me your GPS coordinates!",
              "quick_replies": [
                  {
                      "content_type": "location",
                  }
              ]
          }
        }
      ),
      headers={'Content-type': 'application/json'}
    )
    if r.status_code != requests.codes.ok:
        print r.text
    return r.json


def load_persistent_menu(token):
    """Sets up a persistent menu."""
    r = requests.post(
        "https://graph.facebook.com/v2.6/me/thread_settings",
        params={"access_token": token},
        data=json.dumps(
            {
                "setting_type": "call_to_actions",
                "thread_state": "existing_thread",
                "call_to_actions": [
                    {
                        "type": "postback",
                        "title": "Update my location",
                        "payload":  json.dumps({"update_location": True}),
                    },
                    {
                        "type": "web_url",
                        "title": "Go to yelp.com",
                        "url": "http://yelp.com",
                    }
                ]
            }
        ),
        headers={'Content-type': 'application/json'}
    )
    if r.status_code != requests.codes.ok:
        print r.text


def find_next_open_time(hours_dict):
    """Finds the next opening time for a business."""
    # Assumes all days are defined
    open_hours = hours_dict[0]["open"]
    if len(open_hours) < 7:
        return "", ""
    today = datetime.datetime.today()
    weekday = today.weekday()
    current_time_string = "{}{}".format(today.hour, today.minute)
    # If already closed, return next day's opening time
    if open_hours[weekday]["end"] < current_time_string:
        opening_time_string = open_hours[(weekday+1) % 7]["start"]
    else:
        opening_time_string = open_hours[weekday]["start"]
    return opening_time_string[:2], opening_time_string[2:]
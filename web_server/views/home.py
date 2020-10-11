from flask import Blueprint, request, render_template, redirect, url_for, send_from_directory, session, flash
from markupsafe import Markup
import feeder_api.db_helper as db
import datetime as dt
import json
from . import utils

home_blueprint =  Blueprint('home_blueprint', __name__)

@home_blueprint.route("/home", methods=["GET", "POST"])
def home():
    """
    Renders the Pet Feeder portal page for the user that displays the graphs
    of the food consumed by each pet feeder the user owns, and options to change
    the schedules of the Pet Feeders or drop food immediately.
    """
    if not utils.is_logged_in(session):
        return redirect(url_for("index"))

    user_info = db.getUserByUsername(session.get("username", ""))

    feeder_data = {
        str(user_feeder.get("feederId", "")) : {"name" : user_feeder.get("name", "")}
                    for user_feeder in user_info.get("feeders", [])}

    feeders = db.getFeedersById(list(feeder_data.keys()))

    # Parses the data about the feeder such as the STATUS of the feeder (can it
    # still drop food) and the consumed amount of food.
    for feeder in feeders:
        feeder_id = str(feeder.get("_id", ""))
        feeder_data[feeder_id]["status"] = feeder.get("status", "FAIL")
        feeder_eating_data = db.getOngoingConsumptionLogs(feeder_id)
        feeder_data[feeder_id]["data"] = [
            {
                "x" : data.get("hour", dt.datetime.now()).strftime("%Y-%m-%d %H:00"),
                "y" : data.get("foodEaten", 0)
            }
            for data in feeder_eating_data
        ]

        if feeder_data[feeder_id]["status"] == "OK":
            feeder_data[feeder_id]["status"] = "{name} is functioning normally!".format(name = feeder_data[feeder_id]["name"])
        else:
            feeder_data[feeder_id]["status"] = "{name} was unable to drop food!".format(name = feeder_data[feeder_id]["name"])

    # Renders the home page for the user.
    return render_template("home.html",
                            username = utils.get_username(session),
                            feeders = feeder_data)

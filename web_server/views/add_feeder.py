from flask import Blueprint, request, render_template, redirect, url_for, send_from_directory, session, flash
import feeder_api.db_helper as db
from . import utils

add_feeder_blueprint = Blueprint('add_feeder_blueprint', __name__)

@add_feeder_blueprint.route("/add_feeder", methods=["GET", "POST"])
def add_feeder():
    """
    App Logic for users to associate a new Pet Feeder to their account.

    Users send the product key, authentication key of the pet feeder they want
    to add to their account and a name to call the pet feeder.

    Description and Notify on Success/Failure is a currently unfunctional
    options that would be implemented at a later point.
    """
    if not utils.is_logged_in(session):
        return redirect(url_for("index"))

    if request.method == "POST":
        petfeeder_key = request.form.get("key", None)
        petfeeder_password = request.form.get("password", None)
        petfeeder_name = request.form.get("name", None)
        petfeeder_desc =  request.form.get("desc", None)
        petfeeder_notify_success = "success" in request.form
        petfeeder_notify_failure = "failure" in request.form

        if not petfeeder_key or not petfeeder_password or not petfeeder_name or not petfeeder_desc:
            return redirect(url_for("add_feeder_blueprint.add_feeder"))

        petfeeder_info = db.getFeederByProductKey(petfeeder_key)
        if not petfeeder_info:
            return redirect(url_for("add_feeder_blueprint.add_feeder"))

        if not db.verifyFeeder(petfeeder_info["_id"], petfeeder_password):
            return redirect(url_for("add_feeder_blueprint.add_feeder"))

        user_info = db.getUserByUsername(session.get("username", None))

        if not user_info:
            return redirect(url_for("add_feeder_blueprint.add_feeder"))

        db.addUserFeeder(user_info["_id"],
                            petfeeder_key,
                            name = petfeeder_name,
                            notifySuccess = petfeeder_notify_success,
                            notifyFailure = petfeeder_notify_failure
                            )
        return redirect(url_for("home_blueprint.home"))


    return render_template("add_feeder.html")

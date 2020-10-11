from flask import Blueprint, request, render_template, redirect, url_for, send_from_directory, session, flash, abort
import feeder_api.db_helper as db
from . import utils

admin_blueprint = Blueprint("admin_blueprint", __name__)

def create_feeder(post_data):
    """
    Creates a new Pet Feeder with the product key and authentication key
    given in the POST request.
    """
    address = "deprecated"
    product_key = post_data.get("key", None)
    product_pass = post_data.get("password", None)

    if not product_key or not product_pass:
        return redirect(url_for("admin_blueprint.admin"))

    db.insertFeeder(address, product_key, product_pass)
    return redirect(url_for("home_blueprint.home"))


@admin_blueprint.route("/admin", methods=["GET", "POST"])
def admin():
    """
    Top Secret page for creating new pet feeders.
    """
    if not utils.is_logged_in(session) and not session.get("role", "Users") == "Admin":
        abort(404)

    if request.method == "POST":
        return create_feeder(request.form)

    return render_template("admin.html")

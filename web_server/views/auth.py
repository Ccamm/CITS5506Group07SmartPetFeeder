from flask import Blueprint, request, render_template, redirect, url_for, send_from_directory, session, flash
import feeder_api.db_helper as db
from . import utils

auth_blueprint = Blueprint('auth_blueprint', __name__)

@auth_blueprint.route("/login", methods=["GET", "POST"])
def login():
    """
    Login logic for the user when they want to login to the website and access
    their pet feeder portal.
    """
    if utils.is_logged_in(session):
        return redirect(url_for("home_blueprint.home"))

    if request.method == "POST":
        username = request.form.get("username", None)
        password = request.form.get("password", None)

        if not username or not password:
            return redirect(url_for("auth_blueprint.login"))

        if db.verifyUser(username, password):
            user = db.getUserByUsername(username)
            session['logged_in'] = True
            session['username'] = username
            session['role'] = user.get("name", "User")

            # If the user has no pet feeders it will redirect to the pet feeder
            # registration page so the user can add a pet feeder.
            if len(user.get("feeders", [])) == 0:
                return redirect(url_for("add_feeder_blueprint.add_feeder"))

            return redirect(url_for("home_blueprint.home"))
    return render_template("login.html")

@auth_blueprint.route("/logout")
def logout():
    """
    Logs the user out from their account
    """
    session["logged_in"] = False
    session["username"] = None
    session["role"] = None
    return redirect(url_for("index"))

@auth_blueprint.route("/register", methods=["GET", "POST"])
def register():
    """
    Renders the user registration form when a user wants to signup to the website.
    """
    if utils.is_logged_in(session):
        return redirect(url_for("home_blueprint.home"))

    if request.method == "POST":
        username = request.form.get("username", None)
        email = request.form.get("email", None)
        password = request.form.get("password", None)

        if not username or not email or not password:
            return redirect(url_for("auth_blueprint.register"))

        if not db.insertNewUser(username, email, password):
            return redirect(url_for("auth_blueprint.register"))

        return redirect(url_for("auth_blueprint.login"))
    return render_template("register.html")

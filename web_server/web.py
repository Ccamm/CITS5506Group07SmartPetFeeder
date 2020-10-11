from flask import Flask, request, render_template, redirect, url_for, send_from_directory, session
from views.auth import auth_blueprint
from views.home import home_blueprint
from views.add_feeder import add_feeder_blueprint
from views.admin import admin_blueprint
from views.schedule_manager import schedule_blueprint
import os

"""
Registers the blueprints for the website endpoint resources and routes for
the index page and assets.
"""

app =  Flask(__name__, static_url_path='')

app.register_blueprint(auth_blueprint)
app.register_blueprint(home_blueprint)
app.register_blueprint(add_feeder_blueprint)
app.register_blueprint(admin_blueprint)
app.register_blueprint(schedule_blueprint)

app.secret_key = os.urandom(12)

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/assets/<path:path>')
def send_assets(path):
    return send_from_directory("assets", path)

@app.route('/images/<path:path>')
def send_images(path):
    return send_from_directory("images", path)

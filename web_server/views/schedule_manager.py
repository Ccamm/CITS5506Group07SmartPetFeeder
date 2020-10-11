from flask import Blueprint, request, render_template, redirect, url_for, send_from_directory, session, flash
import feeder_api.db_helper as db
import datetime as dt
from . import utils

schedule_blueprint = Blueprint("schedule_blueprint", __name__)

INDEX_TO_DAY = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
]

def check_user_owns_feeder(user_info, feeder_id):
    """
    Checks the user actually owns the feeder that they are trying to change the
    schedule for.

    Parameters:
        user_info:
            the dictionary containing the user's information from the database.
        feeder_id:
            the id of the feeder to add the schedule too.
    """
    for feeder in user_info.get("feeders", []):
        if str(feeder.get("feederId", "")) == feeder_id:
            return feeder
    return None

def create_daily_schedule(feeder_id, time_str):
    """
    Creates a daily schedule for the PetFeeder at the specified time.

    Parameters:
        feeder_id:
            the database id of the feeder to add the daily schedule to.
        time_str:
            the time to drop the food formatted as a string.
    """
    try:
        schedule_time = dt.datetime.strptime(time_str, "%H:%M")
    except:
        return None

    db.addScheduleItem(feeder_id,
                        scheduleType="R",
                        time=schedule_time,
                        every=1,
                        unit="days")

def create_weekly_schedule(feeder_id, time_str, day):
    """
    Creates a weekly schedule on the given day for the PetFeeder to drop at the
    specified time.

    Parameters:
        feeder_id:
            the database id of the feeder to add the daily schedule to.
        time_str:
            the time to drop the food formatted as a string.
        day:
            the index of the day of the week that the food should be dropped
            (see INDEX_TO_DAY in this code).
    """
    try:
        schedule_time = dt.datetime.strptime(time_str, "%H:%M")
    except Exception as e:
        print(e)
        return None
    db.addScheduleItem(feeder_id,
                        scheduleType="W",
                        time=schedule_time,
                        days=[day])

def add_weekly_schedules(feeder_id, post_form):
    """
    Parses the POST request for any weekly schedules that the user wants to add
    for the pet feeder.

    Parameters:
        feeder_id:
            the id of the pet feeder to add the weekly schedules to.
        post_form:
            the POST request form as a dictionary
    """
    refresh_page = False
    if len(post_form.get("time_monday", "")) != 0:
        time_str = post_form.get("time_monday", "")
        create_weekly_schedule(feeder_id, time_str, 0)
        refresh_page = True

    if len(post_form.get("time_tuesday", "")) != 0:
        time_str = post_form.get("time_tuesday", "")
        create_weekly_schedule(feeder_id, time_str, 1)
        refresh_page = True

    if len(post_form.get("time_wednesday", "")) != 0:
        time_str = post_form.get("time_wednesday", "")
        create_weekly_schedule(feeder_id, time_str, 2)
        refresh_page = True

    if len(post_form.get("time_thursday", "")) != 0:
        time_str = post_form.get("time_thursday", "")
        create_weekly_schedule(feeder_id, time_str, 3)
        refresh_page = True

    if len(post_form.get("time_friday", "")) != 0:
        time_str = post_form.get("time_friday", "")
        create_weekly_schedule(feeder_id, time_str, 4)
        refresh_page = True

    if len(post_form.get("time_saturday", "")) != 0:
        time_str = post_form.get("time_saturday", "")
        create_weekly_schedule(feeder_id, time_str, 5)
        refresh_page = True

    if len(post_form.get("time_sunday", "")) != 0:
        time_str = post_form.get("time_monday", "")
        create_weekly_schedule(feeder_id, time_str, 6)
        refresh_page = True

    return refresh_page

@schedule_blueprint.route("/schedule", methods=["GET", "POST"])
def schedule():
    """
    Renders the schedule page for adding new schedules and listing all
    pre-existing schedules for the pet feeder that the user can remove.
    """

    # Checks the user is logged in
    if not utils.is_logged_in(session):
        return redirect(url_for("index"))

    # Gets the URL argument for the feeder_id
    feeder_id = request.args.get("id", None)
    if not feeder_id:
        # Could not get the feeder id, someone has been naughty if they goof this.
        return redirect(url_for("home_blueprint.home"))

    user_info = db.getUserByUsername(utils.get_username(session))
    feeder_info = check_user_owns_feeder(user_info, feeder_id)

    if not feeder_info:
        # Someone is being naughty trying to access a feeder they do not own
        return redirect(url_for("home_blueprint.home"))

    feeder_db_info = db.getFeeder(feeder_id)

    daily_schedules = []
    weekly_schedules = []

    # Parses all of the pre-existing schedules for the pet feeder
    for sched in feeder_db_info.get("feedSchedule"):
        if sched.get("type", '') == "R":
            try:
                daily_schedules.append({
                    "time" : sched.get("time").strftime("%H:%M")
                })
            except:
                pass
        elif sched.get("type", '') == "W":
            try:
                weekly_schedules.append({
                    "time" : sched.get("time").strftime("%H:%M"),
                    "day"  : INDEX_TO_DAY[sched.get("days")[0]]
                })
            except:
                pass

    # Adds the new schedules for the pet feeder, daily and weekly
    if request.method == "POST":
        if len(request.form.get("time_daily", "")) != 0:
            create_daily_schedule(feeder_id, request.form.get("time_daily", ""))
            return redirect(url_for("schedule_blueprint.schedule", id=feeder_id))

        if add_weekly_schedules(feeder_id, request.form):
            return redirect(url_for("schedule_blueprint.schedule", id=feeder_id))

    # Renders the schedule page
    return render_template("schedule.html",
                            feeder_name = feeder_info["name"],
                            daily_schedules = daily_schedules,
                            weekly_schedules = weekly_schedules)

def delete_daily_schedule(feeder_id, time):
    """
    Deletes the daily schedule for the pet feeder at the given time

    Parameters:
        feeder_id:
            the id of the pet feeder
        time:
            the time of the daily schedule to remove
    """
    db.deleteScheduleItem(
        feeder_id,
        type = "R",
        time = time
    )

def delete_weekly_schedule(feeder_id, day, time):
    """
    Deletes the weeklyschedule for the pet feeder at the given time

    Parameters:
        feeder_id:
            the id of the pet feeder
        time:
            the time of the daily schedule to remove
        day:
            the index of the day of week (see INDEX_TO_DAY)
    """
    day_index = INDEX_TO_DAY.index(day)

    db.deleteScheduleItem(
        feeder_id,
        type = "W",
        time = time,
        days = [day_index]
    )

@schedule_blueprint.route("/delete_schedule")
def delete_schedule():
    """
    The endpoint resource for deleting a schedule for a feeder.
    """
    if not utils.is_logged_in(session):
        return redirect(url_for("index"))

    # Gets the feeder_id from the URL
    feeder_id = request.args.get("id", None)
    if not feeder_id:
        return redirect(url_for("home_blueprint.home"))

    user_info = db.getUserByUsername(utils.get_username(session))
    feeder_info = check_user_owns_feeder(user_info, feeder_id)

    if not feeder_info:
        return redirect(url_for("home_blueprint.home"))

    # Gets the schedule type and time of the delete request from the URL
    sched_type = request.args.get("type", None)
    sched_time_str = request.args.get("time", None)

    if not sched_type or not sched_time_str:
        return redirect(url_for("schedule_blueprint.schedule", id=feeder_id))

    try:
        sched_time = dt.datetime.strptime(sched_time_str, "%H:%M")
    except:
        return redirect(url_for("schedule_blueprint.schedule", id=feeder_id))

    if sched_type == "R":
        delete_daily_schedule(feeder_id, sched_time)
    elif sched_type == "W":
        sched_day = request.args.get("day", "")
        delete_weekly_schedule(feeder_id, sched_day, sched_time)

    return redirect(url_for("schedule_blueprint.schedule", id=feeder_id))


@schedule_blueprint.route("/drop")
def drop():
    """
    Schedules an immediate drop of food for the pet feeder.
    """
    if not utils.is_logged_in(session):
        return redirect(url_for("index"))

    # The feeder id from the URL
    feeder_id = request.args.get("id", None)
    if not feeder_id:
        return redirect(url_for("home_blueprint.home"))

    user_info = db.getUserByUsername(utils.get_username(session))
    feeder_info = check_user_owns_feeder(user_info, feeder_id)

    if not feeder_info:
        return redirect(url_for("home_blueprint.home"))

    drop_offset = dt.timezone(dt.timedelta(hours=8))
    drop_time = dt.datetime.now(drop_offset)

    db.addScheduleItem(feeder_id, scheduleType="S", time=drop_time)
    return redirect(url_for("home_blueprint.home", id=feeder_id))

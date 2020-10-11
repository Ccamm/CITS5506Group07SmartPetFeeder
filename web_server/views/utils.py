def is_logged_in(session):
    """
    Checks the user is logged in.

    Parameters:
        session:
            the session cookie from the user
    """
    return session.get("logged_in", False)

def get_username(session):
    """
    Gets the username from the session cookie.

    Parameters:
        session:
            the session cookie from the user
    """
    return session.get("username", None)

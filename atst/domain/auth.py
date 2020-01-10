from flask import g, redirect, url_for, session, request, current_app as app

from atst.domain.users import Users


UNPROTECTED_ROUTES = [
    "atst.root",
    "dev.login_dev",
    "dev.dev_new_user",
    "atst.login_redirect",
    "atst.logout",
    "atst.unauthorized",
    "atst.helpdocs",
    "static",
    "atst.about",
]


def apply_authentication(app):
    @app.before_request
    # pylint: disable=unused-variable
    def enforce_login():
        user = get_current_user()
        if user:
            g.current_user = user
            g.last_login = get_last_login()

            if should_redirect_to_user_profile(request, user):
                return redirect(url_for("users.user", next=request.path))
        elif not _unprotected_route(request):
            return redirect(url_for("atst.root", next=request.path))


def should_redirect_to_user_profile(request, user):
    has_complete_profile = user.profile_complete
    is_unprotected_route = _unprotected_route(request)
    is_requesting_user_endpoint = request.endpoint in [
        "users.user",
        "users.update_user",
    ]

    if has_complete_profile or is_unprotected_route or is_requesting_user_endpoint:
        return False

    return True


def get_current_user():
    user_id = session.get("user_id")
    if user_id:
        return Users.get(user_id)
    else:
        return False


def get_last_login():
    return session.get("user_id") and session.get("last_login")


def logout():
    if session.get("user_id"):  # pragma: no branch
        dod_id = g.current_user.dod_id
        del session["user_id"]
        del session["last_login"]
        app.logger.info(f"user with EDIPI {dod_id} has logged out")


def _unprotected_route(request):
    if request.endpoint in UNPROTECTED_ROUTES:
        return True

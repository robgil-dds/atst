import urllib.parse as url
from flask import (
    Blueprint,
    render_template,
    g,
    redirect,
    session,
    url_for,
    request,
    make_response,
    current_app as app,
)

from jinja2.exceptions import TemplateNotFound
import pendulum
import os
from werkzeug.exceptions import NotFound

from atst.domain.users import Users
from atst.domain.authnid import AuthenticationContext
from atst.domain.auth import logout as _logout
from atst.domain.exceptions import UnauthenticatedError
from atst.utils.flash import formatted_flash as flash


bp = Blueprint("atst", __name__)


@bp.route("/")
def root():
    if g.current_user:
        return redirect(url_for(".home"))

    redirect_url = app.config.get("CAC_URL")
    if request.args.get("next"):
        redirect_url = url.urljoin(
            redirect_url,
            "?{}".format(url.urlencode({"next": request.args.get("next")})),
        )
        flash("login_next")

    return render_template("login.html", redirect_url=redirect_url)


@bp.route("/home")
def home():
    return render_template("home.html")


@bp.route("/<path:path>")
def catch_all(path):
    try:
        return render_template("{}.html".format(path))
    except TemplateNotFound:
        raise NotFound()


def _client_s_dn():
    return request.environ.get("HTTP_X_SSL_CLIENT_S_DN")


def _make_authentication_context():
    return AuthenticationContext(
        crl_cache=app.crl_cache,
        auth_status=request.environ.get("HTTP_X_SSL_CLIENT_VERIFY"),
        sdn=_client_s_dn(),
        cert=request.environ.get("HTTP_X_SSL_CLIENT_CERT"),
    )


def redirect_after_login_url():
    if request.args.get("next"):
        returl = request.args.get("next")
        if request.args.get(app.form_cache.PARAM_NAME):
            returl += "?" + url.urlencode(
                {app.form_cache.PARAM_NAME: request.args.get(app.form_cache.PARAM_NAME)}
            )
        return returl
    else:
        return url_for("atst.home")


def current_user_setup(user):
    session["user_id"] = user.id
    session["last_login"] = user.last_login
    app.session_limiter.on_login(user)
    app.logger.info(f"authentication succeeded for user with EDIPI {user.dod_id}")
    Users.update_last_login(user)


@bp.route("/login-redirect")
def login_redirect():
    try:
        auth_context = _make_authentication_context()
        auth_context.authenticate()

        user = auth_context.get_user()
        current_user_setup(user)
    except UnauthenticatedError as err:
        app.logger.info(
            f"authentication failed for subject distinguished name {_client_s_dn()}"
        )
        raise err

    return redirect(redirect_after_login_url())


@bp.route("/logout")
def logout():
    _logout()
    response = make_response(redirect(url_for(".root")))
    response.set_cookie("expandSidenav", "", expires=0)
    flash("logged_out")
    return response


@bp.route("/about")
def about():
    return render_template("about.html")


@bp.route("/csp-environment-access")
def csp_environment_access():
    return render_template("mock_csp.html", text="console for this environment")


@bp.route("/jedi-csp-calculator")
def jedi_csp_calculator():
    return redirect(app.csp.cloud.get_calculator_url())

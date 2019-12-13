from flask import redirect, render_template, request as http_request, url_for, g

from .blueprint import applications_bp
from atst.domain.applications import Applications
from atst.domain.exceptions import AlreadyExistsError
from atst.domain.portfolios import Portfolios
from atst.forms.application import NameAndDescriptionForm, EnvironmentsForm
from atst.domain.authz.decorator import user_can_access_decorator as user_can
from atst.models.permissions import Permissions
from atst.utils.flash import formatted_flash as flash
from atst.routes.applications.settings import (
    get_members_data,
    get_new_member_form,
    handle_create_member,
    handle_update_member,
)


def get_new_application_form(form_data, form_class, application_id=None):
    if application_id:
        application = Applications.get(application_id)
        return form_class(form_data, obj=application)
    else:
        return form_class(form_data)


def render_new_application_form(
    template, form_class, portfolio_id=None, application_id=None, form=None
):
    render_args = {"application_id": application_id}
    if application_id:
        application = Applications.get(application_id)
        render_args["form"] = form or form_class(obj=application)
        render_args["application"] = application
    else:
        render_args["form"] = form or form_class()

    return render_template(template, **render_args)


def update_application(form, application_id=None, portfolio_id=None):
    if form.validate():
        application = None
        try:
            if application_id:
                application = Applications.get(application_id)
                application = Applications.update(application, form.data)
                flash("application_updated", application_name=application.name)
            else:
                portfolio = Portfolios.get_for_update(portfolio_id)
                application = Applications.create(
                    g.current_user, portfolio, **form.data
                )
                flash("application_created", application_name=application.name)

            return application

        except AlreadyExistsError:
            flash("application_name_error", name=form.data["name"])
            return False

    else:
        return False


@applications_bp.route("/portfolios/<portfolio_id>/applications/new")
@applications_bp.route("/applications/<application_id>/new/step_1")
@user_can(Permissions.CREATE_APPLICATION, message="view create new application form")
def view_new_application_step_1(portfolio_id=None, application_id=None):
    return render_new_application_form(
        "applications/new/step_1.html",
        NameAndDescriptionForm,
        portfolio_id=portfolio_id,
        application_id=application_id,
    )


@applications_bp.route(
    "/portfolios/<portfolio_id>/applications/new",
    endpoint="create_new_application_step_1",
    methods=["POST"],
)
@applications_bp.route(
    "/applications/<application_id>/new/step_1",
    endpoint="update_new_application_step_1",
    methods=["POST"],
)
@user_can(Permissions.CREATE_APPLICATION, message="view create new application form")
def create_or_update_new_application_step_1(portfolio_id=None, application_id=None):
    form = get_new_application_form(
        {**http_request.form}, NameAndDescriptionForm, application_id
    )
    application = update_application(form, application_id, portfolio_id)

    if application:
        return redirect(
            url_for(
                "applications.update_new_application_step_2",
                application_id=application.id,
            )
        )
    else:
        return (
            render_new_application_form(
                "applications/new/step_1.html",
                NameAndDescriptionForm,
                portfolio_id,
                application_id,
                form,
            ),
            400,
        )


@applications_bp.route("/applications/<application_id>/new/step_2")
@user_can(Permissions.CREATE_APPLICATION, message="view create new application form")
def view_new_application_step_2(application_id):
    application = Applications.get(application_id)
    render_args = {
        "form": EnvironmentsForm(
            data={
                "environment_names": [
                    environment.name for environment in application.environments
                ]
            }
        ),
        "application": application,
    }

    return render_template("applications/new/step_2.html", **render_args)


@applications_bp.route("/applications/<application_id>/new/step_2", methods=["POST"])
@user_can(Permissions.CREATE_APPLICATION, message="view create new application form")
def update_new_application_step_2(application_id):
    form = get_new_application_form(
        {**http_request.form}, EnvironmentsForm, application_id
    )
    if form.validate():
        application = Applications.get(application_id)
        application = Applications.update(application, form.data)
        flash("application_environments_updated")
        return redirect(
            url_for(
                "applications.update_new_application_step_3",
                application_id=application_id,
            )
        )
    else:
        return (
            render_new_application_form(
                "applications/new/step_2.html",
                EnvironmentsForm,
                application_id=application_id,
                form=form,
            ),
            400,
        )


@applications_bp.route("/applications/<application_id>/new/step_3")
@user_can(Permissions.CREATE_APPLICATION, message="view create new application form")
def view_new_application_step_3(application_id):
    application = Applications.get(application_id)
    members = get_members_data(application)
    new_member_form = get_new_member_form(application)

    return render_template(
        "applications/new/step_3.html",
        application_id=application_id,
        application=application,
        members=members,
        new_member_form=new_member_form,
    )


@applications_bp.route("/applications/<application_id>/new/step_3", methods=["POST"])
@applications_bp.route(
    "/applications/<application_id>/new/step_3/member/<application_role_id>",
    methods=["POST"],
)
@user_can(Permissions.CREATE_APPLICATION, message="view create new application form")
def update_new_application_step_3(application_id, application_role_id=None):
    if application_role_id:
        handle_update_member(application_id, application_role_id, http_request.form)
    else:
        handle_create_member(application_id, http_request.form)

    return redirect(
        url_for(
            "applications.view_new_application_step_3", application_id=application_id
        )
    )

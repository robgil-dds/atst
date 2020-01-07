from flask import flash
from atst.utils.localization import translate


MESSAGES = {
    "application_created": {
        "title": "flash.application.created.title",
        "message": "flash.application.created.message",
        "category": "success",
    },
    "application_updated": {
        "title": "flash.success",
        "message": "flash.application.updated",
        "category": "success",
    },
    "application_environments_name_error": {
        "title": None,
        "message": "flash.application.env_name_error.message",
        "category": "error",
    },
    "application_environments_updated": {
        "title": "flash.environment.updated.title",
        "message": "flash.environment.updated.message",
        "category": "success",
    },
    "application_invite_error": {
        "title": "flash.application_invite.error.title",
        "message": "flash.application_invite.error.message",
        "category": "error",
    },
    "application_invite_resent": {
        "title": "flash.application_invite.resent.title",
        "message": "flash.application_invite.resent.message",
        "category": "success",
    },
    "application_invite_revoked": {
        "title": "flash.application_invite.revoked.title",
        "message": "flash.application_invite.revoked.message",
        "category": "success",
    },
    "application_member_removed": {
        "title": "flash.application_member.removed.title",
        "message": "flash.application_member.removed.message",
        "category": "success",
    },
    "application_member_update_error": {
        "title": "flash.application_member.update_error.title",
        "message": "flash.application_member.update_error.message",
        "category": "error",
    },
    "application_member_updated": {
        "title": "flash.application_member.updated.title",
        "message": "flash.application_member.updated.message",
        "category": "success",
    },
    "application_name_error": {
        "title": None,
        "message": "flash.application.name_error.message",
        "category": "error",
    },
    "ccpo_user_added": {
        "title": "flash.success",
        "message": "flash.ccpo_user.added.message",
        "category": "success",
    },
    "ccpo_user_not_found": {
        "title": "ccpo.form.user_not_found_title",
        "message": "ccpo.form.user_not_found_text",
        "category": "info",
    },
    "ccpo_user_removed": {
        "title": "flash.success",
        "message": "flash.ccpo_user.removed.message",
        "category": "success",
    },
    "environment_added": {
        "title": "flash.success",
        "message": "flash.environment_added",
        "category": "success",
    },
    "environment_deleted": {
        "title": "flash.environment.deleted.title",
        "message": "flash.environment.deleted.message",
        "category": "success",
    },
    "form_errors": {
        "title": "flash.form.errors.title",
        "message": "flash.form.errors.message",
        "category": "error",
    },
    "insufficient_funds": {
        "title": "flash.task_order.insufficient_funds.title",
        "message": "",
        "category": "warning",
    },
    "logged_out": {
        "title": "flash.logged_out.title",
        "message": "flash.logged_out.message",
        "category": "info",
    },
    "login_next": {
        "title": "flash.login_required_title",
        "message": "flash.login_required_message",
        "category": "warning",
    },
    "new_application_member": {
        "title": "flash.new_application_member.title",
        "message": "flash.new_application_member.message",
        "category": "success",
    },
    "new_portfolio_member": {
        "title": "flash.success",
        "message": "flash.new_portfolio_member",
        "category": "success",
    },
    "portfolio_member_removed": {
        "title": "flash.deleted_member",
        "message": "flash.delete_member_success",
        "category": "success",
    },
    "primary_point_of_contact_changed": {
        "title": "flash.new_ppoc_title",
        "message": "flash.new_ppoc_message",
        "category": "success",
    },
    "resend_portfolio_invitation": {
        "title": "flash.portfolio_invite.resent.title",
        "message": "flash.portfolio_invite.resent.message",
        "category": "success",
    },
    "resend_portfolio_invitation_error": {
        "title_template": "Portfolio invitation error",
        "message_template": "There was an error processing the invitation for {{ user_name }}.",
        "category": "error",
    },
    "revoked_portfolio_access": {
        "title": "flash.portfolio_member.revoked.title",
        "message": "flash.portfolio_member.revoked.message",
        "category": "success",
    },
    "session_expired": {
        "title": "flash.session_expired.title",
        "message": "flash.session_expired.message",
        "category": "error",
    },
    "task_order_draft": {
        "title": "task_orders.form.draft_alert_title",
        "message": "task_orders.form.draft_alert_message",
        "category": "warning",
    },
    "task_order_number_error": {
        "title": None,
        "message": "flash.task_order_number_error.message",
        "category": "error",
    },
    "task_order_submitted": {
        "title": "flash.task_order.submitted.title",
        "message": "flash.task_order.submitted.message",
        "category": "success",
    },
    "update_portfolio_member": {
        "title_template": "Success!",
        "message_template": """
        You have successfully updated access permissions for {{ member_name }}.
        """,
        "category": "success",
    },
    "update_portfolio_member_error": {
        "title_template": "Permissions for {{ member_name }} could not be updated",
        "message_template": "An unexpected problem occurred with your request, please try again. If the problem persists, contact an administrator.",
        "category": "error",
    },
    "updated_application_team_settings": {
        "title": "flash.success",
        "message": "flash.updated_application_team_settings",
        "category": "success",
    },
    "user_must_complete_profile": {
        "title": "flash.user.complete_profile.title",
        "message": "flash.user.complete_profile.message",
        "category": "info",
    },
    "user_updated": {
        "title": "flash.user.updated.title",
        "message": None,
        "category": "success",
    },
}


def formatted_flash(message_name, **message_args):
    config = MESSAGES[message_name]

    title = translate(config["title"], message_args) if config["title"] else None
    message = translate(config["message"], message_args) if config["message"] else None
    actions = (
        translate(config["actions"], message_args) if config.get("actions") else None
    )

    flash({"title": title, "message": message, "actions": actions}, config["category"])

from flask import flash, render_template_string
from atst.utils.localization import translate

MESSAGES = {
    "portfolio_deleted": {
        "title_template": "Portfolio has been deleted",
        "message_template": "Portfolio '{{portfolio_name}}' has been deleted",
        "category": "success",
    },
    "application_created": {
        "title_template": translate("flash.application.created.title"),
        "message_template": """
            {{ "flash.application.created.message" | translate({"application_name": application_name}) }}
        """,
        "category": "success",
    },
    "application_updated": {
        "title_template": translate("flash.success"),
        "message_template": """
            {{ "flash.application.updated" | translate({"application_name": application_name}) }}
        """,
        "category": "success",
    },
    "application_deleted": {
        "title_template": translate("flash.success"),
        "message_template": """
            {{ "flash.application.deleted" | translate({"application_name": application_name}) }}
            <a href="#">{{ "common.undo" | translate }}</a>
        """,
        "category": "success",
    },
    "application_environments_updated": {
        "title_template": "Application environments updated",
        "message_template": "Application environments have been updated",
        "category": "success",
    },
    "application_invite_error": {
        "title_template": "Application invitation error",
        "message_template": "There was an error processing the invitation for {{ user_name }} from {{ application_name }}",
        "category": "error",
    },
    "application_invite_resent": {
        "title_template": "Application invitation resent",
        "message_template": "You have successfully resent the invite for {{ user_name }} from {{ application_name }}",
        "category": "success",
    },
    "application_invite_revoked": {
        "title_template": "Application invitation revoked",
        "message_template": "You have successfully revoked the invite for {{ user_name }} from {{ application_name }}",
        "category": "success",
    },
    "application_member_removed": {
        "title_template": "Team member removed from application",
        "message_template": "You have successfully deleted {{ user_name }} from {{ application_name }}",
        "category": "success",
    },
    "application_member_update_error": {
        "title_template": "{{ user_name }} could not be updated",
        "message_template": "An unexpected problem occurred with your request, please try again. If the problem persists, contact an administrator.",
        "category": "error",
    },
    "application_member_updated": {
        "title_template": "Team member updated",
        "message_template": "You have successfully updated the permissions for {{ user_name }}",
        "category": "success",
    },
    "application_name_error": {
        "title_template": "",
        "message_template": """{{ 'flash.application.name_error.message' | translate({ 'name': name }) }}""",
        "category": "error",
    },
    "ccpo_user_added": {
        "title_template": translate("flash.success"),
        "message_template": "You have successfully given {{ user_name }} CCPO permissions.",
        "category": "success",
    },
    "ccpo_user_not_found": {
        "title_template": translate("ccpo.form.user_not_found_title"),
        "message_template": translate("ccpo.form.user_not_found_text"),
        "category": "info",
    },
    "ccpo_user_removed": {
        "title_template": translate("flash.success"),
        "message_template": "You have successfully removed {{ user_name }}'s CCPO permissions.",
        "category": "success",
    },
    "environment_added": {
        "title_template": translate("flash.success"),
        "message_template": """
            {{ "flash.environment_added" | translate({ "env_name": environment_name }) }}
        """,
        "category": "success",
    },
    "environment_deleted": {
        "title_template": "{{ environment_name }} deleted",
        "message_template": 'The environment "{{ environment_name }}" has been deleted',
        "category": "success",
    },
    "form_errors": {
        "title_template": "There were some errors",
        "message_template": "<p>Please see below.</p>",
        "category": "error",
    },
    "insufficient_funds": {
        "title_template": "Insufficient Funds",
        "message_template": "",
        "category": "warning",
    },
    "logged_out": {
        "title_template": translate("flash.logged_out"),
        "message_template": """
            You've been logged out.
        """,
        "category": "info",
    },
    "login_next": {
        "title_template": translate("flash.login_required_title"),
        "message_template": translate("flash.login_required_message"),
        "category": "warning",
    },
    "new_application_member": {
        "title_template": """{{ "flash.new_application_member.title" | translate({ "user_name": user_name }) }}""",
        "message_template": """
          <p>{{ "flash.new_application_member.message" | translate({ "user_name": user_name }) }}</p>
        """,
        "category": "success",
    },
    "new_portfolio_member": {
        "title_template": translate("flash.success"),
        "message_template": """
          <p>{{ "flash.new_portfolio_member" | translate({ "user_name": user_name }) }}</p>
        """,
        "category": "success",
    },
    "portfolio_member_removed": {
        "title_template": translate("flash.deleted_member"),
        "message_template": """
            {{ "flash.delete_member_success" | translate({ "member_name": member_name }) }}
        """,
        "category": "success",
    },
    "primary_point_of_contact_changed": {
        "title_template": translate("flash.new_ppoc_title"),
        "message_template": """{{ "flash.new_ppoc_message" | translate({ "ppoc_name": ppoc_name }) }}""",
        "category": "success",
    },
    "resend_portfolio_invitation": {
        "title_template": "Invitation resent",
        "message_template": """
          <p>Successfully sent a new invitation to {{ user_name }}.</p>
        """,
        "category": "success",
    },
    "revoked_portfolio_access": {
        "title_template": "Removed portfolio access",
        "message_template": """
          <p>Portfolio access successfully removed from {{ member_name }}.</p>
        """,
        "category": "success",
    },
    "session_expired": {
        "title_template": "Session Expired",
        "message_template": """
            Your session expired due to inactivity. Please log in again to continue.
        """,
        "category": "error",
    },
    "task_order_draft": {
        "title_template": translate("task_orders.form.draft_alert_title"),
        "message_template": translate("task_orders.form.draft_alert_message"),
        "category": "warning",
    },
    "task_order_number_error": {
        "title_template": "",
        "message_template": """{{ 'flash.task_order_number_error.message' | translate({ 'to_number': to_number }) }}""",
        "category": "error",
    },
    "task_order_submitted": {
        "title_template": "Your Task Order has been uploaded successfully.",
        "message_template": """
        Your task order form for {{ task_order.portfolio_name }} has been submitted.
        """,
        "category": "success",
    },
    "update_portfolio_members": {
        "title_template": "Success!",
        "message_template": """
        <p>You have successfully updated access permissions for members of {{ portfolio.name }}.</p>
        """,
        "category": "success",
    },
    "updated_application_team_settings": {
        "title_template": translate("flash.success"),
        "message_template": """
          <p>{{ "flash.updated_application_team_settings" | translate({"application_name": application_name}) }}</p>
        """,
        "category": "success",
    },
    "user_must_complete_profile": {
        "title_template": "You must complete your profile",
        "message_template": "<p>Before continuing, you must complete your profile</p>",
        "category": "info",
    },
    "user_updated": {
        "title_template": "User information updated.",
        "message_template": "",
        "category": "success",
    },
}


def formatted_flash(message_name, **message_args):
    config = MESSAGES[message_name]
    title = render_template_string(config["title_template"], **message_args)
    message = render_template_string(config["message_template"], **message_args)
    actions = None
    if "actions" in config:
        actions = render_template_string(config["actions"], **message_args)
    flash({"title": title, "message": message, "actions": actions}, config["category"])

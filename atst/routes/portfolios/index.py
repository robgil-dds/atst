from datetime import datetime

from flask import redirect, render_template, url_for, request as http_request, g

from .blueprint import portfolios_bp
from atst.forms.portfolio import PortfolioCreationForm
from atst.domain.reports import Reports
from atst.domain.portfolios import Portfolios
from atst.models.permissions import Permissions
from atst.domain.authz.decorator import user_can_access_decorator as user_can
from atst.utils.flash import formatted_flash as flash


@portfolios_bp.route("/portfolios/new")
def new_portfolio_step_1():
    form = PortfolioCreationForm()
    return render_template("portfolios/new/step_1.html", form=form)


@portfolios_bp.route("/portfolios", methods=["POST"])
def create_portfolio():
    form = PortfolioCreationForm(http_request.form)

    if form.validate():
        portfolio = Portfolios.create(user=g.current_user, portfolio_attrs=form.data)
        return redirect(
            url_for("applications.portfolio_applications", portfolio_id=portfolio.id)
        )
    else:
        return render_template("portfolios/new/step_1.html", form=form), 400


@portfolios_bp.route("/portfolios/<portfolio_id>/reports")
@user_can(Permissions.VIEW_PORTFOLIO_REPORTS, message="view portfolio reports")
def reports(portfolio_id):
    portfolio = Portfolios.get(g.current_user, portfolio_id)

    current_obligated_funds = Reports.obligated_funds_by_JEDI_clin(portfolio)

    if any(map(lambda clin: clin["remaining"] < 0, current_obligated_funds)):
        flash("insufficient_funds")

    # wrapped in str() because the sum of obligated funds returns a Decimal object
    total_portfolio_value = str(
        sum(
            task_order.total_obligated_funds
            for task_order in portfolio.active_task_orders
        )
    )
    return render_template(
        "portfolios/reports/index.html",
        portfolio=portfolio,
        total_portfolio_value=total_portfolio_value,
        current_obligated_funds=current_obligated_funds,
        expired_task_orders=Reports.expired_task_orders(portfolio),
        monthly_spending=Reports.monthly_spending(portfolio),
        retrieved=datetime.now(),  # mocked datetime of reporting data retrival
    )

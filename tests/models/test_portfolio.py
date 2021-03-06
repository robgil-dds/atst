from tests.factories import (
    ApplicationFactory,
    PortfolioFactory,
    TaskOrderFactory,
    CLINFactory,
    random_future_date,
    random_past_date,
)
import datetime


def test_portfolio_applications_excludes_deleted():
    portfolio = PortfolioFactory.create()
    app = ApplicationFactory.create(portfolio=portfolio)
    ApplicationFactory.create(portfolio=portfolio, deleted=True)
    assert len(portfolio.applications) == 1
    assert portfolio.applications[0].id == app.id


def test_funding_duration(session):
    # portfolio with active task orders
    portfolio = PortfolioFactory()

    funding_start_date = random_past_date()
    funding_end_date = random_future_date(year_min=2)

    TaskOrderFactory.create(
        signed_at=random_past_date(),
        portfolio=portfolio,
        create_clins=[
            {
                "start_date": funding_start_date,
                "end_date": random_future_date(year_max=1),
            }
        ],
    )
    TaskOrderFactory.create(
        portfolio=portfolio,
        signed_at=random_past_date(),
        create_clins=[
            {"start_date": datetime.datetime.now(), "end_date": funding_end_date,}
        ],
    )

    assert portfolio.funding_duration == (funding_start_date, funding_end_date)

    # empty portfolio
    empty_portfolio = PortfolioFactory()
    assert empty_portfolio.funding_duration == (None, None)


def test_days_remaining(session):
    # portfolio with task orders
    funding_end_date = random_future_date(year_min=2)
    portfolio = PortfolioFactory()
    TaskOrderFactory.create(
        portfolio=portfolio,
        signed_at=random_past_date(),
        create_clins=[{"end_date": funding_end_date}],
    )

    assert (
        portfolio.days_to_funding_expiration
        == (funding_end_date - datetime.date.today()).days
    )

    # empty portfolio
    empty_portfolio = PortfolioFactory()
    assert empty_portfolio.days_to_funding_expiration == 0


def test_active_task_orders(session):
    portfolio = PortfolioFactory()
    TaskOrderFactory.create(
        portfolio=portfolio,
        signed_at=random_past_date(),
        create_clins=[
            {
                "start_date": datetime.date(2019, 1, 1),
                "end_date": datetime.date(2019, 10, 31),
            }
        ],
    )
    TaskOrderFactory.create(
        portfolio=portfolio, signed_at=random_past_date(), clins=[CLINFactory.create()]
    )
    assert len(portfolio.active_task_orders) == 1

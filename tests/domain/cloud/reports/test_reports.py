from atst.domain.csp.reports import MockReportingProvider
from tests.factories import PortfolioFactory


def test_get_environment_monthly_totals():
    environment = {
        "name": "Test Environment",
        "spending": {
            "this_month": {"JEDI_CLIN_1": 100, "JEDI_CLIN_2": 100},
            "last_month": {"JEDI_CLIN_1": 200, "JEDI_CLIN_2": 200},
            "total": {"JEDI_CLIN_1": 1000, "JEDI_CLIN_2": 1000},
        },
    }
    totals = MockReportingProvider._get_environment_monthly_totals(environment)
    assert totals == {
        "name": "Test Environment",
        "this_month": 200,
        "last_month": 400,
        "total": 2000,
    }


def test_get_application_monthly_totals():
    portfolio = PortfolioFactory.create(
        applications=[
            {"name": "Test Application", "environments": [{"name": "Z"}, {"name": "A"}]}
        ],
    )
    application = {
        "name": "Test Application",
        "environments": [
            {
                "name": "Z",
                "spending": {
                    "this_month": {"JEDI_CLIN_1": 50, "JEDI_CLIN_2": 50},
                    "last_month": {"JEDI_CLIN_1": 150, "JEDI_CLIN_2": 150},
                    "total": {"JEDI_CLIN_1": 250, "JEDI_CLIN_2": 250},
                },
            },
            {
                "name": "A",
                "spending": {
                    "this_month": {"JEDI_CLIN_1": 100, "JEDI_CLIN_2": 100},
                    "last_month": {"JEDI_CLIN_1": 200, "JEDI_CLIN_2": 200},
                    "total": {"JEDI_CLIN_1": 1000, "JEDI_CLIN_2": 1000},
                },
            },
        ],
    }

    totals = MockReportingProvider._get_application_monthly_totals(
        portfolio, application
    )
    assert totals["name"] == "Test Application"
    assert totals["this_month"] == 300
    assert totals["last_month"] == 700
    assert totals["total"] == 2500
    assert [env["name"] for env in totals["environments"]] == ["A", "Z"]

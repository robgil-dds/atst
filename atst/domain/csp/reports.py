from collections import defaultdict
import json
from decimal import Decimal


def load_fixture_data():
    with open("fixtures/fixture_spend_data.json") as json_file:
        return json.load(json_file)


class MockReportingProvider:
    FIXTURE_SPEND_DATA = load_fixture_data()

    @classmethod
    def get_portfolio_monthly_spending(cls, portfolio):
        """
        returns an array of application and environment spending for the 
        portfolio. Applications and their nested environments are sorted in
        alphabetical order by name.
        [
            {
                name
                this_month
                last_month
                total
                environments [
                    {
                        name
                        this_month
                        last_month
                        total
                    }
                ]
            }
        ]
        """

        fixture_apps = cls.FIXTURE_SPEND_DATA.get(portfolio.name, {}).get(
            "applications", []
        )

        for application in portfolio.applications:
            if application.name not in [app["name"] for app in fixture_apps]:
                fixture_apps.append({"name": application.name, "environments": []})

        return sorted(
            [
                cls._get_application_monthly_totals(portfolio, fixture_app)
                for fixture_app in fixture_apps
                if fixture_app["name"]
                in [application.name for application in portfolio.applications]
            ],
            key=lambda app: app["name"],
        )

    @classmethod
    def _get_environment_monthly_totals(cls, environment):
        """
        returns a dictionary that represents spending totals for an environment e.g. 
        {
            name
            this_month
            last_month
            total
        }
        """
        return {
            "name": environment["name"],
            "this_month": sum(environment["spending"]["this_month"].values()),
            "last_month": sum(environment["spending"]["last_month"].values()),
            "total": sum(environment["spending"]["total"].values()),
        }

    @classmethod
    def _get_application_monthly_totals(cls, portfolio, fixture_app):
        """
        returns a dictionary that represents spending totals for an application 
        and its environments e.g. 
            {
                name
                this_month
                last_month
                total
                environments: [
                    {
                        name
                        this_month
                        last_month
                        total
                    }
                ]
            }
        """
        application_envs = [
            env
            for env in portfolio.all_environments
            if env.application.name == fixture_app["name"]
        ]

        environments = [
            cls._get_environment_monthly_totals(env)
            for env in fixture_app["environments"]
            if env["name"] in [e.name for e in application_envs]
        ]

        for env in application_envs:
            if env.name not in [env["name"] for env in environments]:
                environments.append({"name": env.name})

        return {
            "name": fixture_app["name"],
            "this_month": sum(env.get("this_month", 0) for env in environments),
            "last_month": sum(env.get("last_month", 0) for env in environments),
            "total": sum(env.get("total", 0) for env in environments),
            "environments": sorted(environments, key=lambda env: env["name"]),
        }

    @classmethod
    def get_spending_by_JEDI_clin(cls, portfolio):
        """
        returns an dictionary of spending per JEDI CLIN for a portfolio
        {
            jedi_clin: {
                invoiced
                estimated
            },
        }
        """
        if portfolio.name in cls.FIXTURE_SPEND_DATA:
            CLIN_spend_dict = defaultdict(lambda: defaultdict(Decimal))
            for application in cls.FIXTURE_SPEND_DATA[portfolio.name]["applications"]:
                for environment in application["environments"]:
                    for clin, spend in environment["spending"]["this_month"].items():
                        CLIN_spend_dict[clin]["estimated"] += Decimal(spend)
                    for clin, spend in environment["spending"]["total"].items():
                        CLIN_spend_dict[clin]["invoiced"] += Decimal(spend)
            return CLIN_spend_dict
        return {}

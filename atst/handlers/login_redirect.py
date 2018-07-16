import tornado
from atst.handler import BaseHandler


class LoginRedirect(BaseHandler):
    def initialize(self, authnid_client, sessions, authz_client):
        self.authnid_client = authnid_client
        self.sessions = sessions
        self.authz_client = authz_client

    @tornado.gen.coroutine
    def get(self):
        token = self.get_query_argument("bearer-token")
        if token:
            user = yield self._fetch_user_info(token)
            if user:
                authz_user = yield self.create_authz_user(user["id"])
                user["atat_permissions"] = authz_user["atat_permissions"]
                self.login(user)
            else:
                self.write_error(401)

        url = self.get_login_url()
        self.redirect(url)

    @tornado.gen.coroutine
    def _fetch_user_info(self, token):
        try:
            response = yield self.authnid_client.post(
                "/validate", json={"token": token}
            )
            if response.code == 200:
                return response.json["user"]

        except tornado.httpclient.HTTPError as error:
            if error.response.code == 401:
                return None

            else:
                raise error

    @tornado.gen.coroutine
    def create_authz_user(self, user_id):
        response = yield self.authz_client.post(
            "/users", json={"id": user_id, "atat_role": "ccpo"}
        )
        return response.json

from requests_mock import CookieJar
POST_LOGIN = {
    "cookies": CookieJar()
}
POST_LOGIN["cookies"].set("xf_user", "test", path="/", secure=True, expires=0)
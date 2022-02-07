from flask_restplus import Resource, inputs, abort
from flask_httpauth import HTTPTokenAuth
from api import app, api, socket, cache, Flask_Session
from db import Post
from commons import get_env_var

tokens = {
    get_env_var("INTERNAL_API_KEY"): "scraper"
}

auth = HTTPTokenAuth(scheme="Bearer")
@auth.verify_token
def verify_token(token):
    if token in tokens: return tokens[token]


ns = api.namespace("internal")
# DB events could theoretically be handled via native sqlalchemy events, but it would overcomplicate things.
@ns.route("/post/created/<int:post_id>")
class PostCreated(Resource):
    @auth.login_required
    def post(self, post_id):
        session = Flask_Session()
        post = session.query(Post).filter_by(id=post_id).first()
        socket.emit("post_created", post.serialize(), broadcast=True)
        session.close()
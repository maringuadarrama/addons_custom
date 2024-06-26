import odoo
from odoo.http import SESSION_LIFETIME, Request, request, root


def _save_session(self):
    """Save a modified session on disk."""
    sess = self.session

    if not sess.can_save:
        return

    if sess.should_rotate:
        root.session_store.rotate(sess, self.env)  # it saves
    elif sess.is_dirty:
        root.session_store.save(sess)

    # We must not set the cookie if the session id was specified
    # using a http header or a GET parameter.
    # There are two reasons to this:
    # - When using one of those two means we consider that we are
    #   overriding the cookie, which means creating a new session on
    #   top of an already existing session and we don't want to
    #   create a mess with the 'normal' session (the one using the
    #   cookie). That is a special feature of the Javascript Session.
    # - It could allow session fixation attacks.
    cookie_sid = self.httprequest.cookies.get("session_id")
    if not sess.is_explicit and (sess.is_dirty or cookie_sid != sess.sid):
        max_age = SESSION_LIFETIME
        if sess.uid and sess.uid is not odoo.SUPERUSER_ID:
            user = request.env["res.users"].sudo().browse(sess.uid)
            max_age = user._get_session_expiration_time()
        self.future_response.set_cookie("session_id", sess.sid, max_age=max_age, httponly=True)


Request._save_session = _save_session

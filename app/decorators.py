from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def role_required(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('main.login_view'))
            if current_user.vai_tro not in roles:
                flash("Bạn không có quyền truy cập!", "danger")
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)

        return decorated_view

    return wrapper

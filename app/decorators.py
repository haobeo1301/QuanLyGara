from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def role_required(*roles):
    """Decorator kiểm tra quyền người dùng"""

    def wrapper(f):
        @wraps(f)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('main.login_view'))

            # Nếu user không nằm trong danh sách role cho phép
            if current_user.vai_tro not in roles:
                flash("Bạn không có quyền truy cập chức năng này!", "danger")
                return redirect(url_for('main.index'))

            return f(*args, **kwargs)

        return decorated_view

    return wrapper



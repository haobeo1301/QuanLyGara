from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, AnonymousUserMixin
from app.config import Config


# --- VÁ LỖI WTFORMS 3.x ---
def fix_wtforms_conflict():
    try:
        from wtforms.widgets import Select
        _original_call = Select.__call__

        def _patched_call(self, field, **kwargs):
            if hasattr(field, 'iter_choices'):
                original_iter = field.iter_choices

                def iter_choices_wrapper():
                    for item in original_iter():
                        if len(item) == 3:
                            yield (item[0], item[1], item[2], {})
                        else:
                            yield item

                field.iter_choices = iter_choices_wrapper
                try:
                    return _original_call(self, field, **kwargs)
                finally:
                    field.iter_choices = original_iter
            return _original_call(self, field, **kwargs)

        Select.__call__ = _patched_call
        print(">>> FIXED WTFORMS <<<")
    except:
        pass


fix_wtforms_conflict()

db = SQLAlchemy()
login = LoginManager()


# --- CLASS NGƯỜI DÙNG ẨN DANH (FIX LỖI UndefinedError) ---
class Anonymous(AnonymousUserMixin):
    def __init__(self):
        self.vai_tro = None  # Mặc định không có vai trò


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login.init_app(app)

    # Cấu hình Login
    login.login_view = 'main.login_view'
    login.login_message = "Vui lòng đăng nhập."
    login.anonymous_user = Anonymous  # Áp dụng class ẩn danh

    from app import admin
    admin.init_admin(app, db)

    from app.routes import main
    app.register_blueprint(main)

    return app
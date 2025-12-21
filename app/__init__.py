from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from app.config import Config


# --- BẮT ĐẦU VÁ LỖI WTFORMS 3.x VS FLASK-ADMIN ---
# Code này giúp Flask-Admin (cũ) chạy được với WTForms (mới)
def fix_wtforms_conflict():
    try:
        from wtforms.widgets import Select
        _original_call = Select.__call__

        def _patched_call(self, field, **kwargs):
            if hasattr(field, 'iter_choices'):
                original_iter = field.iter_choices

                def iter_choices_wrapper():
                    for item in original_iter():
                        # Nếu thiếu tham số thứ 4 thì chèn thêm dict rỗng
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
        print(">>> ĐÃ VÁ LỖI TƯƠNG THÍCH WTFORMS 3.x <<<")
    except ImportError:
        pass


# Gọi hàm vá ngay khi import
fix_wtforms_conflict()

# Khởi tạo extensions
db = SQLAlchemy()
login = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login.init_app(app)

    # Cấu hình Login
    login.login_view = 'main.login_view'
    login.login_message = "Vui lòng đăng nhập để tiếp tục."
    login.login_message_category = "warning"

    # Import Admin
    from app import admin
    admin.init_admin(app, db)

    # Đăng ký Routes
    from app.routes import main
    app.register_blueprint(main)

    return app

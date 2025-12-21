from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from flask import redirect, url_for
from app.models import NguoiDung, LinhKien, DanhMuc, QuyDinh, UserRole
from wtforms.validators import DataRequired
import hashlib


class BaseAdminView(ModelView):
    def is_accessible(self):
        # Chỉ Admin mới được vào
        return current_user.is_authenticated and current_user.vai_tro == UserRole.ADMIN

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('main.login_view'))


class HomeAdmin(AdminIndexView):
    @expose('/')
    def index(self):
        if not current_user.is_authenticated or current_user.vai_tro != UserRole.ADMIN:
            return redirect(url_for('main.login_view'))
        return super(HomeAdmin, self).index()


class DanhMucView(BaseAdminView):
    column_labels = {'ten': 'Tên danh mục'}
    form_columns = ['ten']
    form_args = {'ten': {'validators': [DataRequired()]}}


class LinhKienView(BaseAdminView):
    column_labels = {'ten': 'Tên LK', 'don_gia': 'Giá', 'so_luong_ton': 'Tồn', 'danh_muc': 'Danh mục'}
    column_list = ['ten', 'don_gia', 'so_luong_ton', 'danh_muc']
    form_columns = ['ten', 'don_gia', 'so_luong_ton', 'danh_muc']
    form_args = {'ten': {'validators': [DataRequired()]}}


class NguoiDungView(BaseAdminView):
    column_labels = {'ten': 'Họ tên', 'ten_dang_nhap': 'Username', 'vai_tro': 'Vai trò', 'active': 'Kích hoạt',
                     'mat_khau': 'Mật khẩu'}
    column_list = ['ten', 'ten_dang_nhap', 'vai_tro', 'active']
    form_columns = ['ten', 'ten_dang_nhap', 'mat_khau', 'vai_tro', 'active']
    form_args = {
        'ten': {'validators': [DataRequired()]},
        'ten_dang_nhap': {'validators': [DataRequired()]},
        'mat_khau': {'validators': [DataRequired()]}
    }

    # Tự động mã hóa mật khẩu MD5 khi tạo mới hoặc sửa
    def on_model_change(self, form, model, is_created):
        if form.mat_khau.data:
            raw = form.mat_khau.data
            if len(raw) != 32:
                model.mat_khau = hashlib.md5(raw.encode('utf-8')).hexdigest()


class QuyDinhView(BaseAdminView):
    column_labels = {'ten': 'Tên quy định', 'gia_tri': 'Giá trị'}
    form_columns = ['ten', 'gia_tri']
    form_args = {'ten': {'validators': [DataRequired()]}}


def init_admin(app, db):
    admin = Admin(app, name='Gara Admin', template_mode='bootstrap4', index_view=HomeAdmin())
    admin.add_view(NguoiDungView(NguoiDung, db.session, name='Người dùng'))
    admin.add_view(LinhKienView(LinhKien, db.session, name='Linh kiện'))
    admin.add_view(DanhMucView(DanhMuc, db.session, name='Danh mục'))
    admin.add_view(QuyDinhView(QuyDinh, db.session, name='Quy định'))



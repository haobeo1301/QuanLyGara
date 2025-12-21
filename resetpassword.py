from app import create_app, db
from app.models import NguoiDung
from sqlalchemy import select
import hashlib

app = create_app()


def reset_admin_pass():
    with app.app_context():
        # 1. Tìm user admin
        stmt = select(NguoiDung).where(NguoiDung.ten_dang_nhap == 'admin')
        user = db.session.execute(stmt).scalar_one_or_none()

        if user:
            print(f"Tìm thấy user: {user.ten_dang_nhap}")
            print(f"Hash cũ: {user.mat_khau}")

            # 2. Tạo hash chuẩn cho '123456'
            # MD5 của 123456 là: e10adc3949ba59abbe56e057f20f883e
            raw_pass = '123456'
            new_hash = hashlib.md5(raw_pass.strip().encode('utf-8')).hexdigest()

            # 3. Cập nhật
            user.mat_khau = new_hash
            user.active = True  # Đảm bảo tài khoản đang kích hoạt
            db.session.commit()

            print(f"--- ĐÃ RESET THÀNH CÔNG ---")
            print(f"Mật khẩu mới hash: {user.mat_khau}")
            print(f"Hãy đăng nhập lại với: admin / 123456")
        else:
            print("Không tìm thấy user admin!")


if __name__ == '__main__':
    reset_admin_pass()
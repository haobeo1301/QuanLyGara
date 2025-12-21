from app import create_app, db
from app.models import NguoiDung, UserRole, QuyDinh, KhachHang, Xe, PhieuTiepNhan, PhieuSuaChua, LinhKien, \
    ChiTietPhieuSua, HoaDon, DanhMuc
from sqlalchemy import select
import hashlib

# Tạo app context
app = create_app()


def init_database():
    with app.app_context():
        # 1. Xóa hết bảng cũ (nếu muốn làm sạch - cẩn thận khi dùng)
        # db.drop_all()

        # 2. Tạo lại tất cả các bảng
        print("Đang tạo bảng trong CSDL suaxedb...")
        db.create_all()
        print("Đã tạo bảng thành công!")

        # 3. Tạo Admin
        stmt = select(NguoiDung).where(NguoiDung.ten_dang_nhap == 'admin')
        admin = db.session.execute(stmt).scalar_one_or_none()

        if not admin:
            print("Đang tạo tài khoản Admin...")
            pw_hash = hashlib.md5('123456'.encode('utf-8')).hexdigest()
            u = NguoiDung(
                ten='Quản Trị Viên',
                ten_dang_nhap='admin',
                mat_khau=pw_hash,
                vai_tro=UserRole.ADMIN,
                active=True
            )
            db.session.add(u)
        else:
            print("Tài khoản Admin đã tồn tại.")

        # 4. Tạo Quy định
        qd_check = db.session.execute(select(QuyDinh).where(QuyDinh.ten == 'MAX_XE')).scalar_one_or_none()
        if not qd_check:
            print("Đang tạo Quy định mẫu...")
            db.session.add(QuyDinh(ten='MAX_XE', gia_tri=30.0))
            db.session.add(QuyDinh(ten='VAT', gia_tri=0.1))

        # 5. Tạo vài dữ liệu mẫu khác để test (Tùy chọn)
        # Tạo danh mục phụ tùng
        dm_check = db.session.execute(select(DanhMuc)).first()
        if not dm_check:
            print("Đang tạo danh mục phụ tùng mẫu...")
            dm1 = DanhMuc(ten="Phụ tùng máy")
            dm2 = DanhMuc(ten="Dầu nhớt")
            db.session.add_all([dm1, dm2])
            db.session.flush()  # Để lấy ID danh mục

            # Tạo vài linh kiện
            lk1 = LinhKien(ten="Bugi NGK", don_gia=50000, so_luong_ton=100, danh_muc_id=dm1.id)
            lk2 = LinhKien(ten="Nhớt Castrol", don_gia=120000, so_luong_ton=50, danh_muc_id=dm2.id)
            db.session.add_all([lk1, lk2])

        db.session.commit()
        print("=== KHỞI TẠO HOÀN TẤT ===")


if __name__ == '__main__':
    try:
        init_database()
    except Exception as e:
        print(f"LỖI: {str(e)}")
        print("Hãy chắc chắn bạn đã tạo database 'suaxedb' trong MySQL Workbench.")
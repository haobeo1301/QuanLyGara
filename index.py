from app import create_app, db, login, dao
from app.models import NguoiDung, UserRole, QuyDinh, HieuXe, DanhMuc, LinhKien
from sqlalchemy import select
import hashlib

app = create_app()
@login.user_loader
def load_user(user_id): return dao.get_user_by_id(user_id)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Seed Admin
        if not db.session.execute(select(NguoiDung).where(NguoiDung.ten_dang_nhap == 'admin')).scalar_one_or_none():
            pw = hashlib.md5('123456'.encode('utf-8')).hexdigest()
            db.session.add_all([
                NguoiDung(ten='Admin', ten_dang_nhap='admin', mat_khau=pw, vai_tro=UserRole.ADMIN),
                NguoiDung(ten='Tiếp Tân', ten_dang_nhap='tn1', mat_khau=pw, vai_tro=UserRole.TIEP_NHAN),
                NguoiDung(ten='Kỹ Thuật', ten_dang_nhap='kt1', mat_khau=pw, vai_tro=UserRole.KY_THUAT),
                NguoiDung(ten='Thu Ngân', ten_dang_nhap='cash1', mat_khau=pw, vai_tro=UserRole.THU_NGAN)
            ])
        # Seed Quy Dinh
        if not db.session.execute(select(QuyDinh)).first():
            db.session.add_all([QuyDinh(ten='MAX_XE', gia_tri=30.0), QuyDinh(ten='VAT', gia_tri=0.1)])
        # Seed Hieu Xe
        if not db.session.execute(select(HieuXe)).first():
            for b in ["Honda", "Toyota", "Yamaha", "Suzuki", "Piaggio", "Vinfast", "Mazda", "Kia", "Hyundai", "Ford"]:
                db.session.add(HieuXe(ten_hieu_xe=b))
        # Seed Linh Kien (De test)
        if not db.session.execute(select(DanhMuc)).first():
            d1 = DanhMuc(ten="Phụ tùng"); d2 = DanhMuc(ten="Dầu nhớt"); db.session.add_all([d1, d2]); db.session.flush()
            db.session.add_all([
                LinhKien(ten="Bugi Denso", don_gia=250000, so_luong_ton=50, danh_muc_id=d1.id),
                LinhKien(ten="Nhớt Castrol", don_gia=180000, so_luong_ton=30, danh_muc_id=d2.id)
            ])
        db.session.commit()
    app.run(debug=True, port=5001)

from app import create_app, db, login, dao
from app.models import NguoiDung, UserRole, QuyDinh, HieuXe
from sqlalchemy import select
import hashlib

app = create_app()


@login.user_loader
def load_user(user_id):
    return dao.get_user_by_id(user_id)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # Admin
        stmt = select(NguoiDung).where(NguoiDung.ten_dang_nhap == 'admin')
        if not db.session.execute(stmt).scalar_one_or_none():
            print(">>> Creating Admin...")
            pw = hashlib.md5('123456'.encode('utf-8')).hexdigest()
            u = NguoiDung(ten='Admin', ten_dang_nhap='admin', mat_khau=pw, vai_tro=UserRole.ADMIN)
            db.session.add(u)

        # Quy định
        if not db.session.execute(select(QuyDinh).where(QuyDinh.ten == 'MAX_XE')).scalars().first():
            db.session.add(QuyDinh(ten='MAX_XE', gia_tri=30.0))
            db.session.add(QuyDinh(ten='VAT', gia_tri=0.1))

        # Hãng xe
        if not db.session.execute(select(HieuXe)).scalars().first():
            print(">>> Seeding Car Brands...")
            brands = ["Honda", "Toyota", "Yamaha", "Suzuki", "Piaggio", "Vinfast", "Mazda", "Kia", "Hyundai", "Ford"]
            for b in brands:
                db.session.add(HieuXe(ten_hieu_xe=b))

        db.session.commit()
        print(">>> SYSTEM READY: http://127.0.0.1:5001")

    app.run(debug=True, port=5001)

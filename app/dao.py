from app.models import NguoiDung, KhachHang, Xe, PhieuTiepNhan, PhieuSuaChua, LinhKien, ChiTietPhieuSua, HoaDon, \
    QuyDinh, UserRole, TrangThaiPhieu
from app import db
import hashlib
from datetime import datetime
from sqlalchemy import select, func, extract


# --- AUTH ---
def auth_user(username, password):
    if not username or not password: return None

    username = username.strip()
    password = password.strip()
    pw_hash = hashlib.md5(password.encode('utf-8')).hexdigest()

    print(f"DEBUG LOGIN: User=[{username}], Hash=[{pw_hash}]")

    stmt = select(NguoiDung).where(NguoiDung.ten_dang_nhap == username)
    user = db.session.execute(stmt).scalar_one_or_none()

    if user:
        if user.mat_khau == pw_hash:
            return user
        else:
            print("DEBUG LOGIN: Sai mật khẩu!")
    else:
        print("DEBUG LOGIN: Không tìm thấy User!")
    return None


def get_user_by_id(user_id):
    return db.session.get(NguoiDung, user_id)


# --- TIẾP NHẬN ---
def check_limit_xe():
    qd = db.session.execute(select(QuyDinh).where(QuyDinh.ten == 'MAX_XE')).scalar_one_or_none()
    limit = int(qd.gia_tri) if qd else 30
    today = datetime.now().date()
    count = db.session.execute(
        select(func.count(PhieuTiepNhan.id)).where(func.date(PhieuTiepNhan.ngay_tiep_nhan) == today)).scalar()
    return count < limit


def create_reception(phone, name, address, plate, brand, issue):
    khach = db.session.execute(select(KhachHang).where(KhachHang.dien_thoai == phone)).scalar_one_or_none()
    if not khach:
        khach = KhachHang(ten=name, dien_thoai=phone, dia_chi=address)
        db.session.add(khach);
        db.session.flush()

    xe = db.session.execute(select(Xe).where(Xe.bien_so == plate)).scalar_one_or_none()
    if not xe:
        xe = Xe(bien_so=plate, hieu_xe=brand, khach_hang_id=khach.id)
        db.session.add(xe);
        db.session.flush()

    phieu = PhieuTiepNhan(xe_id=xe.id, tinh_trang=issue)
    db.session.add(phieu);
    db.session.commit()
    return phieu


def get_today_receptions():
    today = datetime.now().date()
    stmt = select(PhieuTiepNhan).where(func.date(PhieuTiepNhan.ngay_tiep_nhan) == today).order_by(
        PhieuTiepNhan.id.desc())
    return db.session.execute(stmt).scalars().all()


# --- SỬA CHỮA ---
def get_parts(kw=None):
    stmt = select(LinhKien)
    if kw: stmt = stmt.where(LinhKien.ten.contains(kw))
    return db.session.execute(stmt).scalars().all()


def create_repair_ticket(phieu_id, user_id, cart, labor_cost):
    try:
        phieu_sua = PhieuSuaChua(phieu_tiep_nhan_id=phieu_id, nguoi_dung_id=user_id, tien_cong=labor_cost)
        db.session.add(phieu_sua);
        db.session.flush()

        for lk_id, item in cart.items():
            lk = db.session.get(LinhKien, lk_id)
            if lk.so_luong_ton < item['quantity']: raise Exception(f"Hết hàng: {lk.ten}")
            lk.so_luong_ton -= item['quantity']
            ct = ChiTietPhieuSua(phieu_sua_chua_id=phieu_sua.id, linh_kien_id=lk_id, so_luong=item['quantity'],
                                 don_gia=item['price'])
            db.session.add(ct)

        ptn = db.session.get(PhieuTiepNhan, phieu_id)
        ptn.trang_thai = TrangThaiPhieu.DANG_SUA
        db.session.commit()
        return True, "Thành công"
    except Exception as e:
        db.session.rollback()
        return False, str(e)


# --- THANH TOÁN ---
def get_pending_payments():
    stmt = select(PhieuSuaChua).join(PhieuTiepNhan).where(PhieuTiepNhan.trang_thai == TrangThaiPhieu.DANG_SUA)
    return db.session.execute(stmt).scalars().all()


def process_payment(repair_id, user_id):
    try:
        phieu_sua = db.session.get(PhieuSuaChua, repair_id)
        tong_vt = sum(c.so_luong * c.don_gia for c in phieu_sua.chi_tiet)
        qd_vat = db.session.execute(select(QuyDinh).where(QuyDinh.ten == 'VAT')).scalar_one_or_none()
        vat = qd_vat.gia_tri if qd_vat else 0.1
        final = (phieu_sua.tien_cong + tong_vt) * (1 + vat)

        hd = HoaDon(so_tien=final, phieu_sua_chua_id=repair_id, nguoi_dung_id=user_id)
        db.session.add(hd)
        phieu_sua.phieu_tiep_nhan.trang_thai = TrangThaiPhieu.DA_THANH_TOAN
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        raise e


# --- BÁO CÁO ---
def get_revenue(month, year):
    stmt = select(func.date(HoaDon.ngay_thanh_toan), func.sum(HoaDon.so_tien)) \
        .where(extract('month', HoaDon.ngay_thanh_toan) == month, extract('year', HoaDon.ngay_thanh_toan) == year) \
        .group_by(func.date(HoaDon.ngay_thanh_toan))
    return db.session.execute(stmt).all()
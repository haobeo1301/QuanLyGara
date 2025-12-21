# ================== FILE: app/dao.py ==================
from app.models import NguoiDung, KhachHang, Xe, PhieuTiepNhan, PhieuSuaChua, LinhKien, ChiTietPhieuSua, HoaDon, \
    QuyDinh, UserRole, TrangThaiPhieu, HieuXe
from app import db
import hashlib
from datetime import datetime
from sqlalchemy import select, func, extract, and_


# --- AUTH (Đăng nhập) ---
def auth_user(username, password):
    if not username or not password: return None
    username = username.strip()
    password = password.strip()
    pw_hash = hashlib.md5(password.encode('utf-8')).hexdigest()

    print(f"DEBUG LOGIN: User=[{username}], Hash=[{pw_hash}]")

    # Truy vấn theo tên đăng nhập (snake_case)
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


# --- HELPER DỮ LIỆU ---
def get_all_brands():
    """Lấy danh sách Hãng xe từ DB để đổ vào Datalist"""
    return db.session.execute(select(HieuXe)).scalars().all()


# --- VALIDATION LOGIC ---
def check_car_in_progress(plate):
    """
    Kiểm tra xe có đang nằm trong gara không (Có phiếu chưa thanh toán).
    True: Đang sửa (Bận) | False: Rảnh
    """
    stmt_xe = select(Xe).where(Xe.bien_so == plate)
    xe = db.session.execute(stmt_xe).scalar_one_or_none()
    if not xe: return False

    # Tìm phiếu chưa thanh toán (Trạng thái != DA_THANH_TOAN)
    stmt_phieu = select(PhieuTiepNhan).where(
        and_(
            PhieuTiepNhan.xe_id == xe.id,
            PhieuTiepNhan.trang_thai != TrangThaiPhieu.DA_THANH_TOAN
        )
    )
    # Dùng scalars().first() để an toàn, tránh lỗi MultipleResultsFound
    phieu = db.session.execute(stmt_phieu).scalars().first()
    return True if phieu else False


# --- TIẾP NHẬN XE ---
def check_limit_xe():
    """Kiểm tra giới hạn số xe trong ngày"""
    qd = db.session.execute(select(QuyDinh).where(QuyDinh.ten == 'MAX_XE')).scalar_one_or_none()
    limit = int(qd.gia_tri) if qd else 30

    today = datetime.now().date()
    count = db.session.execute(
        select(func.count(PhieuTiepNhan.id)).where(func.date(PhieuTiepNhan.ngay_tiep_nhan) == today)
    ).scalar()

    return count < limit


def get_car_info_by_plate(plate):
    """API: Lấy thông tin xe và khách qua biển số"""
    stmt = select(Xe).where(Xe.bien_so == plate)
    xe = db.session.execute(stmt).scalar_one_or_none()
    if xe:
        return {
            "found": True,
            "bien_so": xe.bien_so,
            "hieu_xe": xe.hieu_xe,
            "khach_hang": {
                "ten": xe.khach_hang.ten,
                "dien_thoai": xe.khach_hang.dien_thoai,
                "dia_chi": xe.khach_hang.dia_chi
            }
        }
    return {"found": False}


def get_customer_info_by_phone(phone):
    """API: Lấy thông tin khách qua SĐT"""
    stmt = select(KhachHang).where(KhachHang.dien_thoai == phone)
    kh = db.session.execute(stmt).scalar_one_or_none()
    if kh:
        return {
            "found": True,
            "ten": kh.ten,
            "dia_chi": kh.dia_chi
        }
    return {"found": False}


def create_reception(phone, name, address, plate, brand, issue):
    """
    Tạo phiếu tiếp nhận (Transaction).
    1. Tạo/Update Khách.
    2. Tạo/Update Xe.
    3. Tạo Phiếu.
    """
    try:
        # 1. Xử lý Khách Hàng
        stmt_kh = select(KhachHang).where(KhachHang.dien_thoai == phone)
        khach = db.session.execute(stmt_kh).scalar_one_or_none()

        if not khach:
            khach = KhachHang(ten=name, dien_thoai=phone, dia_chi=address)
            db.session.add(khach);
            db.session.flush()
        else:
            # Cập nhật thông tin mới nhất nếu khách thay đổi
            khach.ten = name
            khach.dia_chi = address
            db.session.flush()

        # 2. Xử lý Xe
        stmt_xe = select(Xe).where(Xe.bien_so == plate)
        xe = db.session.execute(stmt_xe).scalar_one_or_none()

        if not xe:
            xe = Xe(bien_so=plate, hieu_xe=brand, khach_hang_id=khach.id)
            db.session.add(xe);
            db.session.flush()
        else:
            # Nếu xe đổi chủ (SĐT người mang xe đến khác chủ cũ trong DB)
            if xe.khach_hang_id != khach.id:
                xe.khach_hang_id = khach.id
            # Cập nhật lại hiệu xe (nếu user sửa)
            if brand:
                xe.hieu_xe = brand
            db.session.flush()

        # 3. Tạo Phiếu
        phieu = PhieuTiepNhan(xe_id=xe.id, tinh_trang=issue)
        db.session.add(phieu)

        db.session.commit()
        return True, "Tiếp nhận thành công!", phieu

    except Exception as e:
        db.session.rollback()
        # Trả về False và nội dung lỗi
        return False, str(e), None


def get_today_receptions():
    """Lấy danh sách phiếu TRONG NGÀY HÔM NAY (Cho trang tiếp nhận)"""
    today = datetime.now().date()
    stmt = select(PhieuTiepNhan).where(func.date(PhieuTiepNhan.ngay_tiep_nhan) == today).order_by(
        PhieuTiepNhan.id.desc())
    return db.session.execute(stmt).scalars().all()


def get_all_recent_tickets():
    """Lấy 50 phiếu gần nhất BẤT KỂ NGÀY (Cho Dashboard)"""
    stmt = select(PhieuTiepNhan).order_by(PhieuTiepNhan.id.desc()).limit(50)
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



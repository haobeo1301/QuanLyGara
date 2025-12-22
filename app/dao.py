from app.models import NguoiDung, KhachHang, Xe, PhieuTiepNhan, PhieuSuaChua, LinhKien, ChiTietPhieuSua, HoaDon, \
    QuyDinh, UserRole, TrangThaiPhieu, HieuXe, TrangThaiPhieuSua
from app import db
import hashlib
from datetime import datetime
from sqlalchemy import select, func, extract, and_
import logging
import random
import json

# --- CẤU HÌNH LOGGING (ĐÃ SỬA) ---
# Thay vì dùng logging.basicConfig (gây ảnh hưởng toàn server), ta tạo một logger riêng
offline_logger = logging.getLogger('offline_logger')
offline_logger.setLevel(logging.ERROR)  # Logger này chỉ quan tâm đến lỗi

# Tạo handler ghi ra file (chỉ gắn vào logger này)
file_handler = logging.FileHandler('offline_transactions.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
offline_logger.addHandler(file_handler)


# --- CÁC HÀM CƠ BẢN (AUTH, USER, XE...) ---

def auth_user(username, password):
    if not username or not password: return None
    username = username.strip()
    password = password.strip()
    pw_hash = hashlib.md5(password.encode('utf-8')).hexdigest()
    stmt = select(NguoiDung).where(NguoiDung.ten_dang_nhap == username)
    user = db.session.execute(stmt).scalar_one_or_none()
    if user and user.mat_khau == pw_hash: return user
    return None


def get_user_by_id(user_id):
    return db.session.get(NguoiDung, user_id)


def get_all_brands():
    return db.session.execute(select(HieuXe)).scalars().all()


def check_car_in_progress(plate):
    stmt_xe = select(Xe).where(Xe.bien_so == plate)
    xe = db.session.execute(stmt_xe).scalar_one_or_none()
    if not xe: return False
    stmt_phieu = select(PhieuTiepNhan).where(
        and_(PhieuTiepNhan.xe_id == xe.id, PhieuTiepNhan.trang_thai != TrangThaiPhieu.DA_THANH_TOAN)
    )
    phieu = db.session.execute(stmt_phieu).scalars().first()
    return True if phieu else False


def check_limit_xe():
    qd = db.session.execute(select(QuyDinh).where(QuyDinh.ten == 'MAX_XE')).scalar_one_or_none()
    limit = int(qd.gia_tri) if qd else 30
    today = datetime.now().date()
    count = db.session.execute(
        select(func.count(PhieuTiepNhan.id)).where(func.date(PhieuTiepNhan.ngay_tiep_nhan) == today)).scalar()
    return count < limit


def get_car_info_by_plate(plate):
    stmt = select(Xe).where(Xe.bien_so == plate)
    xe = db.session.execute(stmt).scalar_one_or_none()
    if xe:
        return {"found": True, "bien_so": xe.bien_so, "hieu_xe": xe.hieu_xe,
                "khach_hang": {"ten": xe.khach_hang.ten, "dien_thoai": xe.khach_hang.dien_thoai,
                               "dia_chi": xe.khach_hang.dia_chi}}
    return {"found": False}


def get_customer_info_by_phone(phone):
    stmt = select(KhachHang).where(KhachHang.dien_thoai == phone)
    kh = db.session.execute(stmt).scalar_one_or_none()
    if kh: return {"found": True, "ten": kh.ten, "dia_chi": kh.dia_chi}
    return {"found": False}


def create_reception(phone, name, address, plate, brand, issue):
    try:
        stmt_kh = select(KhachHang).where(KhachHang.dien_thoai == phone)
        khach = db.session.execute(stmt_kh).scalar_one_or_none()
        if not khach:
            khach = KhachHang(ten=name, dien_thoai=phone, dia_chi=address)
            db.session.add(khach)
            db.session.flush()
        else:
            khach.ten = name
            khach.dia_chi = address
            db.session.flush()

        stmt_xe = select(Xe).where(Xe.bien_so == plate)
        xe = db.session.execute(stmt_xe).scalar_one_or_none()
        if not xe:
            xe = Xe(bien_so=plate, hieu_xe=brand, khach_hang_id=khach.id)
            db.session.add(xe)
            db.session.flush()
        else:
            if xe.khach_hang_id != khach.id: xe.khach_hang_id = khach.id
            if brand: xe.hieu_xe = brand
            db.session.flush()

        phieu = PhieuTiepNhan(xe_id=xe.id, tinh_trang=issue)
        db.session.add(phieu)
        db.session.commit()

        # [TERMINAL LOG]
        print(f"✅ Đã tiếp nhận xe: {plate} - Khách: {name}")

        return True, "Tiếp nhận thành công!", phieu
    except Exception as e:
        db.session.rollback()
        print(f"❌ Lỗi tiếp nhận: {str(e)}")
        return False, str(e), None


def get_today_receptions():
    today = datetime.now().date()
    stmt = select(PhieuTiepNhan).where(func.date(PhieuTiepNhan.ngay_tiep_nhan) == today).order_by(
        PhieuTiepNhan.id.desc())
    return db.session.execute(stmt).scalars().all()


def count_today_receptions():
    today = datetime.now().date()
    return db.session.execute(
        select(func.count(PhieuTiepNhan.id)).where(func.date(PhieuTiepNhan.ngay_tiep_nhan) == today)).scalar()


def get_all_recent_tickets():
    stmt = select(PhieuTiepNhan).order_by(PhieuTiepNhan.id.desc()).limit(50)
    return db.session.execute(stmt).scalars().all()


def get_list_waiting_repair():
    stmt = select(PhieuTiepNhan).where(PhieuTiepNhan.trang_thai == TrangThaiPhieu.CHO_SUA).order_by(
        PhieuTiepNhan.id.desc())
    return db.session.execute(stmt).scalars().all()


def get_reception_by_id(id):
    return db.session.get(PhieuTiepNhan, id)


def get_parts(kw=None):
    stmt = select(LinhKien)
    if kw and kw.strip(): stmt = stmt.where(LinhKien.ten.contains(kw))
    stmt = stmt.limit(50)
    return db.session.execute(stmt).scalars().all()


def save_repair_ticket_v2(phieu_tiep_nhan_id, nguoi_dung_id, items, labor_cost, action):
    try:
        is_draft = (action == 'draft')
        status_enum = TrangThaiPhieuSua.NHAP if is_draft else TrangThaiPhieuSua.HOAN_THANH

        phieu_sua = PhieuSuaChua(
            phieu_tiep_nhan_id=phieu_tiep_nhan_id,
            nguoi_dung_id=nguoi_dung_id,
            tien_cong=labor_cost,
            ngay_sua=datetime.now(),
            trang_thai_phieu=status_enum
        )
        db.session.add(phieu_sua)
        db.session.flush()

        for item in items:
            lk_id = int(item['id'])
            qty = int(item['qty'])
            price = float(item['price'])
            lk = db.session.get(LinhKien, lk_id)
            if not is_draft:
                if lk.so_luong_ton < qty: raise Exception(f"Linh kiện '{lk.ten}' không đủ hàng.")
                lk.so_luong_ton -= qty
            ct = ChiTietPhieuSua(phieu_sua_chua_id=phieu_sua.id, linh_kien_id=lk_id, so_luong=qty, don_gia=price)
            db.session.add(ct)

        ptn = db.session.get(PhieuTiepNhan, phieu_tiep_nhan_id)
        if not is_draft: ptn.trang_thai = TrangThaiPhieu.DANG_SUA

        db.session.commit()

        # [TERMINAL LOG]
        print(f"✅ Đã lưu phiếu sửa chữa (ID: {phieu_sua.id}) - Trạng thái: {action}")

        return True, "Đã lưu phiếu thành công."
    except Exception as e:
        db.session.rollback()
        print(f"❌ Lỗi lưu phiếu: {str(e)}")
        return False, str(e)


def get_pending_payments():
    stmt = select(PhieuSuaChua).join(PhieuTiepNhan).where(PhieuTiepNhan.trang_thai == TrangThaiPhieu.DANG_SUA)
    return db.session.execute(stmt).scalars().all()


# --- LOGIC THANH TOÁN & BÁO CÁO ---

def get_config_vat():
    qd = db.session.execute(select(QuyDinh).where(QuyDinh.ten == 'VAT')).scalar_one_or_none()
    return qd.gia_tri if qd else None


def mock_bank_api_call(amount):
    # Giả lập: 10% lỗi
    if random.random() < 0.1: return False, "Lỗi kết nối cổng thanh toán (Mã: 502)"
    return True, f"TRANS-{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8].upper()}"


def process_payment_advanced(repair_id, user_id, payment_method, amount_tendered, discount, manual_vat=None):
    try:
        phieu_sua = db.session.get(PhieuSuaChua, repair_id)
        if not phieu_sua: return {"success": False, "msg": "Phiếu không tồn tại."}

        ptn = phieu_sua.phieu_tiep_nhan
        if ptn.trang_thai == TrangThaiPhieu.DA_THANH_TOAN: return {"success": False, "msg": "Đã thanh toán rồi."}

        tong_vt = sum(c.so_luong * c.don_gia for c in phieu_sua.chi_tiet)
        subtotal = phieu_sua.tien_cong + tong_vt

        current_vat = get_config_vat()
        applied_vat = 0.0
        if current_vat is not None:
            applied_vat = current_vat
        else:
            if manual_vat is None: return {"success": False, "msg": "Thiếu VAT."}
            try:
                manual_vat = float(manual_vat)
                if manual_vat < 0 or manual_vat > 0.3: return {"success": False, "msg": "VAT không hợp lệ."}
                applied_vat = manual_vat
            except:
                return {"success": False, "msg": "Lỗi định dạng VAT."}

        taxable = subtotal - discount
        if taxable < 0: taxable = 0
        final_amount = taxable + (taxable * applied_vat)

        change_amount = 0
        if payment_method == 'cash':
            if amount_tendered < final_amount: return {"success": False, "msg": "Khách đưa thiếu tiền."}
            change_amount = amount_tendered - final_amount
        elif payment_method in ['transfer', 'pos']:
            ok, msg = mock_bank_api_call(final_amount)
            if not ok: return {"success": False, "msg": msg}

        # --- THỬ LƯU VÀO DATABASE ---
        try:
            hd = HoaDon(so_tien=final_amount, phieu_sua_chua_id=repair_id, nguoi_dung_id=user_id)
            phieu_sua.phieu_tiep_nhan.trang_thai = TrangThaiPhieu.DA_THANH_TOAN
            db.session.add(hd)
            db.session.commit()

            # [TERMINAL LOG] - In ra console (OK)
            print(f"💰 [ONLINE] Thanh toán thành công! HĐ #{hd.id} | Tổng: {final_amount:,.0f} đ | User: {user_id}")

            return {"success": True, "msg": "Thành công!",
                    "data": {"id": hd.id, "total": final_amount, "change": change_amount, "vat_rate": applied_vat,
                             "method": payment_method}}

        except Exception as db_e:
            # --- LỖI DB -> CHUYỂN QUA OFFLINE FILE ---
            db.session.rollback()

            log_entry = {
                "time": str(datetime.now()),
                "repair_id": repair_id,
                "amount": final_amount,
                "error": str(db_e)
            }
            # Sử dụng offline_logger thay vì logging.error (để tránh ảnh hưởng console)
            offline_logger.error(json.dumps(log_entry))

            print(f"⚠️ [OFFLINE] Lỗi kết nối DB! Đã lưu giao dịch tạm vào file log.")

            return {"success": True, "warning": True, "msg": "Offline Mode: Đã lưu tạm.",
                    "data": {"id": "OFFLINE", "total": final_amount, "change": change_amount, "vat_rate": applied_vat,
                             "method": payment_method}}

    except Exception as e:
        print(f"❌ Lỗi hệ thống: {str(e)}")
        return {"success": False, "msg": str(e)}


def get_report_data_by_range(from_date, to_date, report_type='revenue'):
    try:
        start = datetime.strptime(from_date, '%Y-%m-%d').date()
        end = datetime.strptime(to_date, '%Y-%m-%d').date()
    except ValueError:
        return {"error": "Định dạng ngày sai."}

    if start > end: return {"error": "Ngày bắt đầu > Ngày kết thúc."}

    data = [];
    summary = {"total": 0, "count": 0}
    try:
        # 1. BÁO CÁO DOANH THU
        if report_type == 'revenue':
            stmt = select(func.date(HoaDon.ngay_thanh_toan), func.sum(HoaDon.so_tien), func.count(HoaDon.id)) \
                .where(and_(func.date(HoaDon.ngay_thanh_toan) >= start, func.date(HoaDon.ngay_thanh_toan) <= end)) \
                .group_by(func.date(HoaDon.ngay_thanh_toan)).order_by(func.date(HoaDon.ngay_thanh_toan))
            results = db.session.execute(stmt).all()
            data = [{"label": r[0].strftime('%d/%m/%Y'), "value": r[1], "count": r[2]} for r in results]
            summary["total"] = sum(item['value'] for item in data)
            summary["count"] = sum(item['count'] for item in data)

        # 2. BÁO CÁO SỐ LƯỢNG XE
        elif report_type == 'reception':
            stmt = select(func.date(PhieuTiepNhan.ngay_tiep_nhan), func.count(PhieuTiepNhan.id)) \
                .where(
                and_(func.date(PhieuTiepNhan.ngay_tiep_nhan) >= start, func.date(PhieuTiepNhan.ngay_tiep_nhan) <= end)) \
                .group_by(func.date(PhieuTiepNhan.ngay_tiep_nhan)).order_by(func.date(PhieuTiepNhan.ngay_tiep_nhan))
            results = db.session.execute(stmt).all()
            data = [{"label": r[0].strftime('%d/%m/%Y'), "value": r[1]} for r in results]
            summary["total"] = sum(item['value'] for item in data)

        # 3. [MỚI] BÁO CÁO LINH KIỆN BÁN RA (Top 10)
        elif report_type == 'parts':
            # Join PhieuTiepNhan -> PhieuSuaChua -> ChiTiet -> LinhKien
            stmt = select(LinhKien.ten, func.sum(ChiTietPhieuSua.so_luong),
                          func.sum(ChiTietPhieuSua.so_luong * ChiTietPhieuSua.don_gia)) \
                .join(ChiTietPhieuSua, LinhKien.id == ChiTietPhieuSua.linh_kien_id) \
                .join(PhieuSuaChua, ChiTietPhieuSua.phieu_sua_chua_id == PhieuSuaChua.id) \
                .join(PhieuTiepNhan, PhieuSuaChua.phieu_tiep_nhan_id == PhieuTiepNhan.id) \
                .where(
                and_(func.date(PhieuTiepNhan.ngay_tiep_nhan) >= start, func.date(PhieuTiepNhan.ngay_tiep_nhan) <= end)) \
                .group_by(LinhKien.ten).order_by(func.sum(ChiTietPhieuSua.so_luong).desc()).limit(10)

            results = db.session.execute(stmt).all()
            # label: Tên linh kiện, value: Số lượng, total_money: Thành tiền
            data = [{"label": r[0], "value": r[1], "total_money": r[2]} for r in results]
            summary["total"] = sum(item['value'] for item in data)  # Tổng số lượng bán

        # 4. [MỚI] BÁO CÁO LỖI HƯ HỎNG (Top 10)
        elif report_type == 'issues':
            stmt = select(PhieuTiepNhan.tinh_trang, func.count(PhieuTiepNhan.id)) \
                .where(
                and_(func.date(PhieuTiepNhan.ngay_tiep_nhan) >= start, func.date(PhieuTiepNhan.ngay_tiep_nhan) <= end)) \
                .group_by(PhieuTiepNhan.tinh_trang) \
                .order_by(func.count(PhieuTiepNhan.id).desc()).limit(10)

            results = db.session.execute(stmt).all()
            data = [{"label": r[0], "value": r[1]} for r in results]
            summary["total"] = sum(item['value'] for item in data)  # Tổng số lỗi ghi nhận

        print(f"📊 [REPORT] Loại: {report_type} | Kết quả: {len(data)} dòng.")

        return {"success": True, "data": data, "summary": summary, "report_type": report_type,
                "range": f"{start.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')}"}
    except Exception as e:
        print(f"❌ Lỗi báo cáo: {str(e)}")
        return {"error": str(e)}


def get_revenue(month, year):
    stmt = select(func.date(HoaDon.ngay_thanh_toan), func.sum(HoaDon.so_tien)).where(
        extract('month', HoaDon.ngay_thanh_toan) == month, extract('year', HoaDon.ngay_thanh_toan) == year).group_by(
        func.date(HoaDon.ngay_thanh_toan))
    return db.session.execute(stmt).all()
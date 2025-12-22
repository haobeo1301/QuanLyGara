import random
from datetime import datetime, timedelta
import hashlib
from faker import Faker
from app import create_app, db
from app.models import (
    NguoiDung, KhachHang, Xe, PhieuTiepNhan, PhieuSuaChua,
    LinhKien, ChiTietPhieuSua, HoaDon, QuyDinh, UserRole,
    TrangThaiPhieu, TrangThaiPhieuSua, HieuXe, DanhMuc
)
from sqlalchemy import select

# Cấu hình Faker tiếng Việt
fake = Faker('vi_VN')
app = create_app()

# CẤU HÌNH SỐ LƯỢNG
NUM_CUSTOMERS = 100  # 100 Khách
NUM_CARS = 150  # 150 Xe
NUM_RECEPTIONS = 300  # 300 Giao dịch

# DANH SÁCH LINH KIỆN CÓ NGHĨA (Theo danh mục)
REAL_PARTS_DATA = {
    "Động cơ & Máy": [
        ("Bugi Iridium Denso", 250000),
        ("Bugi NGK Platinum", 180000),
        ("Lọc gió động cơ K&N", 1200000),
        ("Lọc xăng Toyota Vios", 850000),
        ("Dây curoa cam Bosch", 550000),
        ("Bơm nước làm mát", 1400000),
        ("Ron nắp quy lát", 350000),
        ("Mobin sườn", 900000),
        ("Lọc dầu (Nhớt) Honda", 150000)
    ],
    "Gầm xe & Phanh": [
        ("Phuộc nhún trước Kayaba", 1800000),
        ("Phuộc nhún sau Tokico", 1600000),
        ("Má phanh đĩa trước Brembo", 2200000),
        ("Bố thắng sau Nissin", 450000),
        ("Rô tuyn lái ngoài", 650000),
        ("Rô tuyn cân bằng", 550000),
        ("Cao su chân máy", 800000),
        ("Bạc đạn bánh trước SKF", 950000)
    ],
    "Điện - Đèn - Còi": [
        ("Bình ắc quy GS 12V-60Ah", 1650000),
        ("Bình ắc quy Đồng Nai 12V-45Ah", 1200000),
        ("Bóng đèn pha LED Philips", 1800000),
        ("Bóng đèn Halogen Osram", 350000),
        ("Còi sên Denso (Cặp)", 450000),
        ("Cảm biến lùi 4 mắt", 1100000),
        ("Máy phát điện (Dinamo)", 4500000)
    ],
    "Dầu nhớt & Hóa chất": [
        ("Nhớt Castrol Magnatec 10W-40 (4L)", 650000),
        ("Nhớt Motul H-Tech 100 Plus (4L)", 850000),
        ("Nhớt Mobil 1 Gold 5W-30", 320000),
        ("Nước làm mát màu xanh (Can)", 150000),
        ("Dầu hộp số tự động ATF", 250000),
        ("Dầu thắng DOT4", 120000),
        ("Nước rửa kính", 60000)
    ],
    "Lốp & Mâm xe": [
        ("Lốp Michelin Primacy 4", 2600000),
        ("Lốp Bridgestone Turanza", 2400000),
        ("Lốp Dunlop Enasave", 2100000),
        ("Vành đúc hợp kim 16 inch", 3500000),
        ("Cảm biến áp suất lốp TPMS", 2800000)
    ]
}


def get_random_date(start_days_ago=90):
    """Lấy ngày ngẫu nhiên trong 3 tháng qua"""
    start_date = datetime.now() - timedelta(days=start_days_ago)
    random_days = random.randrange(start_days_ago)
    # Thêm giờ ngẫu nhiên để biểu đồ không bị dồn cục
    return start_date + timedelta(days=random_days, hours=random.randint(7, 17), minutes=random.randint(0, 59))


def seed_all():
    with app.app_context():
        # Xóa dữ liệu cũ (Tùy chọn, cẩn thận mất dữ liệu thật)
        # db.drop_all()
        # db.create_all()

        print("--- BẮT ĐẦU TẠO DỮ LIỆU MẪU (THỰC TẾ) ---")

        # 1. Tạo Danh Mục & Linh Kiện từ Dictionary
        print(f"-> Đang tạo Danh mục và Linh kiện...")
        all_parts_objs = []

        for cat_name, parts_list in REAL_PARTS_DATA.items():
            # Tạo hoặc lấy danh mục
            cat = db.session.execute(select(DanhMuc).where(DanhMuc.ten == cat_name)).scalar_one_or_none()
            if not cat:
                cat = DanhMuc(ten=cat_name)
                db.session.add(cat)
                db.session.flush()

            # Tạo linh kiện thuộc danh mục đó
            for p_name, p_price in parts_list:
                # Kiểm tra xem có chưa để tránh trùng lặp khi chạy nhiều lần
                existing_part = db.session.execute(select(LinhKien).where(LinhKien.ten == p_name)).scalar_one_or_none()
                if not existing_part:
                    # Random sai số giá một chút cho tự nhiên (+- 10%)
                    variance = random.uniform(0.9, 1.1)
                    final_price = int(p_price * variance / 1000) * 1000  # Làm tròn

                    lk = LinhKien(
                        ten=p_name,
                        don_gia=final_price,
                        so_luong_ton=random.randint(20, 100),
                        danh_muc_id=cat.id
                    )
                    db.session.add(lk)
                    all_parts_objs.append(lk)
                else:
                    all_parts_objs.append(existing_part)

        db.session.flush()

        # 2. Tạo Khách hàng
        print(f"-> Đang tạo {NUM_CUSTOMERS} khách hàng...")
        customers = []
        for _ in range(NUM_CUSTOMERS):
            kh = KhachHang(
                ten=fake.name(),
                dien_thoai=fake.numerify(text="09########"),
                dia_chi=fake.address()
            )
            db.session.add(kh)
            customers.append(kh)
        db.session.flush()

        # 3. Tạo Hãng xe & Xe
        print(f"-> Đang tạo {NUM_CARS} xe...")
        brands = ["Toyota", "Honda", "Hyundai", "Kia", "Mazda", "Ford", "Mercedes", "VinFast", "Mitsubishi"]
        for b in brands:
            if not db.session.execute(select(HieuXe).where(HieuXe.ten_hieu_xe == b)).scalar_one_or_none():
                db.session.add(HieuXe(ten_hieu_xe=b))
        db.session.flush()

        cars = []
        for _ in range(NUM_CARS):
            plate = f"{random.randint(50, 99)}{random.choice(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'K'])}-{random.randint(10000, 99999)}"
            xe = Xe(
                bien_so=plate,
                hieu_xe=random.choice(brands),
                khach_hang_id=random.choice(customers).id
            )
            db.session.add(xe)
            cars.append(xe)
        db.session.flush()

        # 4. Tạo Phiếu Tiếp Nhận & Giao dịch
        print(f"-> Đang tạo {NUM_RECEPTIONS} giao dịch...")

        # Đảm bảo có Admin
        admin_user = db.session.execute(
            select(NguoiDung).where(NguoiDung.ten_dang_nhap == 'admin')).scalar_one_or_none()
        if not admin_user:
            pw = hashlib.md5('123456'.encode('utf-8')).hexdigest()
            admin_user = NguoiDung(ten='Admin', ten_dang_nhap='admin', mat_khau=pw, vai_tro=UserRole.ADMIN)
            db.session.add(admin_user)
            db.session.flush()

        tinh_trang_list = ["Bảo dưỡng định kỳ", "Thay nhớt", "Kêu gầm", "Móp cản sau", "Máy rung", "Điều hòa không mát",
                           "Thay lốp", "Sơn dặm", "Kiểm tra tổng quát"]

        for _ in range(NUM_RECEPTIONS):
            rcv_date = get_random_date()
            car = random.choice(cars)

            # Tỷ lệ trạng thái: 80% Đã thanh toán (Để báo cáo đẹp), 15% Đang sửa, 5% Chờ
            rand_stat = random.random()
            status = TrangThaiPhieu.DA_THANH_TOAN
            if rand_stat > 0.95:
                status = TrangThaiPhieu.CHO_SUA
            elif rand_stat > 0.8:
                status = TrangThaiPhieu.DANG_SUA

            # Phiếu tiếp nhận
            ptn = PhieuTiepNhan(
                ngay_tiep_nhan=rcv_date,
                tinh_trang=random.choice(tinh_trang_list),
                trang_thai=status,
                xe_id=car.id
            )
            db.session.add(ptn)
            db.session.flush()

            # Nếu đã vào sửa chữa
            if status in [TrangThaiPhieu.DANG_SUA, TrangThaiPhieu.DA_THANH_TOAN]:
                labor = random.choice([150000, 250000, 400000, 600000, 1000000])  # Tiền công
                psc = PhieuSuaChua(
                    ngay_sua=rcv_date + timedelta(hours=random.randint(1, 4)),
                    tien_cong=labor,
                    trang_thai_phieu=TrangThaiPhieuSua.HOAN_THANH,
                    phieu_tiep_nhan_id=ptn.id,
                    nguoi_dung_id=admin_user.id
                )
                db.session.add(psc)
                db.session.flush()

                # Chọn ngẫu nhiên linh kiện (từ 1 đến 6 món)
                if all_parts_objs:
                    num_items = random.randint(1, 6)
                    chosen_parts = random.sample(all_parts_objs, min(num_items, len(all_parts_objs)))

                    total_parts_cost = 0
                    for p in chosen_parts:
                        qty = random.randint(1, 4)  # Số lượng 1-4
                        ct = ChiTietPhieuSua(
                            phieu_sua_chua_id=psc.id,
                            linh_kien_id=p.id,
                            so_luong=qty,
                            don_gia=p.don_gia
                        )
                        db.session.add(ct)
                        total_parts_cost += (p.don_gia * qty)

                # Nếu ĐÃ THANH TOÁN -> Tạo Hóa Đơn
                if status == TrangThaiPhieu.DA_THANH_TOAN:
                    vat = 0.1
                    # Thanh toán sau khi sửa xong khoảng 1-2 tiếng
                    pay_date = psc.ngay_sua + timedelta(hours=random.randint(1, 3))
                    if pay_date > datetime.now(): pay_date = datetime.now()

                    total_amount = (labor + total_parts_cost) * (1 + vat)

                    hd = HoaDon(
                        ngay_thanh_toan=pay_date,
                        so_tien=total_amount,
                        phieu_sua_chua_id=psc.id,
                        nguoi_dung_id=admin_user.id
                    )
                    db.session.add(hd)

        db.session.commit()
        print(f"=== ĐÃ TẠO XONG DỮ LIỆU ===")
        print(f"-> Đã thêm {len(all_parts_objs)} linh kiện thực tế.")
        print(f"-> Đã thêm {NUM_RECEPTIONS} giao dịch.")
        print(f"User: admin / Pass: 123456")


if __name__ == '__main__':
    seed_all()
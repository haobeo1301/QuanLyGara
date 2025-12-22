from app import db
from flask_login import UserMixin
from sqlalchemy import Integer, String, Float, Boolean, ForeignKey, DateTime, Enum, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

class UserRole(enum.Enum):
    ADMIN = 1
    TIEP_NHAN = 2
    KY_THUAT = 3
    THU_NGAN = 4

class TrangThaiPhieu(enum.Enum):
    CHO_SUA = "Chờ sửa"
    DANG_SUA = "Đang sửa"
    DA_THANH_TOAN = "Đã thanh toán"

class TrangThaiPhieuSua(enum.Enum):
    NHAP = "Nháp"
    HOAN_THANH = "Hoàn thành"

class HieuXe(db.Model):
    __tablename__ = 'hieu_xe'
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    ten_hieu_xe = db.Column(String(50), nullable=False, unique=True)
    def __str__(self): return self.ten_hieu_xe

class NguoiDung(db.Model, UserMixin):
    __tablename__ = 'nguoi_dung'
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    ten = db.Column(String(50), nullable=False)
    ten_dang_nhap = db.Column(String(50), nullable=False)
    mat_khau = db.Column(String(100), nullable=False)
    vai_tro = db.Column(Enum(UserRole), default=UserRole.TIEP_NHAN)
    active = db.Column(Boolean, default=True)
    __table_args__ = (UniqueConstraint('ten_dang_nhap', name='uq_nguoidung_username'),)
    def __str__(self): return self.ten

class KhachHang(db.Model):
    __tablename__ = 'khach_hang'
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    ten = db.Column(String(50), nullable=False)
    dien_thoai = db.Column(String(20), nullable=False)
    dia_chi = db.Column(String(200))
    xes = relationship('Xe', backref='khach_hang', lazy=True)
    __table_args__ = (UniqueConstraint('dien_thoai', name='uq_khachhang_sdt'),)
    def __str__(self): return self.ten

class Xe(db.Model):
    __tablename__ = 'xe'
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    bien_so = db.Column(String(20), nullable=False)
    hieu_xe = db.Column(String(50)) 
    khach_hang_id = db.Column(Integer, ForeignKey('khach_hang.id'), nullable=False)
    phieu_tiep_nhan = relationship('PhieuTiepNhan', backref='xe', lazy=True)
    __table_args__ = (UniqueConstraint('bien_so', name='uq_xe_bienso'),)
    def __str__(self): return self.bien_so

class PhieuTiepNhan(db.Model):
    __tablename__ = 'phieu_tiep_nhan'
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    ngay_tiep_nhan = db.Column(DateTime, default=datetime.now)
    tinh_trang = db.Column(Text)
    trang_thai = db.Column(Enum(TrangThaiPhieu), default=TrangThaiPhieu.CHO_SUA)
    xe_id = db.Column(Integer, ForeignKey('xe.id'), nullable=False)
    phieu_sua_chua = relationship('PhieuSuaChua', backref='phieu_tiep_nhan', uselist=False)

class DanhMuc(db.Model):
    __tablename__ = 'danh_muc'
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    ten = db.Column(String(50), nullable=False)
    __table_args__ = (UniqueConstraint('ten', name='uq_danhmuc_ten'),)
    def __str__(self): return self.ten

class LinhKien(db.Model):
    __tablename__ = 'linh_kien'
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    ten = db.Column(String(100), nullable=False)
    don_gia = db.Column(Float, default=0)
    so_luong_ton = db.Column(Integer, default=0)
    danh_muc_id = db.Column(Integer, ForeignKey('danh_muc.id'), nullable=False)
    danh_muc = relationship('DanhMuc', backref='linh_kiens')
    def __str__(self): return self.ten

class PhieuSuaChua(db.Model):
    __tablename__ = 'phieu_sua_chua'
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    ngay_sua = db.Column(DateTime, default=datetime.now)
    tien_cong = db.Column(Float, default=0)
    trang_thai_phieu = db.Column(Enum(TrangThaiPhieuSua), default=TrangThaiPhieuSua.HOAN_THANH)
    phieu_tiep_nhan_id = db.Column(Integer, ForeignKey('phieu_tiep_nhan.id'), unique=True, nullable=False)
    nguoi_dung_id = db.Column(Integer, ForeignKey('nguoi_dung.id'), nullable=False)
    chi_tiet = relationship('ChiTietPhieuSua', backref='phieu_sua_chua', lazy=True)
    hoa_don = relationship('HoaDon', backref='phieu_sua_chua', uselist=False)

class ChiTietPhieuSua(db.Model):
    __tablename__ = 'chi_tiet_phieu_sua'
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    phieu_sua_chua_id = db.Column(Integer, ForeignKey('phieu_sua_chua.id'), nullable=False)
    linh_kien_id = db.Column(Integer, ForeignKey('linh_kien.id'), nullable=False)
    so_luong = db.Column(Integer, default=1)
    don_gia = db.Column(Float, default=0)
    linh_kien = relationship('LinhKien')

class HoaDon(db.Model):
    __tablename__ = 'hoa_don'
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    ngay_thanh_toan = db.Column(DateTime, default=datetime.now)
    so_tien = db.Column(Float, default=0)
    phieu_sua_chua_id = db.Column(Integer, ForeignKey('phieu_sua_chua.id'), unique=True, nullable=False)
    nguoi_dung_id = db.Column(Integer, ForeignKey('nguoi_dung.id'), nullable=False)

class QuyDinh(db.Model):
    __tablename__ = 'quy_dinh'
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    ten = db.Column(String(50), nullable=False)
    gia_tri = db.Column(Float, default=0)
    __table_args__ = (UniqueConstraint('ten', name='uq_quydinh_ten'),)

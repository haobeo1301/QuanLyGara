# ================== FILE: app/routes.py ==================
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import dao
from app.models import PhieuTiepNhan, UserRole
from app.decorators import role_required
from datetime import datetime
import re

main = Blueprint('main', __name__)


@main.route("/")
def index():
    # Lấy danh sách mới nhất cho Dashboard
    tickets = dao.get_all_recent_tickets()
    today_str = datetime.now().strftime("Ngày %d tháng %m năm %Y")
    return render_template('index.html', tickets=tickets, today_date=today_str)


@main.route('/login', methods=['GET', 'POST'])
def login_view():
    if current_user.is_authenticated: return redirect(url_for('main.index'))
    if request.method == 'POST':
        u = dao.auth_user(request.form.get('username'), request.form.get('password'))
        if u:
            login_user(u)
            return redirect(url_for('main.index'))
        else:
            flash('Tên đăng nhập hoặc mật khẩu không đúng', 'danger')
    return render_template('login.html')


@main.route('/logout')
def logout_view():
    logout_user()
    return redirect(url_for('main.login_view'))


# --- API HELPERS (Dùng cho Ajax tự động điền) ---
@main.route('/api/check-plate', methods=['POST'])
def check_plate_api():
    plate = request.json.get('plate')
    return jsonify(dao.get_car_info_by_plate(plate))


@main.route('/api/check-phone', methods=['POST'])
def check_phone_api():
    phone = request.json.get('phone')
    return jsonify(dao.get_customer_info_by_phone(phone))


# --- ROUTE TIẾP NHẬN (LOGIC VALIDATE ĐẦY ĐỦ) ---
@main.route('/reception', methods=['GET', 'POST'])
@role_required(UserRole.ADMIN, UserRole.TIEP_NHAN)
def reception():
    # Kiểm tra giới hạn xe ngay khi vào trang
    is_limit_reached = not dao.check_limit_xe()

    # Lấy danh sách Hãng xe từ DB để Validate
    db_brands = dao.get_all_brands()
    brand_names_display = [b.ten_hieu_xe for b in db_brands]
    brand_names_lower = [b.ten_hieu_xe.lower() for b in db_brands]

    form_data = {}
    errors = {}
    db_error = None
    new_ticket = None

    if request.method == 'POST':
        form_data = request.form

        # 1. Check giới hạn lần 2
        if not dao.check_limit_xe():
            flash('Đã đạt giới hạn số lượng xe trong ngày!', 'danger')
            return redirect(url_for('main.reception'))

        # 2. Lấy dữ liệu & Chuẩn hóa
        plate = form_data.get('plate', '').strip().upper()
        phone = form_data.get('phone', '').strip()
        name = form_data.get('name', '').strip()
        brand_input = form_data.get('brand', '').strip()

        # 3. VALIDATE DỮ LIỆU

        # A. Biển số
        if not plate:
            errors['plate'] = "Vui lòng nhập biển số."
        elif dao.check_car_in_progress(plate):
            errors['plate'] = f"Xe {plate} đang sửa chữa (chưa thanh toán)."

        # B. Số điện thoại (Regex: 10 số, bắt đầu số 0)
        if not phone:
            errors['phone'] = "Vui lòng nhập SĐT."
        elif not re.match(r'^0\d{9}$', phone):
            errors['phone'] = "SĐT không hợp lệ (Phải là 10 chữ số, bắt đầu bằng 0)."

        # C. Tên khách
        if not name:
            errors['name'] = "Tên khách là bắt buộc."

        # D. Hiệu xe (Phải nằm trong danh sách DB)
        if not brand_input:
            errors['brand'] = "Vui lòng nhập hiệu xe."
        elif brand_input.lower() not in brand_names_lower:
            errors['brand'] = f"Hãng '{brand_input}' không được hỗ trợ hoặc sai chính tả."

        # 4. XỬ LÝ KẾT QUẢ
        if errors:
            flash("Dữ liệu không hợp lệ. Vui lòng kiểm tra các ô màu đỏ.", "warning")
        else:
            try:
                # Chuẩn hóa tên hãng (ví dụ: honda -> Honda)
                final_brand = brand_input.title()

                success, msg, ticket_obj = dao.create_reception(
                    phone=phone, name=name, address=form_data.get('address'),
                    plate=plate, brand=final_brand, issue=form_data.get('issue')
                )

                if success:
                    flash(msg, 'success')
                    new_ticket = ticket_obj  # Gửi object phiếu xuống để hiện Modal In
                    form_data = {}  # Reset form
                else:
                    db_error = msg  # Lỗi logic DB (nhưng kết nối ok)

            except Exception as e:
                # Lỗi mất kết nối CSDL
                db_error = "Mất kết nối với cơ sở dữ liệu! Vui lòng kiểm tra lại."
                print(f"SYSTEM ERROR: {e}")

    # Render template
    return render_template('reception.html',
                           tickets=dao.get_today_receptions(),
                           limit_reached=is_limit_reached,
                           form_data=form_data,
                           errors=errors,
                           db_error=db_error,
                           new_ticket=new_ticket,
                           valid_brands=brand_names_display)


# --- CÁC ROUTE KHÁC ---

@main.route('/repair', methods=['GET', 'POST'])
@role_required(UserRole.ADMIN, UserRole.KY_THUAT)
def repair():
    pid = request.args.get('id')
    ticket = dao.db.session.get(PhieuTiepNhan, pid) if pid else None
    if request.method == 'POST':
        labor = float(request.form.get('labor', 0))
        cart = session.get('cart', {})
        ok, msg = dao.create_repair_ticket(pid, current_user.id, cart, labor)
        if ok:
            session['cart'] = {}
            flash('Đã lưu phiếu sửa chữa', 'success')
            return redirect(url_for('main.index'))
        flash(msg, 'danger')
    return render_template('repair.html', ticket=ticket)


@main.route('/api/parts')
def api_parts():
    parts = dao.get_parts(request.args.get('kw'))
    return jsonify([{'id': p.id, 'ten': p.ten, 'gia': p.don_gia, 'ton': p.so_luong_ton} for p in parts])


@main.route('/api/cart', methods=['POST'])
def add_cart():
    data = request.json
    cart = session.get('cart', {})
    if str(data['id']) in cart:
        cart[str(data['id'])]['quantity'] += 1
    else:
        cart[str(data['id'])] = {'id': data['id'], 'name': data['name'], 'price': data['price'], 'quantity': 1}
    session['cart'] = cart
    return jsonify(cart)


@main.route('/payment', methods=['GET', 'POST'])
@role_required(UserRole.ADMIN, UserRole.THU_NGAN)
def payment():
    if request.method == 'POST':
        try:
            dao.process_payment(request.form['repair_id'], current_user.id)
            flash('Thanh toán OK', 'success')
        except Exception as e:
            flash(str(e), 'danger')
        return redirect(url_for('main.payment'))
    return render_template('payment.html', list=dao.get_pending_payments())


@main.route('/report')
@role_required(UserRole.ADMIN)
def report():
    m = request.args.get('month', 12)
    y = request.args.get('year', 2025)
    data = dao.get_revenue(m, y)
    return render_template('report.html',
                           labels=[str(d[0].day) for d in data],
                           values=[d[1] for d in data], m=m, y=y)
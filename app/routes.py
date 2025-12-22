from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import dao
from app.models import PhieuTiepNhan, UserRole
from app.decorators import role_required
from datetime import datetime
import re, json

main = Blueprint('main', __name__)


@main.route("/")
def index():
    tickets = dao.get_all_recent_tickets()
    today_count = dao.count_today_receptions()
    today_str = datetime.now().strftime("Ngày %d tháng %m năm %Y")
    return render_template('index.html', tickets=tickets, today_count=today_count, today_date=today_str)


@main.route('/login', methods=['GET', 'POST'])
def login_view():
    if current_user.is_authenticated: return redirect(url_for('main.index'))
    if request.method == 'POST':
        u = dao.auth_user(request.form.get('username'), request.form.get('password'))
        if u:
            login_user(u); return redirect(url_for('main.index'))
        else:
            flash('Đăng nhập thất bại', 'danger')
    return render_template('login.html')


@main.route('/logout')
def logout_view():
    logout_user()
    return redirect(url_for('main.login_view'))


@main.route('/api/check-plate', methods=['POST'])
def check_plate_api():
    return jsonify(dao.get_car_info_by_plate(request.json.get('plate')))


@main.route('/api/check-phone', methods=['POST'])
def check_phone_api():
    return jsonify(dao.get_customer_info_by_phone(request.json.get('phone')))


@main.route('/api/parts/search')
def search_parts():
    kw = request.args.get('kw', '')
    parts = dao.get_parts(kw)
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


@main.route('/api/cart/delete', methods=['POST'])
def delete_cart_item():
    data = request.json;
    prod_id = str(data.get('id'));
    cart = session.get('cart', {})
    if prod_id in cart: del cart[prod_id]; session['cart'] = cart
    return jsonify({'success': True, 'cart': cart})


@main.route('/reception', methods=['GET', 'POST'])
@role_required(UserRole.ADMIN, UserRole.TIEP_NHAN)
def reception():
    is_limit_reached = not dao.check_limit_xe()
    db_brands = dao.get_all_brands()
    brand_names_display = [b.ten_hieu_xe for b in db_brands]
    brand_names_lower = [b.ten_hieu_xe.lower() for b in db_brands]
    form_data = {};
    errors = {};
    db_error = None;
    new_ticket = None

    if request.method == 'POST':
        form_data = request.form
        if not dao.check_limit_xe():
            flash('Đã đạt giới hạn!', 'danger');
            return redirect(url_for('main.reception'))

        plate = form_data.get('plate', '').strip().upper()
        phone = form_data.get('phone', '').strip()
        name = form_data.get('name', '').strip()
        brand_input = form_data.get('brand', '').strip()

        if not plate:
            errors['plate'] = "Nhập biển số."
        elif dao.check_car_in_progress(plate):
            errors['plate'] = f"Xe {plate} đang sửa."
        if not phone:
            errors['phone'] = "Nhập SĐT."
        elif not re.match(r'^0\d{9}$', phone):
            errors['phone'] = "SĐT sai format."
        if not name: errors['name'] = "Nhập tên."
        if not brand_input:
            errors['brand'] = "Nhập hãng."
        elif brand_input.lower() not in brand_names_lower:
            errors['brand'] = "Hãng không hợp lệ."

        if errors:
            flash("Dữ liệu lỗi.", "warning")
        else:
            try:
                success, msg, ticket_obj = dao.create_reception(
                    phone=phone, name=name, address=form_data.get('address'),
                    plate=plate, brand=brand_input.title(), issue=form_data.get('issue')
                )
                if success:
                    flash(msg, 'success'); new_ticket = ticket_obj; form_data = {}
                else:
                    db_error = msg
            except Exception as e:
                db_error = "Lỗi kết nối!"; print(f"ERROR: {e}")

    return render_template('reception.html', tickets=dao.get_today_receptions(), limit_reached=is_limit_reached,
                           form_data=form_data, errors=errors, db_error=db_error, new_ticket=new_ticket,
                           valid_brands=brand_names_display)


@main.route('/technician/dashboard')
@role_required(UserRole.ADMIN, UserRole.KY_THUAT)
def tech_dashboard():
    return render_template('tech_dashboard.html', tickets=dao.get_list_waiting_repair())


@main.route('/repair', methods=['GET', 'POST'])
@role_required(UserRole.ADMIN, UserRole.KY_THUAT)
def repair():
    pid = request.args.get('id')
    if not pid: flash('Chọn xe trước.', 'warning'); return redirect(url_for('main.tech_dashboard'))

    ticket = dao.get_reception_by_id(pid)
    if not ticket: flash('Phiếu không tồn tại.', 'danger'); return redirect(url_for('main.tech_dashboard'))

    if request.method == 'POST':
        try:
            items = json.loads(request.form.get('items_json') or '[]')
            labor = float(request.form.get('labor_cost', 0))
            action = request.form.get('action')
            if not items and labor == 0:
                flash("Nhập liệu!", "warning")
            else:
                ok, msg = dao.save_repair_ticket_v2(pid, current_user.id, items, labor, action)
                if ok:
                    session['cart'] = {}; flash(msg, 'success'); return redirect(url_for('main.tech_dashboard'))
                else:
                    flash(msg, 'danger')
        except Exception as e:
            flash(f"Lỗi: {e}", "danger")

    return render_template('repair.html', ticket=ticket, cart=session.get('cart', {}))


@main.route('/payment', methods=['GET', 'POST'])
@role_required(UserRole.ADMIN, UserRole.THU_NGAN)
def payment():
    if request.method == 'POST':
        try:
            dao.process_payment(request.form['repair_id'], current_user.id); flash('Thanh toán OK', 'success')
        except Exception as e:
            flash(str(e), 'danger')
        return redirect(url_for('main.payment'))
    return render_template('payment.html', list=dao.get_pending_payments())


@main.route('/report')
@role_required(UserRole.ADMIN)
def report():
    m = request.args.get('month', 12);
    y = request.args.get('year', 2025)
    data = dao.get_revenue(m, y)
    return render_template('report.html', labels=[str(d[0].day) for d in data], values=[d[1] for d in data], m=m, y=y)

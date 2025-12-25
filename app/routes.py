from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import dao
from app.models import PhieuTiepNhan, UserRole
from app.decorators import role_required
from datetime import datetime
import re, json
import csv
from io import StringIO
from flask import make_response

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
            login_user(u);
            return redirect(url_for('main.index'))
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
                    flash(msg, 'success');
                    new_ticket = ticket_obj;
                    form_data = {}
                else:
                    db_error = msg
            except Exception as e:
                db_error = "Lỗi kết nối!";
                print(f"ERROR: {e}")
    max_xe = dao.get_daily_limit()
    return render_template('reception.html', tickets=dao.get_today_receptions(), max_xe=max_xe,
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
    if not pid:
        flash('Chọn xe trước.', 'warning')
        return redirect(url_for('main.tech_dashboard'))

    ticket = dao.get_reception_by_id(pid)
    if not ticket:
        flash('Phiếu không tồn tại.', 'danger')
        return redirect(url_for('main.tech_dashboard'))

    vat_rate = dao.get_config_vat() or 0.0

    cart_data = session.get('cart', {})
    labor_cost_value = 0.0

    if request.method == 'GET' and ticket.phieu_sua_chua:
        draft = ticket.phieu_sua_chua
        labor_cost_value = draft.tien_cong
        cart_data = {}
        for ct in draft.chi_tiet:
            s_id = str(ct.linh_kien_id)
            cart_data[s_id] = {
                'id': ct.linh_kien_id,
                'name': ct.linh_kien.ten,
                'price': ct.don_gia,
                'qty': ct.so_luong,
                'max': ct.linh_kien.so_luong_ton
            }

        session['cart'] = cart_data
        flash(f"Đã tải lại bản nháp (Lần sửa cuối: {draft.ngay_sua.strftime('%H:%M %d/%m')})", "info")

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
                    if action != 'draft':
                        session['cart'] = {}
                    flash(msg, 'success')
                    return redirect(url_for('main.tech_dashboard'))
                else:
                    flash(msg, 'danger')
        except Exception as e:
            flash(f"Lỗi: {e}", "danger")

    return render_template(
        'repair.html',
        ticket=ticket,
        cart=cart_data,
        vat_rate=vat_rate,
        labor_cost=labor_cost_value
    )


@main.route('/payment', methods=['GET', 'POST'])
@role_required(UserRole.ADMIN, UserRole.THU_NGAN)
def payment():
    if request.method == 'POST':
        try:
            data = request.json
            repair_id = data.get('repair_id')
            method = data.get('method')
            discount = float(data.get('discount', 0))
            tendered = float(data.get('tendered', 0))
            manual_vat = data.get('manual_vat')

            result = dao.process_payment_advanced(
                repair_id=repair_id,
                user_id=current_user.id,
                payment_method=method,
                amount_tendered=tendered,
                discount=discount,
                manual_vat=manual_vat
            )
            return jsonify(result)
        except Exception as e:
            return jsonify({"success": False, "msg": f"Lỗi Server: {str(e)}"})

    current_vat = dao.get_config_vat()
    pending_list = dao.get_pending_payments()
    return render_template('payment.html', list=pending_list, vat_config=current_vat)


@main.route('/report')
@role_required(UserRole.ADMIN)
def report():
    report_type = request.args.get('type', 'revenue')
    now = datetime.now()
    default_start = now.replace(day=1).strftime('%Y-%m-%d')
    default_end = now.strftime('%Y-%m-%d')

    from_date = request.args.get('from_date', default_start)
    to_date = request.args.get('to_date', default_end)

    result = dao.get_report_data_by_range(from_date, to_date, report_type)

    error_msg = None
    if "error" in result:
        flash(result["error"], "danger")
        error_msg = result["error"]
        result = {"data": [], "summary": {"total": 0}}
    elif not result["data"]:
        flash("Không có dữ liệu trong khoảng thời gian này.", "warning")

    return render_template('report.html',
                           report_data=result,
                           filter={"from": from_date, "to": to_date, "type": report_type},
                           error_msg=error_msg)


@main.route('/report/export')
@role_required(UserRole.ADMIN)
def export_report():
    try:
        report_type = request.args.get('type', 'revenue')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')

        result = dao.get_report_data_by_range(from_date, to_date, report_type)

        if "error" in result or not result["data"]:
            flash("Không có dữ liệu để xuất file!", "warning")
            return redirect(url_for('main.report'))

        si = StringIO()
        si.write('\ufeff')
        cw = csv.writer(si)

        if report_type == 'revenue':
            cw.writerow(['Ngày', 'Số hóa đơn', 'Doanh thu (VNĐ)'])
            for row in result['data']:
                cw.writerow([row['label'], row['count'], "{:.0f}".format(row['value'])])
        elif report_type == 'reception':
            cw.writerow(['Ngày', 'Số lượng xe tiếp nhận'])
            for row in result['data']:
                cw.writerow([row['label'], row['value']])
        elif report_type == 'parts':
            cw.writerow(['Tên linh kiện', 'Số lượng bán', 'Tổng doanh thu (VNĐ)'])
            for row in result['data']:
                cw.writerow([row['label'], row['value'], "{:.0f}".format(row['total_money'])])
        elif report_type == 'issues':
            cw.writerow(['Tên lỗi / Tình trạng', 'Số lần gặp'])
            for row in result['data']:
                cw.writerow([row['label'], row['value']])

        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename=baocao_{report_type}_{from_date}.csv"
        output.headers["Content-type"] = "text/csv"
        return output

    except Exception as e:
        flash(f"Lỗi: {str(e)}", "danger")
        return redirect(url_for('main.report'))


@main.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password_view():
    if request.method == 'POST':
        old_pass = request.form.get('old_pass')
        new_pass = request.form.get('new_pass')
        confirm_pass = request.form.get('confirm_pass')

        if not old_pass or not new_pass or not confirm_pass:
            flash('Vui lòng nhập đầy đủ thông tin', 'warning')
        elif new_pass != confirm_pass:
            flash('Mật khẩu xác nhận không khớp', 'danger')
        else:
            success, msg = dao.change_password(current_user.id, old_pass, new_pass)
            if success:
                flash(msg, 'success')
                return redirect(url_for('main.index'))
            else:
                flash(msg, 'danger')

    return render_template('change_password.html')
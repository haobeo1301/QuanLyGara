from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import dao
from app.models import PhieuTiepNhan, UserRole
from app.decorators import role_required


main = Blueprint('main', __name__)


@main.route("/")
def index():
    return render_template('index.html')


@main.route('/login', methods=['GET', 'POST'])
def login_view():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
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


# --- QUYỀN TIẾP NHẬN ---
@main.route('/reception', methods=['GET', 'POST'])
@role_required(UserRole.ADMIN, UserRole.TIEP_NHAN)
def reception():
    if request.method == 'POST':
        if not dao.check_limit_xe():
            flash('Đã full xe hôm nay!', 'warning')
        else:
            try:
                dao.create_reception(
                    request.form['phone'], request.form['name'], request.form.get('address'),
                    request.form['plate'], request.form.get('brand'), request.form['issue']
                )
                flash('Tiếp nhận thành công', 'success')
            except Exception as e:
                flash(str(e), 'danger')
            return redirect(url_for('main.reception'))
    return render_template('reception.html', tickets=dao.get_today_receptions())


# --- QUYỀN KỸ THUẬT ---
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


# --- QUYỀN THU NGÂN ---
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


# --- QUYỀN ADMIN (Báo cáo) ---
@main.route('/report')
@role_required(UserRole.ADMIN)
def report():
    m = request.args.get('month', 12)
    y = request.args.get('year', 2025)
    data = dao.get_revenue(m, y)
    return render_template('report.html',
                           labels=[str(d[0].day) for d in data],
                           values=[d[1] for d in data], m=m, y=y)



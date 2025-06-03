from flask import Blueprint, render_template, redirect, url_for, \
                  flash, request
from flask_login import login_user, logout_user, login_required, \
                        current_user
from app.models import db, Usuario
from werkzeug.security import check_password_hash

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# ------------ login ------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home_bp.home'))

    if request.method == 'POST':
        user = Usuario.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user, remember=('remember' in request.form))
            flash('Sesión iniciada', 'success')
            next_page = request.args.get('next') or url_for('home_bp.home')
            return redirect(next_page)
        flash('Credenciales incorrectas', 'danger')

    return render_template('auth/login.html')


# ------------ logout ------------
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('auth.login'))


# ------------  decorator de rol admin ------------
from functools import wraps
from flask import abort
def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin():
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

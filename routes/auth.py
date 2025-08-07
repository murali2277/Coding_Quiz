from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.user import find_user_by_rollno, update_user_password_and_first_login, get_user_collection
from utils.password import verify_password, hash_password

auth_bp = Blueprint('auth', __name__)

ADMIN_ROLLNOS = ["714023107066", "714023107067", "714023107099", "714023107105"]

@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        rollno = request.form['rollno']
        password = request.form['password']
        user = find_user_by_rollno(rollno)
        print('User found:', user)  # Debug print
        if user:
            print('Password in DB:', user['password'])  # Debug print
            if verify_password(password, user['password']):
                print('Password check:', verify_password(password, user['password']))  # Debug print
        if user and verify_password(password, user['password']):
            session['user_id'] = str(user['_id'])
            session['rollno'] = user['rollno']
            if user.get('first_login', True):
                return redirect(url_for('auth.change_password'))
            return redirect(url_for('auth.dashboard'))
        else:
            flash('Invalid roll number or password', 'danger')
    return render_template('login.html')

@auth_bp.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session or 'rollno' not in session:
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        if new_password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('change_password.html')
        password_hash = hash_password(new_password)
        update_user_password_and_first_login(session['rollno'], password_hash)
        flash('Password changed successfully. Please login again.', 'success')
        session.clear()
        return redirect(url_for('auth.login'))
    return render_template('change_password.html')

@auth_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('dashboard.html', rollno=session.get('rollno'))

@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if 'user_id' not in session or 'rollno' not in session:
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        if new_password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('reset_password.html')
        password_hash = hash_password(new_password)
        update_user_password_and_first_login(session['rollno'], password_hash)
        flash('Password changed successfully. Please login again.', 'success')
        session.clear()
        return redirect(url_for('auth.login'))
    return render_template('reset_password.html')

@auth_bp.route('/rollno_types')
def rollno_types():
    users = list(get_user_collection().find())
    print("User count:", len(users))  # Debug print
    return '<br>'.join([str(u) for u in users])

@auth_bp.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        rollno = request.form['rollno']
        password = request.form['password']
        user = find_user_by_rollno(rollno)
        if user and rollno in ADMIN_ROLLNOS and verify_password(password, user['password']):
            session['admin'] = True
            session['admin_rollno'] = rollno
            return redirect(url_for('auth.admin_panel'))
        else:
            flash('Invalid admin credentials', 'danger')
    return render_template('admin_login.html')

@auth_bp.route('/admin_panel')
def admin_panel():
    if not session.get('admin'):
        return redirect(url_for('auth.admin_login'))
    users = list(get_user_collection().find())
    return render_template('admin_panel.html', users=users)

@auth_bp.route('/admin_reset_password/<rollno>', methods=['POST'])
def admin_reset_password(rollno):
    if not session.get('admin'):
        return redirect(url_for('auth.admin_login'))
    new_password = request.form['new_password']
    password_hash = hash_password(new_password)
    update_user_password_and_first_login(rollno, password_hash)
    flash(f'Password reset for {rollno}', 'success')
    return redirect(url_for('auth.admin_panel'))

@auth_bp.route('/admin_set_first_login/<rollno>', methods=['POST'])
def admin_set_first_login(rollno):
    if not session.get('admin'):
        return redirect(url_for('auth.admin_login'))
    get_user_collection().update_one({"rollno": rollno}, {"$set": {"first_login": True}})
    flash(f'first_login set for {rollno}', 'success')
    return redirect(url_for('auth.admin_panel'))

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

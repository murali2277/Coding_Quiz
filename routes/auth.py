from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.user import find_user_by_email
from utils.password import verify_password

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = find_user_by_email(email)
        if user and verify_password(password, user['password']):
            session['user_id'] = str(user['_id'])
            session['email'] = user['email']
            return redirect(url_for('dashboard'))  # Replace with your dashboard route
        else:
            flash('Invalid email or password', 'danger')
    return render_template('login.html')


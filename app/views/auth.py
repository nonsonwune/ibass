# app/views/auth.py
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user, login_required
from ..models.user import User
from ..forms.auth import LoginForm, SignupForm, ChangePasswordForm, ResendVerificationForm
from ..extensions import db
from ..utils.security import generate_verification_token, confirm_verification_token
from ..utils.email import send_verification_email
from sqlalchemy import func

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.admin_dashboard'))  # Fixed from admin.dashboard
        return redirect(url_for('main.home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        username = User.normalize_username(form.username.data)
        user = User.query.filter(func.lower(User.username) == username).first()
        
        if user and user.check_password(form.password.data):
            if not user.is_verified:
                flash('Please verify your email address before logging in.', 'warning')
                return redirect(url_for('auth.login'))
            
            login_user(user, remember=form.remember_me.data)
            flash('Logged in successfully.', 'success')
            
            next_page = request.args.get('next')
            if user.is_admin:
                return redirect(url_for('admin.admin_dashboard'))
            return redirect(next_page if next_page else url_for('main.home'))
            
        flash('Login unsuccessful. Please check username and password.', 'danger')
    
    return render_template('auth/login.html', form=form)

@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = SignupForm()
    if form.validate_on_submit():
        username = User.normalize_username(form.username.data)
        existing_user = User.query.filter(func.lower(User.username) == username).first()
        if existing_user:
            flash('Username already exists.', 'danger')
            return redirect(url_for('auth.signup'))

        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('auth.signup'))

        user = User(username=username, email=form.email.data)
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()

        token = generate_verification_token(user.email)
        send_verification_email(user.email, token)

        flash('Account created successfully. Please check your email to verify your account.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/signup.html', form=form)


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))

@bp.route('/verify_email/<token>')
def verify_email(token):
    try:
        email = confirm_verification_token(token)
    except:
        flash('The confirmation link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.login'))
    
    user = User.query.filter_by(email=email).first()
    if user is None:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.login'))
    
    if user.is_verified:
        flash('Account already verified. Please log in.', 'success')
    else:
        user.is_verified = 1
        db.session.commit()
        flash('Your account has been verified. You can now log in.', 'success')
    return redirect(url_for('auth.login'))

@bp.route('/resend_verification', methods=['GET', 'POST'])
def resend_verification():
    form = ResendVerificationForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and not user.is_verified:
            token = generate_verification_token(user.email)
            send_verification_email(user.email, token)
            flash('A new verification email has been sent.', 'success')
        else:
            flash('Email address is not associated with any unverified account.', 'danger')
        return redirect(url_for('auth.login'))
    return render_template('auth/resend_verification.html', form=form)

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Your password has been updated.', 'success')
            return redirect(url_for('main.profile', username=current_user.username))
        else:
            flash('Invalid current password.', 'danger')
    return render_template('auth/change_password.html', form=form)
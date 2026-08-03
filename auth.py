import psycopg2
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db

auth = Blueprint('auth', __name__)


@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not (username and password and confirm_password):
            flash("Please fill in every field.")
            return redirect(url_for('auth.signup'))

        if password != confirm_password:
            flash("Passwords don't match.")
            return redirect(url_for('auth.signup'))

        if len(password) < 8 or not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
            flash("Password must be at least 8 characters and include a letter and a number.")
            return redirect(url_for('auth.signup'))

        conn = get_db()
        cursor = conn.cursor()

        hashed_password = generate_password_hash(password)

        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, hashed_password)
            )
            conn.commit()
            conn.close()
            return redirect(url_for('auth.login'))

        except psycopg2.IntegrityError:
            conn.rollback()
            conn.close()
            flash("Username already exists. Please choose another.")
            return redirect(url_for('auth.signup'))

    return render_template('signup.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('demo'))

        flash("Invalid username or password.")
        return redirect(url_for('auth.login'))


    return render_template('login.html')


@auth.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))


@auth.route('/profile/update', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    new_username = request.form.get('username', '').strip()
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '').strip()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()

    # Require the current password before changing anything —
    # protects against someone editing a session left open on a shared machine
    if not user or not check_password_hash(user['password'], current_password):
        conn.close()
        flash("Current password is incorrect.")
        return redirect(url_for('dashboard'))

    if new_username and new_username != user['username']:
        try:
            cursor.execute(
                "UPDATE users SET username = %s WHERE id = %s",
                (new_username, session['user_id'])
            )
            session['username'] = new_username
        except psycopg2.IntegrityError:
            conn.rollback()
            conn.close()
            flash("That username is already taken.")
            return redirect(url_for('dashboard'))

    if new_password:
        cursor.execute(
            "UPDATE users SET password = %s WHERE id = %s",
            (generate_password_hash(new_password), session['user_id'])
        )

    conn.commit()
    conn.close()
    flash("Profile updated.")
    return redirect(url_for('dashboard'))
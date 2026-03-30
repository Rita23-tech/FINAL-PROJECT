from flask import flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db

auth = Blueprint('auth', __name__)


@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username and password:
            conn = get_db()
            cursor = conn.cursor()

            hashed_password = generate_password_hash(password)

            try:
                cursor.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, hashed_password)
                )
                conn.commit()
                conn.close()
                return redirect(url_for('auth.login'))

            except:
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

        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            return redirect(url_for('demo'))

        flash("Invalid username or password.")
        return redirect(url_for('auth.login'))


    return render_template('login.html')


@auth.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))

from flask import session, redirect, url_for



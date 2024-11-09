from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import os
import yaml
import random
import string
from functools import wraps

app = Flask(__name__)
app.config.from_object('config.Config')
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)


# 用户模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    expiration_date = db.Column(db.DateTime, nullable=True)
    subscription_link = db.Column(db.String(200), nullable=True, unique=True)

    def __repr__(self):
        return f"<User {self.username}>"


# 管理员验证装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash("请先登录", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if request.method == 'POST':
        if 'username' in request.form and 'password' in request.form:
            # 添加用户
            hashed_password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
            expiration_days = int(request.form.get('expiration_days', 30))
            expiration_date = datetime.now() + timedelta(days=expiration_days)
            subscription_link = generate_subscription_link()

            new_user = User(
                username=request.form['username'],
                password=hashed_password,
                expiration_date=expiration_date,
                subscription_link=subscription_link
            )
            db.session.add(new_user)
            db.session.commit()
            flash('用户已创建', 'success')

        elif 'delete_user' in request.form:
            # 删除用户
            user = User.query.get(request.form['delete_user'])
            if user:
                db.session.delete(user)
                db.session.commit()
                flash('用户已删除', 'success')

        elif 'extend_expiration' in request.form:
            # 更新用户有效期
            user = User.query.get(request.form['extend_expiration'])
            additional_days = int(request.form.get('additional_days', 0))
            if user:
                user.expiration_date += timedelta(days=additional_days)
                db.session.commit()
                flash('有效期已更新', 'success')

    users = User.query.all()
    return render_template('admin.html', users=users)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == 'admin' and request.form.get(
                'password') == 'admin_password':  # 假设密码是 'admin_password'
            session['admin_logged_in'] = True
            flash('登录成功', 'success')
            return redirect(url_for('admin'))
        else:
            flash('用户名或密码错误', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash("已退出登录", "info")
    return redirect(url_for('login'))


@app.route('/<path:subscription_link>', methods=['GET', 'POST'])
def subscription(subscription_link):
    user = User.query.filter_by(subscription_link=subscription_link).first()
    if not user:
        return "链接无效", 404

    if request.method == 'POST':
        password = request.form.get('password')
        if bcrypt.check_password_hash(user.password, password):
            if user.expiration_date < datetime.now():
                return "链接已失效", 404
            # 返回 YAML 文件内容
            return send_file('iggfeed.yaml', mimetype='application/x-yaml')
        else:
            flash("密码错误", "danger")

    return render_template('subscription.html', user=user)


def generate_subscription_link():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))


if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)

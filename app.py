from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import os
import yaml
import random
import string

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


@app.route('/admin', methods=['GET', 'POST'])
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

    users = User.query.all()
    return render_template('admin.html', users=users)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            flash('登录成功', 'success')
            return redirect(url_for('admin'))
        else:
            flash('用户名或密码错误', 'danger')
    return render_template('login.html')


@app.route('/<path:subscription_link>.yml')
def subscription(subscription_link):
    user = User.query.filter_by(subscription_link=subscription_link).first()
    if not user or user.expiration_date < datetime.now():
        return "链接已失效或无效", 404
    return send_file('iggfeed.yaml', mimetype='application/x-yaml')


def generate_subscription_link():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))


if __name__ == '__main__':
    # db.create_all()
    with app.app_context():
        db.create_all()  # 创建数据库和表
    app.run(debug=True)

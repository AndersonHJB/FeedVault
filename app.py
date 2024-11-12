from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import os
import random
import string
import qrcode
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


# 用户登录验证装饰器
def user_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_logged_in' not in session:
            flash("请先登录", "danger")
            return redirect(url_for('user_login'))
        return f(*args, **kwargs)

    return decorated_function


# 管理员登录验证装饰器
def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash("请先登录", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function

@app.route('/')
def index():
    # 定义视频列表
    videos = [
        {'id': 'Video1', 'title': '视频1', 'filename': '03-为什么代码看懂，却不会写？.mp4'},
        {'id': 'Video2', 'title': '视频2', 'filename': '03-为什么代码看懂，却不会写？.mp4'},
        {'id': 'Video3', 'title': '视频3', 'filename': '03-为什么代码看懂，却不会写？.mp4'},
    ]
    return render_template('index.html', videos=videos)


@app.route('/admin', methods=['GET', 'POST'])
@admin_login_required
def admin():
    if request.method == 'POST':
        if 'username' in request.form and 'password' in request.form:
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
            user = User.query.get(request.form['delete_user'])
            if user:
                db.session.delete(user)
                db.session.commit()
                flash('用户已删除', 'success')

        elif 'extend_expiration' in request.form:
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
        if request.form.get('username') == 'admin' and request.form.get('password') == 'admin':
            session['admin_logged_in'] = True
            flash('登录成功', 'success')
            return redirect(url_for('admin'))
        else:
            flash('用户名或密码错误', 'danger')
    return render_template('login.html')


@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            if user.expiration_date < datetime.now():
                flash('您的账户已过期，请购买', 'warning')
                return redirect(url_for('purchase'))
            else:
                session['user_logged_in'] = True
                session['user_id'] = user.id
                flash('用户登录成功', 'success')
                return redirect(url_for('subscription'))
        else:
            flash('用户名或密码错误', 'danger')
    return render_template('user_login.html')


@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    session.pop('user_logged_in', None)
    session.pop('user_id', None)
    flash("已退出登录", "info")
    return redirect(url_for('login'))


@app.route('/subscription')
@user_login_required
def subscription():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    if not user:
        return "用户不存在", 404

    if user.expiration_date < datetime.now():
        flash('您的账户已过期，请购买', 'warning')
        return redirect(url_for('purchase'))

    # 计算剩余天数
    remaining_days = (user.expiration_date - datetime.now()).days

    # 生成用户的专属订阅链接
    subscription_url = url_for('get_subscription_file', subscription_link=user.subscription_link, _external=True)

    # 生成订阅链接二维码
    qr = qrcode.make(subscription_url)
    qr_path = f"static/qrcodes/{user.subscription_link}.png"
    qr.save(qr_path)

    return render_template('subscription.html', user=user, subscription_url=subscription_url,
                           remaining_days=remaining_days, qr_path=qr_path)

@app.route('/purchase', methods=['GET', 'POST'])
def purchase():
    return render_template('purchase.html')

@app.route('/subscription/<subscription_link>.yml')
def get_subscription_file(subscription_link):
    # 验证订阅链接是否有效
    user = User.query.filter_by(subscription_link=subscription_link).first()
    if not user or user.expiration_date < datetime.now():
        return "订阅链接已失效或无效", 404

    # 返回本地的 YAML 文件
    return send_file('iggfeed.yaml', mimetype='application/x-yaml')


def generate_subscription_link():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))


if __name__ == '__main__':
    # 创建静态目录用于存储二维码图像
    os.makedirs('static/qrcodes', exist_ok=True)
    db.create_all()
    # app.run(debug=True)
    app.run()

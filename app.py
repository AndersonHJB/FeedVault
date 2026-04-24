from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from flask_apscheduler import APScheduler
from sqlalchemy import inspect, text
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
mail = Mail(app)
scheduler = APScheduler()
scheduler.init_app(app)

SUBSCRIPTION_FILE_NAME = 'AI悦创·编程1v1.yaml'
SUBSCRIPTION_FILE_PATH = os.path.join(app.root_path, SUBSCRIPTION_FILE_NAME)
SUBSCRIPTION_REFRESH_LIMIT = 2
SUBSCRIPTION_REFRESH_WINDOW_DAYS = 7
EXPIRED_USER_AUTO_DELETE_AFTER_HOURS = 12


# 用户模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    expiration_date = db.Column(db.DateTime, nullable=True)
    subscription_link = db.Column(db.String(200), nullable=True, unique=True)
    yaml_version_mtime = db.Column(db.Integer, nullable=True)
    yaml_refresh_window_start = db.Column(db.DateTime, nullable=True)
    yaml_refresh_count = db.Column(db.Integer, nullable=False, default=0)
    yaml_refresh_limit = db.Column(db.Integer, nullable=True)
    auto_deleted_at = db.Column(db.DateTime, nullable=True)

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


def ensure_database_schema():
    """兼容已有数据库，自动补齐新增字段。"""
    db.create_all()
    inspector = inspect(db.engine)
    existing_columns = {column["name"] for column in inspector.get_columns(User.__tablename__)}
    alter_statements = []

    if "yaml_version_mtime" not in existing_columns:
        alter_statements.append("ALTER TABLE user ADD COLUMN yaml_version_mtime INTEGER")
    if "yaml_refresh_window_start" not in existing_columns:
        alter_statements.append("ALTER TABLE user ADD COLUMN yaml_refresh_window_start DATETIME")
    if "yaml_refresh_count" not in existing_columns:
        alter_statements.append("ALTER TABLE user ADD COLUMN yaml_refresh_count INTEGER DEFAULT 0")
    if "yaml_refresh_limit" not in existing_columns:
        alter_statements.append("ALTER TABLE user ADD COLUMN yaml_refresh_limit INTEGER")
    if "auto_deleted_at" not in existing_columns:
        alter_statements.append("ALTER TABLE user ADD COLUMN auto_deleted_at DATETIME")

    for stmt in alter_statements:
        db.session.execute(text(stmt))
    if alter_statements:
        db.session.commit()


def get_subscription_file_mtime():
    try:
        return int(os.path.getmtime(SUBSCRIPTION_FILE_PATH))
    except OSError:
        return None


def reset_user_refresh_window(user, yaml_mtime):
    """配置文件更新时，按该版本更新时间重置 7 天窗口与次数。"""
    user.yaml_version_mtime = yaml_mtime
    user.yaml_refresh_window_start = datetime.fromtimestamp(yaml_mtime)
    user.yaml_refresh_count = 0


def get_effective_refresh_limit(user):
    refresh_limit = user.yaml_refresh_limit
    if refresh_limit is None:
        return SUBSCRIPTION_REFRESH_LIMIT
    try:
        refresh_limit = int(refresh_limit)
    except (TypeError, ValueError):
        return SUBSCRIPTION_REFRESH_LIMIT
    return refresh_limit if refresh_limit >= 0 else SUBSCRIPTION_REFRESH_LIMIT


def auto_soft_delete_expired_users():
    """把过期超过宽限期的用户标记为自动删除，保留记录用于后续恢复。"""
    now = datetime.now()
    expiration_cutoff = now - timedelta(hours=EXPIRED_USER_AUTO_DELETE_AFTER_HOURS)
    users = User.query.filter(
        User.auto_deleted_at.is_(None),
        User.expiration_date.isnot(None),
        User.expiration_date <= expiration_cutoff
    ).all()

    for user in users:
        user.auto_deleted_at = now

    if users:
        db.session.commit()

    return len(users)


def normalize_admin_view(view_name):
    if view_name == 'auto_deleted':
        return 'auto_deleted'
    return 'active'


def get_admin_view_context(view_name='active'):
    auto_soft_delete_expired_users()
    view_name = normalize_admin_view(view_name)
    active_users = User.query.filter(
        User.auto_deleted_at.is_(None)
    ).order_by(User.id.asc()).all()
    auto_deleted_users = User.query.filter(
        User.auto_deleted_at.isnot(None)
    ).order_by(User.auto_deleted_at.desc(), User.id.desc()).all()
    selected_users = auto_deleted_users if view_name == 'auto_deleted' else active_users

    return {
        'initial_view': view_name,
        'users': enumerate(selected_users, start=1),
        'active_user_count': len(active_users),
        'auto_deleted_user_count': len(auto_deleted_users),
        'default_refresh_limit': SUBSCRIPTION_REFRESH_LIMIT,
        'auto_delete_after_hours': EXPIRED_USER_AUTO_DELETE_AFTER_HOURS
    }


with app.app_context():
    ensure_database_schema()
    auto_soft_delete_expired_users()


# --------------------------------------------------
# 定时任务：发送到期用户列表给管理员
# --------------------------------------------------
def send_expired_users_email():
    """
    每次执行时，将所有已到期用户列表一次性发给管理员邮箱。
    定时由 APScheduler 驱动，不影响现有业务逻辑。
    """
    with app.app_context():
        expired_users = User.query.filter(
            User.auto_deleted_at.is_(None),
            User.expiration_date <= datetime.now()
        ).all()

        if not expired_users:
            # 没有过期用户就不发送邮件
            return

        # 邮件正文
        lines = [
            f"{u.username} | 过期于 {u.expiration_date.strftime('%Y-%m-%d %H:%M:%S')}"
            for u in expired_users
        ]
        body = "以下用户已过期：\n\n" + "\n".join(lines)

        msg = Message(
            subject=f"到期用户报告（{len(expired_users)} 人）",
            recipients=[app.config["ADMIN_EMAIL"]],
            body=body
        )
        mail.send(msg)


# --------------------------------------------------
# 注册定时任务：每 15 分钟执行一次
# 如需改成每天/每小时，请调整 trigger
# --------------------------------------------------
scheduler.add_job(
    id="expired_users_email_job",
    func=send_expired_users_email,
    trigger="interval",
    # trigger="cron",
    # hour=10,           # 10:00
    minutes=30,
    timezone="Asia/Shanghai"   # 若服务器在国内；在美西用 "America/Los_Angeles"
)


def auto_soft_delete_expired_users_job():
    with app.app_context():
        auto_soft_delete_expired_users()


scheduler.add_job(
    id="expired_users_auto_delete_job",
    func=auto_soft_delete_expired_users_job,
    trigger="interval",
    minutes=30,
    timezone="Asia/Shanghai"
)
scheduler.start()


@app.route('/')
def index():
    # 定义视频列表，新增 `video_source` 字段表示视频来源
    videos = [
        # {'id': 'Video1', 'title': 'Mac/Win教程', 'filename': '2024-11-25 20-08-50.mp4', 'source': 'local'},  # 本地视频
        # {'id': 'Video2', 'title': '视频2', 'filename': 'https://gitee.com/huangjiabaoaiyc/img/releases/download/1.1.4/03-%E4%B8%BA%E4%BB%80%E4%B9%88%E4%BB%A3%E7%A0%81%E7%9C%8B%E6%87%82%EF%BC%8C%E5%8D%B4%E4%B8%8D%E4%BC%9A%E5%86%99%EF%BC%9F.mp4', 'source': 'url'},  # 外部视频
        # {'id': 'Video3', 'title': '视频3', 'filename': '03-为什么代码看懂，却不会写？.mp4', 'source': 'local'}  # 本地视频
    ]
    return render_template('index.html', videos=videos)


@app.route('/admin', methods=['GET', 'POST'])
@admin_login_required
def admin():
    current_view = normalize_admin_view(request.form.get('current_view') or request.args.get('view'))
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

        elif 'set_refresh_limit' in request.form:
            user = User.query.get(request.form['set_refresh_limit'])
            if user:
                raw_limit = (request.form.get('custom_refresh_limit') or '').strip()
                if raw_limit == '':
                    user.yaml_refresh_limit = None
                    db.session.commit()
                    flash(f'用户 {user.username} 已恢复默认最大次数（{SUBSCRIPTION_REFRESH_LIMIT} 次）', 'success')
                else:
                    try:
                        custom_limit = int(raw_limit)
                    except ValueError:
                        flash('最大次数必须是整数', 'danger')
                    else:
                        if custom_limit < 0:
                            flash('最大次数不能小于 0', 'danger')
                        else:
                            user.yaml_refresh_limit = custom_limit
                            db.session.commit()
                            flash(f'用户 {user.username} 的最大次数已更新为 {custom_limit} 次', 'success')

        elif 'reset_refresh_counter' in request.form:
            user = User.query.get(request.form['reset_refresh_counter'])
            if user:
                yaml_mtime = get_subscription_file_mtime()
                user.yaml_refresh_count = 0
                user.yaml_refresh_window_start = datetime.now()
                if yaml_mtime is not None:
                    user.yaml_version_mtime = yaml_mtime
                db.session.commit()
                flash(f'用户 {user.username} 的刷新次数已提前重置', 'success')

        elif 'restore_auto_deleted_user' in request.form:
            user = User.query.get(request.form['restore_auto_deleted_user'])
            restore_days = int(request.form.get('restore_expiration_days', 30))
            if user and user.auto_deleted_at:
                if restore_days <= 0:
                    flash('恢复有效期天数必须大于 0', 'danger')
                else:
                    user.expiration_date = datetime.now() + timedelta(days=restore_days)
                    user.auto_deleted_at = None
                    db.session.commit()
                    flash(f'用户 {user.username} 已恢复，有效期 {restore_days} 天', 'success')

    return render_template('admin.html', **get_admin_view_context(current_view))


@app.route('/admin/users/<view_name>')
@admin_login_required
def admin_users_view(view_name):
    view_name = normalize_admin_view(view_name)
    template_name = '_admin_auto_deleted_users.html' if view_name == 'auto_deleted' else '_admin_active_users.html'
    return render_template(template_name, **get_admin_view_context(view_name))


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
        user = User.query.filter_by(username=username, auto_deleted_at=None).first()
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
    if not user or user.auto_deleted_at:
        return "用户不存在", 404

    if user.expiration_date < datetime.now():
        flash('您的账户已过期，请购买', 'warning')
        return redirect(url_for('purchase'))

    # 计算剩余天数
    remaining_days = (user.expiration_date - datetime.now()).days

    # 生成用户的专属订阅链接
    subscription_url = url_for('get_subscription_file', subscription_link=user.subscription_link, _external=True, _scheme='https')
    # print("subscription_url", subscription_url)
    # 生成订阅链接二维码
    qr = qrcode.make(subscription_url)
    qr_path = f"static/qrcodes/{user.subscription_link}.png"
    qr.save(qr_path)

    return render_template('subscription.html', user=user, subscription_url=subscription_url,
                           remaining_days=remaining_days, qr_path=qr_path)


@app.route('/purchase', methods=['GET', 'POST'])
def purchase():
    return render_template('purchase.html')


@app.route('/subscription/<subscription_link>.yaml')
def get_subscription_file(subscription_link):
    # 验证订阅链接是否有效
    user = User.query.filter_by(subscription_link=subscription_link, auto_deleted_at=None).first()
    if not user or user.expiration_date < datetime.now():
        return "订阅链接已失效或无效", 404

    yaml_mtime = get_subscription_file_mtime()
    if yaml_mtime is None:
        return "订阅配置文件不存在", 500

    now = datetime.now()
    has_state_update = False

    # 配置文件一更新，就重置该用户的 7 天窗口与请求次数。
    if user.yaml_version_mtime != yaml_mtime:
        reset_user_refresh_window(user, yaml_mtime)
        has_state_update = True

    window_start = user.yaml_refresh_window_start or datetime.fromtimestamp(yaml_mtime)
    window_end = window_start + timedelta(days=SUBSCRIPTION_REFRESH_WINDOW_DAYS)
    if now > window_end:
        if has_state_update:
            db.session.commit()
        return f"当前配置版本的刷新窗口已结束（{SUBSCRIPTION_REFRESH_WINDOW_DAYS}天），请等待配置更新后重置", 429

    current_count = user.yaml_refresh_count or 0
    refresh_limit = get_effective_refresh_limit(user)
    if current_count >= refresh_limit:
        if has_state_update:
            db.session.commit()
        return f"当前配置版本的刷新次数已达上限（{refresh_limit}次），请等待配置更新后重置", 429

    user.yaml_refresh_count = current_count + 1
    db.session.commit()

    # 返回本地的 YAML 文件
    response = make_response(send_file(SUBSCRIPTION_FILE_PATH, mimetype='application/x-yaml'))

    # 让 Clash/Meta 可读取用户专属订阅到期时间（Unix 秒级时间戳）。
    expire_ts = int(user.expiration_date.timestamp())
    response.headers['subscription-userinfo'] = f"upload=0; download=0; total=0; expire={expire_ts}"

    return response


def generate_subscription_link():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))


if __name__ == '__main__':
    # 创建静态目录用于存储二维码图像
    os.makedirs('static/qrcodes', exist_ok=True)
    with app.app_context():
        ensure_database_schema()
    # app.run(debug=True)
    # app.run()
    app.run(host="0.0.0.0", port=8990)

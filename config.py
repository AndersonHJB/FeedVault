import os

class Config:
    SECRET_KEY = os.urandom(24)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ---- New ----  邮件发送相关 -----------------------
    # 把下面四项改成自己的 SMTP 信息；也可以放到环境变量
    MAIL_SERVER = 'smtp.qq.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'MAIL_USERNAME'
    MAIL_PASSWORD = 'MAIL_PASSWORD'
    MAIL_DEFAULT_SENDER = ("AI悦创系统", MAIL_USERNAME)

    # 接收到期提醒的管理员邮箱
    ADMIN_EMAIL = 'ADMIN_EMAIL'

    # ---- New ----  APScheduler（定时任务）开关 -------
    SCHEDULER_API_ENABLED = True

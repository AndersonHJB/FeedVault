import os

class Config:
    SECRET_KEY = os.urandom(24)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

SERVER_NAME = 'fv.bornforthis.cn'
PREFERRED_URL_SCHEME = 'https'

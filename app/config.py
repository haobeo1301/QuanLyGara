import os


class Config:
    # Kết nối MySQL: suaxedb
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:123456@localhost/suaxedb?charset=utf8mb4'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'DEV_KEY_123456'  # Nên đổi khi deploy
    PAGE_SIZE = 10

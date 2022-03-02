import os


basedir = os.path.abspath(os.path.dirname(__file__))  # generally used to tell flask where to put our sqlite. But here we use postgres


class Config(object):
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", '')  # , "sqlite://")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from common.config import settings

# MySQL は wait_timeout を過ぎたアイドルの接続を切る。切れた接続をプールから渡すと、間が空いた後の最初の要求が失敗する
engine = create_engine(settings.database_url, hide_parameters=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import DATABASE_URL


class Base(DeclarativeBase):
    pass


class DramaSeries(Base):
    __tablename__ = "drama_series"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Identity
    series_id = Column(String(64), nullable=False, index=True)
    genre_type = Column(String(32), nullable=False)
    category = Column(String(32), nullable=False)

    # Ranking context
    rank_order = Column(Integer, nullable=True)

    # From ranking API
    title = Column(String(255), nullable=False)
    cover_url = Column(Text, nullable=True)
    episode_cnt = Column(Integer, nullable=True)
    play_cnt = Column(BigInteger, nullable=True)
    score = Column(String(32), nullable=True)
    video_desc = Column(Text, nullable=True)
    vid = Column(String(64), nullable=True)

    # Parsed from recommend_reason_list
    hot_score = Column(Float, nullable=True)
    hot_content = Column(String(255), nullable=True)
    hot_content_value = Column(BigInteger, nullable=True)

    # From detail API
    author = Column(String(255), nullable=True)
    copyright = Column(String(255), nullable=True)
    duration = Column(String(64), nullable=True)
    detail_category = Column(String(255), nullable=True)
    detail_desc = Column(Text, nullable=True)
    book_pic = Column(Text, nullable=True)
    total_episodes = Column(Integer, nullable=True)

    # Debug
    raw_recommend_reason = Column(Text, nullable=True)

    # Status
    detail_fetched = Column(Boolean, default=False)
    episodes_fetched = Column(Boolean, default=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("series_id", "genre_type", "category", name="uq_series_genre_cat"),
    )


class DramaEpisode(Base):
    __tablename__ = "drama_episodes"

    id = Column(Integer, primary_key=True, autoincrement=True)

    series_id = Column(String(64), nullable=False, index=True)
    video_id = Column(String(64), nullable=False)

    episode_no = Column(Integer, nullable=True)
    episode_title = Column(String(128), nullable=True)
    first_pass_time = Column(String(64), nullable=True)

    # Object storage upload result
    quality = Column(String(16), nullable=True)
    origin_url_fetched_at = Column(DateTime, nullable=True)
    origin_expire_time = Column(String(64), nullable=True)
    upload_status = Column(String(32), default="pending")
    object_storage_url = Column(Text, nullable=True)
    object_key = Column(Text, nullable=True)
    file_size = Column(BigInteger, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("video_id", name="uq_video_id"),
    )


engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()

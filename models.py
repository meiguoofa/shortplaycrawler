from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
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


class DailyNewDrama(Base):
    """一部当日上新的剧（来自 shangxinrili_hg 接口）。"""

    __tablename__ = "daily_new_dramas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    series_id = Column(String(64), nullable=False, index=True)
    fetch_date = Column(Date, nullable=False, index=True)

    # From shangxinrili_hg response
    title = Column(String(255), nullable=False)
    cover_url = Column(Text, nullable=True)
    episode_cnt = Column(Integer, nullable=True)
    category = Column(String(64), nullable=True)  # from sub_title_list[0].content

    # Filled by detail_hg follow-up
    author = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Original raw JSON for debugging
    raw_payload = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("series_id", "fetch_date", name="uq_daily_series_date"),
    )


class EpisodeAsset(Base):
    """某部 daily-new-drama 的某一集视频在 TOS 中的位置。"""

    __tablename__ = "episode_assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    daily_new_drama_id = Column(Integer, ForeignKey("daily_new_dramas.id"), nullable=False, index=True)
    video_id = Column(String(64), nullable=False, index=True)
    episode_no = Column(Integer, nullable=True)
    episode_title = Column(String(128), nullable=True)

    object_key = Column(Text, nullable=True)
    object_url = Column(Text, nullable=True)
    file_size = Column(BigInteger, nullable=True)

    status = Column(String(32), default="pending")  # pending/uploaded/failed
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class TranslationJob(Base):
    """对一部 daily-new-drama 做某语言的翻译+海报重绘任务。"""

    __tablename__ = "translation_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    daily_new_drama_id = Column(Integer, ForeignKey("daily_new_dramas.id"), nullable=False, index=True)
    target_lang = Column(String(16), nullable=False, index=True)  # en/zh/pt/pt-BR/id

    image_model = Column(String(64), nullable=True)
    image_prompt = Column(Text, nullable=True)  # backward-compat: same as image_prompt_final
    image_prompt_template = Column(Text, nullable=True)  # editable template (with {target_lang}/{synopsis})

    # Translation prompts (editable templates + final substituted values)
    translate_system_prompt = Column(Text, nullable=True)  # template
    translate_user_prompt = Column(Text, nullable=True)  # template
    translate_system_prompt_final = Column(Text, nullable=True)  # final substituted
    translate_user_prompt_final = Column(Text, nullable=True)  # final substituted

    status = Column(String(32), default="pending")  # pending/translating/poster_generating/processing_episodes/done/failed
    translated_title = Column(String(255), nullable=True)
    translated_desc = Column(Text, nullable=True)

    poster_object_key = Column(Text, nullable=True)
    poster_object_url = Column(Text, nullable=True)

    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    batch_id = Column(String(36), nullable=True, index=True)

    # Screenshot + description (Step 4) - nullable for backward compat with old jobs
    desc_lang = Column(String(16), nullable=True)  # ISO code for image descriptions
    desc_model = Column(String(64), nullable=True)  # vision model name
    desc_prompt_template = Column(Text, nullable=True)  # editable template (with {target_lang})
    desc_prompt_final = Column(Text, nullable=True)  # final substituted

    __table_args__ = (
        UniqueConstraint("daily_new_drama_id", "target_lang", name="uq_drama_lang"),
    )


class DramaScreenshot(Base):
    """某部 TranslationJob 的某集某位置的截图 + 大模型描述。"""

    __tablename__ = "drama_screenshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    translation_job_id = Column(Integer, ForeignKey("translation_jobs.id"), nullable=False, index=True)
    daily_new_drama_id = Column(Integer, ForeignKey("daily_new_dramas.id"), nullable=False, index=True)
    episode_no = Column(Integer, nullable=False)
    position_index = Column(Integer, nullable=False)  # 0 or 1 (对应 SCREENSHOT_POSITIONS 索引)
    position_ratio = Column(Float, nullable=False)    # 1/3 or 2/3

    object_key = Column(Text, nullable=True)
    object_url = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    status = Column(String(32), default="pending")  # pending/uploaded/described/failed
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("translation_job_id", "episode_no", "position_index", name="uq_job_ep_pos"),
    )


class CartItem(Base):
    """用户从搜索结果加入待处理清单的剧（购物车项）。"""

    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    series_id = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    cover_url = Column(Text, nullable=True)
    episode_cnt = Column(Integer, nullable=True)
    category = Column(String(255), nullable=True)
    author = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    raw_payload = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("series_id", name="uq_cart_series"),
    )


from sqlalchemy import event as _sa_event
from sqlalchemy import inspect as _sa_inspect
from sqlalchemy import text as _sa_text

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False, "timeout": 30},
    pool_pre_ping=True,
)


@_sa_event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


SessionLocal = sessionmaker(bind=engine)


def _migrate_translation_jobs_add_desc_columns() -> None:
    """SQLite 不支持 IF NOT EXISTS ADD COLUMN；用 inspect 检查后幂等 ALTER。

    只追加列，不修改/删除已有数据。CLAUDE.md：严禁清除数据库数据。
    """
    insp = _sa_inspect(engine)
    if "translation_jobs" not in insp.get_table_names():
        return  # 表还没建，create_all 会处理
    existing_cols = {c["name"] for c in insp.get_columns("translation_jobs")}
    additions = [
        ("desc_lang", "VARCHAR(16)"),
        ("desc_model", "VARCHAR(64)"),
        ("desc_prompt_template", "TEXT"),
        ("desc_prompt_final", "TEXT"),
    ]
    with engine.begin() as conn:
        for name, typ in additions:
            if name not in existing_cols:
                conn.execute(_sa_text(f"ALTER TABLE translation_jobs ADD COLUMN {name} {typ}"))


def init_db():
    Base.metadata.create_all(engine)
    _migrate_translation_jobs_add_desc_columns()


def get_session():
    return SessionLocal()

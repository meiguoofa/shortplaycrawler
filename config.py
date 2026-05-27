import os

# Load .env file if exists
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

# API
CRAWL_CODE = "FXKBAGV5OJQH"
RANKING_BASE_URL = "http://43.142.49.190:1789/tool/duanju/hg/%E6%8E%92%E8%A1%8C%E6%A6%9C/%E7%AD%9B%E9%80%89%E8%BF%9B%E5%85%A5.php"
DETAIL_URL = "http://160.202.253.154:1231/api/hg/wai_api_detail.php"
EPISODES_URL = "http://160.202.253.154:1231/api/hg/wai_api_book.php"
PLAY_URL = "http://43.142.49.190:1789/api/g/gui_play.php"

# 6 ranking lists
RANKING_LISTS = [
    {"genre_type": "漫剧", "genre": "comic_series", "category": "奇幻", "cate": "cate_6"},
    {"genre_type": "漫剧", "genre": "comic_series", "category": "玄幻", "cate": "cate_7"},
    {"genre_type": "漫剧", "genre": "comic_series", "category": "豪门", "cate": "cate_936"},
    {"genre_type": "AI短剧", "genre": "ai_series", "category": "奇幻", "cate": "cate_6"},
    {"genre_type": "AI短剧", "genre": "ai_series", "category": "玄幻", "cate": "cate_7"},
    {"genre_type": "AI短剧", "genre": "ai_series", "category": "豪门", "cate": "cate_936"},
]

# Rate limiting
DEFAULT_SLEEP = 0.5
PLAY_URL_SLEEP = 2.0
MAX_RETRIES = 3

# Crawl settings
DEFAULT_LIMIT = 100
VIDEO_QUALITY = "720p"

# Database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'data', 'crawl.db')}"

# Object Storage - Volcengine TOS (S3 compatible)
TOS_CONFIG = {
    "endpoint_url": os.environ.get("TOS_ENDPOINT_URL", "https://tos-s3-cn-shanghai.volces.com"),
    "region": os.environ.get("TOS_REGION", "cn-shanghai"),
    "bucket": os.environ.get("TOS_BUCKET", "duanju123123"),
    "access_key_id": os.environ.get("TOS_ACCESS_KEY_ID", ""),
    "secret_access_key": os.environ.get("TOS_SECRET_ACCESS_KEY", ""),
    "public_base_url": os.environ.get("TOS_PUBLIC_BASE_URL", "https://duanju123123.tos-cn-shanghai.volces.com"),
}

# Download/Upload concurrency per series
DOWNLOAD_CONCURRENCY = 10

# veFaaS cloud function URL for internal TOS transfer
# Deploy vefaas/tos_transfer.py to veFaaS, then paste the trigger URL here
VEFAAS_URL = ""

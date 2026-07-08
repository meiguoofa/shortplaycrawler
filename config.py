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
CRAWL_CODE = os.environ.get("CRAWL_CODE", "")
RANKING_BASE_URL = "http://36.138.76.25:4455/tool/duanju/hg/%E6%8E%92%E8%A1%8C%E6%A6%9C/%E7%AD%9B%E9%80%89%E8%BF%9B%E5%85%A5.php"
DETAIL_URL = "http://36.138.76.25:4455/api/api.php?platform=wpf11&action=detail_hg"
EPISODES_URL = "http://36.138.76.25:4455/api/api.php?platform=wpf11&action=book_hg"
PLAY_URL = "http://36.138.76.25:4455/api/api.php?platform=wpf11&action=play_hg"

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
# Per-drama episode upload concurrency in pipeline (5 = 5 episodes in parallel)
EPISODE_UPLOAD_CONCURRENCY = 5
# Per-batch drama concurrency — how many dramas run pipeline in parallel
DRAMA_PIPELINE_CONCURRENCY = 10

# veFaaS cloud function URL for internal TOS transfer
# Deploy vefaas/tos_transfer.py to veFaaS, then paste the trigger URL here
VEFAAS_URL = ""

# ── Daily new drama + translation + poster regeneration ──
DAILY_NEW_URL = "http://36.138.76.25:4455/api/api.php?platform=wpf11&action=shangxinrili_hg"
DAILY_NEW_CRON_HOUR = 9  # Beijing time
DAILY_NEW_TIMEZONE = "Asia/Shanghai"

# Search (aggregated across 5 platforms)
SEARCH_API_BASE = "http://36.138.76.25:4455/api/api.php"
SEARCH_PLATFORMS = [
    {"action": "search_hg",    "platform": "hg",            "label": "红果短剧"},
    {"action": "search_dm_hg", "platform": "hgmj",          "label": "红果漫剧"},
    {"action": "search_hm",    "platform": "hm",            "label": "河马短剧"},
    {"action": "search_hl",    "platform": "huolong",       "label": "火龙漫剧"},
    {"action": "search_dl",    "platform": "xingyadongli",  "label": "星芽/东梨短剧"},
]

# Doubao (translation + image gen) via Volcengine ARK (OpenAI-compatible)
DOUBAO_API_KEY = os.environ.get("DOUBAO_API_KEY", "")
DOUBAO_BASE_URL = os.environ.get("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
DOUBAO_TRANSLATE_MODEL = os.environ.get("DOUBAO_TRANSLATE_MODEL", "doubao-seed-2-0-pro-260215")
DOUBAO_TRANSLATE_MODELS = [
    "doubao-seed-2-0-pro-260215",
]

# Mobinova chat models for translation (gpt-5.4 etc.)
MOBINOVA_CHAT_BASE_URL = "https://mobinova.cc/v1"
MOBINOVA_CHAT_API_KEY = os.environ.get("MOBINOVA_CHAT_API_KEY", "")
MOBINOVA_TRANSLATE_MODEL = os.environ.get("MOBINOVA_TRANSLATE_MODEL", "gpt-5.4")
MOBINOVA_TRANSLATE_MODELS = [
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.5",
]
MOBINOVA_DEFAULT_TRANSLATE_MODEL = "gpt-5.4"
DOUBAO_IMAGE_MODELS = [
    "doubao-seedream-5-0-260128",
    "doubao-seedream-4-5-251128",
    "doubao-seedream-4-0-250828",
]
DOUBAO_DEFAULT_IMAGE_MODEL = "doubao-seedream-4-0-250828"
DEFAULT_IMAGE_MODEL = "openai/gpt-image-2"  # 全局默认生图模型（UI 默认选这个）
DOUBAO_IMAGE_SIZE = "1536x2048"  # 3:4 竖版海报 (was 2048x2048)

# Mobinova gpt-image-2 (OpenAI-compatible, text-to-image + edits, supports reference image)
MOBINOVA_API_KEY = os.environ.get("MOBINOVA_API_KEY", "")
MOBINOVA_BASE_URL = "https://image.mobinova.cc/v1"
MOBINOVA_IMAGE_MODEL = "openai/gpt-image-2"
MOBINOVA_IMAGE_SIZE = "1024x1536"  # 3:4 竖版

# Translation target languages (ISO code → display name shown to LLM)
TRANSLATE_LANGS = {
    "en":    "English",
    "zh":    "中文",
    "pt":    "Português",
    "pt-BR": "Português (Brasil)",
    "id":    "Bahasa Indonesia",
}

# Image generation default prompt (user-editable on web; {target_lang} and {synopsis} are substituted at run time)
DEFAULT_IMAGE_GEN_PROMPT = (
    "以这张封面作为参考图片，保留原图中人物面部特征不变，"
    "将图中的文字替换为{target_lang}，"
    "结合目标语言国家（{target_lang}）的文化特点和剧情简介({synopsis})，"
    "更换服装和场景，生成新的海报图片。"
)

# Translation prompts (user-editable on web; {target_lang}/{title}/{description} substituted at run time)
DEFAULT_TRANSLATE_SYSTEM_PROMPT = (
    "你是专业的本地化翻译。请把用户给的中文剧名和简介翻译成{target_lang}。"
    "严格按格式输出两行：\nTITLE=<译文剧名>\nDESC=<译文简介>\n不要输出任何其他内容。"
)
DEFAULT_TRANSLATE_USER_PROMPT = "剧名：{title}\n简介：{description}"

# TOS object key prefix for generated posters
TOS_IMAGE_OBJECT_PREFIX = "posters"

# Export dir for CSV/Excel
EXPORT_DIR = os.path.join(BASE_DIR, "data", "exports")

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="短剧数据")

# Serve static files (vendor JS, app.js, etc.)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

from web.routes import router
app.include_router(router)

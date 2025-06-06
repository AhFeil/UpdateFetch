import os
from typing import Annotated, Literal, Optional

from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import preprocess
from AutoCallerFactory import AllocateDownloader

app = FastAPI()
templates = Jinja2Templates(directory='templates')
allocate_downloader = AllocateDownloader(preprocess.data, preprocess.config.temp_download_dir)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    context = {"categories": preprocess.data.categories}
    return templates.TemplateResponse(request=request, name="index.html", context=context)

class FilterParams(BaseModel):
    name: str
    platform: Optional[Literal["android", "windows", "linux"]] = "linux"
    arch: Optional[Literal["arm64", "amd64"]] = "amd64"

@app.get("/download/")
async def download(params: Annotated[FilterParams, Query()]):
    situation = preprocess.data.get_item_situation(params.name, params.platform, params.arch)
    if not situation:
        raise HTTPException(status_code=404, detail="Resource not found")
    fp = await allocate_downloader.get_file(situation)
    if not fp:
        raise HTTPException(status_code=503, detail="Resource temporarily unavailable")
    return FileResponse(path=fp, filename=os.path.basename(fp))

@app.get("/favicon.ico")
async def favicon():
    fp = "static/favicon.ico"
    return FileResponse(path=fp, filename=os.path.basename(fp))


from enum import Enum

class AdditionalPage(Enum):
    robots = "robots.txt"
    sitemap = "sitemap.xml"

# 缓存 todo
@app.get("/{file}", response_class=PlainTextResponse)
async def static_from_root(file: AdditionalPage):
    with open(os.path.join("templates", file.value), 'r', encoding="utf-8") as f:
        content = f.read()
    return content


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=7500)

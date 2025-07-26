import os
from pathlib import Path
from enum import Enum
from typing import Annotated, Literal, Optional

from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import preprocess
from AutoCallerFactory import AllocateDownloader
from dataHandle import ItemLocation

app = FastAPI()
templates = Jinja2Templates(directory='templates')
allocate_downloader = AllocateDownloader(preprocess.data, preprocess.config.temp_download_dir)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    context = {"categories": preprocess.data.categories}
    return templates.TemplateResponse(request=request, name="index.html", context=context)


class ItemLocationFilter(BaseModel):
    name: str
    platform: Optional[Literal["android", "windows", "linux"]] = "linux"
    arch: Optional[Literal["arm64", "amd64"]] = "amd64"

    def to_item_location(self) -> ItemLocation:
        return ItemLocation(self.name, self.platform, self.arch)


@app.get("/download/")
async def download(params: Annotated[ItemLocationFilter, Query()]):
    situation = preprocess.data.get_item_situation(params.to_item_location())
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



class AdditionalPage(Enum):
    robots = "robots.txt"
    sitemap = "sitemap.xml"

additional_pages = {
    item.value: Path(f"templates/{item.value}").read_text(encoding="utf-8")
    for item in AdditionalPage
}

@app.get("/{file}", response_class=PlainTextResponse)
async def static_from_root(file: AdditionalPage):
    return additional_pages[file.value]


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=7500)

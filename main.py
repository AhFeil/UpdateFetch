import os

from fastapi import FastAPI
from fastapi.responses import FileResponse

from AutoCallerFactory import AllocateDownloader
import preprocess
config = preprocess.config
data = preprocess.data
allocate_downloader = AllocateDownloader(config.temp_download_dir, data.version_data, config.GithubAPI)

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/download/")
async def download(name: str, platform: str, arch: str):
    item = data.get_items().get(name)
    if not item:
        return {"state": "no item"}
    filepath = await allocate_downloader.get_file(item, name, platform, arch)
    if not filepath:
        return {"name": name, "platform": platform, "arch": arch}
    return FileResponse(path=filepath, filename=os.path.basename(filepath))


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=7500)

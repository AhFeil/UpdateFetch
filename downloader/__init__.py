from .AbstractClass import APILimitException, NotFound
from .Github import GithubDownloader
from .FDroid import FDroidDownloader
from .Only1Link import Only1LinkDownloader

downloader_classes = {
    "github": GithubDownloader,
    "fdroid": FDroidDownloader,
    "only1link": Only1LinkDownloader
}

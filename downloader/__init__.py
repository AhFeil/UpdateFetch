from .AbstractClass import APILimitException, NotFound
from .GithubDownloader import GithubDownloader
from .FDroidDownloader import FDroidDownloader

downloader_classes = {
    "github": GithubDownloader,
    "fdroid": FDroidDownloader,
    # "only1link": Only1LinkDownloader
}

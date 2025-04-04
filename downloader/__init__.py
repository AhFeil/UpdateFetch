from .AbstractClass import APILimitException 
from .GithubDownloader import GithubDownloader

downloader_classes = {
    "github": GithubDownloader, 
    # "fdroid": FDroidDownloader, 
    # "only1link": Only1LinkDownloader
}

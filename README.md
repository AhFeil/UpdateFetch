# UpdateFetch

根据下载项配置文件，定期检查和下载软件的最新版，方便在特殊网络环境中下载软件，配合 UpdateFetchWeb 更方便使用。

创建这个项目的需求动力是在“长城防火墙”下，国内机子想装个 serverstatus 探针都要梯子，虽然可以手动上传，但是不方便写脚本。后来又发现这个项目还方便给其他人分享 GitHub 上的好用 APP 等，他们也方便自行更新软件，于是又写了 UpdateFetchWeb 作为前端。


## 功能

1. 方便在国内直接下载软件，如 xray、serverstatus-rust ，不用每次都加代理
2. 方便给一般用户分享软件，以及方便他们更新，如 Bitwarden 、Element


## 思路


一句话介绍：**程序每天检查一次所有下载项是否有更新，如果有新的版本，就下载并上传到指定目录，给出下载链接**。


程序结构：
1. preprocess.py, configHandle.py, dataHandle.py。加载配置和数据的，对应配置文件是 config.yaml，对应的数据目录是 data
2. update_fetch.py，主程序；run_as_scheduled.py，在主程序基础上加上定期运行
3. AutoCallerFactory.py。调度下载器的，
4. AbstractClass.py, ConcreteClass.py 类，下载器和上传器。ConcreteClass 中，为不同网站编写不同的下载器，上传器只有 MinIO 一种
5. apiHandle.py。上传数据到 UpdateFetchWeb


data 目录:
1. items.yaml，下载项配置文件
2. retained_version，如果有保留特定版本的需求，可以手动修改，防止在更新时，把旧版本删除。

3. versoin_deque.json，保留已下载的版本，用于自动清除旧版本
4. version，保留最新版的版本，用于比对这次运行检测的最新版是否已经下载
5. latest_link.json，保存下载项最新版本的下载链接

---


程序一次只处理一个下载项，因此下载项应该相互独立。下载项可能有多个版本，不同平台（Windows、Linux、Android）和 CPU 架构（AMD64、ARM64）的组合。


## 管理员


config.yaml 示例

```yaml
is_production: true
curl_path: curl         # curl 二进制程序的路径
minio_server: 185.149.146.103:9000   # minio 服务端的 API 地址，必须是这种形式，可以用域名，但不能带 http 
minio_client_path: mc   # mc 二进制程序的路径
minio_host_alias: uf    # mc 添加主机时的 ALIAS
bucket: updatefetch     # mc 上传时，要放到哪个 bucket

# GitHub API ，解除查找最新版本时的请求限制。如果不了解，可删除
X-GitHub-Api-Version: "2022-11-28"
Authorization: "Bearer github_pat_11xxxxxxkBbu0_mfgypv21NLBCxxxxxxxxxxxxxxxxxxxxxxxxxxxxxbQTWJA1"

# 与 UpdateFetchWeb 相关的，若删除则不进行与 web 的交互，不影响本程序自身功能
web_domain: http://185.149.146.103:7699/   # 最后必须带 /
web_Token: Token b8xxxxxxxxxxxxxxxxxxxxxxxxx40f142
category_default_title: Uncategorized   # 这个必须填
## 下面是默认图片和项目主页，可删除
default_image: https://ib.ahfei.blog:443/imagesbed/undefined_image_url_200-24-01-05.webp
default_website: https://github.com/AhFeil/updatefetchWeb
```


安装步骤在博客： **等待写文章**


## 使用




### 下载项配置文件


为了方便管理，本项目会重命名下载后的文件，格式为： **软件名-系统-架构-版本.后缀名**，每个部分用 `-` 连接，因此软件名不能带有 - ，会导致程序出错。


*GitHub 网站 release 下载*

> 本项目最初参考 Linux 下的自动下载最新版的 shell 脚本，因此 GitHub 下载器是模仿这种脚本思路来的


```yaml
# 以 xray 为例
xray_binary:   # 下载项的名称，在上传时，会创建同名目录；以及在下载器会用到
  name: xray   # 软件名，用于重命名下载后的文件，推荐全小写，不能带有 - 
  category_title: Server
  image: https://ib.ahfei.blog/imagesbed/xray_logo_cpd-24-01-03.webp
  website: github   # 用哪个下载器
  project_name: XTLS/Xray-core   # 项目名称
  sample_url: https://github.com/XTLS/Xray-core/releases/download/${tag}/Xray-${system}-${ARCHITECTURE}${suffix_name}   # release 中的下载链接，${} 包裹的在下载时会被替换成实际值
  system:   # 软件要下载哪些系统的，左边是用于重命名的标准名称，右边的列表里，左项是 sample_url 中应该实际填写的，右边是对应的后缀名
    windows: [windows, .zip]
    linux: [linux, .zip]
  architecture:   # 软件要下载哪些架构的，左边是用于重命名的标准名称，右边是 sample_url 中应该实际填写的
    arm64: arm64-v8a
    amd64: '64'

# 最终，下载器会组合出 4 个下载链接，并下载，假设查到的最新版是 v1.8.7， 4 个网址分别是
# https://github.com/XTLS/Xray-core/releases/download/v1.8.7/Xray-windows-arm64-v8a.zip
# https://github.com/XTLS/Xray-core/releases/download/v1.8.7/Xray-windows-64.zip
# https://github.com/XTLS/Xray-core/releases/download/v1.8.7/Xray-linux-arm64-v8a.zip
# https://github.com/XTLS/Xray-core/releases/download/v1.8.7/Xray-linux-64.zip
```

category_title、image 是 UpdateFetchWeb 会用到的，可以省略。

对于 GitHub，sample_url 前面一部分是一样的，因此有一种简写形式 `~/${tag}/Xray-${system}-${ARCHITECTURE}${suffix_name}`


> tag 切片。如果 GitHub 某项目的 tag 是这种 desktop-v2023.12.1，但实际文件名要的是 2023.12.1，可以使用切片取 tag 的一部分，出于代码的简便起见，不支持 `[9:]` 这种写法，而是 `[9:18]` 不能有空的，两边都要有数字，不检查是否合法。由于左闭右开，要填 18，而不是 17。


---

*FDroid 下载*

> 下面的介绍中，省略同作用的字段

```yaml
SchildChat:
  name: schildchat
  website: fdroid
  project_name: de.spiritcroc.riotx   # 这个到软件在 FDroid 网站的页面，其网址最后一部分就是
  # 因为 FDroid 上都是安卓平台的 APP，因此不必填写系统，在代码里写死了 Android 系统
  architecture:
    arm64: arm64-v8a
```

FDroid 目前遇到了 3 种形式：
1. 第一种是上面的，不同架构的下载地址不一样（架构名是固定的 x86_64, x86, arm64-v8a, armabi-v7a），每个版本有 4 个下载链接。例子： https://f-droid.org/en/packages/de.spiritcroc.riotx/
2. 第二种是四种架构合一的，每个版本只有 1 个下载链接，应该在所有架构都通用。例子： https://f-droid.org/en/packages/com.osfans.trime/ ，这种加上 4in1: true 即可，architecture 依然填写
3. 不显示架构的，每个版本只有 1 个下载链接，例子： https://f-droid.org/en/packages/org.fox.tttrss/ ，暂时不支持

```yaml
# 四种架构合一
Trime:
  name: trime
  website: fdroid
  project_name: com.osfans.trime
  4in1: true
  architecture:
    arm64: arm64-v8a
```

---

*就逮着一个网址下*

比较通用的选择

> Emby 在 GitHub 的下载，是在项目仓库中放着，下载链接是固定的，没法判断版本，因此写了这个下载器

```yaml
Emby_Android:
  name: emby_for_android
  website: only1link
  multi:
    # 一个下载链接，对应一套系统、架构、后缀名
    - downlink: https://github.com/MediaBrowser/Emby.Releases/raw/master/android/emby-android-google-arm64-v8a-release.apk
      system: android
      suffix: .apk
      architecture: arm64
# 因为不好判断版本是否更新，目前是取运行时日期作为版本，如果每天运行一次，则每次都会下载
```


### 上传器


目前只有 MinIO


MinIO 的下载链接格式是

```
http://ip:9000/bucket_name/file.name
```



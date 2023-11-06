import json
from http.server import BaseHTTPRequestHandler, HTTPServer

latest_version_link_filepath = "./data/latest_link.json"

# 手动填写一些配置
AMD64_ALIAS = {"amd64", "x64"}
ARM64_ALIAS = {"arm64", "arm"}
Windows_ALIAS = {"windows", "win"}
Android_ALIAS = {"android", "ad"}
Linux_ALIAS = {"linux"}

# 生成一些下面程序需要的数据
ARCH_LIST = [AMD64_ALIAS, ARM64_ALIAS]
SYSTEM_LIST = [Windows_ALIAS, Android_ALIAS, Linux_ALIAS]
ALL_ARCH = set()
ALL_SYSTEM = set()
for i in ARCH_LIST:
    ALL_ARCH.update(i)
for i in SYSTEM_LIST:
    ALL_SYSTEM.update(i)


def update_link():
    """其实就是重新读取一次文件，更新变量"""
    with open(latest_version_link_filepath, 'r', encoding='utf-8') as f:
        items_link = json.load(f)
    return items_link

items_link = update_link()

# 预先编写好的函数，根据发来的网址返回另一个对应的网址
def redirect(url):
    # 预先写一些静态网页，如果有相应错误，就跳转到那里
    app_no_exist = "https://example.com"
    version_no_exist = "https://example.com"
    check = "https://example.com"

    global items_link
    # 从网址中得到在最后的 path
    # path = url.rsplit("/", 1)[-1]
    path = url
    element = path.split("-")
    name = element[0]
    links = items_link.get(name)
    if not links:  # 若压根不存在，也就不用执行下面的了
        print(f"this file {name} does not exist")
        items_link = update_link()   # 更新，也许就有了，第二次查询的时候就能正常跳转了
        return app_no_exist
    if len(links) == 1:  # 若只对应一个网址，直接返回
        return links[0]
    if len(element) < 3:
        print("check your path")
        return check
    
    # 传来的网址，和列表里存的，都不区分大小写
    lower_path = path.lower()
    parameter1 = lower_path.split('-')[1]
    parameter2 = lower_path.split('-')[2]

    # 先判别出哪个代表系统，哪个代表架构
    if parameter1 in ALL_ARCH:
        arch, system = parameter1, parameter2
    else:
        arch, system = parameter2, parameter1

    specific_arch = None
    specific_system = None
    # 再找出实际的系统和架构
    for i, specific_arch in enumerate(ARCH_LIST):
        if arch in specific_arch:
            actual_arch = i
    for i, specific_system in enumerate(SYSTEM_LIST):
        if system in specific_system:
            actual_system = i
    if not (isinstance(actual_arch, int) and isinstance(actual_system, int)):
        # 若有一个找不到，就应该是输错了
        print("check your path")
        return check

    specific_arch = ARCH_LIST[actual_arch]
    specific_system = SYSTEM_LIST[actual_system]

    real_path = None
    # 寻找，哪个网址里，包含实际系统和架构的名称集合中的一个
    for link in links:
        for one_arch in specific_arch:
            if one_arch in link:  # 先看这个网址是否包含特定架构的名称
                for one_system in specific_system:
                    if one_system in link:  # 再看这个网址是否包含特定系统的名称
                        real_path = link  # 若都满足，就是它了
                        break
            if real_path:
                break
        if real_path:  # 如果找到了，就不再寻找，返回第一个网址
            break

    if real_path:
        return real_path
    else:
        items_link = update_link()
        return version_no_exist


class RedirectHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 获取浏览器请求的网址
        url = self.path[1:]  # 去除开头的 '/'
        print(url)

        # 调用预先编写好的函数获取重定向的网址
        redirect_url = redirect(url)

        # 发送重定向响应给浏览器
        self.send_response(302)
        self.send_header('Location', redirect_url)
        self.end_headers()


if __name__ == '__main__':
    server_class = HTTPServer
    handler_class = RedirectHandler
    host = '0.0.0.0'
    port = 8000
    # 设置监听的主机和端口号
    server_address = (host, port)
    # 创建服务器对象并指定处理请求的处理程序（RedirectHandler）
    httpd = server_class(server_address, handler_class)

    try:
        # 启动服务器并保持运行，直到按下 Ctrl+C 终止
        print(f"Listening on {host}:{port}...")
        httpd.serve_forever()
    except KeyboardInterrupt:
        # 按下 Ctrl+C 时关闭服务器
        httpd.server_close()
        print("Server stopped.")

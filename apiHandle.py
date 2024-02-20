import requests
import json

from configHandle import setup_logger
logger = setup_logger(__name__)

# 我们应该能保证 updatefetchWeb，除了种类 category_title 可能不存在，其他都会存在，因为是程序创建的

def universal_data(config_instance, item_config, version, name_and_latest_link):
    """生成统一格式"""
    latest_version = version
    download = []
    for link in name_and_latest_link[item_config["name"]]:
        path = link.rsplit("/", 1)[-1]
        element = path.split("-", maxsplit=3)
        # 名称格式为：{self.name}-{formated_sys}-{formated_arch}-{latest_version}{suffix_name}
        system = element[1]
        arch = element[2]
        download.append({'platform': system, 'architecture': arch, 'link': link})
    
    category_title = item_config.get('category_title', config_instance.category_default_title)
    image = item_config.get('image', config_instance.default_image)
    if item_config['website'] == 'github':
        website = "https://github.com/" + item_config['project_name']
    elif item_config['website'] == 'fdroid':
        website = "https://f-droid.org/packages/" + item_config['project_name']
    else:   # 不能根据已有信息生成的，则从 下载项配置 中读取
        website = item_config.get('website_url', config_instance.default_website)
    
    u_data = {
        'category_title': category_title,
        'name': item_config["name"],
        'image': image,
        'website': website,
        'version': latest_version,
        'download': download,
    }
    return u_data


class WebAPI():
    """向 Web 增、删、更新 item 的"""
    def __init__(self, web_domain, web_Token):
        self.web_domain = web_domain
        self.web_Token = web_Token
        self.api_url4category = web_domain + 'api/categories/'
        self.api_url4item = web_domain + 'api/items/'
        self.api_url4download = web_domain + 'api/downloads/'

    def item_exists(self, item_name):
        """检查 item 是否存在，根据 name"""
        return self.get_something_id_by_onekey(self.api_url4item, 'name', item_name)

    def get_something_id_by_onekey(self, api_url, onekey, onevalue):
        # 发送 GET 请求并传递查询参数
        response = requests.get(api_url, headers={'Authorization': self.web_Token})

        if response.status_code == 200:
            # 解析 JSON 响应数据
            response_json = response.json()
            for i in response_json:
                if i[onekey] == onevalue:
                    return i['id']
            return None
        else:
            logger.error(f"Error: {response.status_code}")
            return None

    def get_download_id_by_multitude(self, item_id, dl, response_json=None):
        # 发送 GET 请求并传递查询参数
        if response_json:
            downloads = response_json
            for download in downloads:
                if download['item'] == item_id and download['platform'] == dl['platform'] and download['architecture'] == dl['architecture']:
                    return download['id']
            return None
        else:   # 如果传递了 response，就不再请求，避免多次查询相同数据
            response = requests.get(self.api_url4download, headers={'Authorization': self.web_Token})
            if response.status_code == 200:
                # 解析 JSON 响应数据
                downloads = response.json()
                for download in downloads:
                    if download['item'] == item_id and download['platform'] == dl['platform'] and download['architecture'] == dl['architecture']:
                        return download['id']
                return None
            else:
                logger.error(f"Error: {response.status_code}")
                return None

    def add_item_and_link(self, item):
        """添加一个下载项, item 是 u_data 格式"""
        
        # 设置要添加的数据
        category_id = self.get_something_id_by_onekey(self.api_url4category, 'title', item['category_title'])
        if category_id:
            new_item = {
                "name": item['name'],
                "image": item['image'],
                "website": item['website'],
                "version": item['version'],
                "category": category_id
            }
        else:
            raise Exception(f"Category '{item['category_title']}' not found")
        # 发起POST请求以创建新的分类
        response = requests.post(self.api_url4item, data=json.dumps(new_item), headers={'Content-Type': 'application/json', 'Authorization': self.web_Token})
        # 返回201表示创建成功，返回新建 item 的信息
        logger.info(response.status_code)
        logger.info(response.json())

        
        item_id = self.get_something_id_by_onekey(self.api_url4item, 'name', item['name'])
        if item_id:
            for dl in item['download']:
                dl['item'] = item_id
                response = requests.post(self.api_url4download, data=json.dumps(dl), headers={'Content-Type': 'application/json', 'Authorization': self.web_Token})
                logger.info(response.status_code)
                logger.info(response.json())
        else:
            raise Exception(f"Category '{item['name']}' not found")

    def update_link(self, item):
        """更新下载链接"""
        # 设置要编辑的数据
        item_id = self.get_something_id_by_onekey(self.api_url4item, 'name', item['name'])
        response = requests.get(self.api_url4download, headers={'Authorization': self.web_Token})
        response_json = response.json()

        for dl in item['download']:
            dl_id = self.get_download_id_by_multitude(item_id, dl, response_json)   # 急需优化
            if dl_id:
                dl['item'] = item_id
                update_url = f"{self.api_url4download}{dl_id}/"
                response = requests.put(update_url, data=json.dumps(dl), headers={'Content-Type': 'application/json', 'Authorization': self.web_Token})
                # 返回201表示创建成功，返回新建 link 的信息
                logger.info(response.status_code)
                logger.info(response.json())
            else:
                raise Exception(f"dl not found")

    def update_item(self, item):
        """更新一个下载项，认为下载项一定存在，要改的只有 version"""
        category_id = self.get_something_id_by_onekey(self.api_url4category, 'title', item['category_title'])
        if category_id:
            new_item = {
                "name": item['name'],
                "image": item['image'],
                "website": item['website'],
                "version": item['version'],
                "category": category_id
            }
            item_id = self.get_something_id_by_onekey(self.api_url4item, 'name', item['name'])
            update_url = f"{self.api_url4item}{item_id}/"
            # 发起POST请求以创建新的分类
            response = requests.put(update_url, data=json.dumps(new_item), headers={'Content-Type': 'application/json', 'Authorization': self.web_Token})
            # 返回201表示创建成功
            logger.info(response.status_code)
            # 返回新建 item 的信息
            logger.info(response.json())
        else:
            raise Exception(f"Category '{item['category_title']}' not found")



    def delete_item(self, item):
        """暂时没法自动删除，只能手动去后台删。自动删除需要对比这次和上次的配置文件，这需要能预先构建一个统一格式才方便比对"""
        category_id_to_delete = 1  # 假设要删除ID为1的分类

        # 发起DELETE请求以删除分类
        delete_url = f'http://your_domain/api/categories/{category_id_to_delete}/'
        response = requests.delete(delete_url)

        # 返回204表示删除成功
        logger.info(response.status_code)


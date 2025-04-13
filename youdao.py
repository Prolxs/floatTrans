import requests
import json

from utils.AuthV3Util import addAuthParams


def createRequest(query, src, dit):
    # 从配置文件读取有道API认证信息
    config_path = r"C:\ProgramData\FloatTrans\config.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            youdao_config = config["YoudaoAPI"]
            APP_KEY = youdao_config["apppid"]
            APP_SECRET = youdao_config["apikey"]
    except Exception as e:
        print(f"加载有道API配置失败: {e}")
        return None

    if not APP_KEY or not APP_SECRET:
        print("有道API认证信息未配置")
        return None

    vocab_id = ''  # 可选的用户词表ID
    data = {'q': query, 'from': src, 'to': dit, 'vocabId': vocab_id}
    
    addAuthParams(APP_KEY, APP_SECRET, data)
    
    header = {'Content-Type': 'application/x-www-form-urlencoded'}
    res = doCall('https://openapi.youdao.com/api', header, data, 'post')
    return res.json()['translation'][0]


def doCall(url, header, params, method):
    if 'get' == method:
        return requests.get(url, params)
    elif 'post' == method:
        return requests.post(url, params, header)

# 网易有道智云翻译服务api调用demo
# api接口: https://openapi.youdao.com/api
if __name__ == '__main__':
    createRequest("conserve", "zh", 'en')

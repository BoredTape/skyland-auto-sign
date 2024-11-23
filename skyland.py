#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File: skyland.py(森空岛签到)
Author: Bwmgd
cron: 0 30 8 * * *
new Env('森空岛签到');
Update: 2024/10/09
"""
import hashlib
import hmac
import json
import logging
import os.path
import threading
import time
from datetime import date
from urllib import parse

import requests
import notify

from SecuritySm import get_d_id

token_save_name = 'TOKEN.txt'
app_code = '4ca99fa6b56cc2ba'
token_env = os.environ.get('SKLAND_TOKEN')
# 现在想做什么？
current_type = os.environ.get('SKYLAND_TYPE')
skyland_notify = os.getenv('SKYLAND_NOTIFY') or ''

http_local = threading.local()
header = {
    'cred': '',
    'User-Agent': 'Skland/1.0.1 (com.hypergryph.skland; build:100001014; Android 31; ) Okhttp/4.11.0',
    'Accept-Encoding': 'gzip',
    'Connection': 'close'
}
header_login = {
    'User-Agent': 'Skland/1.0.1 (com.hypergryph.skland; build:100001014; Android 31; ) Okhttp/4.11.0',
    'Accept-Encoding': 'gzip',
    'Connection': 'close',
    'dId': get_d_id()
}

# 签名请求头一定要这个顺序，否则失败
# timestamp是必填的,其它三个随便填,不要为none即可
header_for_sign = {
    'platform': '',
    'timestamp': '',
    'dId': '',
    'vName': ''
}

# 签到url
sign_url = "https://zonai.skland.com/api/v1/game/attendance"
# 绑定的角色url
binding_url = "https://zonai.skland.com/api/v1/game/player/binding"
# 验证码url
login_code_url = "https://as.hypergryph.com/general/v1/send_phone_code"
# 验证码登录
token_phone_code_url = "https://as.hypergryph.com/user/auth/v2/token_by_phone_code"
# 密码登录
token_password_url = "https://as.hypergryph.com/user/auth/v1/token_by_phone_password"
# 使用token获得认证代码
grant_code_url = "https://as.hypergryph.com/user/oauth2/v2/grant"
# 使用认证代码获得cred
cred_code_url = "https://zonai.skland.com/web/v1/user/auth/generate_cred_by_code"


def sendMessage(title: str, content: str, type: str):
    """
    整合消息
    :param title: 标题
    :param content: 内容
    :param type: 类型
    :return: none
    """
    if (skyland_notify):
        type = type.strip()
        if type == 'TG':
            notify.telegram_bot(title, content)
        elif type == 'BARK':
            notify.bark(title, content)
        elif type == 'DD':
            notify.dingding_bot(title, content)
        elif type == 'FSKEY':
            notify.feishu_bot(title, content)
        elif type == 'GOBOT':
            notify.go_cqhttp(title, content)
        elif type == 'GOTIFY':
            notify.gotify(title, content)
        elif type == 'IGOT':
            notify.iGot(title, content)
        elif type == 'SERVERJ':
            notify.serverJ(title, content)
        elif type == 'PUSHDEER':
            notify.pushdeer(title, content)
        elif type == 'PUSHPLUS':
            notify.pushplus_bot(title, content)
        elif type == 'QMSG':
            notify.qmsg_bot(title, content)
        elif type == 'QYWXAPP':
            notify.wecom_app(title, content)
        elif type == 'QYWXBOT':
            notify.wecom_bot(title, content)
        else:
            pass


def config_logger():
    current_date = date.today().strftime('%Y-%m-%d')
    if not os.path.exists('logs'):
        os.mkdir('logs')
    logger = logging.getLogger()

    file_handler = logging.FileHandler(f'./logs/{current_date}.log', encoding='utf-8')
    logger.addHandler(file_handler)
    logging.getLogger().setLevel(logging.DEBUG)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    def filter_code(text):
        filter_key = ['code', 'cred', 'token']
        try:
            j = json.loads(text)
            if not j.get('data'):
                return text
            data = j['data']
            for i in filter_key:
                if i in data:
                    data[i] = '*****'
            return json.dumps(j, ensure_ascii=False)
        except:
            return text

    _get = requests.get
    _post = requests.post

    def get(*args, **kwargs):
        response = _get(*args, **kwargs)
        logger.info(f'GET {args[0]} - {response.status_code} - {filter_code(response.text)}')
        return response

    def post(*args, **kwargs):
        response = _post(*args, **kwargs)
        if len(args) > 0:
            logger.info(f'POST {args[0]} - {response.status_code} - {filter_code(response.text)}')
        else:
            logger.info(f'POST {response.status_code} - {filter_code(response.text)}')
        return response

    # 替换 requests 中的方法
    requests.get = get
    requests.post = post


def generate_signature(token: str, path, body_or_query):
    """
    获得签名头
    接口地址+方法为Get请求？用query否则用body+时间戳+ 请求头的四个重要参数（dId，platform，timestamp，vName）.toJSON()
    将此字符串做HMAC加密，算法为SHA-256，密钥token为请求cred接口会返回的一个token值
    再将加密后的字符串做MD5即得到sign
    :param token: 拿cred时候的token
    :param path: 请求路径（不包括网址）
    :param body_or_query: 如果是GET，则是它的query。POST则为它的body
    :return: 计算完毕的sign
    """
    # 总是说请勿修改设备时间，怕不是yj你的服务器有问题吧，所以这里特地-2
    t = str(int(time.time()) - 2)
    token = token.encode('utf-8')
    header_ca = json.loads(json.dumps(header_for_sign))
    header_ca['timestamp'] = t
    header_ca_str = json.dumps(header_ca, separators=(',', ':'))
    s = path + body_or_query + t + header_ca_str
    hex_s = hmac.new(token, s.encode('utf-8'), hashlib.sha256).hexdigest()
    md5 = hashlib.md5(hex_s.encode('utf-8')).hexdigest().encode('utf-8').decode('utf-8')
    logging.info(f'算出签名: {md5}')
    return md5, header_ca


def get_sign_header(url: str, method, body, h):
    p = parse.urlparse(url)
    if method.lower() == 'get':
        h['sign'], header_ca = generate_signature(http_local.token, p.path, p.query)
    else:
        h['sign'], header_ca = generate_signature(http_local.token, p.path, json.dumps(body))
    for i in header_ca:
        h[i] = header_ca[i]
    return h


def parse_user_token(t):
    try:
        t = json.loads(t)
        return t['data']['content']
    except:
        pass
    return t


def get_cred_by_token(token):
    grant_code = get_grant_code(token)
    return get_cred(grant_code)


def get_token(resp):
    if resp.get('status') != 0:
        raise Exception(f'获得token失败：{resp["msg"]}')
    return resp['data']['token']


def get_grant_code(token):
    response = requests.post(grant_code_url, json={
        'appCode': app_code,
        'token': token,
        'type': 0
    }, headers=header_login)
    resp = response.json()
    if response.status_code != 200:
        raise Exception(f'获得认证代码失败：{resp}')
    if resp.get('status') != 0:
        raise Exception(f'获得认证代码失败：{resp["msg"]}')
    return resp['data']['code']


def get_cred(grant):
    resp = requests.post(cred_code_url, json={
        'code': grant,
        'kind': 1
    }, headers=header_login).json()
    if resp['code'] != 0:
        raise Exception(f'获得cred失败：{resp["message"]}')
    return resp['data']


def get_binding_list():
    v = []
    resp = requests.get(binding_url, headers=get_sign_header(binding_url, 'get', None, http_local.header)).json()

    if resp['code'] != 0:
        print(f"请求角色列表出现问题：{resp['message']}")
        if resp.get('message') == '用户未登录':
            print(f'用户登录可能失效了，请重新运行此程序！')
            os.remove(token_save_name)
            return []
    for i in resp['data']['list']:
        if i.get('appCode') != 'arknights':
            continue
        v.extend(i.get('bindingList'))
    return v


def do_sign(cred_resp):
    http_local.token = cred_resp['token']
    http_local.header = header.copy()
    http_local.header['cred'] = cred_resp['cred']
    characters = get_binding_list()
    global msg
    for i in characters:
        body = {
            'gameId': 1,
            'uid': i.get('uid')
        }
        # list_awards(1, i.get('uid'))
        resp = requests.post(sign_url, headers=get_sign_header(sign_url, 'post', body, http_local.header),
                             json=body).json()
        if resp['code'] != 0:
            print(f'角色{i.get("nickName")}({i.get("channelName")})签到失败了！原因：{resp.get("message")}')
            msg += f'角色{i.get("nickName")}({i.get("channelName")})签到失败了！原因：{resp.get("message")}\n'
            continue
        awards = resp['data']['awards']
        for j in awards:
            res = j['resource']
            print(
                f'角色{i.get("nickName")}({i.get("channelName")})签到成功，获得了{res["name"]}×{j.get("count") or 1}'
            )
            msg += f'角色{i.get("nickName")}({i.get("channelName")})签到成功，获得了{res["name"]}×{j.get("count") or 1}\n'


def read_from_env():
    v = []
    token_list = token_env.split(';')
    for i in token_list:
        i = i.strip()
        if i and i not in v:
            v.append(parse_user_token(i))
    print(f'从环境变量中读取到{len(v)}个token...')
    return v


def init_token():
    if token_env:
        print('使用环境变量里面的token')
        # 对于github action,不需要存储token,因为token在环境变量里
        return read_from_env()
    global msg
    msg = '请添加token!!!'


def start():
    global msg
    token = init_token()
    for i in token:
        try:
            do_sign(get_cred_by_token(i))
        except Exception as ex:
            print(f'签到失败，原因：{str(ex)}')
            msg += f'签到失败，原因：{str(ex)}\n'
            logging.error('', exc_info=ex)
    print("签到完成！")


if __name__ == '__main__':
    print('本项目源代码仓库：https://github.com/xxyz30/skyland-auto-sign(已被github官方封禁)')
    print('https://gitee.com/FancyCabbage/skyland-auto-sign')
    config_logger()

    logging.info('=========starting==========')
    msg = ""
    start_time = time.time()
    start()
    end_time = time.time()
    logging.info(f'complete with {(end_time - start_time) * 1000} ms')
    logging.info('===========ending============')
    sendMessage('森空岛签到', msg, skyland_notify.strip())
    # notify.wecom_app("森空岛签到", msg)

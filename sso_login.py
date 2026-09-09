#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""云课堂自动登录（SSO 免验证码场景）

链路（2026-09-09 逆向验证）：
  1. GET authserver 登录页 -> cookie + execution + pwdEncryptSalt(每次会话下发)
  2. 密码加密: AES-CBC-PKCS7(64位随机前缀+明文, key=salt, iv=16位随机), Base64
  3. checkNeedCaptcha 探测, true 则退出(避免加重失败计数)
  4. POST 登录 -> 302 重定向链中提取 ticket
  5. GET /api/v1/tickets/{ticket} -> {userId, sessionId(96位hex)}
  6. token = DES-CBC-decrypt(sessionId, key=iv=njlz@123)
  7. 写入 config.json 并验证

账号密码: 在 config.json 的 username / password 字段填入, 只存本机, 不上传。
"""
import base64
import json
import os
import random
import re
import sys

import requests
from Crypto.Cipher import AES, DES
from Crypto.Util.Padding import pad

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, 'config.json')

LOGIN_URL = ('https://authserver.nwafu.edu.cn/authserver/login'
             '?service=https%3A%2F%2Fylb.nwafu.edu.cn%2Fssoserver%2Flogin'
             '%3FplatformNumber%3D002%26platformType%3D4%26parentPlatformNum%3D010')
AUTHSERVER = 'https://authserver.nwafu.edu.cn'
JXZX = 'https://jxzx.nwafu.edu.cn'
CLIENT_KEY = 'njlz@123'
AES_CHARS = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"


def random_string(n: int) -> str:
    return ''.join(random.choice(AES_CHARS) for _ in range(n))


def encrypt_password(pwd: str, salt: str) -> str:
    key = salt.encode()
    iv = random_string(16).encode()
    data = pad((random_string(64) + pwd).encode(), 16)
    return base64.b64encode(AES.new(key, AES.MODE_CBC, iv).encrypt(data)).decode()


def sign_headers(token: str = '') -> dict:
    import hashlib, time, uuid
    t = str(int(time.time() * 1000))
    nonce = hashlib.md5((str(uuid.uuid4()) + t).encode()).hexdigest().lower()
    sign = hashlib.md5((nonce + t + CLIENT_KEY).encode()).hexdigest().lower()
    return {'x-Token': token, 'x-Time': t, 'x-Nonce': nonce, 'x-Sign': sign,
            'X-Requested-With': 'xmlhttprequest',
            'Origin': 'https://ylb.nwafu.edu.cn', 'Referer': 'https://ylb.nwafu.edu.cn/'}


def main():
    cfg = json.load(open(CFG, encoding='utf-8'))
    username, password = cfg.get('username'), cfg.get('password')
    if not username or not password:
        print('config.json 缺少 username / password，请先填写')
        sys.exit(1)

    s = requests.Session()
    s.headers['User-Agent'] = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                               'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36')

    # 1. 登录页: cookie + salt + execution
    html = s.get(LOGIN_URL, timeout=20).text
    salt = re.search(r'id="pwdEncryptSalt" value="([^"]+)"', html)
    execution = re.search(r'name="execution" value="([^"]+)"', html)
    if not salt or not execution:
        print('登录页解析失败（页面结构可能变更）')
        sys.exit(1)
    salt, execution = salt.group(1), execution.group(1)

    # 2. 验证码探测
    r = s.get(f'{AUTHSERVER}/authserver/checkNeedCaptcha.htl',
              params={'username': username, '_': random_string(13)}, timeout=15)
    if '"isNeed":true' in r.text:
        print('当前需要图形验证码（近期登录失败次数过多已触发风控）。')
        print('请改用浏览器登录智慧课堂后，用书签let或F12取 sessionId 走 refresh_token.py；')
        print('通常等待一段时间或成功登录一次后，失败计数会重置。')
        sys.exit(2)

    # 3. 提交登录
    enc = encrypt_password(password, salt)
    r = s.post(LOGIN_URL, data={
        'username': username, 'password': enc, 'captcha': '',
        '_eventId': 'submit', 'cllt': 'userNameLogin', 'dllt': 'generalLogin',
        'lt': '', 'execution': execution}, timeout=20, allow_redirects=False)

    # 4. 跟随重定向链, 提取 ticket
    ticket = None
    for _ in range(10):
        m = re.search(r'ticket=(ST-[\w.\-]+)', r.headers.get('Location', '') or r.url)
        if m:
            ticket = m.group(1)
            break
        if r.status_code in (301, 302, 303, 307):
            nxt = r.headers['Location']
            r = s.get(nxt, timeout=20, allow_redirects=False)
        else:
            break
    if not ticket:
        tip = re.findall(r'showErrorTip[^>]*><span>([^<]+)<', r.text)
        err = re.search(r'(用户名或密码[^\u4e00-\u9fa5]*[\u4e00-\u9fa5]{2,12})', r.text)
        print('登录未成功。', '服务端提示:', tip[0] if tip else (err.group(1) if err else f'HTTP {r.status_code}'))
        print('若提示密码错误请检查 config.json 的 password；触发验证码请走书签let降级路径。')
        sys.exit(3)
    print('ticket 获取成功')

    # 5. ticket 换 sessionId
    vc = __import__('hashlib').md5(b'&signKey=123123').hexdigest()
    r = s.get(f'{JXZX}/authoritycontrolplatformapi/api/v1/tickets/{ticket}',
              params={'ticket': ticket, 'validCode': vc},
              headers=sign_headers(), timeout=20)
    data = r.json()
    if not data.get('sessionId'):
        print('ticket 兑换失败:', r.text[:200])
        sys.exit(4)
    user_id = data['userId']
    session_hex = data['sessionId']

    # 6. DES 解密得 token
    des = DES.new(CLIENT_KEY.encode(), DES.MODE_CBC, iv=CLIENT_KEY.encode())
    plain = des.decrypt(bytes.fromhex(session_hex))
    plain = plain[:-plain[-1]]
    token = plain.decode('ascii').strip()

    # 7. 写回并验证
    cfg['token'], cfg['user_id'], cfg['student_id'] = token, user_id, user_id
    json.dump(cfg, open(CFG, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'新凭证已写入 config.json（{token[:13]}...）')

    from yunketang_client import YunketangClient
    term = YunketangClient(token).keepalive()
    print(f'凭证验证通过：{term.get("description", term)}')


if __name__ == '__main__':
    main()

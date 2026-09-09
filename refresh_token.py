#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""云课堂凭证刷新工具

用法：
  python3 refresh_token.py '<粘贴的 sessionId JSON>'
或直接运行后按提示粘贴。

sessionId 获取方式（三选一，推荐书签let）：
  1. 书签let：在智慧课堂页面点击书签「复制云课堂凭证」，sessionId 进剪贴板
  2. F12 控制台执行 console.log(localStorage.getItem('sessionId'))，复制输出
  3. F12 → 应用 → 本地存储空间 → 找 sessionId
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yunketang_client import token_from_session, YunketangClient

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, 'config.json')


def main():
    if len(sys.argv) > 1:
        raw = sys.argv[1].strip()
    else:
        raw = input('粘贴 sessionId JSON: ').strip()

    try:
        token = token_from_session(raw)
    except Exception as e:
        print(f'解密失败：{e}\n请确认粘贴的是完整的 {{\\"data\\":...,\\"time\\":...}} JSON')
        sys.exit(1)

    cfg = json.load(open(CFG, encoding='utf-8'))
    cfg['token'] = token
    json.dump(cfg, open(CFG, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'token 已写入 config.json（{token[:13]}...）')

    try:
        term = YunketangClient(token).keepalive()
        print(f'凭证验证通过：{term.get("description", term)}')
    except Exception as e:
        print(f'凭证已写入，但验证失败：{e}')
        sys.exit(2)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""云课堂凭证刷新工具

用法（三选一）：
  python3 refresh_token.py --stdin            从 stdin 读取（PowerShell 下最稳，见下）
  python3 refresh_token.py '<粘贴的 sessionId JSON>'  直接传参
  python3 refresh_token.py                    运行后按提示粘贴

提示：在 Windows PowerShell 下直接传 JSON 参数会被吞掉 {}" 等字符而失败，
     推荐用 --stdin（echo '<json>' | python refresh_token.py --stdin）或
     直接运行后粘贴。

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
    argv = [a.lower() for a in sys.argv[1:]]
    if '--stdin' in argv:
        raw = sys.stdin.read().strip()
    elif len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        raw = sys.argv[1].strip()
    else:
        raw = input('粘贴 sessionId JSON: ').strip()

    if not raw:
        print('未读取到内容，请提供 sessionId JSON')
        sys.exit(1)

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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""云课堂凭证刷新工具

用法：刷新 token（三选一）：
  python refresh_token.py --stdin            从 stdin 读取（PowerShell 下最稳，见下）
  python refresh_token.py '<粘贴的 sessionId JSON>'  直接传参
  python refresh_token.py                    运行后按提示粘贴

自动回填 student_id / user_id（可选）：
  python refresh_token.py --userinfo --userinfo-stdin   从 stdin 读 userInfo 密文并回填
  python refresh_token.py --userinfo '<userInfo JSON>'  直接传参回填
  只回填 id 时不要传 --token；如需同时刷新 token，追加 --token（sessionId 走 --stdin 或参数）
  例：同时刷新 token 且回填 id：
    --token --stdin（sessionId 走 stdin） + --userinfo --userinfo-stdin（userInfo 走 stdin）

提示：在 Windows PowerShell 下直接传 JSON 参数会被吞掉 {}" 等字符而失败，
     推荐用 --stdin（echo '<json>' | python refresh_token.py --stdin）或
     直接运行后粘贴。

凭证获取（书签let，二选一）：
  sessionId ：在智慧课堂页面点书签「复制云课堂凭证」
  userInfo  ：点书签「复制云课堂 userId」（同 sessionId 一样，会进剪贴板）
  也可 F12 控制台执行 console.log(localStorage.getItem('sessionId')) /
      console.log(localStorage.getItem('userInfo'))，复制输出。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yunketang_client import token_from_session, user_id_from_userinfo, YunketangClient

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, 'config.json')


def _read_input(argv, lower, stdin_flag, prompt):
    """读单个输入源：指定 --stdin 从 stdin 读；否则取首个非 -- 参数；否则交互粘贴"""
    if stdin_flag in lower:
        return sys.stdin.read().strip()
    plain = [a for a in argv if not a.startswith('--')]
    if plain:
        return plain[0].strip()
    return input(prompt).strip()


def main():
    argv = sys.argv[1:]
    lower = [a.lower() for a in argv]

    want_userinfo = '--userinfo' in lower
    # 刷新 token 的显式意图：--token，或直接传 sessionId 参数（兼容旧用法）
    explicit_token = '--token' in lower
    positional = [a for a in argv if not a.startswith('--')]
    want_token = explicit_token or (bool(positional) and not want_userinfo)

    def read_userinfo():
        return _read_input(argv, lower, '--userinfo-stdin', '粘贴 userInfo JSON（复制云课堂 userId 书签产物）: ')

    def read_session():
        return _read_input(argv, lower, '--stdin',
                           '粘贴 sessionId JSON（复制云课堂凭证书签产物）: ')

    cfg = json.load(open(CFG, encoding='utf-8'))
    save = lambda: json.dump(cfg, open(CFG, 'w', encoding='utf-8'),
                             ensure_ascii=False, indent=2)

    if want_userinfo:
        raw = read_userinfo()
        if raw:
            try:
                cfg['student_id'] = cfg['user_id'] = user_id_from_userinfo(raw)
                save()
                print(f'已自动回填 student_id / user_id = {cfg["student_id"]}'
                      '（无需手动抓包）')
            except Exception as e:
                print(f'userInfo 解析失败：{e}\n请粘贴完整的 {{\\"data\\":...,\\"time\\":...}} JSON')
                sys.exit(1)
        else:
            print('未读取到 userInfo，跳过自动回填')

    if want_token:
        raw = read_session()
        if not raw:
            print('未读取到内容，请提供 sessionId JSON')
            sys.exit(1)
        try:
            token = token_from_session(raw)
        except Exception as e:
            print(f'解密失败：{e}\n请粘贴完整的 {{\\"data\\":...,\\"time\\":...}} JSON')
            sys.exit(1)
        cfg['token'] = token
        save()
        print(f'token 已写入 config.json（{token[:13]}...）')
        try:
            term = YunketangClient(token).keepalive()
            print(f'凭证验证通过：{term.get("description", term)}')
        except Exception as e:
            print(f'凭证已写入，但验证失败：{e}')
            sys.exit(2)


if __name__ == '__main__':
    main()

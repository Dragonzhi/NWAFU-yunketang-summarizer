#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
西农云课堂（ylb.nwafu.edu.cn）提词客户端
=========================================
逆向来源（2026-09-09 侦察）：
  - 前端 Vue SPA，业务接口在 jxzx.nwafu.edu.cn 的微服务群
  - 认证：x-Token = DES-CBC 解密(localStorage.sessionId)，key/iv = "njlz@123"
    localStorage.sessionId.data = AES-ECB(sessionId明文hex)，key = "mysupersecret123"
  - 签名：x-Nonce = md5(随机串+时间戳), x-Sign = md5(nonce+时间戳+"njlz@123")
  - validCode：默认 md5("&signKey=123123")；taskId 类接口 md5("taskId="+id+"&signKey=123123")
  - token 滑动过期（约 1 小时），定期调用任意接口即可保活

接口地图：
  GET  /courseApi/v1/terms/nowterm                              当前学期（保活用）
  GET  /teachingApi/v1/videoinfo/student/courses                课程列表（studentId/schoolYear/term）
  POST /teachingApi/v1/videoinfos/page                          节次列表（userId/groupIds/openStatus/week/schoolYear/term/page/pageSize）
  GET  /lzaiapi/v1/spotbroadcastspeechrecognitions?taskId=x     提词全文（逐句+时间戳）
  GET  /teachingApi/v1/recordvideo/{id}/summarize               平台AI要点总结（aiClassroom页）
  GET  /teachingApi/v1/recordvideo/{id}/abstracts               平台AI摘要列表
  GET  /teachingApi/v1/recordvideo/{id}/mindmap                 平台AI思维导图（mindMapContent JSON串）
  GET  /teachingApi/v1/airecordvideokeywordstatistics/list      平台AI关键词统计（recordVideoInfoId=id）
"""
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid

from Crypto.Cipher import AES, DES

# Windows 控制台默认 GBK，强制 UTF-8 输出，避免中文乱码/编码报错
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, 'config.json')

DEFAULT_SALT = '&signKey=123123'
CLIENT_KEY = 'njlz@123'          # x-Sign 盐，同时是 DES key/iv
AES_KEY = b'mysupersecret123'    # localStorage.sessionId 的 AES-ECB key

BASE = 'https://jxzx.nwafu.edu.cn'
HEADERS_COMMON = [
    '-H', 'Origin: https://ylb.nwafu.edu.cn',
    '-H', 'Referer: https://ylb.nwafu.edu.cn/',
    '-H', 'X-Requested-With: xmlhttprequest',
    '-H', 'Accept: application/json',
    '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
          '(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36 Edg/152.0.0.0',
]


def md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest().lower()


def valid_code_default() -> str:
    return md5(DEFAULT_SALT)


def valid_code_task(task_id: str) -> str:
    return md5('taskId=' + task_id + DEFAULT_SALT)


def token_from_session(raw_localstorage_value: str) -> str:
    """用户 Console 导出的 localStorage.sessionId 原始 JSON -> x-Token"""
    obj = json.loads(raw_localstorage_value)
    aes = AES.new(AES_KEY, AES.MODE_ECB)
    aes_plain = aes.decrypt(base64.b64decode(obj['data']))
    aes_plain = aes_plain[:-aes_plain[-1]]          # 去 PKCS7 填充
    hex_str = aes_plain.decode()
    des = DES.new(CLIENT_KEY.encode(), DES.MODE_CBC, iv=CLIENT_KEY.encode())
    des_plain = des.decrypt(bytes.fromhex(hex_str))
    des_plain = des_plain[:-des_plain[-1]]          # 去 PKCS5 填充
    token = des_plain.decode('ascii').strip()
    return token


class YunketangClient:
    def __init__(self, token: str):
        self.token = token

    def _request(self, url: str, body: dict | None = None, timeout: int = 30) -> str:
        t = str(int(time.time() * 1000))
        nonce = md5(str(uuid.uuid4()) + t)
        sign = md5(nonce + t + CLIENT_KEY)
        cmd = ['curl', '-s', '-m', str(timeout), url,
               '-H', f'x-Token: {self.token}',
               '-H', f'x-Time: {t}',
               '-H', f'x-Nonce: {nonce}',
               '-H', f'x-Sign: {sign}'] + HEADERS_COMMON
        if body is not None:
            cmd += ['-H', 'Content-Type: application/json', '-d', json.dumps(body)]
        r = subprocess.run(cmd, capture_output=True)
        return r.stdout.decode("utf-8", errors="replace")

    def _get_json(self, url, body=None):
        out = self._request(url, body)
        data = json.loads(out)
        if isinstance(data, dict) and ('error' in data or data.get('code') not in (None, 200, '200')):
            if 'tokenExpired' in json.dumps(data) or data.get('code') == 401:
                raise PermissionError('token 已失效，请重新登录后更新 config.json')
            raise RuntimeError(f'接口错误: {out[:200]}')
        return data

    # ---------- 接口 ----------
    def keepalive(self) -> dict:
        """调当前学期接口，兼作保活与连通性检测"""
        return self._get_json(
            f'{BASE}/courseApi/v1/terms/nowterm?validCode={valid_code_default()}')

    def courses(self, student_id: str, school_year: str, term: str) -> list:
        vc = valid_code_default()
        return self._get_json(
            f'{BASE}/teachingApi/v1/videoinfo/student/courses'
            f'?studentId={student_id}&schoolYear={school_year}&term={term}&validCode={vc}')

    def videos(self, user_id: str, group_ids: str, school_year: str, term: str,
               week=None, page: int = 1, page_size: int = 50) -> list:
        """返回 videoInfoResourceList，含 taskId/startTime/teacherNames 等"""
        vc = valid_code_default()
        body = {"userId": user_id, "groupIds": group_ids, "openStatus": "1",
                "week": week, "schoolYear": school_year, "term": term,
                "validCode": vc, "page": page, "pageSize": page_size}
        data = self._get_json(f'{BASE}/teachingApi/v1/videoinfos/page?validCode={vc}', body)
        return data.get('videoInfoResourceList', []) if isinstance(data, dict) else data

    def transcript(self, task_id: str) -> list:
        """返回 [{startTimeStamp, endTimeStamp, recognitionResult}]"""
        vc = valid_code_task(task_id)
        data = self._get_json(
            f'{BASE}/lzaiapi/v1/spotbroadcastspeechrecognitions'
            f'?identifySensitiveWord=true&taskId={task_id}&validCode={vc}')
        return data[0]['speechRecognitionResults'] if data else []

    # ---------- 平台自带 AI 产出（aiClassroom 页，逆向自前端 chunk） ----------
    # 注意：AI 产物按节课异步生成，「未找到」(B99999) 是正常空态而非故障
    def _ai_get(self, url: str):
        try:
            return self._get_json(url)
        except RuntimeError as e:
            if '未找到' in str(e):
                return None
            raise

    def ai_summary(self, record_id: str) -> dict | None:
        """平台 AI 要点总结 {summarizeContent: ...}；未生成返回 None"""
        return self._ai_get(
            f'{BASE}/teachingApi/v1/recordvideo/{record_id}/summarize'
            f'?validCode={md5("id=" + record_id + DEFAULT_SALT)}')

    def ai_abstracts(self, record_id: str) -> list | None:
        """平台 AI 摘要要点列表；未生成返回 None"""
        return self._ai_get(
            f'{BASE}/teachingApi/v1/recordvideo/{record_id}/abstracts'
            f'?validCode={md5("id=" + record_id + DEFAULT_SALT)}')

    def ai_mindmap(self, record_id: str) -> dict | None:
        """平台 AI 思维导图 {mindMapContent: '<json字符串>'}；未生成返回 None"""
        return self._ai_get(
            f'{BASE}/teachingApi/v1/recordvideo/{record_id}/mindmap'
            f'?validCode={md5("id=" + record_id + DEFAULT_SALT)}')

    def ai_keywords(self, record_id: str) -> list:
        """平台 AI 关键词统计（词云），无则空列表"""
        return self._get_json(
            f'{BASE}/teachingApi/v1/airecordvideokeywordstatistics/list'
            f'?recordVideoInfoId={record_id}&validCode='
            f'{md5("recordVideoInfoId=" + record_id + DEFAULT_SALT)}')


def transcript_to_text(results: list) -> str:
    """逐句转写合并成带时间戳的纯文本（每分钟一行锚点）"""
    lines, last_min = [], -1
    for r in results:
        m = int(r['startTimeStamp'] // 60)
        if m != last_min:
            lines.append(f'\n[{m:02d}:00]')
            last_min = m
        lines.append(r['recognitionResult'].strip())
    return '\n'.join(lines).strip()


# ---------- CLI ----------
def _load_config():
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


def main():
    import sys
    cfg = _load_config()
    client = YunketangClient(cfg['token'])
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'keepalive'

    if cmd == 'keepalive':
        print('保活/连通性:', client.keepalive())
    elif cmd == 'courses':
        for c in client.courses(cfg['student_id'], cfg['school_year'], cfg['term']):
            print(f"{c['courseId']}  {c['courseName']}[{c['classNames'].split('[')[1]}"
                  f"  最近更新 {c['maxUpdateDate']}  教师 {c['teacherNames']}")
    elif cmd == 'videos':
        course_id = sys.argv[2]
        for v in client.videos(cfg['user_id'], cfg['group_ids'][course_id],
                               cfg['school_year'], cfg['term']):
            print(f"{v.get('id', '-')}  {v['taskId']}  {v['videoInfoName']}  "
                  f"{v['startTime'][:16]}  {v['teacherNames']}")
    elif cmd == 'ai':
        rid = sys.argv[2]
        print('=== 平台AI要点总结 ===')
        print(((client.ai_summary(rid) or {}).get('summarizeContent')) or '（未生成）')
        print('=== 平台AI摘要 ===')
        abstracts = client.ai_abstracts(rid) or []
        for a in abstracts:
            print(json.dumps(a, ensure_ascii=False))
        if not abstracts:
            print('（未生成）')
        print('=== 平台AI思维导图 ===')
        mc = (client.ai_mindmap(rid) or {}).get('mindMapContent')
        if mc:
            def walk(node, depth=0):
                print('  ' * depth + node.get('topic', ''))
                for ch in node.get('children', []):
                    walk(ch, depth + 1)
            walk(json.loads(mc))
        else:
            print('（未生成）')
        print('=== 平台AI关键词 ===')
        kws = client.ai_keywords(rid) or []
        print('  '.join(f"{k['keywordName']}x{k['keywordCount']}" for k in kws)
              or '（无）')
    elif cmd == 'transcript':
        task_id = sys.argv[2]
        out = sys.argv[3] if len(sys.argv) > 3 else None
        text = transcript_to_text(client.transcript(task_id))
        if out:
            with open(out, 'w', encoding="utf-8") as f:
                f.write(text)
            print(f'已写入 {out}，{len(text)} 字')
        else:
            print(text[:3000])
    else:
        print(__doc__)


if __name__ == '__main__':
    main()

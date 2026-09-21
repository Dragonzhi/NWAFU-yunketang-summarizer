# 云课堂总结器 · 安装与使用

西农智慧课堂（ylb.nwafu.edu.cn）课堂实录总结 skill。适配 Trae / Claude Code / Codex 等支持 Agent Skills 规范（SKILL.md）的 agent。

> **免责声明**：本工具仅供个人学习复习使用，须登录使用者本人账号查看本人有权限的课程内容，不得用于爬取他人数据或干扰平台。请克制使用；因使用本工具导致的账号风控、接口变更失效等情况由使用者自行承担。config.json 含个人凭证，切勿分享或上传。

## 安装（Trae）

1. Trae 支持用户级与项目级 Skill（完整兼容 SKILL.md 规范）
2. 用户级：把 `yunketang-summarizer` 整个文件夹放进 Trae 的用户级 skills 目录（或在 Trae 的 Skills 面板导入；具体入口见 Trae 文档 docs.trae.ai/ide/skills）
3. 项目级：把文件夹放进项目根目录的 skills 目录，仅该项目可用
4. 装好后对 agent 说「总结今天的课」即可触发；若未自动触发，直接说「按 yunketang-summarizer 总结今天的课」

## 依赖

- Python 3.9+
- `pip install pycryptodome`

## 首次配置

1. `pip install pycryptodome`
2. 复制 `config.example.json` 为 `config.json`（config.json 含个人凭证，已被 .gitignore 排除），然后打开它：确认 `student_id` / `group_ids` / `school_year` / `term` 已填
3. 登录一次智慧课堂网页版，按下方书签let/F12 方式取 sessionId，跑 `python refresh_token.py` 验证连通
4. 学期切换时更新 `school_year` / `term` / `group_ids`（抓包新学期的课程列表可得）

## 凭证刷新（token 约一小时滑动过期）

> 提示：课堂转写由平台异步生成、出稿时间不稳定，总结前建议先在平台上确认目标节次的转写已完成——反正都要登录平台，顺手取凭证刷新即可。

### 方式一：书签let（两秒）

在浏览器书签栏新建书签，名称随意（如「复制云课堂凭证」），地址填：

```
javascript:(()=>{const s=localStorage.getItem('sessionId');if(!s){alert('未找到sessionId，请先登录智慧课堂');return;}navigator.clipboard.writeText(s).then(()=>alert('已复制到剪贴板'));})()
```

使用：登录智慧课堂后，在平台任意页面点一下这个书签 → sessionId 进剪贴板 → 粘贴给 agent 或运行 `python refresh_token.py`（直接运行会提示粘贴）。

### 方式二：F12 控制台

登录平台后按 F12 → 控制台执行：

```js
console.log(localStorage.getItem('sessionId'))
```

复制输出，粘贴给 agent 或 refresh_token.py。

## 常用指令

| 对 agent 说 | 效果 |
|---|---|
| 总结今天的课 | 找到最新一节课，总结并归档 |
| 总结云计算 9 月 8 日的课 | 按课程和日期定位 |
| 把云计算这两周的课都总结了 | 批量总结多节课 |
| 把云计算整学期的课全总结了 | 学期补档模式 |
| 出云计算的复习提纲 | 合并全部总结 → 00_期末复习提纲.md |
| 把今天课的提词原文给我 | 只拉原文不总结 |

## 归档

总结写入 `config.json` 里 `archive_dir` 指定的目录（默认工作区下 `云课堂总结/`），按课程分文件夹、按周次命名。私人学习材料，不要推公开仓库。

## 文件说明

- `SKILL.md` — agent 执行流程说明
- `yunketang_client.py` — 平台接口客户端（签名/解密/提词）
- `refresh_token.py` — 凭证刷新工具（配合书签let/F12 手动刷新）
- `config.json` — 凭证与配置（含 token，不要外传）

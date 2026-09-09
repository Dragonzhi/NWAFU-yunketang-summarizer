# 西农云课堂总结器（yunketang-summarizer）

西农智慧课堂（ylb.nwafu.edu.cn）课堂实录总结工具。课堂录像（含语音识别提词）在课程第二天挂到平台后，本工具自动拉取老师讲话逐句提词，总结为结构化复习笔记并归档。适配 Trae / Claude Code / Codex 等支持 Agent Skills（SKILL.md）规范的 agent。

## 它能做什么

- **一句话总结课程**：对 agent 说「总结今天的课」，自动定位最新一节课、拉提词、生成笔记
- **结构化输出**：一页纸速览 + 老师强调的考点 + 带时间戳的详细笔记（可回跳视频定位）+ 作业通知
- **自动归档**：按课程分文件夹、按周次命名，攒成自己的复习笔记库
- **批量模式**：「把云计算这两周的课都总结了」「整学期补档」
- **期末复习提纲**：合并全部笔记，汇总高频考点与概念地图
- **凭证自动刷新**：支持 CAS 自动登录，token 过期无需手动折腾（也保留书签/F12 手动降级路径）

## 快速开始

```bash
pip install pycryptodome requests
cp config.example.json config.json   # Windows: copy config.example.json config.json
# 编辑 config.json 填入个人信息（详见 INSTALL.md）
python sso_login.py                  # 验证自动登录
```

然后把本文件夹放入 agent 的 skills 目录，对它说「总结今天的课」即可。

**完整安装、配置与使用说明见 [INSTALL.md](INSTALL.md)。**

## 文件结构

| 文件 | 说明 |
|---|---|
| `SKILL.md` | agent 执行流程（Skill 规范入口） |
| `yunketang_client.py` | 平台接口客户端：签名/解密/拉提词 |
| `sso_login.py` | CAS 自动登录（config 填学号密码后全自动） |
| `refresh_token.py` | 凭证手动刷新（配合书签let / F12） |
| `config.example.json` | 配置模板，复制为 config.json 后填写 |
| `config.json` | 个人凭证与配置（**不入库，切勿分享**） |

## 免责声明

仅供个人学习复习使用，须登录本人账号查看本人有权限的课程内容，不得爬取他人数据或干扰平台；账号风控、接口变更失效等后果由使用者自行承担。

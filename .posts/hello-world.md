---
title: BossHunter 部署实践
date: 2026-09-17
slug: hello-world
cover: /medias/featureimages/1.jpg
tags:
  - BossHunter
  - 求职
  - AI Agent
categories:
  - 工具
summary: BossHunter 部署实践：从环境搭建到完整链路打通，包括简历管理和定制简历生成。
description: BossHunter 从环境搭建到完整链路打通的部署实践，含简历管理与定制简历生成
---

BossHunter 是由 [shengjidaguai-china/BossHunter](https://github.com/shengjidaguai-china/BossHunter) 维护的本地智能求职 Agent 项目，版本 v2.4.0。本文记录了在 Windows + WSL2 环境下从零部署到跑通完整链路的实践过程。

## 项目简介

BossHunter 实现了一套完整的求职自动化流程：

1. **多平台岗位采集** — 串行采集 BOSS 直聘、智联招聘、前程无忧 51job 和猎聘
2. **AI 评分与筛选** — 关键词预筛 + JD 深度评分
3. **人工确认** — 投递前必须审核确认
4. **个性化招呼语** — 根据 JD 和简历自动生成
5. **低频安全发送** — 随机间隔 + 时间窗口 + 每日上限
6. **HR 回复监听** — 实时监测投递后的回复
7. **定制简历** — 根据岗位 JD 辅助生成针对性简历

> ⚠️ 自动化操作招聘平台存在账号限制或封禁风险。本项目仅供学习、研究和个人求职效率提升；请遵守平台规则，保持低频，并自行承担使用风险。

## 环境准备

部署前需要准备以下环境：

| 依赖 | 版本 | 用途 |
| --- | --- | --- |
| Python | 3.10+ | 核心运行时 |
| Node.js | 22+ | Browser Runtime / CDP 代理 |
| Google Chrome | 最新稳定版 | 连接已登录的招聘平台 |
| AI API Key | — | Anthropic 或 OpenAI 兼容接口 |

## 部署步骤

### 1. 安装依赖

```bash
git clone https://github.com/shengjidaguai-china/BossHunter.git
cd BossHunter
npm --prefix src/bosshunter/web/frontend ci
npm --prefix src/bosshunter/web/frontend run build
pip install -e .
```

### 2. 开启 Chrome 远程调试

```bash
# Linux（推荐使用独立用户目录）
google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.bosshunter-chrome"
```

使用独立用户目录时，需要在这个 Chrome 窗口中登录要使用的招聘平台，并保持窗口开启。

### 3. 完成本地配置

```bash
bosshunter web
```

浏览器打开 `http://127.0.0.1:8686`，完成：

1. 上传自己的简历（.md、.docx 或带文字层的 .pdf）
2. 设置搜索关键词、目标城市、评分阈值
3. 配置 AI 服务商和 API Key（在面板中输入，不要提交到代码仓库）

### 4. 检查连接

```bash
bosshunter ai-status
bosshunter connect
```

### 5. 运行

```bash
bosshunter run
```

完整流程：采集岗位 → AI 评分 → 人工确认投递清单 → 生成招呼语 → 低频发送 → 监听回复。

## 实测结果

| 项 | 值 |
| --- | --- |
| 采集岗位 | 92 |
| 评分通过 / 过滤 | 76 / 16 |
| 实测发送 | 5（人工确认） |
| 评分阈值 | 60（低匹配优先练手策略） |

## 简历管理

项目本身支持 JD→定制简历，但缺少多简历管理和历史记录。为此自研了 `tools/resume_manager.py`：

```bash
resume-mgr list                                   # 基础简历列表（* 当前使用）
resume-mgr import 简历.docx --use                 # 导入并设为当前
resume-mgr use 简历.md                            # 切换简历
resume-mgr tailor --jd jd.txt --title 岗位 --company 公司  # 生成定制简历
cat jd.txt | resume-mgr tailor --jd -              # 支持 stdin
resume-mgr history                                # 定制简历历史
```

自研工具复用了项目的 `bosshunter.ai.resume`（AI + 校验 + 渲染）和 `bosshunter.browser`（CDP），不重造生成逻辑。产物保存在 `data/resumes/` 下，包括 .md + .pdf + .png。

## 注意事项

1. 许可证为 PolyForm Noncommercial（**非开源**），仅限非商业用途
2. 仅 BOSS 直聘支持自动发送和监听；智联/51job/猎聘仅支持只读采集
3. API Key 只在本地面板输入，不要发送到聊天、Issue 或提交文件中
4. 所有投递必须经过人工确认，不会在未经确认时发送

详细部署步骤见 [个人仓库 setup/SETUP.md](https://github.com/atcXiGua/personal/tree/main/bosshunter/setup/SETUP.md)，踩坑记录见 [LESSONS.md](https://github.com/atcXiGua/personal/tree/main/bosshunter/LESSONS.md)。

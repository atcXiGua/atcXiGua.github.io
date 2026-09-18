---
title: 两个 opencode skill：把 ChatGPT 对话一键变成博客文章
slug: opencode-skills-blog-pipeline
date: 2026-09-18
cover: /medias/featureimages/15.jpg
tags:
  - opencode
  - Agent
  - 自动化
  - 博客
categories:
  - 工具
summary: 两个 opencode skill 的完整落地指南：chatgpt-conversation-extract 从分享链接提取对话，blog-publish 把 Markdown 一键发布到 Hexo+Matery 静态博客。含完整脚本、部署步骤与防坑清单。
description: opencode skill 落地指南：ChatGPT 对话提取 + 静态博客自动发布流水线，含完整脚本与踩坑经验
---

## 这是一条什么流水线

我在 [opencode](https://opencode.ai) 里沉淀了两个 skill，串成一条链：

```
ChatGPT 分享链接 ──skill 1──▶ 本地 Markdown ──skill 2──▶ Hexo 博客页面 ──▶ git push ──▶ 线上
```

- **chatgpt-conversation-extract**：给一个 `https://chatgpt.com/share/<id>` 链接，提取完整对话文本
- **blog-publish**：给一篇带 frontmatter 的 Markdown，发布到纯静态的 Hexo + Matery 站点（全量重生成文章页、首页、归档、标签、分类、搜索、RSS，再 push）

写这篇文章的目的，是让我**其他 PC 上的 agent 读完就能照着落地**——两个 skill 的完整文件、依赖、每一步操作和所有踩过的坑都在下面。

## 环境准备（新 PC 上做一次）

```bash
# 1. 克隆博客仓库（脚本和模板都在仓库的 .posts/ 目录里，随仓库同步）
git clone git@github.com:atcXiGua/atcXiGua.github.io.git /mnt/d/tmp/blog

# 2. Python 3.10+，仅需标准库（urllib/re/json/html/yaml 都用标准库，无第三方依赖）

# 3. git 身份
git config --global user.name "atcXiGua"
git config --global user.email "271125381@qq.com"

# 4. SSH key（GitHub 写权限），放到 ~/.ssh/ 并在 GitHub 注册公钥

# 5. 创建两个 skill 目录（内容见附录，逐字复制即可）
mkdir -p ~/.config/opencode/skills/blog-publish
mkdir -p ~/.config/opencode/skills/chatgpt-conversation-extract
```

opencode 的全局 skill 约定：`~/.config/opencode/skills/<name>/SKILL.md`，文件开头是 frontmatter（`name` + `description`），opencode 启动时自动加载并在匹配场景时提示使用。

> 磁盘规则（我的环境）：所有写入走挂载盘 `/mnt/d/`（临时文件 `/mnt/d/tmp/`），不要往 C 盘或 WSL 根文件系统写大文件。

## Skill 1：ChatGPT 对话提取

ChatGPT 分享页是 JS 渲染的，`webfetch` 直接抓只能拿到标题。但完整对话数据以 **React Server Components（RSC）流**的形式内嵌在 HTML 的 `<script>` 块里，调用形式是 `window.__reactRouterContext.streamController.enqueue("<双重转义JSON>")`。

提取流程：抓 HTML → 找全部 `enqueue("...")` → `json.loads` 解一层转义得到 RSC payload → 递归收集全部字符串 → 过滤"长度 >100 且密集含中文"的串 → 得到按顺序的消息。

实测可用（提取了 4 条完整消息）：

```bash
python3 ~/.config/opencode/skills/chatgpt-conversation-extract/extract_chatgpt.py \
  "https://chatgpt.com/share/<id>" /mnt/d/tmp/chatgpt_conv.txt
```

输出是 `==== MESSAGE 0 ====` 分隔的文本文件，`read` 它即可进入后续加工。

**已知局限**（提取时心里有数）：

| 现象 | 原因 | 处理 |
|---|---|---|
| 短消息被丢弃 | 过滤条件是"长度 >100 且含 10 个以上连续中文"，短的寒暄会被过滤 | 正常，长内容都在 |
| 消息顺序可能非对话序 | RSC 字符串表的收集顺序不等于对话顺序 | 通读后按语义重排 |
| 提取到 0 条 | URL 不是公开分享，或被风控 | 浏览器打开链接确认可匿名访问 |
| `403` | 要带浏览器 UA | 脚本已带 UA，直接 curl 会 403 是正常的 |

## Skill 2：博客自动发布

站点是 **Hexo + hexo-theme-matery 的纯静态生成站点**——仓库里没有 Hexo 源码，所有页面由 `.posts/publish.py` 从 `.posts/*.md` 全量重新生成。源文件即真理，派生页面不手工改。

```bash
python3 .posts/publish.py regen --blog /mnt/d/tmp/blog   # 全量重生成
python3 .posts/publish.py git  --blog /mnt/d/tmp/blog     # regen + commit + push
```

每次 `regen` 会重生成：文章页（含上/下一篇链）、首页卡片、`search.xml`、`atom.xml`、归档页（含 ECharts 日历数据重算）、归档年/月页、标签云 + 各标签详情页、分类页。删掉某个 `.md` 再 regen，对应文章会从所有页面移除。

**文章源文件格式**（`.posts/<slug>.md`）：

```markdown
---
title: 文章标题
slug: url-slug
date: 2026-09-18
cover: /medias/featureimages/15.jpg
tags:
  - 标签1
  - 标签2
categories:
  - 分类名
summary: 首页卡片摘要
description: SEO 描述
---

正文（Markdown）……
```

必填 `title` / `slug` / `date` / `cover`；封面图在 `medias/featureimages/` 里选已有的（0-23.jpg）。

**md2html.py 支持的 Markdown 子集**：ATX 标题（`##`/`###`/`####`，自动生成 hexo 风格锚点）、围栏代码块（输出 `<pre class="line-numbers language-lang"><code class="language-lang">`，前端由 Prism.js 语法高亮 + 行号 + 语言标签）、GFM 表格、引用、有序/无序列表、加粗、行内代码、链接、图片、分隔线、**标签平衡的多行 raw HTML 块**（整体透传）。

## 串起来：一次完整的"对话变文章"

```bash
# 1. 提取对话
python3 ~/.config/opencode/skills/chatgpt-conversation-extract/extract_chatgpt.py \
  "https://chatgpt.com/share/<id>" /mnt/d/tmp/conv.txt

# 2. agent 读取 conv.txt，整理成一篇博客 Markdown（加 frontmatter）
#    → 写入 /mnt/d/tmp/blog/.posts/<slug>.md

# 3. 全量重生成
python3 .posts/publish.py regen --blog /mnt/d/tmp/blog

# 4. 本地验证（见下节）

# 5. 发布
python3 .posts/publish.py git --blog /mnt/d/tmp/blog
```

第 2 步是 agent 的核心工作：对话原文是"聊天"，博客文章要有结构——定标题、分章节、去寒暄、补 frontmatter。提取脚本只负责把数据搬出来。

**本地验证**（每次必做，模板结构最容易在这里出问题）：

```bash
python3 -m http.server 8765 --bind 127.0.0.1   # 在博客根目录执行
```

用浏览器打开 `http://127.0.0.1:8765/<文章路径>/?v=N`，检查：

- `#toc-aside` 的父元素是 `.row`，且与 `#main-content` 不重叠（目录栏错位是最常见的坑）
- `#articleContent` 内 `pre` / `code` 标签开闭数量一致
- 代码块左上角有语言标签、左侧有行号、关键字有语法着色（Prism）
- `#prenext-posts .article` 数量为 2（上/下一篇）
- 首页卡片数 == 文章数；归档页 timeline 块数 == 文章数
- 控制台无 JS 报错

## 防坑清单

| 坑 | 症状 | 解法 |
|---|---|---|
| raw HTML 标签不配平 | 目录栏被吃进代码块容器、正文被遮挡 | 转换器按块级标签深度配平整体透传；源 MD 里代码示例一律用 ` ```lang ` 围栏，不用 raw `<pre><code>` |
| frontmatter 列表项为空 | 空标签的页面路径退化为 `tags/index.html`，覆盖标签云首页 | 解析时空值不进入标签列表；发布前确认 tags/categories 无空项 |
| `#toc-aside` 不是 `.row` 直接子元素 | 目录栏错位、遮挡正文 | 从站点现有页面提取模板后，用 HTML 解析器校验祖先链是 `main.post-container > .row` |
| 围栏代码块内的空行 | 被当成段落分隔，代码块中间长出 `<p>` | 转换器已修；源文件里代码块保持原样即可 |
| 代码块语言标签为空 | Matery 的 `codeLang.js` 从 `<pre>` 的 class 读语言 | 类名输出在 `<pre>` 上（`line-numbers language-xxx`），不能只在 `<code>` 上 |
| 代码块长行横向溢出 | 视觉上超出代码块边界 | `css/my.css` 里 `pre/pre code` 加 `white-space: pre-wrap` + `overflow-wrap: anywhere` |
| 文章页"文章链接"写死 | reprint 区链接指向别的文章 | 模板里用 `{{PERMALINK}}` 占位符 |
| 文章日期格式 | 排序/归档页年月错 | 一律 `YYYY-MM-DD` |
| `http.server` 会话不持久 | 每次 bash 调用 workdir 会重置 | 启动服务时指定 `workdir`，或每次 `cd` 后再执行 |
| opencode skill 不触发 | description 写得不像场景 | description 里写清"什么时候用 + 用户会怎么说"，中英文都写 |

## 附录：skill 完整文件

> 三个文件逐字复制到对应路径即可。`publish.py` / `md2html.py` / 模板文件随博客仓库同步，在 `.posts/` 目录下，不需要单独复制。

### `~/.config/opencode/skills/chatgpt-conversation-extract/SKILL.md`

```markdown
---
name: chatgpt-conversation-extract
description: 从 ChatGPT 分享链接（https://chatgpt.com/share/<id>）提取完整对话文本。当用户提供 ChatGPT 分享链接并要求读取、整理对话内容、基于对话改简历或归档访谈记录时使用。包含可直接运行的提取脚本。Use when the user shares a chatgpt.com/share URL.
---

# ChatGPT 对话提取

把 ChatGPT 分享链接的完整对话内容提取成本地文本文件，供阅读、分析或后续加工。

## 用法

python3 ~/.config/opencode/skills/chatgpt-conversation-extract/extract_chatgpt.py "<分享URL>" "/mnt/d/tmp/chatgpt_conv.txt"

- 第一个参数：分享链接
- 第二个参数：输出路径（默认写到 /mnt/d/tmp/）
- 输出格式：`==== MESSAGE 0 ====` 开头、按顺序排列的消息列表

## 为什么这样提取（原理）

- 分享页内容靠 JS 渲染，直接抓 HTML 只能拿到标题；
- 完整对话数据以 React Server Components（RSC）流形式内嵌在 HTML 的多个 <script> 块里，
  调用形式是 window.__reactRouterContext.streamController.enqueue("<双重转义JSON>")；
- 提取流程：抓 HTML → 找含 enqueue("...") 的 script → json.loads 解一层转义 →
  递归收集全部字符串 → 过滤"长度 >100 且密集含中文"的串。

## 踩坑注意

- 转义层级：enqueue 参数是 JS 字符串，json.loads('"'+arg+'"') 解一层即可，别手动 replace
- 多 script 分片：RSC 流可能拆成多个 enqueue，脚本已遍历全部并合并收集
- 登录墙：静态 HTML 里数据完整，curl 带 UA 即可拿到
- 判断成功：输出里应包含用户/助手轮流的长文本；若 MESSAGE 过少，检查 URL 是否公开分享
```

### `~/.config/opencode/skills/chatgpt-conversation-extract/extract_chatgpt.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract conversation text from a ChatGPT share link (chatgpt.com/share/<id>)."""
import re, json, sys, urllib.request

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")

def collect_strings(x, out):
    if isinstance(x, str):
        out.append(x)
    elif isinstance(x, dict):
        for v in x.values():
            collect_strings(v, out)
    elif isinstance(x, list):
        for v in x:
            collect_strings(v, out)

def extract_conversation(raw):
    """Return list of decoded RSC payloads found in the HTML."""
    payloads = []
    for m in re.finditer(r'<script[^>]*>(.*?)</script>', raw, re.S):
        content = m.group(1)
        if "enqueue(" not in content:
            continue
        for em in re.finditer(r'enqueue\("((?:[^"\\]|\\.)*)"\)', content, re.S):
            try:
                payloads.append(json.loads('"' + em.group(1) + '"'))
            except Exception:
                continue
    return payloads

def main(url, outpath):
    raw = fetch(url)
    payloads = extract_conversation(raw)
    if not payloads:
        print("no conversation payload found")
        return 1

    strings = []
    for p in payloads:
        try:
            p = json.loads(p)  # RSC payload is itself a JSON string -> parse into structure
        except Exception:
            pass
        collect_strings(p, strings)

    # conversation messages: reasonably long strings with dense CJK text
    conv = [s for s in strings if len(s) > 100 and re.search(r'[\u4e00-\u9fff]{10,}', s)]

    with open(outpath, "w", encoding="utf-8") as f:
        for i, s in enumerate(conv):
            f.write(f"\n{'='*20} MESSAGE {i} {'='*20}\n{s}\n")
    print(f"extracted {len(conv)} messages -> {outpath}")
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python3 extract_chatgpt.py <share_url> [output.txt]")
        sys.exit(1)
    url = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "/mnt/d/tmp/chatgpt_conv.txt"
    sys.exit(main(url, out))
```

### `~/.config/opencode/skills/blog-publish/SKILL.md`

```markdown
---
name: blog-publish
description: 把 Markdown 文章发布到 Hexo+Matery 静态博客站点（atcXiGua.github.io）。当用户要发博客、加文章、更新文章，或提到 .posts/publish.py、博客仓库、simple life 站点时使用。包含发布脚本与验证流程。Use when the user wants to publish/update a blog post on the static blog site.
---

# 博客发布（Hexo + Matery 纯静态站点）

站点 atcXiGua.github.io 是 Hexo + hexo-theme-matery 的纯静态生成站点（仓库里没有 Hexo 源码）。
所有页面由 <blog>/.posts/publish.py 从 .posts/*.md 源文件重新生成。

- 博客仓库：默认克隆在 /mnt/d/tmp/blog（分支 master）
- 源文章：<blog>/.posts/*.md（带 YAML frontmatter）
- 发布器：<blog>/.posts/publish.py
- Markdown 转换器：<blog>/.posts/md2html.py（自写，无第三方依赖）

## 发布流程

1. 准备源文件：把 Markdown 放进 <blog>/.posts/<slug>.md，frontmatter 必填
   title / slug / date / cover，可选 tags / categories / summary / description。
   封面图在 <blog>/medias/featureimages/ 下选已有的。
2. 重新生成所有派生页面：
   python3 .posts/publish.py regen --blog /mnt/d/tmp/blog
3. 本地验证：启动 python3 -m http.server 8765（workdir=博客根目录），用浏览器检查
   #toc-aside 父元素是 .row、pre/code 标签平衡、#prenext-posts .article 数量为 2、
   首页卡片数 == 文章数、控制台无报错。
4. 提交并推送：
   python3 .posts/publish.py git --blog /mnt/d/tmp/blog

## Markdown 支持子集（md2html.py）

ATX 标题（自动生成 hexo 风格锚点 headerlink）、围栏代码块、GFM 表格、引用、
有序/无序列表、加粗、行内代码、链接、图片、分隔线、平衡的多行 raw HTML 块（整体透传）。

## 常见坑

- raw HTML 必须标签平衡，否则转换器会把后续内容（含目录栏）吃进错误的容器
- frontmatter 列表项不要留空值，否则空标签页路径退化为 tags/index.html 覆盖标签首页
- #toc-aside 必须是 .row 的直接子元素，否则目录栏错位遮挡正文
- 文章日期用 YYYY-MM-DD
- 模板文件：.posts/tpl_post.html（文章页）、tpl_archive.html（归档）、tpl_list.html（标签/分类列表页）
```

## 写在最后

这两个 skill 的本质是把**重复的机械流程固化成脚本 + 场景描述**：agent 读到 description 知道"该用这个工具"，脚本保证"每一步可复现"。整套东西没有任何高深技术，难的是把每一步的坑都踩过一遍并写进文档——这也是这篇文章存在的意义。

对话 → 文章 → 发布，一条命令的链条搭好之后，剩下的就是专注内容本身。

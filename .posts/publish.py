#!/usr/bin/env python3
"""Blog publisher for the hexo-theme-matery static site.

Usage:
  python3 publish.py regen [--blog DIR]   # regenerate all derived pages from .posts
  python3 publish.py git   [--blog DIR]   # regen + commit + push

Source of truth: <blog>/.posts/*.md with YAML frontmatter.
Derived (regenerated every run): post pages, index cards, search.xml,
atom.xml, archives (index + year + month), tags pages, categories pages.

Frontmatter fields:
  title* slug* date* cover* summary description
  tags [list] categories [list]            (* required)
"""
import sys, os, re, json, glob, html, subprocess, datetime, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import md2html

DEFAULT_BLOG = '/mnt/d/tmp/blog'

# ---------------------------------------------------------------- frontmatter
def parse_fm(md):
    m = re.match(r'^---\n(.*?)\n---\n', md, re.S)
    if not m:
        raise SystemExit('missing YAML frontmatter')
    fm_raw, body = m.group(1), md[m.end():]
    fm = {}
    for line in fm_raw.split('\n'):
        if not line.strip() or line.strip().startswith('#'):
            continue
        mm = re.match(r'^(\w+):\s*(.*)$', line)
        if not mm:
            continue
        key, val = mm.group(1), mm.group(2).strip()
        fm[key] = val
    # list values (tags/categories) collected from following indented lines
    cur = None
    for line in fm_raw.split('\n'):
        mm = re.match(r'^(\w+):\s*(.*)$', line)
        m2 = re.match(r'^\s*-\s+(.+)$', line)
        if mm:
            cur = mm.group(1)
            if mm.group(2).strip():
                fm[cur] = mm.group(2).strip(); cur = None
        elif m2 and cur:
            fm.setdefault(cur, [])
            if isinstance(fm[cur], str):
                fm[cur] = [fm[cur]] if fm[cur].strip() else []
            fm[cur].append(m2.group(1).strip())
    return fm, body

def load_posts(blog):
    posts = []
    for f in sorted(glob.glob(os.path.join(blog, '.posts', '*.md'))):
        md = open(f, encoding='utf-8').read()
        fm, body = parse_fm(md)
        for req in ('title', 'slug', 'date', 'cover'):
            if req not in fm:
                raise SystemExit(f'{f}: missing required field "{req}"')
        tags = [t for t in fm.get('tags', []) if t]
        if isinstance(tags, str): tags = [tags]
        cats = [c for c in fm.get('categories', []) if c]
        if isinstance(cats, str): cats = [cats]
        posts.append(dict(
            title=fm['title'], slug=fm['slug'], date=fm['date'], cover=fm['cover'],
            tags=tags, cats=cats,
            summary=fm.get('summary', fm.get('description', '')),
            description=fm.get('description', fm.get('summary', '')),
            keywords=fm.get('keywords', ''),
            body_html=md2html.convert(body),
            body_md=body,
        ))
    # newest first
    posts.sort(key=lambda p: p['date'], reverse=True)
    return posts

# ---------------------------------------------------------------- helpers
def url_for(p):
    d = datetime.date.fromisoformat(p['date'])
    return f"/{d.year}/{d.month:02d}/{d.day:02d}/{p['slug']}/"

def perm_for(p):
    return 'https://atcxigua.github.io' + url_for(p)

def esc(s):
    return html.escape(s, quote=False)

def date_iso(p):
    return p['date'] + 'T00:00:00+08:00'

def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True)

# ---------------------------------------------------------------- post page
POST_TPL = os.path.join(HERE, 'tpl_post.html')

def render_post(p, prev, nxt, blog):
    tpl = open(POST_TPL, encoding='utf-8').read()
    chips = '\n'.join(
        f'                <a href="/tags/{t}/"><span class="chip bg-color">{esc(t)}</span></a>'
        for t in p['tags']) or '                <span class="chip bg-color">无标签</span>'
    kw = p['keywords'] or (', '.join(p['tags'] + [p['title'], 'simple life']))
    out = (tpl
           .replace('{{TITLE}}', esc(p['title']))
           .replace('{{KEYWORDS}}', esc(kw))
           .replace('{{DESCRIPTION}}', esc(p['description']))
           .replace('{{COVER}}', esc(p['cover']))
           .replace('{{POST_TITLE}}', esc(p['title']))
           .replace('{{DATE}}', p['date'])
           .replace('{{TAGS}}', chips)
           .replace('{{BODY}}', p['body_html'])
           .replace('{{PERMALINK}}', perm_for(p)))
    out = out.replace('{{PREVNEXT}}', prenext_html(prev, nxt))
    d = datetime.date.fromisoformat(p['date'])
    path = os.path.join(blog, f"{d.year}", f"{d.month:02d}", f"{d.day:02d}", p['slug'], 'index.html')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write(out)
    return path

def card(p, aos='zoom-in'):
    return f'''            <div class="article col s12 m6 l4" data-aos="{aos}">
                <div class="card">
                    <a href="{url_for(p)}">
                        <div class="card-image">
                            <img src="{p['cover']}" class="responsive-img" alt="{esc(p['title'])}">
                            <span class="card-title">{esc(p['title'])}</span>
                        </div>
                    </a>
                    <div class="card-content article-content">
                        <div class="summary block-with-text">
                            {esc(p['summary'])}
                        </div>
                        <div class="publish-info">
                            <span class="publish-date">
                                <i class="far fa-clock fa-fw icon-date"></i>{p['date']}
                            </span>
                            <span class="publish-author">
                                <i class="fas fa-user fa-fw"></i>
                                atcXiGua
                            </span>
                        </div>
                    </div>
                </div>
            </div>'''

def prenext_html(prev, nxt):
    def one(p, side, label):
        badge = (f'<i class="far fa-dot-circle"></i>&nbsp;{label}' if side == 'left'
                 else f'{label}&nbsp;<i class="far fa-dot-circle"></i>')
        return f'''        <div class="article col s12 m6" data-aos="fade-up">
            <div class="article-badge {side}-badge text-color">
                {badge}
            </div>
            <div class="card">
                <a href="{url_for(p)}">
                    <div class="card-image">
                        <img src="{p['cover']}" class="responsive-img" alt="{esc(p['title'])}">
                        <span class="card-title">{esc(p['title'])}</span>
                    </div>
                </a>
                <div class="card-content article-content">
                    <div class="summary block-with-text">
                        {esc(p['summary'])}
                    </div>
                    <div class="publish-info">
                            <span class="publish-date">
                                <i class="far fa-clock fa-fw icon-date"></i>{p['date']}
                            </span>
                        <span class="publish-author">
                            <i class="fas fa-user fa-fw"></i>
                            atcXiGua
                        </span>
                    </div>
                </div>
            </div>
        </div>'''
    return ('<article id="prenext-posts" class="prev-next articles">\n'
            '    <div class="row article-row">\n        \n'
            + one(prev, 'left', '上一篇') + '\n        \n        '
            + one(nxt, 'right', '下一篇') +
            '\n        \n    </div>\n</article>')

# ---------------------------------------------------------------- timeline block
def timeline_block(p):
    d = datetime.date.fromisoformat(p['date'])
    return f'''        <div class="cd-timeline-block">
            <div class="cd-timeline-img year" data-aos="zoom-in-up">
                <a href="/archives/{d.year}">{d.year}</a>
            </div>
            <div class="cd-timeline-img month" data-aos="zoom-in-up">
                <a href="/archives/{d.year}/{d.month:02d}">{d.month:02d}</a>
            </div>
            <div class="cd-timeline-img day" data-aos="zoom-in-up">
                <span>{d.day}</span>
            </div>
            <article class="cd-timeline-content" data-aos="fade-up">
                <div class="article col s12 m6">
                    <div class="card">
                        <a href="{url_for(p)}">
                            <div class="card-image">
                                <img src="{p['cover']}" class="responsive-img" alt="{esc(p['title'])}">
                                <span class="card-title">{esc(p['title'])}</span>
                            </div>
                        </a>
                        <div class="card-content article-content">
                            <div class="summary block-with-text">
                                {esc(p['summary'])}
                            </div>
                            <div class="publish-info">
                                <span class="publish-date">
                                    <i class="far fa-clock fa-fw icon-date"></i>{p['date']}
                                </span>
                                <span class="publish-author">
                                    <i class="fas fa-user fa-fw"></i>
                                    atcXiGua
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </article>
        </div>
'''

def calendar_data(posts):
    if not posts:
        return ('["2026-01-01", 0]', '["2026-01-01", "2026-12-31"]')
    dates = sorted(datetime.date.fromisoformat(p['date']) for p in posts)
    start = dates[0]
    end = dates[-1]
    # span at least 12 months for a readable calendar
    if (end - start).days < 365:
        start = end - datetime.timedelta(days=365)
    counts = {}
    for p in posts:
        counts[p['date']] = counts.get(p['date'], 0) + 1
    rows, d = [], start
    while d <= end:
        rows.append(f'["{d.isoformat()}", {counts.get(d.isoformat(), 0)}]')
        d += datetime.timedelta(days=1)
    return ', '.join(rows), f'["{start.isoformat()}", "{end.isoformat()}"]'

def render_archive_page(tpl, posts, page_title, blog, out_path):
    cal, rng = calendar_data(posts)
    timeline = ''.join(timeline_block(p) for p in posts) or '        \n'
    out = (tpl.replace('{{PAGE_TITLE}}', esc(page_title))
              .replace('{{CALENDAR_DATA}}', cal)
              .replace('{{CALENDAR_RANGE}}', rng)
              .replace('{{TIMELINE}}', timeline))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, 'w', encoding='utf-8').write(out)

def list_page(tpl, posts, page_title, heading, blog, out_path):
    cards = '\n'.join(card(p, aos='fade-up') for p in posts) or '            \n'
    out = (tpl.replace('{{PAGE_TITLE}}', esc(page_title))
              .replace('{{HEADING}}', esc(heading))
              .replace('{{CARDS}}', cards))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, 'w', encoding='utf-8').write(out)

# ---------------------------------------------------------------- main
def regen(blog):
    posts = load_posts(blog)
    if not posts:
        raise SystemExit('no posts found under .posts/')
    print(f'loaded {len(posts)} posts: ' + ', '.join(p['slug'] for p in posts))

    # ---- post pages (prev/next chain)
    for i, p in enumerate(posts):
        prev = posts[i - 1] if i > 0 else p
        nxt = posts[i + 1] if i + 1 < len(posts) else p
        path = render_post(p, prev, nxt, blog)
        print('post page:', os.path.relpath(path, blog))

    # ---- index.html cards
    idx_path = os.path.join(blog, 'index.html')
    idx = open(idx_path, encoding='utf-8').read()
    cards = '\n             <!-- 隐藏某个文章 -->\n'.join(card(p) for p in posts)
    cards = '             <!-- 隐藏某个文章 -->\n' + cards + '\n              <!-- 隐藏某个文章 -->\n'
    idx = re.sub(r'(<div class="row article-row">)(.*?)(\s*</div>\s*</article>)',
                 lambda m: m.group(1) + '\n' + cards + '        ' + m.group(3),
                 idx, count=1, flags=re.S)
    open(idx_path, 'w', encoding='utf-8').write(idx)
    print('updated index.html cards')

    # ---- search.xml
    entries = []
    for p in posts:
        entries.append(
            f'''    <entry>
      <title>{esc(p['title'])}</title>
      <link href="{url_for(p)}"/>
      <url>{url_for(p)}</url>
      <content type="html"><![CDATA[{p['body_html']}]]></content>
    </entry>''')
    search = ('<?xml version="1.0" encoding="utf-8"?>\n<search>\n  \n    \n'
              + '\n    \n'.join(entries)
              + '\n  \n  \n</search>\n')
    open(os.path.join(blog, 'search.xml'), 'w', encoding='utf-8').write(search)
    print('regenerated search.xml')

    # ---- atom.xml
    updated = max(p['date'] for p in posts) + 'T00:00:00+08:00'
    feed = [f'''<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>simple life</title>
  <link rel="alternate" href="https://atcxigua.github.io/"/>
  <link rel="self" href="https://atcxigua.github.io/atom.xml"/>
  <id>https://atcxigua.github.io/</id>
  <updated>{updated}</updated>
  <author>
    <name>atcXiGua</name>
  </author>
  <subtitle>simple life</subtitle>''']
    for p in posts:
        feed.append(f'''
  <entry>
    <title>{esc(p['title'])}</title>
    <link rel="alternate" href="{perm_for(p)}"/>
    <id>{perm_for(p)}</id>
    <published>{date_iso(p)}</published>
    <updated>{date_iso(p)}</updated>
    <summary type="html"><![CDATA[{esc(p['summary'])}]]></summary>
    <content type="html"><![CDATA[{p['body_html']}]]></content>
  </entry>''')
    feed.append('\n</feed>\n')
    open(os.path.join(blog, 'atom.xml'), 'w', encoding='utf-8').write(''.join(feed))
    print('regenerated atom.xml')

    # ---- archives
    tpl_arch = open(os.path.join(HERE, 'tpl_archive.html'), encoding='utf-8').read()
    tpl_list = open(os.path.join(HERE, 'tpl_list.html'), encoding='utf-8').read()

    # prune stale archive dirs
    for d in glob.glob(os.path.join(blog, 'archives', '*')):
        if os.path.isdir(d) and not re.match(r'^\d{4}$', os.path.basename(d)):
            shutil.rmtree(d)
    for d in glob.glob(os.path.join(blog, 'archives', '*', '*')):
        if os.path.isdir(d) and not re.match(r'^\d{2}$', os.path.basename(d)):
            shutil.rmtree(d)

    # main archives page (all posts)
    render_archive_page(tpl_arch, posts, '归档', blog,
                        os.path.join(blog, 'archives', 'index.html'))
    print('regenerated archives/index.html')

    # year + month pages
    by_year = {}
    for p in posts:
        y = datetime.date.fromisoformat(p['date']).year
        by_year.setdefault(y, []).append(p)
    for y, yp in sorted(by_year.items(), reverse=True):
        render_archive_page(tpl_arch, yp, f'归档: {y}', blog,
                            os.path.join(blog, 'archives', str(y), 'index.html'))
        by_month = {}
        for p in yp:
            m = datetime.date.fromisoformat(p['date']).month
            by_month.setdefault(m, []).append(p)
        for m, mp in sorted(by_month.items(), reverse=True):
            render_archive_page(tpl_arch, mp, f'归档: {y}/{m}', blog,
                                os.path.join(blog, 'archives', str(y), f'{m:02d}', 'index.html'))
        print(f'regenerated archives/{y} (+{len(by_month)} months)')

    # ---- tags
    by_tag = {}
    for p in posts:
        for t in p['tags']:
            by_tag.setdefault(t, []).append(p)
    tag_idx = open(os.path.join(blog, 'tags', 'index.html'), encoding='utf-8').read()
    chips = '\n'.join(
        f'                <a href="/tags/{esc(t)}/"><span class="chip bg-color">{esc(t)}</span></a>'
        for t in sorted(by_tag)) or '                暂无标签'
    tag_idx = re.sub(r'(<div class="tag-chips">)(.*?)(</div>)',
                     lambda m: m.group(1) + '\n' + chips + '\n            ' + m.group(3),
                     tag_idx, count=1, flags=re.S)
    open(os.path.join(blog, 'tags', 'index.html'), 'w', encoding='utf-8').write(tag_idx)
    for t, tp in sorted(by_tag.items()):
        list_page(tpl_list, tp, f'标签: {t}', f'标签: {t}', blog,
                  os.path.join(blog, 'tags', t, 'index.html'))
    print(f'regenerated tags ({len(by_tag)} tags)')

    # ---- categories
    by_cat = {}
    for p in posts:
        for c in p['cats']:
            by_cat.setdefault(c, []).append(p)
    cat_idx = open(os.path.join(blog, 'categories', 'index.html'), encoding='utf-8').read()
    chips = '\n'.join(
        f'                <a href="/categories/{esc(c)}/"><span class="chip bg-color">{esc(c)}</span></a>'
        for c in sorted(by_cat)) or '                你目前还没有对文章进行分类.'
    cat_idx = re.sub(r'(<div class="tag-chips">)(.*?)(</div>)',
                     lambda m: m.group(1) + '\n' + chips + '\n            ' + m.group(3),
                     cat_idx, count=1, flags=re.S)
    open(os.path.join(blog, 'categories', 'index.html'), 'w', encoding='utf-8').write(cat_idx)
    for c, cp in sorted(by_cat.items()):
        list_page(tpl_list, cp, f'分类: {c}', f'分类: {c}', blog,
                  os.path.join(blog, 'categories', c, 'index.html'))
    print(f'regenerated categories ({len(by_cat)} categories)')

    return posts

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'regen'
    blog = DEFAULT_BLOG
    if '--blog' in sys.argv:
        blog = sys.argv[sys.argv.index('--blog') + 1]
    if cmd == 'regen':
        regen(blog)
        print('done. review changes, then run `git` to commit & push.')
    elif cmd == 'git':
        posts = regen(blog)
        titles = ', '.join(p['title'] for p in posts[:3])
        msg = f"blog: 发布文章 ({len(posts)} 篇) - {titles}"
        run(['git', 'add', '-A'], blog)
        run(['git', 'commit', '-m', msg], blog)
        run(['git', 'push', 'origin', 'master'], blog)
        print('committed & pushed')
    else:
        print(__doc__)

if __name__ == '__main__':
    main()

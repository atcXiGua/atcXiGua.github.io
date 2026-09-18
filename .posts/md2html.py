#!/usr/bin/env python3
"""Markdown -> hexo-theme-matery HTML converter (subset).

Supports: ATX headings (h2-h4, with headerlink anchors), paragraphs, fenced
code with language, GFM tables, blockquote, ordered/unordered lists (flat),
bold, inline code, links, images, thematic break, and inline HTML passthrough.
"""
import re

def _esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def _slug(text):
    """hexo-style heading id: strip tags, keep CJK, spaces->-, lower ascii."""
    t = re.sub(r'<[^>]+>', '', text)
    t = t.replace(' ', '-')
    return t

def _inline(s):
    """inline formatting: code, bold, links, images. escapes first."""
    s = _esc(s)
    # inline code
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    # images ![alt](url)
    s = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)',
               r'<img src="\2" alt="\1" class="lozad" data-src="\2">', s)
    # links [text](url)
    def link(m):
        txt, url = m.group(1), m.group(2)
        return f'<a target="_blank" rel="noopener" href="{url}">{txt}</a>'
    s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, s)
    # bold
    s = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
    # italic (avoid clashing with bold)
    s = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<em>\1</em>', s)
    # bare url
    s = re.sub(r'(?<!["\'>])(https?://[^\s<>&]+)',
               r'<a target="_blank" rel="noopener" href="\1">\1</a>', s)
    return s

def _table(lines):
    """GFM table -> <table>"""
    rows = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if re.match(r'^\|[\s:\-|]+\|?$', ln):
            continue  # separator
        cells = [c.strip() for c in ln.strip('|').split('|')]
        rows.append(cells)
    if not rows:
        return ''
    head = rows[0]
    body = rows[1:]
    out = ['<table>', '<thead>', '<tr>' + ''.join(f'<th>{_inline(c)}</th>' for c in head) + '</tr>', '</thead>']
    if body:
        out.append('<tbody>')
        for r in body:
            out.append('<tr>' + ''.join(f'<td>{_inline(c)}</td>' for c in r) + '</tr>')
        out.append('</tbody>')
    out.append('</table>')
    return '\n'.join(out)

_BLOCK_TAGS = ('div', 'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td', 'ul',
               'ol', 'li', 'p', 'blockquote', 'pre', 'code', 'article', 'section',
               'header', 'footer', 'aside', 'main', 'figure', 'figcaption', 'details',
               'summary', 'dl', 'dt', 'dd', 'form', 'fieldset', 'video', 'audio')


def _tag_delta(line):
    """net change in block-tag nesting for one line of raw HTML."""
    op = len(re.findall(r'<(%s)\b[^>]*(?<!/)>' % '|'.join(_BLOCK_TAGS), line))
    cl = len(re.findall(r'</(%s)>' % '|'.join(_BLOCK_TAGS), line))
    return op - cl


def _raw_html(lines, i, n):
    """consume a balanced raw-HTML block starting at lines[i]; return (html, next_i)"""
    block, depth = [], 0
    while i < n:
        ln = lines[i]
        depth += _tag_delta(ln)
        block.append(ln)
        i += 1
        if depth <= 0:
            break
    return '\n'.join(block), i


def convert(md):
    md = md.replace('\r\n', '\n')
    lines = md.split('\n')
    out, i, n = [], 0, len(lines)

    def flush_para(buf):
        if buf:
            txt = ' '.join(l.strip() for l in buf).strip()
            if txt:
                out.append(f'<p>{_inline(txt)}</p>')

    para = []
    while i < n:
        line = lines[i]

        # fenced code
        m = re.match(r'^\s*```(\w*)', line)
        if m:
            if para: flush_para(para); para = []
            lang = m.group(1)
            code, i = [], i + 1
            while i < n and not lines[i].strip().startswith('```'):
                code.append(lines[i]); i += 1
            i += 1  # skip closing fence
            cls = f' class="language-{lang}"' if lang else ''
            pre_cls = f' class="language-{lang}"' if lang else ''
            code_text = _esc('\n'.join(code))
            out.append(f'<pre{pre_cls}><code{cls}>{code_text}</code></pre>')
            continue

        # table
        if line.strip().startswith('|') and i + 1 < n and re.match(r'^\s*\|[\s:\-|]+\|?\s*$', lines[i + 1]):
            if para: flush_para(para); para = []
            tbl, i = [line], i + 1
            while i < n and lines[i].strip().startswith('|'):
                tbl.append(lines[i]); i += 1
            out.append(_table(tbl))
            continue

        # heading
        m = re.match(r'^(#{2,4})\s+(.*)$', line)
        if m:
            if para: flush_para(para); para = []
            level = len(m.group(1))
            text = m.group(2).strip()
            inner = _inline(text)
            sid = _slug(re.sub(r'<[^>]+>', '', inner))
            out.append((f'<h{level} id="{sid}">'
                        f'<a href="#{sid}" class="headerlink" title="{re.sub(r"<[^>]+>", "", inner)}"></a>'
                        f'{inner}</h{level}>'))
            i += 1
            continue

        # h1 in body -> h2 (post title is the only h1, in the cover)
        m = re.match(r'^#\s+(.*)$', line)
        if m:
            if para: flush_para(para); para = []
            text = m.group(1).strip()
            inner = _inline(text)
            sid = _slug(re.sub(r'<[^>]+>', '', inner))
            out.append((f'<h2 id="{sid}">'
                        f'<a href="#{sid}" class="headerlink" title="{re.sub(r"<[^>]+>", "", inner)}"></a>'
                        f'{inner}</h2>'))
            i += 1
            continue

        # thematic break
        if re.match(r'^\s*([-*_])\1{2,}\s*$', line):
            if para: flush_para(para); para = []
            out.append('<hr>')
            i += 1
            continue

        # blockquote
        if line.strip().startswith('>'):
            if para: flush_para(para); para = []
            quote, i = [], i
            while i < n and lines[i].strip().startswith('>'):
                quote.append(re.sub(r'^\s*>\s?', '', lines[i])); i += 1
            qtext = ' '.join(l.strip() for l in quote).strip()
            out.append(f'<blockquote><p>{_inline(qtext)}</p></blockquote>')
            continue

        # list
        m = re.match(r'^\s*[-*+]\s+(.*)$', line)
        m2 = re.match(r'^\s*\d+\.\s+(.*)$', line)
        if m or m2:
            if para: flush_para(para); para = []
            ordered = bool(m2)
            tag = 'ol' if ordered else 'ul'
            items, i = [], i
            pat = re.compile(r'^\s*(\d+\.|[-*+])\s+(.*)$')
            while i < n and pat.match(lines[i]):
                items.append(pat.match(lines[i]).group(2)); i += 1
            out.append(f'<{tag}>')
            for it in items:
                out.append(f'<li>{_inline(it)}</li>')
            out.append(f'</{tag}>')
            continue

        # blank line ends paragraph
        if not line.strip():
            flush_para(para); para = []
            i += 1
            continue

        # raw HTML block (balanced, passed through verbatim)
        if re.match(r'^\s*<', line):
            if para: flush_para(para); para = []
            html_block, i = _raw_html(lines, i, n)
            out.append(html_block)
            continue

        para.append(line)
        i += 1

    flush_para(para)
    return '\n'.join(out)

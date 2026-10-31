#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
memory_tool.py — 项目记忆工具（零第三方依赖，标准库实现）
配合 project-memory skill 的 SKILL.md 协议使用。

用法（Windows 本机可用 `py memory_tool.py`，其他环境用 `python3 memory_tool.py`）：

  py memory_tool.py init [--root DIR]                    # 创建 .memory/MEMORY.md（已存在则跳过）
  py memory_tool.py add --title T --content C            # 追加/更新一条记忆（标题已存在则更新）
                         [--section 结论|待办|数据|陷阱] [--status 完成|进行中|已废弃|存疑] [--root DIR]
  py memory_tool.py search 关键词 [--root DIR]           # 关键词检索，输出匹配条目
  py memory_tool.py list [--root DIR]                    # 列出全部条目
  py memory_tool.py compact [--max-entries N] [--root DIR]  # 条目超限时把最旧条目移入 MEMORY-archive.md

记忆文件：<root>/.memory/MEMORY.md，格式遵循 SKILL.md 第 1 节。
"""

import argparse
import datetime
import re
import sys
from pathlib import Path

# ---------- 常量 ----------
SECTION_MAP = {
    "结论": "关键结论与决策",
    "待办": "未完成事项",
    "数据": "关键事实与数据",
    "陷阱": "已知陷阱与注意事项",
}
DEFAULT_SECTION = "关键结论与决策"
ENTRY_RE = re.compile(r"^### 条目 (\d{8}-\d{2}): (.+?)\s*$", re.M)

TEMPLATE = """# 项目记忆：{name}

> 最后更新：{ts}
> 条目总数：0

## 项目概况
（一句话说明项目目标 / 研究问题 / 核心任务。）

## 关键结论与决策

## 未完成事项

## 关键事实与数据

## 已知陷阱与注意事项
"""


# ---------- 基础读写 ----------
def mem_path(root: Path) -> Path:
    return root / ".memory" / "MEMORY.md"


def archive_path(root: Path) -> Path:
    return root / ".memory" / "MEMORY-archive.md"


def ensure_init(root: Path, name: str = "未命名项目") -> bool:
    """确保 MEMORY.md 存在，不存在则创建。返回 True 表示本次新建。"""
    p = mem_path(root)
    if p.exists():
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    p.write_text(TEMPLATE.format(name=name, ts=now), encoding="utf-8")
    return True


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def write_text(p: Path, text: str) -> None:
    p.write_text(text, encoding="utf-8")


def normalize_blank(text: str) -> str:
    """把连续空行压成最多一个空行，保证 markdown 可读性。"""
    return re.sub(r"\n{3,}", "\n\n", text)


def update_header(text: str) -> str:
    """更新文件头部的最后更新时间和条目总数。"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    count = len(ENTRY_RE.findall(text))
    text = re.sub(r"> 最后更新：.*", f"> 最后更新：{now}", text, count=1)
    text = re.sub(r"> 条目总数：.*", f"> 条目总数：{count}", text, count=1)
    return text


def split_entries(text: str):
    """按条目块切分。块 = 条目标题行 → 下一个条目标题或分区标题或文件尾。
    返回 (头部, [(编号, 标题, 块文本), ...])。条目块绝不吞分区标题。"""
    starts = [m.start() for m in ENTRY_RE.finditer(text)]
    if not starts:
        return text, []
    head = text[: starts[0]]
    # 边界：所有条目标题行 + 所有分区标题行
    bounds = set(starts)
    for m in re.finditer(r"^## ", text, re.M):
        bounds.add(m.start())
    bounds = sorted(bounds)
    blocks = []
    for pos in starts:
        idx = bounds.index(pos)
        end = bounds[idx + 1] if idx + 1 < len(bounds) else len(text)
        m = ENTRY_RE.match(text, pos, end)
        blocks.append((m.group(1), m.group(2).strip(), text[pos:end]))
    return head, blocks


def next_entry_id(text: str) -> str:
    today = datetime.datetime.now().strftime("%Y%m%d")
    max_seq = 0
    for num, _title, _block in split_entries(text)[1]:
        if num.startswith(today + "-"):
            seq = int(num.split("-")[1])
            max_seq = max(max_seq, seq)
    return f"{today}-{max_seq + 1:02d}"


# ---------- 子命令 ----------
def cmd_init(args) -> None:
    root = Path(args.root).resolve()
    created = ensure_init(root, name=args.name)
    if created:
        print(f"[init] 已创建 {mem_path(root)}")
    else:
        print(f"[init] 已存在：{mem_path(root)}")


def cmd_add(args) -> None:
    root = Path(args.root).resolve()
    created = ensure_init(root, name=args.name)
    if created:
        print(f"[add] 记忆文件不存在，已自动创建 {mem_path(root)}")
    p = mem_path(root)
    text = read_text(p)

    section = SECTION_MAP.get(args.section, DEFAULT_SECTION)
    title = args.title.strip()
    content = args.content.strip()
    status = args.status if args.status else "进行中"

    # 标题已存在 -> 精确替换该条目块（条目标题行 → 下一个条目标题/分区标题/文件尾），其余文本原样保留
    match = None
    for m in ENTRY_RE.finditer(text):
        if m.group(2).strip() == title:
            match = m
            break
    if match:
        start = match.start()
        end = len(text)
        for m in ENTRY_RE.finditer(text):
            if start < m.start() < end:
                end = m.start()
        for m in re.finditer(r"^## ", text, re.M):
            if start < m.start() < end:
                end = m.start()
        new_block = f"### 条目 {match.group(1)}: {title}\n- 内容：{content}\n- 状态：{status}\n"
        text = text[:start] + new_block + text[end:]
        text = normalize_blank(text)
        print(f"[add] 已更新条目 {match.group(1)}：{title}")
        write_text(p, update_header(text))
        return

    # 标题不存在 -> 新建条目，插入到目标分区末尾
    entry_id = next_entry_id(text)
    new_block = f"### 条目 {entry_id}: {title}\n- 内容：{content}\n- 状态：{status}\n"
    section_pos = text.find(f"## {section}\n")
    if section_pos == -1:
        # 分区不存在：追加到文件末尾
        text = text.rstrip() + f"\n\n## {section}\n\n" + new_block
    else:
        # 分区末尾 = 下一个分区标题位置或文件尾
        after = text[section_pos + len(f"## {section}\n"):]
        next_sec = re.search(r"^## ", after, re.M)
        seg_end = section_pos + len(f"## {section}\n") + (next_sec.start() if next_sec else len(after))
        text = text[:seg_end] + "\n" + new_block + "\n" + text[seg_end:]
    text = normalize_blank(text)
    print(f"[add] 已新增条目 {entry_id}：{title}（分区：{section}）")
    write_text(p, update_header(text))


def cmd_search(args) -> None:
    root = Path(args.root).resolve()
    p = mem_path(root)
    if not p.exists():
        print(f"[search] 记忆文件不存在：{p}（先执行 init）")
        return
    text = read_text(p)
    kw = args.keyword.strip()
    _head, blocks = split_entries(text)
    hits = [b for _n, _t, b in blocks if kw.lower() in b.lower()]
    if not hits:
        print(f"[search] 未找到包含「{kw}」的条目")
        return
    print(f"[search] 找到 {len(hits)} 条匹配「{kw}」：\n")
    for b in hits:
        print(b.strip() + "\n" + "-" * 40)


def cmd_list(args) -> None:
    root = Path(args.root).resolve()
    p = mem_path(root)
    if not p.exists():
        print(f"[list] 记忆文件不存在：{p}")
        return
    _head, blocks = split_entries(read_text(p))
    if not blocks:
        print("[list] 暂无条目")
        return
    print(f"[list] 共 {len(blocks)} 条：\n")
    for num, title, block in blocks:
        st = re.search(r"^- 状态：(.+)$", block, re.M)
        stv = st.group(1).strip() if st else "-"
        print(f"  {num}  [{stv}] {title}")


def cmd_compact(args) -> None:
    root = Path(args.root).resolve()
    p = mem_path(root)
    if not p.exists():
        print(f"[compact] 记忆文件不存在：{p}")
        return
    text = read_text(p)
    head, blocks = split_entries(text)
    if len(blocks) <= args.max_entries:
        print(f"[compact] 条目数 {len(blocks)} <= 上限 {args.max_entries}，无需归档")
        return
    # 按编号排序，最旧的排最前（编号 YYYYMMDD-NN 可直接比较）
    blocks.sort(key=lambda x: x[0])
    overflow = blocks[: len(blocks) - args.max_entries]
    keep = blocks[len(blocks) - args.max_entries:]
    text = normalize_blank(head + "".join(b for _n, _t, b in keep))
    ap = archive_path(root)
    existing = read_text(ap)
    moved = "\n".join(b.strip() for _n, _t, b in overflow)
    if existing:
        new_archive = existing.rstrip() + f"\n\n## 归档（{datetime.date.today()}）\n\n" + moved + "\n"
    else:
        new_archive = f"# 项目记忆归档\n\n## 归档（{datetime.date.today()}）\n\n" + moved + "\n"
    write_text(ap, new_archive)
    write_text(p, update_header(text))
    print(f"[compact] 已归档 {len(overflow)} 条至 {ap}，保留 {len(keep)} 条")


# ---------- 入口 ----------
def main() -> None:
    parser = argparse.ArgumentParser(description="项目记忆工具（零依赖）")
    # 公共参数：放入父解析器，使所有子命令都能接受
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--root", default=".", help="项目根目录（默认当前目录）")
    parent.add_argument("--name", default="未命名项目", help="init 时使用的项目名称")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", parents=[parent], help="创建记忆文件")
    p_init.set_defaults(fn=cmd_init)

    p_add = sub.add_parser("add", parents=[parent], help="追加/更新一条记忆")
    p_add.add_argument("--title", required=True, help="条目标题")
    p_add.add_argument("--content", required=True, help="条目正文")
    p_add.add_argument("--section", choices=list(SECTION_MAP.keys()), default=None, help="分区")
    p_add.add_argument("--status", choices=["完成", "进行中", "已废弃", "存疑"], default=None)
    p_add.set_defaults(fn=cmd_add)

    p_search = sub.add_parser("search", parents=[parent], help="关键词检索")
    p_search.add_argument("keyword", help="检索关键词")
    p_search.set_defaults(fn=cmd_search)

    p_list = sub.add_parser("list", parents=[parent], help="列出全部条目")
    p_list.set_defaults(fn=cmd_list)

    p_compact = sub.add_parser("compact", parents=[parent], help="归档最旧条目")
    p_compact.add_argument("--max-entries", type=int, default=200)
    p_compact.set_defaults(fn=cmd_compact)

    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()

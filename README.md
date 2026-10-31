# project-memory

Project-level cross-session memory skill for AI agents (Codex / Doubao).

项目级跨会话记忆 Skill：同一项目内智能体自动读写 `.memory/MEMORY.md`，新会话可继承旧会话的结论、待办、数据与陷阱。

## 文件结构

| 文件 | 说明 |
| --- | --- |
| `SKILL.md` | 记忆协议规范：记忆文件位置、分区、条目格式、写入与读取时机 |
| `memory_tool.py` | 零依赖命令行工具（仅 Python 标准库），提供 `init/add/search/list/compact` 子命令 |

## 记忆协议（摘要）

- 记忆文件固定为项目根目录 `.memory/MEMORY.md`
- 分区：`## 结论` / `## 待办` / `## 数据` / `## 陷阱`
- 条目格式：`### 条目 YYYYMMDD-NN: 标题`，正文含 内容 / 依据 / 状态
- 写入时机与会话结束挂钩；新会话先读取再回答

## 安装

将 `SKILL.md` 与 `memory_tool.py` 放入智能体的 skills 目录：

- Codex：`~/.codex/skills/project-memory/`
- 豆包：豆包技能目录 `skills/project-memory/`

## 用法

```bash
python memory_tool.py init --root <项目目录>
python memory_tool.py add --root <项目目录> --section 结论 --title "标题" --content "内容"
python memory_tool.py search --root <项目目录> --query 关键词
python memory_tool.py list --root <项目目录>
```

## License

MIT

# AWR — Agent Web Review (Claude Code Plugin)

在浏览器里点网页元素加评论，Claude Code 用 `/awr` 拉取评论、改代码、resolve。Pull 模型。

## 依赖（外部，需独立运行）

1. **AWR server** — Python 服务，跑在 `localhost:9876`，MCP endpoint `http://localhost:9876/mcp`。
2. **Chrome 扩展** — 装好，登录后可在网页元素上加评论（可选截图）。

## 用法

在 CC 会话里说 `/awr`（或"处理 web 评论"），CC 会：

1. 调 `awr_get_comments(status="open")` 拉取所有未处理评论
2. 逐条读评论、定位源码、改代码
3. 调 `awr_resolve_comment` 标记已处理（浏览器刷新后看到绿色勾号）

## 安装

把本目录复制/软链到 `~/.claude/plugins/awr/`：

```bash
cp -r awr-claude-plugin ~/.claude/plugins/awr
```

重启 Claude Code 后，插件自动加载 MCP 配置并注册 `/awr` 命令。

## 结构

```
awr-claude-plugin/
├── plugin.json                 # 插件清单
├── .mcp.json                   # MCP 配置（指向 localhost:9876/mcp）
├── commands/
│   └── awr.md                  # /awr 命令（触发完整闭环）
└── skills/
    └── awr-workflow/
        └── SKILL.md            # CC 处理评论的工作流指导（含截图处理）
```

> 本切片为单项目：`/awr` 拉取所有 open 评论。多项目映射（`project_path` 过滤 + `/awr-setup` 端口探测）见后续 issue。

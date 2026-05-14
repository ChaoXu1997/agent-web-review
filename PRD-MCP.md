# MCP Integration & Agent Auto-Run — PRD

## Problem Statement

当前 Agent Web Review 的数据流是单向的：用户添加评论 → agent 手动 curl 读取。用户希望一键将评论提交给 Hermes Agent，agent 自动读取评论、修改代码、标记 resolved，形成完整闭环。同时 agent 应通过 MCP 协议原生集成，而非每次手动 curl。

## Solution

将 Python server 同时实现为 MCP server（stdio transport），暴露评论管理 tools。Hermes 配置连接后自动获得这些 tools。扩展 popup 新增"Send to Hermes"按钮，点击后 server 自动启动 Hermes 实例并注入评论上下文，Hermes 自动处理所有 open 评论。

## Modules

### 1. MCP Server（深模块）

将已有 storage 层包装为 MCP tools，通过 stdio transport 暴露。核心复杂度在于 MCP 协议实现，对外接口极简——三个 tool 函数。所有 agent 交互通过这三个 tool 完成，agent 无需了解 HTTP API 细节。

### 2. 项目路径映射

维护 page_url → 本地项目目录的映射关系。agent 启动时需要知道在哪个目录下工作。存储为 JSON 文件，提供 CRUD API。

### 3. Agent 启动调度

"Send to Hermes"按钮的 server 端逻辑。收集当前页面的 open 评论，查找对应项目路径，构建 prompt，通过 subprocess 在 Ghostty 中启动 Hermes。Hermes 启动后通过 MCP tools 读取完整评论数据并自动处理。

### 4. Popup UI

扩展 popup 新增"Send to Hermes"按钮和项目路径映射配置面板。按钮仅在有 open 评论时显示，点击后调用 server API 触发 agent 启动。

## User Stories

1. As a user, I want to click a "Send to Hermes" button in the popup to automatically start Hermes with my review comments, so that I don't need to manually copy comments to the agent.
1. As a user, I want Hermes to automatically read all open comments for the current page and process them, so that the review-to-fix loop is fully automated.
1. As a user, I want Hermes to mark comments as resolved after processing each one, so that I can track which reviews have been addressed.
1. As a user, I want to configure which page URL maps to which local project directory, so that Hermes opens in the correct working directory.
1. As an agent (Hermes), I want to use MCP tools to read comments, so that I can natively access review data without manual HTTP calls.
1. As an agent (Hermes), I want to use MCP tools to mark comments as resolved, so that the user can see which reviews are done.
1. As an agent (Hermes), I want to receive the page URL and project context on startup, so that I know which page and codebase to work on.
1. As a user, I want the "Send to Hermes" button to only appear when there are open comments, so that the UI stays clean.
1. As a user, I want to manage URL-to-project mappings in the popup, so that I can configure different projects for different dev servers.
1. As a user, I want to see feedback when Hermes is launched (success/error), so that I know if the agent started correctly.

## Implementation Decisions

- **MCP SDK**: 使用官方 Python SDK (`mcp[cli]`)，FastMCP 封装，stdio transport。server 文件为 `server/mcp_server.py`，可独立运行也可被 import。
- **MCP Tool 命名**: 使用 `awr_` 前缀避免命名冲突：`awr_get_comments`、`awr_resolve_comment`、`awr_delete_comment`。
- **Agent 启动命令**: 默认 `ghostty -e hermes`，用户可在 popup 中配置。server 通过 `subprocess.Popen` 在新终端窗口中启动。
- **Prompt 注入**: server 构建启动 prompt，包含 page_url、项目路径、open 评论摘要（id + selector + comment_text）。Hermes 启动后通过 MCP tools 获取完整数据，prompt 只提供上下文和指令。
- **项目路径映射存储**: 存储在 `data/projects.json`，格式为 `{"http://localhost:3000": "/home/chao/projects/my-app"}`。提供 `GET/POST/DELETE /api/projects` CRUD API。
- **MCP 与 HTTP 共存**: MCP server 和 HTTP server 可以同时运行（各自独立进程），也可以合并为单进程。采用合并方案——HTTP server 启动时可选启用 MCP mode（通过命令行参数 `--mcp`），默认仅运行 HTTP。
- **自动处理 prompt**: Hermes 启动时接收的 prompt 指令："请读取当前页面所有 open 评论（通过 MCP tool awr_get_comments），逐条处理：修改代码后调用 awr_resolve_comment 标记已处理。项目目录: {path}，页面URL: {url}。"
- **Hermes MCP 配置**: 用户需在 `~/.hermes/config.yaml` 中手动添加 MCP server 配置（一次性操作），server README 中提供配置示例。

## Testing Decisions

- **MCP tools 测试**: 通过 FastMCP 的测试机制验证 tool 输入输出。测试 awr_get_comments 的过滤参数、awr_resolve_comment 的状态更新、awr_delete_comment 的删除行为。
- **项目映射 API 测试**: 与现有 server 测试模式一致，测试 CRUD 操作和边界情况。
- **Agent 启动测试**: 仅验证 subprocess 调用参数正确性，不验证 Hermes 实际行为（需要终端环境）。
- **不测 popup UI**: Chrome 扩展 UI 需要浏览器环境，跳过。

## Out of Scope

- Claude Code 集成（后续可扩展）
- Agent 执行进度实时展示
- Agent 执行结果的自动验证
- 多 agent 同时工作
- 远程 MCP server（SSE/HTTP transport）
- 非 Ghostty 终端支持（后续可扩展）

## Further Notes

- `pip install "mcp[cli]"` 是唯一的额外依赖，打破了"stdlib only"约束，但 MCP 是核心功能需求
- Hermes config.yaml 配置示例：
  ```yaml
  mcp_servers:
    awr:
      command: "python3"
      args: ["/home/chao/projects/agent-web-review/server/mcp_server.py"]
      timeout: 30
  ```
- 现有 HTTP API 和测试完全不受影响，MCP 功能是增量添加

## QA Strategy

1. **MCP tools 验证**: 使用 MCP Inspector（`npx @modelcontextprotocol/inspector`）连接 MCP server，测试三个 tool 的输入输出
2. **Hermes 集成验证**: 配置 Hermes MCP server 后，在对话中确认 `awr_get_comments` 等 tool 可用
3. **端到端验证**: 打开测试页面 → 添加评论 → 点"Send to Hermes" → Hermes 启动并自动处理评论 → 刷新页面确认 resolved marker
4. **项目映射验证**: 在 popup 中添加/删除映射，确认"Send to Hermes"使用正确的工作目录
5. **回归测试**: 确认现有 55 个 Python 测试全部通过

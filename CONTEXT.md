# Agent Web Review — Context

Chrome 扩展 + Python 本地服务器，让用户在网页上点击元素添加评论，AI agent（Claude Code 等）通过 MCP tools 读取并处理，浏览器实时显示处理状态。主要服务于本地前端开发场景（localhost）。

## Language

**Comment**:
用户在页面上对某个元素或区域添加的一条审查意见。包含元素定位信息（selector、XPath、截图）和评论文本。
_Avoid_: 反馈、review、annotation

**Marker**:
评论在页面上对应的可视编号圆点，钉在被评论元素右上角。点击可展开详情面板。
_Avoid_: 徽标、pin、tag

**Inspect mode**:
扩展激活的交互模式，鼠标 hover 高亮元素，点击打开评论面板。通过 Alt+Shift+C 或 popup 按钮切换。
_Avoid_: 审查模式、review mode

**Resolved**:
agent 处理完某条评论后将状态从 open 改为 resolved，浏览器扩展经 SSE 实时收到推送显示绿色勾号。
_Avoid_: done、completed、fixed

**Channel**:
曾考虑的方案（Claude Code v2.1.80+ 的 MCP server 机制，通过 `<channel>` 标签 push 评论进会话），实测后被否决（ADR-001 决策 5：GLM 代理静默禁用 channels，需 Anthropic 官方认证），当前不采用。
_Avoid_: 推送、通知、事件流

**Pull 模型**（当前采用）:
AI agent 主动调 MCP tool（`awr_get_comments(project_path=CWD)`）拉取评论，修改代码后调 `awr_resolve_comment` 标记已处理。通过 `/awr` 命令一键触发完整闭环。
_Avoid_: 主动拉取、定时轮询

## Relationships

- 一条 **Comment** 对应一个 **Marker**
- 一个 **Marker** 属于一条 **Comment**
- **Comment** 有两种状态: open（待处理）→ resolved（已处理）
- 用户通过 **Inspect mode** 创建 **Comment**，浏览器扩展 POST 到 server 存储
- **Pull 模型**: agent 调 `awr_get_comments` 拉取评论，修改代码后调 `awr_resolve_comment` 标记 resolved，SSE 推送实时通知浏览器扩展

## Workflow

### Pull 模型（正式方案，Channel 因 GLM 代理不兼容被否决）

1. 用户在浏览器中打开前端页面（dev server）
2. 用户开启 Inspect mode，点击元素，输入评论文本
3. 评论 POST 到 server 存储（in-memory / JSON 文件，免鉴权单人本地）
4. 用户在 CC 中说 `/awr` 或"处理 web 评论"
5. CC 调 MCP tool `awr_get_comments(project_path=<CWD>)` 拉取评论
6. CC 根据评论的 `element_html`、`element_selector`、`comment_text` 定位源码并修改
7. CC 调 `awr_resolve_comment` 标记已处理
8. 用户刷新页面，看到 resolved marker（绿色勾号）

## Flagged ambiguities

- agent 更新评论时只改 status 不填 reply 文本——这是用户的明确选择，保持简单。
- ~~Channel 模型下是否需要保留截图（screenshot_b64）？~~ Channel 否决后不适用。
- ~~GLM 代理下 Channels 是否可用？~~ **已实测否决**（2026-06-23）：`[claudeai-mcp] Disabled: API-key auth precedence active`，channels 需要 Anthropic 官方认证。
- 存储层简化方向：砍 users/projects/鉴权，保留评论基本存储（in-memory 或 JSON 文件）。

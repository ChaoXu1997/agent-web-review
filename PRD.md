# Comment Lifecycle & Bug Fixes — PRD

## Problem Statement

Agent Web Review 当前只支持创建和删除 Comment，缺少 agent 处理完成后的反馈回路。用户无法知道 agent 是否处理了某条评论、处理结果如何。同时存在两个影响使用体验的 bug：页面刷新时 marker 重复叠加，以及 MutationObserver 在 SPA 页面上性能过激。

## Solution

引入 Comment 状态生命周期（open → resolved），让 agent 处理完评论后标记为 resolved 而非直接删除。用户刷新页面后能直观看到哪些评论已处理、哪些待处理，确认后可批量清除已处理评论。同时修复两个已知 bug。

## Modules

### 1. Comment Status API（深模块）

封装 Comment 状态变更逻辑的 server 端 API。接口极简——一个 PATCH 端点接受 comment id 和目标 status，校验合法性后写入存储并广播 SSE 事件。所有状态转换规则集中在此模块，content script 和 agent 只通过这个接口交互。

### 2. Resolved Marker 渲染

Content script 中区分 open/resolved 两种 Marker 的视觉呈现。Resolved Marker 使用绿色勾号样式，点击后展开详情面板显示原文和当前状态。这是用户感知 agent 工作成果的核心交互。

### 3. Comment 加载去重

修复页面刷新或多次 loadComments 调用时 marker 重复叠加的 bug。在加载前清除已有 marker，确保与 server 数据一致。

### 4. MutationObserver 优化

将当前 observe 整个 document.body childList + subtree 的策略改为更保守的方式，避免 SPA 页面（React/Vue）频繁 DOM 变更导致不必要的 marker 重定位。

### 5. 批量清除 UI

在 popup 中提供"清除已处理评论"按钮，调用已有的 DELETE API 按 status 过滤删除。属于轻量 UI 入口，逻辑委托给 server 端。

## User Stories

1. As a user, I want to see which Comments have been resolved by an agent, so that I can track progress of my review feedback.
1. As a user, I want resolved Comments to display a green checkmark Marker on the page, so that I can visually distinguish them from open ones at a glance.
1. As a user, I want to click a resolved Marker and see a detail panel showing the original comment text and resolved status, so that I can verify what was reviewed.
1. As a user, I want to batch clear all resolved Comments via the popup, so that I don't have to delete them one by one after verification.
1. As a user, I want the popup comment list to visually differentiate open and resolved Comments (different marker color/icon), so that I can scan the list quickly.
1. As an agent (Hermes / Claude Code), I want to mark a Comment as resolved via a PATCH API with just the comment id and status, so that I can signal completion without writing reply text.
1. As an agent, I want to filter Comments by status when fetching (e.g. only open ones), so that I don't re-read already resolved Comments.
1. As an agent, I want the PATCH response to return the updated Comment, so that I can confirm the status change succeeded.
1. As a user, I want page refresh to not create duplicate Markers for the same Comment, so that the page stays clean after reload.
1. As a user, I want the extension to not cause performance issues on SPA pages with frequent DOM updates, so that my development workflow is not interrupted.
1. As an agent, I want the SSE stream to include a "comment_resolved" event, so that I can subscribe to status changes in real-time if needed.
1. As a user, I want the popup to show a count of open vs resolved Comments, so that I can quickly assess review progress.

## Implementation Decisions

- **状态值**: Comment.status 使用字符串枚举 "open" | "resolved"，与现有 "open" 默认值兼容，不破坏已有数据。
- **PATCH API 设计**: `PATCH /api/comments/:id`，body 为 `{"status": "resolved"}`。只接受 "resolved" 作为目标值（open → resolved 单向转换），拒绝无效状态值返回 400。保持接口最小化。
- **无 reply 字段**: 用户明确选择 agent 只改状态不留处理说明，Comment model 不新增字段。
- **批量清除 API**: 复用现有 `DELETE /api/comments?page_url=<url>` 模式，新增 `?status=resolved` 查询参数支持按状态过滤删除。服务端组合 page_url + status 两个可选过滤条件。
- **GET 列表过滤**: `GET /api/comments` 新增 `?status=open` 查询参数，支持按状态过滤。agent 可以只拉取待处理的评论。
- **SSE 事件**: 新增 "comment_resolved" 事件类型，广播更新后的完整 Comment 对象。content script 监听此事件更新对应 Marker 样式。
- **Marker 去重策略**: loadComments 时先清除所有已有 Marker DOM 节点，重置 markerCount，然后根据 server 返回的完整列表重新渲染。简单可靠，不依赖本地状态同步。
- **MutationObserver 优化**: 移除全局 childList + subtree 观察。改为仅在 activate 时做一次全量 marker 定位，之后仅在 scroll/resize 事件中重定位。如果后续发现定位漂移问题，可以改为更精细的 ResizeObserver 策略。
- **删除 showcase.html**: 此文件是静态展示 mockup，不属于功能代码，直接删除。

## Testing Decisions

- **测试什么**: 测试外部行为（API 输入输出、状态转换规则、过滤逻辑），不测试 DOM 渲染细节。
- **新增 server 测试**:
  - PATCH 端点：成功更新状态、无效 comment id 返回 404、无效 status 值返回 400、非法 id 格式返回 400。
  - GET 过滤：按 status=open 过滤只返回 open 评论、按 status=resolved 过滤、组合 page_url + status 过滤、无匹配返回空数组。
  - DELETE 过滤：按 status=resolved 删除只清除 resolved 评论、组合 page_url + status 过滤。
  - SSE 事件：comment_resolved 事件在 PATCH 后正确广播。
- **先例**: 现有 test_server.py 有 19 个 API 测试，test_storage.py 有 11 个存储测试。新测试遵循相同模式（setUp 创建临时目录，tearDown 清理）。
- **不测 content script**: Content script 的 DOM 交互需要浏览器环境，当前测试框架不支持，跳过。

## Out of Scope

- Comment 编辑功能（修改原文）
- Comment 回复功能（agent 或用户追加文本）
- 暗色主题 / UI 视觉升级
- 多用户 / 协作场景
- 评论导出
- 状态回退（resolved → open）
- 非 localhost 场景的专项优化

## Further Notes

- 本次改动完全向后兼容：现有 open 状态的评论不受影响，新字段/参数都是可选的。
- agent 集成示例：`curl -X PATCH http://localhost:9876/api/comments/<id> -H "Content-Type: application/json" -d '{"status":"resolved"}'`
- Hermes Agent 可以通过 terminal 工具直接调用 curl 完成评论标记，Claude Code 同理。

## QA Strategy

1. **Server API 验证**: 启动本地服务器，用 curl 测试 PATCH/GET/DELETE 的新增过滤参数，确认状态转换、过滤、SSE 事件正确。
2. **扩展手动测试**: 加载扩展到 Chrome，在 showcase 页面或任意 localhost 页面创建评论，通过 curl 模拟 agent 标记 resolved，刷新页面验证 marker 视觉和交互。
3. **Bug 回归**: 刷新页面多次确认无重复 marker；在 React/Vue dev server 页面开启 inspect mode 确认无卡顿。
4. **Popup 验证**: 打开 popup 确认评论列表中 open/resolved 区分显示、批量清除按钮工作正常、计数准确。
5. **Agent 端到端**: Hermes 或 Claude Code 读取评论 → 标记 resolved → 用户确认，走完完整闭环。

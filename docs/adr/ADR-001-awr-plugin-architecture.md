# ADR-001: AWR Claude Code 插件化架构

## 状态

**Accepted** — Pull 模型确定，Channel 模型因 GLM 代理不兼容被否决。

## 背景

用户希望把 Agent Web Review（Chrome 扩展 + Python 服务器）开发成 Claude Code 插件，辅助 UI 开发。核心诉求：在浏览器里点元素加评论 → 评论送达正在运行的 CC 会话 → CC 改代码 → 反馈回来。

## 决策

### 1. 插件边界：瘦客户端 ✅

**决定**: 插件只打包 MCP 配置 + skills + commands，不包含 server 源码和 Chrome 扩展。server 和扩展作为外部依赖，独立运行。

**理由**:
- Claude Code 插件本质是轻量配置+工作流指导，不是运行时服务
- server/扩展是长期运行的重组件，已有成熟部署（systemd）
- 瘦客户端让插件可独立更新、最小侵入

### 2. 分发对象：先本地 ✅

**决定**: 先只给自己本地使用，server URL 硬编码 localhost:9876。发布到 marketplace 列为后续 milestone。

### 3. 辅助深度：纯打包 + 填缺口 ✅

**决定**: 插件 = MCP 配置 + `/awr-setup` skill（端口探测+映射注册）+ workflow skill + `/awr` 命令。不新增超出 review→fix→resolve 循环的能力。

### 4. 自动化：手动触发 ✅

**决定**: 用户说 `/awr` 或"处理 web 评论"才触发闭环。不加 hook 自动化。

### 5. 通道：Pull 模型 ✅（Channel 被否决）

**决定**: 使用 Pull 模型——CC 主动调 MCP tool 拉取评论。

**Channel 否决原因**（2026-06-23 实测）:
- CC 2.1.185 在 GLM 代理下静默禁用 channels
- debug 日志: `[claudeai-mcp] Disabled: API-key auth precedence active`
- `--channels` flag 不报错但 channel server 根本不被 spawn
- 文档明确: channels 需要 Anthropic 官方认证（claude.ai / Console API key），不支持第三方代理

**Pull 模型工作流**:
1. 用户在浏览器评论（Chrome 扩展 → POST → server 存储）
2. 用户在 CC 说 `/awr`（或自然语言"处理 web 评论"）
3. CC 调 `awr_get_comments(project_path=<CWD>)` 拉取评论
4. CC 根据评论修改代码
5. CC 调 `awr_resolve_comment` 标记已处理
6. 用户刷新浏览器，看到 resolved marker

**优化 Pull 体验**:
- `/awr` 一个命令触发完整闭环（比自然语言更短）
- MCP tool 的 `project_path` 参数已实现——CC 传 CWD 即可，不需知道 page_url
- workflow skill 指导 CC 如何高效处理评论（读评论 → 定位源码 → 改 → resolve）

### 6. 存储：简化 ✅

**决定**:
- **砍**: users 表 + auth.py + admin routes(免鉴权,单人本地);comments 的 user_id 字段;MCP tools 的 user 检查
- **comments**: 改 in-memory(dict,按 page_url 分组,server 重启丢失可接受)
- **projects 映射**: JSON 文件持久化(CWD↔URL 双向,Pull 模型必需,重启不丢)
- **保留**: SSE(resolved marker 实时更新);MCP tools(去 user 维度)

**理由**:
- 单人本地使用,不需要 users/projects 鉴权表、API key
- 评论是临时任务,in-memory 平衡"不持久化"和"Pull 必需临时存"
- projects 映射必须持久化(否则每次重启要重新 setup)

### 7. 截图：可选 ✅

**决定**:
- **扩展端**: 评论面板相机图标可选截图(已有),强化"已截图/未截图"状态指示,默认不截
- **数据**: `screenshot_b64` 保持可选字段(有截图才带,无为 null)
- **MCP tool**: `awr_get_comments` 返回时自然带或不带截图,**不加过滤参数**(KISS);CC 自己看字段,有图 multimodal 看,无图靠 element_html + selector + 文字
- **后续优化**: 若评论多/截图大,再拆 `get_comment_screenshot(comment_id)` 单独取(YAGNI,暂不做)

**理由**:
- 视觉问题靠截图,CC 能精准理解;纯逻辑/文案评论不需截图,省数据
- 用户按需选择,避免每次截图的负担

### 8. /awr-setup：端口探测 + 多项目 ✅

**决定**:
- **端口探测**: 方案 A——读 package.json scripts(dev/start 里的 -p/--port)+ 框架配置(vite.config server.port / next.config),按框架默认推断(Vite 5173 / Next·CRA 3000) → 给用户确认/修正 → 探测不到则问用户输入
- **映射注册**: 探测确认后,POST /api/projects 注册 `http://localhost:<port>` → CWD
- **多项目并行**: projects 映射支持多条,每个项目各自 `/awr-setup` 一次。JSON 文件存多条 `{url: cwd}`

**理由**:
- 读配置推断比扫端口准(扫端口多项目时不知道哪个是当前的)
- 用户确认环节避免推断错误(端口被占、配置没写)
- 多项目是用户的真实场景(awesome-claude-code / kt-bioinfo 前端并行)

## 插件目录结构

```
awr-claude-plugin/          # → ~/.claude/plugins/awr/
├── plugin.json             # 插件清单
├── .mcp.json               # MCP 配置（指向 localhost:9876/mcp）
├── skills/
│   ├── awr-setup/          # 端口探测 + 项目映射注册
│   │   └── SKILL.md
│   └── awr-workflow/       # CC 处理评论的工作流指导
│       └── SKILL.md
├── commands/
│   └── awr.md              # /awr 命令（触发完整闭环）
└── hooks/                  # （后续可选）Stop hook 提示未处理评论
```

## 后续迭代

- [x] Channels 兼容性实测 → **否决**（GLM 代理不支持）
- [x] `/awr-setup` skill 实现（端口探测 + 项目映射注册）
- [x] `/awr` command 实现（触发闭环）
- [x] AWR workflow skill（指导 CC 如何读评论→定位源码→改代码→resolve）
- [x] `.mcp.json` 配置（连 server + API key 注入）
- [x] 简化 server 存储层（砍 users/projects 鉴权，保留评论基本存储）
- [x] Hook 自动化（Stop 时提示未处理评论数，可选）
- [ ] Marketplace 发布（扩展分发 + server 安装文档 + 配置 UI）

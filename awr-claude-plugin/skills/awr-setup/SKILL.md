---
name: awr-setup
description: 探测当前项目的 dev server 端口、把 http://localhost:<port>↔CWD 映射注册到 AWR server，让 /awr 能按当前工作目录过滤评论。用户首次用 AWR、跑 /awr-setup、或 /awr 提示"未注册映射"时触发。
---

# AWR Setup — 端口探测 + 项目映射注册

把当前项目的 `http://localhost:<port>` ↔ CWD 映射注册到 AWR server，使 `/awr` 能按当前工作目录反查评论。

## 步骤

### 1. 探测 dev server 端口

按以下优先级推断候选端口（取到第一个就停止）：

1. **读 `package.json`**：解析 `scripts.dev` / `scripts.start` 字符串里的 `-p <n>` / `--port <n>`（也兼容 `-p=<n>`、`--port=<n>`）。
2. **读框架配置**：
   - `vite.config.{js,ts,mjs}` → `server.port`（如 `server: { port: 5173 }`）
   - `next.config.{js,mjs,ts}` → Next 默认 3000（端口几乎不写进 config）
   - `vue.config.js` → `devServer.port`
3. **按框架默认推断**：Vite → 5173；Next / CRA → 3000；其他框架无默认。

### 2. 用户确认/修正

- **探测到候选端口** → 把候选端口告诉用户确认或修正（例："探测到端口 5173（来自 vite.config 的 server.port），对吗？"）。
- **探测不到**（无 package.json、配置都没写、无框架默认）→ 直接问用户输入端口号（例："没探测到端口，你的 dev server 跑在哪个端口？"）。

确定一个最终端口号后再继续。

### 3. 注册映射

用确定的端口号 + 当前工作目录绝对路径，POST 注册映射：

```bash
curl -i -X POST http://localhost:9876/api/projects \
  -H "Content-Type: application/json" \
  -d "{\"page_url\": \"http://localhost:<PORT>\", \"project_path\": \"<CWD 绝对路径>\"}"
```

- payload 字段：`page_url`（含 `http://localhost:<port>`，无尾斜杠、无 path）、`project_path`（当前 CWD 绝对路径）。
- 返回 `201` + 新建条目 = 成功。
- 返回 `409`（`mapping for ... already exists`）= 该 page_url 已注册过，**不是错误**，可视为成功（幂等）。
- 返回其他（如连不上 server）→ 提示用户确认 AWR server 在 `localhost:9876` 已启动。

### 4. 多项目并行

- 每个项目**各自在自己的 CWD 跑一次** `/awr-setup`（切换到该项目目录再触发）。server 支持多条映射，不同项目互不干扰。
- 映射持久化在 server 的 JSON 文件，**server 重启不丢**，无需重复 setup（除非端口变了）。

### 5. 完成

告诉用户：setup 完成，之后跑 `/awr` 会自动按当前 CWD 过滤评论——只处理当前项目的评论，不会串到其他项目。

## 注意
- `page_url` 必须带上 scheme（`http://`）和端口；host 一律 `localhost`（本地单用户，ADR-001 决策 2）。
- 若同一 CWD 换了端口，先 `DELETE /api/projects?page_url=<旧url>` 删旧映射，再 POST 新映射。

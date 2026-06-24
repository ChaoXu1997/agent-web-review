---
description: 处理当前项目的 web review 评论 —— MCP 拉取、改代码、resolve
---

处理当前项目的所有 open web review 评论（按当前工作目录过滤）。

1. 调用 `awr_get_comments` MCP tool，传：
   - `project_path` = **当前工作目录的绝对路径**（server 据此反查注册的 page_url，只返回当前项目的评论）
   - `status` = `open`
   
   如果返回空或报"未注册映射"：说明当前 CWD 还没跑过 `/awr-setup` → 提示用户先跑 `/awr-setup` 注册 page_url↔CWD 映射，然后重试 `/awr`。
2. 对每条评论：
   - 读 `comment_text`（reviewer 想改什么）
   - 用 `element_html`、`element_selector`、`page_url` 定位对应的源文件/组件（页面是最近生成的，结构熟悉）
   - 若有 `screenshot_b64` 字段，查看截图理解视觉问题
   - 实现请求的修改
   - 调用 `awr_resolve_comment(comment_id=<该评论 id>)` 标记已处理
3. 汇报处理了哪些评论、改了什么。

---
description: 处理当前项目的 web review 评论 —— MCP 拉取、改代码、resolve
---

处理当前项目的所有 open web review 评论。

1. 调用 `awr_get_comments` MCP tool，`status` 设为 `open`，拉取所有未处理评论。
2. 对每条评论：
   - 读 `comment_text`（reviewer 想改什么）
   - 用 `element_html`、`element_selector`、`page_url` 定位对应的源文件/组件（页面是最近生成的，结构熟悉）
   - 若有 `screenshot_b64` 字段，查看截图理解视觉问题
   - 实现请求的修改
   - 调用 `awr_resolve_comment(comment_id=<该评论 id>)` 标记已处理
3. 汇报处理了哪些评论、改了什么。

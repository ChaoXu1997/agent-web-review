---
name: awr-workflow
description: 处理 Agent Web Review 网页评论的工作流——用 element_html/selector 定位源码、改、resolve。处理 /awr 评论或 fix web reviews 时用。
---

# AWR Workflow — 处理 Web Review 评论

处理网页评论时（通过 /awr 或 "process web comments"）：

## 每条评论字段
- `comment_text` — reviewer 想改什么
- `element_html` — 被评论元素的 HTML（用来定位源组件）
- `element_selector` — 元素的 CSS selector
- `page_url` — 评论所在页面
- `screenshot_b64`（可选）— 截图，只有 reviewer 主动截图才有

## 处理步骤
1. **定位源码**：用 `element_html` + `element_selector` 找到对应的源文件/组件。页面最近生成，结构熟悉。
2. **理解意图**：
   - 有 `screenshot_b64` → 看图（multimodal）抓视觉问题。
   - 无截图 → 靠 `element_html` + `element_selector` + `comment_text`。
3. **改代码**：实现请求的修改。
4. **resolve**：调 `awr_resolve_comment(comment_id=<id>)`。浏览器经 SSE 实时更新（刷新后看到绿色勾号）。

## 注意
- 无截图的评论（纯逻辑/文案）靠定位信息+文字就够，不强求截图。
- 带截图的评论（视觉问题）优先看图，理解更准。

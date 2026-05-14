# Agent Web Review — Context

Chrome 扩展 + Python 本地服务器，让用户在网页上点击元素添加评论，AI agent 通过 HTTP API 读取并处理。主要服务于本地前端开发场景（localhost）。

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
agent 处理完某条评论后将状态从 open 改为 resolved，不附带处理说明。
_Avoid_: done、completed、fixed

## Relationships

- 一条 **Comment** 对应一个 **Marker**
- 一个 **Marker** 属于一条 **Comment**
- **Comment** 有两种状态: open（待处理）→ resolved（已处理）
- 用户通过 **Inspect mode** 创建 **Comment**
- Agent 通过 HTTP API 将 open **Comment** 标记为 **Resolved**

## Workflow

1. 用户开启 Inspect mode，点击页面元素，输入评论文本
2. Agent（Hermes / Claude Code）curl 读取 open 状态的评论
3. Agent 根据评论修改前端代码
4. Agent 通过 PATCH API 将评论标记为 resolved（仅改状态，不留说明）
5. 用户刷新页面，resolved 评论显示绿色勾号 marker，点击展开详情
6. 用户确认后可批量清除 resolved 评论

## Flagged ambiguities

- agent 更新评论时只改 status 不填 reply 文本——这是用户的明确选择，保持简单。

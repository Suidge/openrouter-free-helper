# OpenRouter Free Model Monitor Cron Task

目标：检查 OpenRouter 当前可用的免费模型状态，并输出简短摘要。

执行要求：
1. 在工作区内运行本地检查脚本 `/Users/neoshi/.openclaw/workspace/skills/openrouter-free-helper/scripts/check-models.py`
2. 不要依赖浏览器，不要访问无关网站
3. 如果脚本成功运行，基于脚本输出给出 2-5 行纯文本摘要
4. 摘要应说明以下之一：
   - 有新的免费模型
   - 有免费模型到期/移除
   - 没有变化
   - 脚本执行失败，并简述原因
5. 不要自行发送消息，直接把摘要作为最终输出，交给 cron delivery 发送

注意：
- 仅执行本地脚本与必要的本地读取
- 保持任务自包含，不携带无关对话上下文
- 输出必须简短、明确、可直接发给主人

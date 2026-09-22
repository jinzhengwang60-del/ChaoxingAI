# ChaoxingAI

学习通章节测试 AI 辅助脚本与本地 Python 服务。当前脚本版本：**4.0.9-ai**。

浏览器脚本提取题目，向本机服务请求 DeepSeek 建议，并在页面显示推荐、置信度和解析。当前版本会自动选择或替换答案；所有题目核对通过后，倒计时 5 秒自动提交，进入已知批阅结果页后继续原章节流程。

> AI 建议可能错误，置信度是模型自评；“选择核对通过”只表示页面选择与建议一致，不表示答案正确。请在课程允许的范围内使用。首次使用应观察一个章节的完整流程。

## 快速开始

需要 Python 3.10+、脚本猫等支持 GM_xmlhttpRequest 的用户脚本管理器，以及自己的 DeepSeek API 密钥。Python 服务只使用标准库，无需安装依赖。

1. 下载本仓库，或克隆后进入项目目录。
2. 将 `outputs/.env.example` 复制为 `outputs/.env`，填写 `DEEPSEEK_API_KEY`，按需修改 `DEEPSEEK_MODEL`。
3. 从项目根目录运行：

   ```powershell
   python outputs/server.py
   ```

4. 保持终端运行，访问 <http://127.0.0.1:8787/health>。`ok: true` 只说明本地服务正常，不证明密钥有效。
5. 在脚本猫中新建**普通脚本**，粘贴 `outputs/auto-ai.js` 全文并保存。关闭其他同类脚本，允许本脚本访问 `127.0.0.1`。
6. 刷新学习通课程页面。每题显示分析及选择结果；顶部可暂停自动选择与提交。

密钥只保存在本机 `.env`，不要写入浏览器脚本或提交到 GitHub。修改 `.env` 后重启服务。

## 功能与边界

- 支持原脚本题目页面中的单选、多选和判断题。尚未识别的题型或页面结构会阻止自动提交。
- 根据可见选项字母和正文匹配答案；判断题按对/错语义识别，不假设 A 永远代表正确。
- 自动替换已有选择；多选会取消多余选项并补选。无建议、控件异常或状态不匹配时停止。人工干预或暂停会阻止自动提交。
- 全部题目实际选择与建议一致后，5 秒倒计时自动提交。提交尝试记录在当前标签页 sessionStorage 中，刷新不重复提交；新标签页不共享该保护。
- 提交接口缺失、网站拒绝或结果未知时停留。网站确认框需手动处理。已发出的请求不能由暂停按钮撤回。
- 只通过已有批阅结果页分支确认任务完成。网站布局和接口变化可能导致功能失效。
- 图片沿用原提取规则，本服务不下载或识别图片。
- 原有视频、任务推进及可选登录代码保留，原件供比对。作者留言面板已移除，来源和许可仍保留。

## 数据与配置

服务只监听 `127.0.0.1:8787`。题干、题型和选项会发送至 DeepSeek；浏览器不持有 DeepSeek API 密钥。

配置文件在 `outputs/.env`；模型默认为 `deepseek-chat`，请根据账号可用模型调整。缓存位于 `outputs/cache.sqlite3`，键包含题干、题型、选项、模型及提示词版本。停止服务后删除该文件可清缓存。环境文件、缓存、临时工作文件和旧版备份均不纳入 Git。

## 项目结构

```text
source/auto.js          用户提供的原脚本（保留原件）
outputs/auto-ai.js      当前浏览器脚本
outputs/server.py       本地 AI 服务
outputs/.env.example    配置示例
outputs/安装说明.md     使用与排错说明
tests/                  本地模拟回归测试
NOTICE.md               来源与修改说明
LICENSE                 GPL v3 许可证文本
```

## 验证

在项目根目录运行；JavaScript 测试需要 Node.js，Python 测试不调用真实 AI API：

```powershell
node --check outputs/auto-ai.js
python -m unittest discover -s tests -p "test_*.py" -v
node tests/test_selection.cjs
node tests/test_submission.cjs
node tests/test_browser.cjs
node tests/test_chapters.cjs
node tests/test_startup.cjs
```

模拟测试覆盖选项匹配、判断题、已有答案替换、异常暂停、提交保护、初始化和章节调度、本地 HTTP 与缓存。用户已反馈 4.0.8-ai 在其课程中成功运行；4.0.9-ai 仅移除留言面板并更新版本号。这不等于所有课程和浏览器都经过验证。

## 许可

GPL-3.0-or-later。原脚本作者及来源见 [NOTICE.md](NOTICE.md)，许可全文见 [LICENSE](LICENSE)。

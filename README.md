# ChaoxingAI

学习通章节测试 AI 辅助脚本与本地服务。浏览器脚本版本：**4.0.10-ai**；Windows 启动器版本：**1.0.0**。

浏览器脚本提取题目，向本机服务请求 DeepSeek 建议，并在页面显示推荐、置信度和解析。当前版本会自动选择或替换答案；所有题目核对通过后，倒计时 5 秒自动提交，进入已知批阅结果页后继续原章节流程。

> AI 建议可能错误，置信度是模型自评；“选择核对通过”只表示页面选择与建议一致，不表示答案正确。请在课程允许的范围内使用。首次使用应观察一个章节的完整流程。

## Windows 用户：双击启动（推荐）

[**下载 Windows 启动器 v1.0.0**](https://github.com/jinzhengwang60-del/ChaoxingAI/releases/download/launcher-v1.0.0/ChaoxingAI-Windows-v1.0.0.zip) · [版本说明与校验文件](https://github.com/jinzhengwang60-del/ChaoxingAI/releases/tag/launcher-v1.0.0) · [安装浏览器脚本](https://scriptcat.org/zh-CN/script-show-page/8102)

使用 `ChaoxingAI-Windows-v1.0.0.zip` 发布包，完整解压后双击 **ChaoxingAI-Launcher.exe**。不需要安装 Python，也不需要修改 `.env`。

1. 首次打开点击“获取 API 密钥”，在 DeepSeek 官方平台注册或登录并创建密钥。
2. 粘贴完整密钥，点击“测试并保存，启动服务”。测试会真实请求一道很短的示例题，可能产生少量 API 费用。
3. 显示“服务运行中 / 已就绪”后，点击“安装 / 更新浏览器脚本”，从[脚本猫](https://scriptcat.org/zh-CN/script-show-page/8102)安装普通脚本，刷新课程页面。
4. 以后双击启动器即可自动读取配置并启动服务；可以最小化，退出会停止服务。

密钥使用 Windows 当前账号加密保存到 `%LOCALAPPDATA%\ChaoxingAI\settings.json`，缓存也在同一目录。配置不随发布包分发。模型默认 `deepseek-flash`；其他模型可在“高级设置”填写。每个用户仍需自己的 API 密钥，API 可能收费。

已有旧配置可通过“导入原 .env”读取，不会修改原文件。启动器和原 `server.py` 都使用 8787 端口，切换前先停止旧服务。重复打开启动器会提示使用已有窗口。

发布包在 GitHub Releases 下载，不需要使用绿色 Code 按钮下载源码。开发者也可以按下方构建步骤生成。程序未做发布者代码签名，首次运行时 Windows 可能显示发布者未知。

## 源码运行方式

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
- 原有视频、任务推进及可选登录代码保留，原件供比对。作者留言和旧题库配置面板已移除，来源和许可仍保留。

## 数据与配置

服务只监听 `127.0.0.1:8787`。题干、题型和选项会发送至 DeepSeek；浏览器不持有 DeepSeek API 密钥。

直接运行 `server.py` 时，配置文件在 `outputs/.env`，默认模型沿用 `deepseek-chat`；请按账号可用模型调整。缓存位于 `outputs/cache.sqlite3`。Windows 启动器使用独立的加密配置与缓存目录，默认模型为 `deepseek-flash`。缓存键包含题干、题型、选项、模型及提示词版本。停止服务后删除对应缓存文件可清缓存。密钥、缓存、临时工作文件、打包产物和旧版备份均不纳入 Git。

## 项目结构

```text
source/auto.js          用户提供的原脚本（保留原件）
outputs/auto-ai.js      当前浏览器脚本
outputs/server.py       本地 AI 服务
outputs/launcher.py     Windows 配置向导
outputs/desktop_core.py 加密配置、单实例与服务控制
outputs/launcher_help.html 随程序附带的首次配置教程
outputs/.env.example    配置示例
outputs/安装说明.md     使用与排错说明
tests/                  本地模拟回归测试
packaging/              Windows 打包与校验脚本
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

模拟测试覆盖选项匹配、判断题、已有答案替换、异常暂停、提交保护、初始化和章节调度、本地 HTTP 与缓存。用户已反馈 4.0.8-ai 在其课程中成功运行；4.0.9-ai 仅移除留言面板并更新版本号。4.0.10-ai 移除旧题库配置面板及其输入框、保存按钮初始化逻辑，AI 作答、提交和章节推进代码保持不变。这不等于所有课程和浏览器都经过验证。

启动器测试另覆盖 Windows 加密配置、单实例、端口冲突、服务停止和重启、配置隔离、连接错误提示及实际 Tk 按钮回调。测试使用模拟密钥和响应，不调用收费 API。

## 构建 Windows 发布包

开发环境需要 Windows x64 和 Python 3.10+。在项目根目录运行：

```powershell
.\packaging\build_windows.ps1
```

构建依赖安装在 `work/desktop-build-env`，不会修改系统 Python 包。输出位于 `dist/`：

- `ChaoxingAI-Launcher.exe`：单文件图形启动器；
- `ChaoxingAI-Windows-v1.0.0.zip`：用户分发包，含启动器、快速开始、许可证及完整源码压缩包；
- `SHA256SUMS.txt`：分发包校验值。

构建脚本会运行打包后的离线自检，移除子进程中的 Python/Conda 路径，检查界面运行环境、加密存储、本地 HTTP 服务及包内无密钥文件。无需在用户机器上安装构建工具。

## 许可

GPL-3.0-or-later。原脚本作者及来源见 [NOTICE.md](NOTICE.md)，许可全文见 [LICENSE](LICENSE)。

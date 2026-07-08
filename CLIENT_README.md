# TikTok Drama Center 批量上传工具

> 这份 README 是给客户端仓库 `auto-script-upload` 的 README 模板。
> 服务端仓库（`short-drama-crawl`）把更新写在这里方便审阅，确认后请 `cp` 到客户端仓库覆盖原 `README.md`。

## 功能

- 读取 `export_*.xlsx` 中的剧集信息
- 自动下载封面图与视频到本地
- 在 Edge 浏览器中批量创建 draft、填写表单、上传视频、保存
- `monitor.py` 监听服务端批次任务，完成后自动拉取 Excel 并触发上传

## 环境要求

- Windows 10/11
- Python 3.12（已安装）
- 系统已安装 Microsoft Edge

## 安装

```bash
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

如果 Chromium 内核未安装，可执行：

```bash
.venv/Scripts/python.exe -m playwright install chromium
```

（实际运行使用系统 Edge，Chromium 仅作备用。）

## 首次登录

持久化登录态保存在 `./browser_data`。如果尚未登录，先运行分析脚本完成登录：

```bash
.venv/Scripts/python.exe analyze_page.py
```

按提示在弹出的 Edge 窗口中登录 TikTok，回到终端按回车抓取字段即可。

## 运行上传

处理 Excel 中全部剧集：

```bash
.venv/Scripts/python.exe upload.py
```

仅测试前 1 部剧：

```bash
.venv/Scripts/python.exe upload.py --limit 1
```

指定其他 Excel：

```bash
.venv/Scripts/python.exe upload.py path/to/your.xlsx
```

## 自动化监控（monitor.py）

监控服务端批次任务，完成后自动下载 xlsx 并触发 `upload.py`。

### 基本用法

```bash
# 监控批次（默认每 30s 轮询一次，完成后自动下载 + 上传）
.venv/Scripts/python.exe monitor.py <batch_id>

# 只下载 xlsx 不触发 upload（用于测试）
.venv/Scripts/python.exe monitor.py <batch_id> --no-upload

# 限制只处理前 1 部剧（端到端测试）
.venv/Scripts/python.exe monitor.py <batch_id> --limit 1

# 自定义服务端地址和轮询间隔
.venv/Scripts/python.exe monitor.py <batch_id> --server http://your-server:5173 --interval 60
```

下载的 xlsx 存放在 `./downloads/batch_<batch_id 前 8 位>.xlsx`。

参数完整列表（`monitor.py --help`）：

| 参数 | 说明 |
|---|---|
| `batch_id`（位置参数） | 要监控的批次 ID，UUID 格式 |
| `--server URL` | 服务端地址，默认 `http://45.78.235.74:5173` |
| `--interval N` | 轮询间隔秒数，默认 30 |
| `--limit N` | 仅处理前 N 部剧（测试用） |
| `--no-upload` | 只下载 xlsx，不触发 `upload.py` |

### 1. 获取 batch_id

服务端 Web UI（`http://45.78.235.74:5173`）左侧菜单"每日上新" → 顶部 Tab"批次列表"，可以看到所有批次的表格，每行最左侧就是 `batch_id`（UUID 格式，如 `6c27f639-6288-4d0f-86f3-ce151b6ae4a0`），点击即可复制。

也可以直接调接口拿：

```bash
curl "http://45.78.235.74:5173/api/daily-new/batches" | python -m json.tool
```

返回的 `batches[].batch_id` 即可。每条记录还带 `done_count / failed_count / job_count`，可以一眼看出哪些批次已经完成。

判定一个批次是否已完成：`done_count + failed_count == job_count`（即所有任务都到达终态）。

### 2. 多客户端部署

每个客户端机器独立运行 `monitor.py`，**各指定一个不同的 `batch_id`**，互不干扰。服务端不会限制一个 `batch_id` 只能被一个客户端监听 —— 多个客户端监听同一个 `batch_id` 也能各自拿到 xlsx（但会重复上传，不建议）。

典型部署：

- 客户端 A（办公室机器）：`monitor.py <batch_id_A>` —— 处理英文版本
- 客户端 B（家里机器）：`monitor.py <batch_id_B>` —— 处理葡语版本
- 客户端 C（云机器）：`monitor.py <batch_id_C>` —— 处理印尼语版本

部署步骤：

1. 在每台客户端机器按上面"安装"和"首次登录"完成环境准备
2. 在服务端 Web UI 分别为每种语言触发一个批次，记录各自的 `batch_id`
3. 在每台客户端机器上 `monitor.py <对应的 batch_id>` 即可

注意：每台机器的 `./browser_data` 登录态是独立的，需要各自完成"首次登录"步骤。如果同一家 TikTok 账号在多台机器同时上传，可能触发风控，建议每台机器用不同的账号。

### 3. 错误处理与重跑

**轮询期间网络错误 / 服务端重启：** `monitor.py` 会捕获请求异常并打印 `[warn] 查询失败: ...`，等待 `--interval` 秒后重试，不会退出。可以放心长时间挂着。

**批次有任务失败：** `failed_count > 0` 时批次仍会被判定为完成（`done + failed == total`）。`monitor.py` 会打印警告但继续下载 xlsx 并触发上传，xlsx 中会缺少失败任务对应的数据行。建议在服务端 Web UI 上排查失败任务（看 `error_message` 字段），修复后用 `--limit` 重新跑 `monitor` 验证。

**`upload.py` 上传失败：** `monitor.py` 把 `upload.py` 的退出码透传出来，自己退出码相同。失败时可以：

- 直接重跑 `monitor.py <batch_id>` —— xlsx 会重新下载覆盖，`upload.py` 从头执行
- 或者只跑 `upload.py ./downloads/batch_<batch_id 前 8 位>.xlsx --limit 1` 单独测试某一部剧
- 浏览器自动化失败会截图到 `./errors/row_<行号>.png`，看截图判断是登录过期 / 选择器变化 / 网络问题

**Ctrl+C 中断：** 随时可中断，重跑会从轮询阶段重新开始。已经上传过的剧在服务端没有去重，**重跑会重复上传**，建议上传失败时用 `--limit` 精确重跑失败的剧。

### 4. 服务端接口契约

`monitor.py` 调用的两个接口：

**GET `/api/daily-new/batches/{batch_id}`** —— 查询批次状态

返回字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `batch_id` | string | 批次 ID |
| `total_jobs` | int | 批次内任务总数 |
| `done_count` | int | 成功任务数 |
| `failed_count` | int | 失败任务数 |
| `pending_count` | int | 仍在处理中的任务数（含 `pending` / `translating` / `poster_generating` / `processing_episodes`） |
| `jobs` | array | 任务详情列表 |

完成判定：`total_jobs > 0 && done_count + failed_count == total_jobs`

**GET `/api/daily-new/batches/{batch_id}/export?format=xlsx`** —— 下载 Excel

返回 `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` 文件流，约 10–50 KB（取决于剧集数）。

**默认服务端地址：** `http://45.78.235.74:5173`（如需改用其他服务端，传 `--server`）

## 输入文件说明

### export_*.xlsx

| 列名 | 用途 |
|---|---|
| 原剧名 | 保留 |
| 原简介 | 保留 |
| 作者 | 保留 |
| 分类 | 保留（不用于表单） |
| 原海报URL | 保留 |
| 翻译语言 | 保留 |
| 翻译后剧名 | 表单「剧集名」 |
| 翻译后简介 | 表单「剧集描述」 |
| 新海报URL | 表单「封面图」 |
| 剧集数 | 表单「总集数」 |
| 剧集 URL | 该剧全部视频 URL，以换行分隔 |

### attr_require.txt

已固化为代码中的默认值：

- 免费预览集数：8
- 个人页剧集展示集数：3
- 目标人群：男性
- 源语言：中文
- 是否 AI 短剧：是
- 托管模式：开启
- 版权自查承诺：勾选
- 发布方式：过审后自动发布
- 保存（不提交）

## 输出

- `./downloads/`：下载的封面与视频缓存，以及 `monitor.py` 拉取的 xlsx
- `./errors/row_<行号>.png`：失败时的页面截图
- 终端打印成功/失败汇总

## 注意事项

- 每部剧独立占用一个浏览器 Tab，最多 10 个 Tab 并行。
- 脚本从 `series/list` 点击「新建」为每部剧创建独立 draft。
- 表单包含自定义下拉框和文件上传，运行过程中请勿手动操作浏览器窗口，以免干扰自动化。
- 多台客户端同时运行时，建议每台用不同的 TikTok 账号，避免触发风控。

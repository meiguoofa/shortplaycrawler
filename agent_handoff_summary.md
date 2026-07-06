# Agent Handoff Summary

更新时间：2026-05-26

本文档用于把本次会话的上下文交接给后续开发 agent，方便继续实现短剧/漫剧数据抓取、入库、对象存储上传和结果展示。

## 工程位置

当前工作目录：

```text
D:\Software\short-drama
```

这是一个 WPF 桌面端程序目录，主要是已编译产物，不是源码工程。

关键文件：

```text
WpfApp1.exe
WpfApp1.pdb
activation.json
download_settings.json
data/crawler_development_plan.md
data/scripts/simulate_top100_crawl.py
data/output/simulations/cate_7_top100_sample/
```

当前激活码：

```text
FXKBAGV5OJQH
```

## 已分析出的配置来源

程序会请求远程配置：

```text
https://mizhi.kissm.top/pc/con.php
```

已确认的一些配置接口：

```text
红果详情：
http://160.202.253.154:1231/api/hg/wai_api_detail.php

红果剧集：
http://160.202.253.154:1231/api/hg/wai_api_book.php

红果播放/下载 URL：
http://43.142.49.190:1789/api/g/gui_play.php

红果片库筛选榜单：
http://43.142.49.190:1789/tool/duanju/hg/排行榜/筛选进入.php
```

大多数接口需要参数：

```text
code=FXKBAGV5OJQH
```

## 已确认的核心抓取链路

完整链路：

```text
榜单筛选 URL
  -> video_data[].recommend_group_id / series_id
  -> 详情接口 book_id={series_id}
  -> 剧集接口 book_id={series_id}
  -> 剧集 data[].video_id
  -> 播放接口 video_id={video_id}
  -> data.video_url
```

注意：

```text
book_id 使用的是榜单返回的 recommend_group_id / series_id。
不是榜单项里的 vid。

剧集接口返回的 video_id 才是获取播放/下载 URL 的单集 ID。
```

## 榜单接口

接口：

```text
http://43.142.49.190:1789/tool/duanju/hg/排行榜/筛选进入.php
```

用户本次提供的榜单 URL：

```text
http://43.142.49.190:1789/tool/duanju/hg/%E6%8E%92%E8%A1%8C%E6%A6%9C/%E7%AD%9B%E9%80%89%E8%BF%9B%E5%85%A5.php?filter_ids=comic_series&session_id=2026052620093984EBB34EBD62BF8616E7&req_scene=comic_series&code=FXKBAGV5OJQH&genre=comic_series&category_dim_theme=cate_7&category_dim_role=&category_dim_epoch=&sort=hot_score&gender=&online_time=
```

参数含义：

| 参数 | 含义 |
| --- | --- |
| `filter_ids` | 首次为 `comic_series`，翻页后为已抓取作品 ID 列表 |
| `session_id` | 会话 ID，接口会返回新的 session_id |
| `req_scene` | 当前为 `comic_series` |
| `genre` | 当前为 `comic_series` |
| `category_dim_theme` | 主题筛选，本次为 `cate_7`，返回内容是“玄幻”类 |
| `category_dim_role` | 角色/设定筛选，空表示不限 |
| `category_dim_epoch` | 背景/年代筛选，空表示不限 |
| `sort` | 排序，本次为 `hot_score` |
| `gender` | 受众，空表示不限 |
| `online_time` | 上线时间，空表示不限 |
| `code` | 激活码 |

返回结构：

```json
{
  "code": 0,
  "message": "SUCCESS",
  "data": {
    "has_more": true,
    "next_offset": 18,
    "session_id": "...",
    "video_data": []
  }
}
```

`video_data` 关键字段：

```text
recommend_group_id
series_id
title
cover
category_schema
recommend_reason_list
episode_cnt
play_cnt
score
video_desc
vid
```

## 榜单分页规律

首次请求：

```text
不传 offset
filter_ids=comic_series
```

第二页：

```text
offset=1
filter_ids=第一页已抓到的 recommend_group_id 列表，英文逗号拼接
```

第三页：

```text
offset=2
filter_ids=前面所有已抓到且去重后的 recommend_group_id 列表
```

以此类推，直到：

```text
达到目标数量
或 data.has_more == false
或本页没有新增 ID
```

注意：

```text
data.next_offset 看起来像累计位置，但软件抓包使用 offset=1、2、3 这种页序号。
正式实现优先模拟软件行为。
```

## 详情接口

接口：

```text
http://160.202.253.154:1231/api/hg/wai_api_detail.php
```

示例：

```text
http://160.202.253.154:1231/api/hg/wai_api_detail.php?book_id=7637517119122312254&code=FXKBAGV5OJQH
```

参数：

```text
book_id={series_id}
code=FXKBAGV5OJQH
```

返回示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": "70",
    "book_id": "7637517119122312254",
    "book_name": "万妖图录传第四季",
    "author": "星际动漫",
    "category": "武侠",
    "desc": "作品简介",
    "duration": "2小时1分59秒",
    "book_pic": "https://..."
  }
}
```

## 剧集接口

接口：

```text
http://160.202.253.154:1231/api/hg/wai_api_book.php
```

示例：

```text
http://160.202.253.154:1231/api/hg/wai_api_book.php?book_id=7637517119122312254&code=FXKBAGV5OJQH
```

参数：

```text
book_id={series_id}
code=FXKBAGV5OJQH
```

返回示例：

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "video_id": "7637519370570173465",
      "title": "第1集",
      "firstPassTime": "1778248589"
    }
  ],
  "total": 70
}
```

## 播放/下载 URL 接口

接口：

```text
http://43.142.49.190:1789/api/g/gui_play.php
```

示例：

```text
http://43.142.49.190:1789/api/g/gui_play.php?video_id=7637519331537996825&code=FXKBAGV5OJQH&level=720p
```

参数：

```text
video_id={ }
code=FXKBAGV5OJQH
level=720p
```

可尝试的清晰度：

```text
720p
1080p
2160p
```

返回示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "expire_time": "1分钟37秒",
    "video_id": "7637519331537996825",
    "video_url": "https://v9-m.wkbrowser.com/...",
    "quality": "720p"
  }
}
```

重要：

```text
data.video_url 是带签名的临时对象存储 URL。
接口返回 expire_time，说明链接会很快过期。
如果要保存视频，需要获取 video_url 后立刻下载并上传自己的对象存储。
```

## 已创建的模拟脚本

文件：

```text
data/scripts/simulate_top100_crawl.py
```

功能：

1. 根据榜单 URL 抓取前 N 个唯一作品。
2. 自动维护 `offset` 和 `filter_ids`。
3. 抓取详情接口。
4. 抓取剧集接口。
5. 抽样抓取播放 URL 验证链路。
6. 输出 JSON 文件。

示例命令：

```powershell
python data\scripts\simulate_top100_crawl.py `
  --url "http://43.142.49.190:1789/tool/duanju/hg/%E6%8E%92%E8%A1%8C%E6%A6%9C/%E7%AD%9B%E9%80%89%E8%BF%9B%E5%85%A5.php?filter_ids=comic_series&session_id=2026052620093984EBB34EBD62BF8616E7&req_scene=comic_series&code=FXKBAGV5OJQH&genre=comic_series&category_dim_theme=cate_7&category_dim_role=&category_dim_epoch=&sort=hot_score&gender=&online_time=" `
  --limit 100 `
  --detail-limit 5 `
  --sleep 0.2 `
  --out-dir data\output\simulations\cate_7_top100_sample
```

参数：

| 参数 | 说明 |
| --- | --- |
| `--url` | 榜单入口 URL |
| `--limit` | 榜单唯一作品数量 |
| `--detail-limit` | 只抓前 N 个作品详情/剧集，0 表示全部 |
| `--sleep` | 请求间隔 |
| `--sample-play-series` | 抽样获取播放 URL 的作品数 |
| `--sample-play-episodes` | 每部抽样多少集 |
| `--out-dir` | 输出目录 |

## 模拟结果

已完成一次 cate_7 前 100 模拟。

输出目录：

```text
data/output/simulations/cate_7_top100_sample/
```

文件：

```text
ranking_items.json
details.json
episodes.json
play_url_samples.json
summary.json
```

结果：

| 项目 | 结果 |
| --- | --- |
| 榜单唯一作品 | 100 |
| 抽样详情 | 5 |
| 抽样剧集列表 | 5 |
| 抽样剧集总数 | 394 |
| 抽样播放 URL | 6 |
| 播放 URL 成功 | 6 |

分页统计：

| offset | 返回条数 | 新增唯一作品 | 累计唯一作品 |
| --- | --- | --- | --- |
| 首次 | 18 | 18 | 18 |
| `1` | 18 | 12 | 30 |
| `2` | 18 | 18 | 48 |
| `3` | 18 | 18 | 66 |
| `4` | 18 | 18 | 84 |
| `5` | 18 | 16 | 100 |

抽样播放 URL：

```text
山海藏墟，无眼窥天 第1集 7641250007055600665 720p success
山海藏墟，无眼窥天 第2集 7641249878709914649 720p success
凡人百世书 第1集 7641248554081602585 720p success
凡人百世书 第2集 7641248476080114713 720p success
谁让这个悍匪修仙的！ 第1集 7642211751160712216 720p success
谁让这个悍匪修仙的！ 第2集 7642211757938707480 720p success
```

另有一次只抓榜单前 100 的完整文件：

```text
data/output/simulations/cate_7_top100/ranking_items.json
```

该目录下的 `ranking_items.json` 是完整可读 JSON，包含 100 部作品。

## 数据库表设计建议

详细表结构已写在：

```text
data/crawler_development_plan.md
```

建议核心表：

```text
crawler_rankings
drama_series
ranking_series
drama_episodes
episode_assets
```

核心设计：

1. `crawler_rankings` 保存榜单任务和筛选参数。
2. `drama_series` 保存作品详情。
3. `ranking_series` 保存榜单和作品关系。
4. `drama_episodes` 保存剧集和 `video_id`。
5. `episode_assets` 保存播放 URL 获取记录、下载状态、对象存储地址。

`episode_assets.status` 建议值：

```text
pending
url_fetched
downloading
downloaded
uploading
uploaded
failed
skipped
```

## 对象存储上传流程

还没有实现，原因：

1. 用户尚未提供对象存储类型和凭证。
2. 批量下载并上传视频需要确认合法授权。

建议流程：

```text
drama_episodes.video_id
  -> gui_play.php 获取临时 video_url
  -> 立即下载到临时文件
  -> 上传到用户对象存储
  -> episode_assets 写入 object_key / object_url / checksum / status
  -> 删除本地临时文件
```

建议对象 key：

```text
{source}/{ranking_key}/{series_id}/{episode_no}_{video_id}_{quality}.mp4
```

建议先实现统一适配层：

```python
class ObjectStorageClient:
    def upload_file(self, local_path: str, object_key: str, content_type: str) -> dict:
        ...
```

可能支持：

```text
阿里云 OSS
腾讯云 COS
七牛云 Kodo
AWS S3 / MinIO
Cloudflare R2
```

## 后续开发建议

### 第一阶段：正式化抓取脚本

把 `simulate_top100_crawl.py` 拆成正式模块：

```text
data/scripts/fetch_ranking.py
data/scripts/fetch_details.py
data/scripts/fetch_episodes.py
data/scripts/fetch_play_urls.py
data/scripts/download_and_upload.py
```

要求：

1. 支持断点续跑。
2. 支持失败重试。
3. 支持限速。
4. 支持保存原始 JSON。
5. 支持 upsert 到数据库。

### 第二阶段：数据库接入

需要用户确认数据库：

```text
MySQL / PostgreSQL / SQLite
```

开发时可先用 SQLite，后续切换 MySQL/PostgreSQL。

### 第三阶段：对象存储接入

需要用户提供：

```text
provider
endpoint
bucket
region
access_key_id
access_key_secret
public_base_url 或 CDN 域名
```

### 第四阶段：展示

建议先做静态 HTML 报告：

```text
data/output/rankings/<ranking_key>/report.html
```

展示内容：

1. 榜单筛选条件。
2. 前 100 作品列表。
3. 每部作品详情。
4. 剧集列表。
5. 对象存储 URL 或下载状态。

## 注意事项

1. 不要把激活码写到前端页面、公开日志或公开仓库。
2. 播放 URL 很快过期，不能长期依赖原始 URL。
3. 批量下载视频前必须确认授权。
4. 前 100 部可能有数千集，下载和上传成本高，需要任务队列。
5. 接口响应有时较慢，100 部详情和剧集串行抓取会超过 3 分钟。
6. 正式实现需要记录每个任务状态，避免中断后从头开始。


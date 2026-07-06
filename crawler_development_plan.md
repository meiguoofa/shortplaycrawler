# 短剧数据抓取开发计划

更新时间：2026-05-26

## 目标

围绕当前 WPF 软件里暴露出的短剧/漫剧数据接口，逐步实现一套可复用的数据抓取流程：

1. 分析用户提供的榜单或筛选 URL，识别接口、参数、分页规律和返回结构。
2. 抓取某个榜单下的全部作品列表。
3. 对每个作品抓取详情信息。
4. 对每个作品抓取剧集列表和每集下载/播放 URL。
5. 将抓取结果保存为结构化文件，并最终用网站或文档展示。

## 当前已知配置来源

软件会从远程配置接口加载功能菜单和接口地址：

```text
https://mizhi.kissm.top/pc/con.php
```

配置里已观察到的关键接口类型：

```text
红果短剧/漫剧搜索：
http://160.202.253.154:1231/api/hg/tou_search.php
http://160.202.253.154:1231/api/hg/tou_dm_search.php

红果详情：
http://160.202.253.154:1231/api/hg/wai_api_detail.php

红果剧集：
http://160.202.253.154:1231/api/hg/wai_api_book.php

红果播放/下载地址：
http://43.142.49.190:1789/api/g/gui_api_play.php
http://43.142.49.190:1789/api/g/gui_play.php

红果片库筛选：
http://43.142.49.190:1789/tool/duanju/hg/排行榜/筛选进入.php
```

大部分接口需要带激活码：

```text
code=FXKBAGV5OJQH
```

## 已分析接口：红果排行榜筛选进入

接口：

```text
http://43.142.49.190:1789/tool/duanju/hg/排行榜/筛选进入.php
```

示例 URL：

```text
http://43.142.49.190:1789/tool/duanju/hg/排行榜/筛选进入.php?filter_ids=comic_series&session_id=2026052620093984EBB34EBD62BF8616E7&req_scene=comic_series&code=FXKBAGV5OJQH&genre=comic_series&category_dim_theme=cate_6&category_dim_role=&category_dim_epoch=&sort=hot_score&gender=&online_time=
```

### 参数说明

| 参数 | 作用 | 当前观察 |
| --- | --- | --- |
| `code` | 激活码 | 必填 |
| `genre` | 榜单/内容类型 | `comic_series` |
| `req_scene` | 请求场景 | 通常和 `genre` 一致 |
| `session_id` | 会话 ID | 软件生成或接口返回，可继续复用 |
| `filter_ids` | 首次请求标识或已加载作品 ID 列表 | 首次为 `comic_series`，翻页后为逗号拼接的 `recommend_group_id` |
| `offset` | 翻页序号 | 首次不传，后续传 `1`、`2`、`3`... |
| `category_dim_theme` | 主题筛选 | 例如 `cate_6`，当前对应“奇幻” |
| `category_dim_role` | 角色/设定筛选 | 空表示不限 |
| `category_dim_epoch` | 背景/年代筛选 | 空表示不限 |
| `sort` | 排序 | `hot_score` 表示热度排序 |
| `gender` | 受众 | 空表示不限 |
| `online_time` | 上线时间筛选 | 空表示不限 |

### 返回结构

接口返回 JSON，核心结构：

```json
{
  "code": 0,
  "message": "SUCCESS",
  "data": {
    "has_more": true,
    "next_offset": 18,
    "session_id": "20260526203142AB62EEA6D8D94AAF76B4",
    "video_data": []
  }
}
```

`video_data` 中每个作品的关键字段：

| 字段 | 含义 |
| --- | --- |
| `recommend_group_id` | 作品 ID，后续详情/剧集接口优先使用 |
| `series_id` | 作品 ID，通常和 `recommend_group_id` 一致 |
| `title` | 作品标题 |
| `cover` | 封面 |
| `category_schema` | 分类信息 JSON 字符串 |
| `recommend_reason_list` | 推荐/热度信息 JSON 字符串 |
| `episode_cnt` | 集数 |
| `play_cnt` | 播放量 |
| `score` | 评分 |
| `video_desc` | 简介 |
| `vid` | 视频 ID，可能用于播放接口 |

### 分页规律

首次请求：

```text
filter_ids=comic_series
不传 offset
```

接口当前返回 18 条数据。

第二页请求：

```text
offset=1
filter_ids=第一页返回的所有 recommend_group_id，用英文逗号拼接
```

第三页请求：

```text
offset=2
filter_ids=前面所有已加载且去重后的 recommend_group_id，用英文逗号拼接
```

持续翻页直到：

```text
data.has_more == false
```

或本页没有新增作品 ID。

注意：`next_offset` 当前观察到像是“累计位置/服务端游标”，但软件抓包 URL 使用的是 `offset=1`、`offset=2` 这种页序号。因此实现时优先模拟软件行为：`offset` 从 1 递增，`filter_ids` 保存已加载 ID。

## 已分析接口：红果作品详情

接口：

```text
http://160.202.253.154:1231/api/hg/wai_api_detail.php
```

示例：

```text
http://160.202.253.154:1231/api/hg/wai_api_detail.php?book_id=7637517119122312254&code=FXKBAGV5OJQH
```

### 参数说明

| 参数 | 作用 | 当前观察 |
| --- | --- | --- |
| `book_id` | 作品 ID | 使用榜单返回的 `recommend_group_id` / `series_id` |
| `code` | 激活码 | 必填 |

注意：这里的 `book_id` 不是榜单项里的单集 `vid`。以“万妖图录传第四季”为例：

```text
recommend_group_id = 7637517119122312254
series_id          = 7637517119122312254
vid                = 7637519370570173465
```

详情接口使用的是：

```text
book_id=7637517119122312254
```

### 返回结构

核心返回：

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

### 标准化映射

| 标准字段 | 来源字段 |
| --- | --- |
| `series_id` | `data.book_id` |
| `title` | `data.book_name` |
| `author` | `data.author` |
| `category` | `data.category` |
| `description` | `data.desc` |
| `duration_text` | `data.duration` |
| `cover` | `data.book_pic` |
| `episode_count` | `data.total` |

## 已分析接口：红果剧集列表

接口：

```text
http://160.202.253.154:1231/api/hg/wai_api_book.php
```

示例：

```text
http://160.202.253.154:1231/api/hg/wai_api_book.php?book_id=7637517119122312254&code=FXKBAGV5OJQH
```

### 参数说明

| 参数 | 作用 | 当前观察 |
| --- | --- | --- |
| `book_id` | 作品 ID | 使用榜单返回的 `recommend_group_id` / `series_id` |
| `code` | 激活码 | 必填 |

### 返回结构

核心返回：

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

### 关键结论

1. 剧集接口的 `book_id` 仍然使用作品 ID，也就是榜单里的 `recommend_group_id` / `series_id`。
2. 剧集接口返回的 `video_id` 是单集 ID。
3. 后续获取播放/下载链接时，应使用每一集的 `video_id` 作为核心参数继续请求播放接口。

链路关系：

```text
榜单接口
  -> recommend_group_id / series_id
  -> 详情接口 book_id
  -> 剧集接口 book_id
  -> 剧集 data[].video_id
  -> 播放/下载 URL 接口
```

## 已分析接口：红果播放/下载 URL

接口：

```text
http://43.142.49.190:1789/api/g/gui_play.php
```

示例：

```text
http://43.142.49.190:1789/api/g/gui_play.php?video_id=7637519331537996825&code=FXKBAGV5OJQH&level=720p
```

### 参数说明

| 参数 | 作用 | 当前观察 |
| --- | --- | --- |
| `video_id` | 单集视频 ID | 使用剧集接口 `data[].video_id` |
| `code` | 激活码 | 必填 |
| `level` | 清晰度 | 当前示例为 `720p`，配置里还出现过 `1080p`、`2160p` |

### 返回结构

核心返回：

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

### 关键结论

1. `data.video_url` 是最终可用于播放/下载的对象存储 URL。
2. `video_url` 带签名参数，且接口返回 `expire_time`，说明该 URL 有时效。
3. 抓取结果里必须记录获取时间和过期信息，避免后续展示时误以为链接永久有效。
4. 需要长期保存视频时，应在获取 `video_url` 后尽快交给下载器下载，而不是只保存链接。

### 标准化映射

| 标准字段 | 来源字段 |
| --- | --- |
| `video_id` | `data.video_id` |
| `quality` | `data.quality` |
| `download_url` | `data.video_url` |
| `expire_time_text` | `data.expire_time` |
| `fetched_at` | 本地抓取时间 |

### 建议抓取流程

对每个剧集的 `video_id`，按目标清晰度请求播放接口：

```text
GET /api/g/gui_play.php?video_id={video_id}&code={code}&level={level}
```

推荐先支持：

```text
720p
1080p
2160p
```

如果某个清晰度失败，则降级到较低清晰度，或记录失败原因。

## 榜单抓取流程设计

### 1. URL 分析阶段

输入：用户提供的一组抓包 URL。

产出：

```text
data/analysis/<接口名>_analysis.md
data/samples/<接口名>_page_1.json
data/samples/<接口名>_page_2.json
```

分析内容：

1. 固定参数和动态参数。
2. 是否需要 `code`、Cookie、Header。
3. 分页方式。
4. 主键字段。
5. 返回数据结构。
6. 可用于详情接口的字段。
7. 可用于播放/下载接口的字段。

### 2. 榜单列表抓取

输入：

```json
{
  "list_url": "http://43.142.49.190:1789/tool/duanju/hg/排行榜/筛选进入.php",
  "params": {
    "code": "FXKBAGV5OJQH",
    "genre": "comic_series",
    "req_scene": "comic_series",
    "category_dim_theme": "cate_6",
    "sort": "hot_score"
  }
}
```

输出：

```text
data/output/rankings/<ranking_key>/ranking_items.json
```

每条标准化为：

```json
{
  "source": "hg",
  "ranking_key": "comic_series_cate_6_hot_score",
  "series_id": "7637517119122312254",
  "title": "万妖图录传第四季",
  "cover": "...",
  "episode_count": 70,
  "score": "8.3",
  "play_count": 5413738,
  "raw": {}
}
```

### 3. 作品详情抓取

候选接口：

```text
http://160.202.253.154:1231/api/hg/wai_api_detail.php
```

待确认参数：

```text
recommend_group_id / series_id / book_id / id
code
```

需要通过抓包或探测确认详情接口实际参数名。

输出：

```text
data/output/rankings/<ranking_key>/details/<series_id>.json
```

标准化字段：

```json
{
  "series_id": "",
  "title": "",
  "cover": "",
  "description": "",
  "categories": [],
  "episode_count": 0,
  "actors": [],
  "raw": {}
}
```

### 4. 剧集列表抓取

候选接口：

```text
http://160.202.253.154:1231/api/hg/wai_api_book.php
```

待确认参数：

```text
recommend_group_id / series_id / book_id / id
code
```

输出：

```text
data/output/rankings/<ranking_key>/episodes/<series_id>.json
```

标准化字段：

```json
{
  "series_id": "",
  "episodes": [
    {
      "episode_no": 1,
      "title": "第1集",
      "vid": "",
      "raw": {}
    }
  ]
}
```

### 5. 下载 URL 抓取

候选接口：

```text
http://43.142.49.190:1789/api/g/gui_api_play.php
http://43.142.49.190:1789/api/g/gui_play.php
```

配置里观察到的播放参数：

```text
level=2160p
level=1080p
level=720p
```

返回 URL 字段：

```text
data.video_url
```

待确认参数：

```text
vid
series_id
book_id
episode_id
level
code
```

输出：

```text
data/output/rankings/<ranking_key>/play_urls/<series_id>.json
```

标准化字段：

```json
{
  "series_id": "",
  "episodes": [
    {
      "episode_no": 1,
      "vid": "",
      "urls": {
        "720p": "",
        "1080p": "",
        "2160p": ""
      }
    }
  ]
}
```

## 本地实现建议

### 目录结构

```text
data/
  crawler_development_plan.md
  samples/
    ranking_filter_page_1.json
    ranking_filter_page_2.json
  output/
    rankings/
      comic_series_cate_6_hot_score/
        ranking_items.json
        details/
        episodes/
        play_urls/
        report.html
  scripts/
    analyze_url.py
    fetch_ranking.py
    fetch_details.py
    fetch_episodes.py
    fetch_play_urls.py
    build_report.py
```

### 数据抓取脚本分层

1. `analyze_url.py`
   - 解析用户提供的 URL。
   - 拆分 query 参数。
   - 对比多条 URL 的差异。
   - 输出接口分析摘要。

2. `fetch_ranking.py`
   - 根据榜单 URL 和参数抓全量作品。
   - 自动维护 `offset` 和 `filter_ids`。
   - 自动去重。

3. `fetch_details.py`
   - 读取 `ranking_items.json`。
   - 并发或限速抓取详情。

4. `fetch_episodes.py`
   - 读取详情或榜单 ID。
   - 抓取剧集列表。

5. `fetch_play_urls.py`
   - 读取剧集列表。
   - 按清晰度抓取播放/下载 URL。
   - 支持失败重试。

6. `build_report.py`
   - 生成 HTML 或 Markdown 报告。

## 呈现方案

### 方案 A：静态 HTML

优点：最简单，可直接打开。

内容：

1. 榜单名称和筛选条件。
2. 作品列表表格。
3. 每个作品的封面、简介、分类、评分、热度。
4. 每集下载 URL。
5. 支持搜索和按分类过滤。

输出：

```text
data/output/rankings/<ranking_key>/report.html
```

### 方案 B：Markdown 文档

优点：便于快速审阅和归档。

输出：

```text
data/output/rankings/<ranking_key>/report.md
```

### 方案 C：本地小网站

优点：适合数据量较大时浏览。

技术选择：

```text
Python FastAPI / Flask
或纯静态 HTML + JSON
```

第一阶段建议先做静态 HTML，避免过早增加复杂度。

## 风险和待确认项

1. 接口是否限频。
   - 建议请求间隔 0.5-2 秒。
   - 播放 URL 抓取可更慢。

2. `session_id` 是否必须实时生成。
   - 当前观察：首次请求会返回新的 `data.session_id`。
   - 后续可以优先沿用首次返回的 `session_id`。

3. `filter_ids` 是否必须完整传入。
   - 当前软件行为是传入已加载作品 ID。
   - 实现时按软件行为模拟，避免缺页或重复。

4. 详情/剧集/播放接口的实际参数名还需抓包确认。
   - 重点抓点击作品详情、展开剧集、点击下载/播放时的请求。

5. 下载 URL 可能有时效签名。
   - 抓取结果需要记录抓取时间。
   - HTML 中标注 URL 可能过期。

## 下一步

1. 用户继续提供某个榜单的抓包 URL。
2. 分析该 URL 的筛选参数和分页规律。
3. 将接口规律追加到本文档。
4. 确认详情接口参数。
5. 确认剧集接口参数。
6. 确认播放/下载 URL 接口参数。
7. 开始编写 `fetch_ranking.py`。

## 实战模拟：cate_7 热度榜前 100

用户提供的榜单入口：

```text
http://43.142.49.190:1789/tool/duanju/hg/排行榜/筛选进入.php?filter_ids=comic_series&session_id=2026052620093984EBB34EBD62BF8616E7&req_scene=comic_series&code=FXKBAGV5OJQH&genre=comic_series&category_dim_theme=cate_7&category_dim_role=&category_dim_epoch=&sort=hot_score&gender=&online_time=
```

当前参数含义：

| 参数 | 值 | 说明 |
| --- | --- | --- |
| `genre` | `comic_series` | 漫剧/漫画短剧榜单 |
| `req_scene` | `comic_series` | 请求场景 |
| `category_dim_theme` | `cate_7` | 主题筛选，当前返回分类为“玄幻” |
| `sort` | `hot_score` | 热度排序 |
| `gender` | 空 | 不限受众 |
| `online_time` | 空 | 不限上线时间 |

已创建模拟脚本：

```text
data/scripts/simulate_top100_crawl.py
```

模拟命令：

```powershell
python data\scripts\simulate_top100_crawl.py `
  --url "http://43.142.49.190:1789/tool/duanju/hg/%E6%8E%92%E8%A1%8C%E6%A6%9C/%E7%AD%9B%E9%80%89%E8%BF%9B%E5%85%A5.php?filter_ids=comic_series&session_id=2026052620093984EBB34EBD62BF8616E7&req_scene=comic_series&code=FXKBAGV5OJQH&genre=comic_series&category_dim_theme=cate_7&category_dim_role=&category_dim_epoch=&sort=hot_score&gender=&online_time=" `
  --limit 100 `
  --detail-limit 5 `
  --sleep 0.2 `
  --out-dir data\output\simulations\cate_7_top100_sample
```

模拟结果：

| 项目 | 结果 |
| --- | --- |
| 榜单作品数 | 100 |
| 抽样详情数 | 5 |
| 抽样剧集列表数 | 5 |
| 抽样剧集总数 | 394 |
| 抽样播放 URL 数 | 6 |
| 播放 URL 成功数 | 6 |

输出文件：

```text
data/output/simulations/cate_7_top100_sample/ranking_items.json
data/output/simulations/cate_7_top100_sample/details.json
data/output/simulations/cate_7_top100_sample/episodes.json
data/output/simulations/cate_7_top100_sample/play_url_samples.json
data/output/simulations/cate_7_top100_sample/summary.json
```

分页结果：

| offset | 接口返回条数 | 新增唯一作品数 | 累计唯一作品数 |
| --- | --- | --- | --- |
| 首次 | 18 | 18 | 18 |
| `1` | 18 | 12 | 30 |
| `2` | 18 | 18 | 48 |
| `3` | 18 | 18 | 66 |
| `4` | 18 | 18 | 84 |
| `5` | 18 | 16 | 100 |

结论：

1. 抓取前 100 个唯一作品可行。
2. 详情接口和剧集接口可通过 `book_id = recommend_group_id / series_id` 串联。
3. 播放接口可通过 `video_id` 获取临时对象存储 URL。
4. 详情和剧集接口响应较慢，100 部全量串行抓取会耗时较长，正式实现应支持断点续跑、限速、重试和并发控制。
5. 播放 URL 有过期时间，应在拿到 URL 后立即下载并上传到自己的对象存储，不应只长期保存原始 `video_url`。

## 数据库表设计建议

以下结构适合 PostgreSQL / MySQL，字段类型可按实际数据库微调。

### `crawler_rankings`

保存榜单任务和筛选条件。

```sql
CREATE TABLE crawler_rankings (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ranking_key VARCHAR(128) NOT NULL UNIQUE,
  source VARCHAR(32) NOT NULL,
  list_url TEXT NOT NULL,
  genre VARCHAR(64),
  req_scene VARCHAR(64),
  category_dim_theme VARCHAR(64),
  category_dim_role VARCHAR(64),
  category_dim_epoch VARCHAR(64),
  sort_key VARCHAR(64),
  gender VARCHAR(32),
  online_time VARCHAR(64),
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);
```

### `drama_series`

保存作品主表。

```sql
CREATE TABLE drama_series (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  source VARCHAR(32) NOT NULL,
  series_id VARCHAR(64) NOT NULL,
  title VARCHAR(255) NOT NULL,
  author VARCHAR(255),
  category VARCHAR(255),
  description TEXT,
  cover_url TEXT,
  episode_count INT,
  duration_text VARCHAR(64),
  score VARCHAR(32),
  play_count BIGINT,
  raw_json JSON,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uk_source_series (source, series_id)
);
```

### `ranking_series`

保存榜单和作品的关系，以及榜单排名。

```sql
CREATE TABLE ranking_series (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ranking_key VARCHAR(128) NOT NULL,
  source VARCHAR(32) NOT NULL,
  series_id VARCHAR(64) NOT NULL,
  rank_no INT,
  hot_text VARCHAR(64),
  raw_json JSON,
  created_at DATETIME NOT NULL,
  UNIQUE KEY uk_ranking_series (ranking_key, source, series_id)
);
```

### `drama_episodes`

保存每个作品的剧集列表。

```sql
CREATE TABLE drama_episodes (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  source VARCHAR(32) NOT NULL,
  series_id VARCHAR(64) NOT NULL,
  video_id VARCHAR(64) NOT NULL,
  episode_no INT,
  title VARCHAR(128),
  first_pass_time VARCHAR(64),
  raw_json JSON,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uk_source_video (source, video_id),
  KEY idx_series (source, series_id)
);
```

### `episode_assets`

保存下载结果和对象存储地址。

```sql
CREATE TABLE episode_assets (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  source VARCHAR(32) NOT NULL,
  series_id VARCHAR(64) NOT NULL,
  video_id VARCHAR(64) NOT NULL,
  quality VARCHAR(32) NOT NULL,
  origin_video_url TEXT,
  origin_url_fetched_at DATETIME,
  origin_expire_time_text VARCHAR(64),
  object_storage_provider VARCHAR(64),
  object_bucket VARCHAR(255),
  object_key TEXT,
  object_url TEXT,
  file_size BIGINT,
  checksum_sha256 VARCHAR(128),
  status VARCHAR(32) NOT NULL,
  error_message TEXT,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uk_video_quality (source, video_id, quality)
);
```

推荐状态值：

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

## 正式抓取流程

### 阶段 1：抓榜单前 100

1. 解析用户给的榜单 URL。
2. 首次请求不传 `offset`，`filter_ids` 使用 URL 原值。
3. 后续请求 `offset=1,2,3...`。
4. `filter_ids` 传已抓到的唯一 `recommend_group_id` 列表。
5. 去重后达到 100 个作品即停止。
6. 写入：
   - `crawler_rankings`
   - `drama_series` 的基础字段
   - `ranking_series`

### 阶段 2：抓前 100 详情

对每个作品：

```text
GET http://160.202.253.154:1231/api/hg/wai_api_detail.php?book_id={series_id}&code={code}
```

写入或更新 `drama_series`。

### 阶段 3：抓前 100 剧集

对每个作品：

```text
GET http://160.202.253.154:1231/api/hg/wai_api_book.php?book_id={series_id}&code={code}
```

将 `data[].video_id` 写入 `drama_episodes`。

### 阶段 4：获取临时视频 URL

对每集：

```text
GET http://43.142.49.190:1789/api/g/gui_play.php?video_id={video_id}&code={code}&level={level}
```

将 `data.video_url`、`data.expire_time`、`data.quality` 写入 `episode_assets`。

### 阶段 5：下载并上传对象存储

前提：确认对这些视频有合法下载、复制、存储和再分发授权。

流程：

1. 获取临时 `video_url`。
2. 立即流式下载到临时文件，或边下载边上传对象存储。
3. 上传到对象存储路径：

```text
{source}/{ranking_key}/{series_id}/{episode_no}_{video_id}_{quality}.mp4
```

4. 上传成功后写入：
   - `episode_assets.object_bucket`
   - `episode_assets.object_key`
   - `episode_assets.object_url`
   - `episode_assets.file_size`
   - `episode_assets.checksum_sha256`
   - `episode_assets.status = uploaded`

5. 删除本地临时文件。

## 对象存储适配层建议

抽象统一上传接口：

```python
class ObjectStorageClient:
    def upload_file(self, local_path: str, object_key: str, content_type: str) -> dict:
        ...
```

返回：

```json
{
  "provider": "s3",
  "bucket": "short-drama",
  "object_key": "hg/cate_7/7641248058436488217/001_7641250007055600665_720p.mp4",
  "object_url": "https://...",
  "etag": "..."
}
```

后续可按实际对象存储实现：

```text
阿里云 OSS
腾讯云 COS
七牛云 Kodo
AWS S3 / MinIO
Cloudflare R2
```

## 正式实现注意事项

1. 下载视频前必须确认授权。
2. 播放 URL 过期很快，获取 URL 和下载必须放在同一个任务里。
3. 全量前 100 可能包含数千集视频，必须做任务队列和断点续跑。
4. 每个接口需要限速，建议 0.5-2 秒间隔，并支持失败重试。
5. 数据库写入要做 upsert，避免重复跑任务产生重复数据。
6. 对象存储上传成功后再标记 `uploaded`，失败保留错误信息以便重试。
7. 不建议把原始 `code` 明文写进前端页面或公开日志。

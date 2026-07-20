# SkyUnity (hi.skyunity.media) 爬取可行性分析

> 分析时间：2026-07-17  
> 分析对象：https://hi.skyunity.media/  
> 目的：评估该剧场的元数据、免费剧集、付费剧集的爬取可行性，以及服务端授权风险

---

## 1. 站点概况

- **前端形态**：UniApp 构建的 H5 SPA，首页 HTML 仅包含 JS/CSS 入口，内容由 JS 动态请求。
- **真实 API 域名**：`https://hi.skyunity.media/api/`
- **视频/图片资源域名**：
  - `v4.xtv.media`（视频、封面）
  - `img.xtv.media`（部分封面）
- **应用标识**：`pid=1309`，`version=20251120`，`ios=3`

---

## 2. 鉴权机制

### 2.1 必须登录

除静态资源外，所有内容接口都需要 `token` + `uid` + `cid`，否则返回 `{"code":-1,"msg":"参数错误"}`。

### 2.2 登录流程

`POST /api/User/login`

请求体需要包含：

- `device`：设备指纹（任意字符串即可，如 UUID）
- `deviceId`：设备 ID
- `pageParamStorage`：JSON 字符串，如 `{"cid":0,"data":""}`
- `pid`、`version`、`ios`
- `sign`、`timestamp`、`lang`、`gmt`

响应返回：

- `token`：会话令牌
- `uid`：用户 ID
- `cid`：渠道 ID

### 2.3 Sign 算法

```text
sign = MD5("73a74wxa58179eef93" + timestamp)
```

- `timestamp` 为秒级 Unix 时间戳
- 固定 key：`73a74wxa58179eef93`
- 部分客户端路径（`ios=1`）使用 SHA256，但 `ios=3` 即可正常访问

---

## 3. 免费内容爬取方案

### 3.1 推荐爬取链路

```text
1. POST /api/User/login                     → 获取 token/uid/cid
2. GET  /api/Videocenter/getHomeCategoryConfigList
                                            → 获取首页分类列表
3. GET  /api/Videocenter/getHomeCategoryById?id={分类ID}
                                            → 获取该分类下的剧集列表（含 vid、封面、剧名、简介）
4. GET  /api/Videocenter/getVideoDrama?vid={vid}&page={页码}&limit=25
                                            → 获取剧集元数据 + 分集列表（count 为总集数）
5. POST /api/Videocenter/getFreeVideoDrama  → 传入免费集 eid，获取可播放 MP4 URL
```

### 3.2 关键字段说明

| 字段 | 含义 |
|---|---|
| `vid` | 剧集 ID |
| `eid` | 单集 ID |
| `episodeorder` | 集数序号 |
| `isvip` | `0`=免费，`1`=付费 |
| `last_free_episodeorder` | 免费集最后一集的序号 |
| `peregold` | 单集付费价格（金币） |
| `cha_high_url` | 分类列表中的预览视频，实测与 EP1 正片 URL 为同一文件 |
| `verticpic` | 竖版封面 |

### 3.3 分页

`getVideoDrama` 默认每页 25 集，通过 `page` 参数翻页，直到取完 `count` 集。

### 3.4 免费集范围

不同剧的免费集数不同，样例：

| 剧名 | 总集数 | 免费集数 |
|---|---|---|
| Mr. Fairchild is expecting! | 60 | 8 |
| Under the Floor | 20 | 5 |
| I Chose You: The Kiln's Echo | 14 | 2 |
| Married to Mr. Voss | 100 | 14 |
| Reborn: StepMom's Obsession | 65 | 9 |

---

## 4. 付费内容：服务端授权风险评估

### 4.1 发现的问题

`POST /api/Videocenter/getFreeVideoDrama` 的设计是**按传入的 `eid` 返回一个邻近窗口的剧集列表**（通常为前后各 2-3 集），而不是仅返回指定的一集。

问题出现在：**服务端在返回邻近窗口时，未对用户是否已购买窗口中的付费集做有效校验**。当传入一个付费集的 `eid` 时，响应中会包含该窗口内的付费集，并附带可直接播放的、带签名的 MP4 URL。

响应中这些付费集的字段显示：

- `pay_status = 1`：未支付
- `is_purchased = 0`：未购买

但服务端仍然下发了真实视频 URL，且 URL 可通过 `HEAD` 请求返回 `200 video/mp4` 验证成功。

### 4.2 影响

- 该问题属于**服务端水平授权/业务逻辑漏洞**，绕过客户端付费流程即可直接获取付费集视频 URL。
- 付费集视频文件本身托管在 `v4.xtv.media`，URL 带 `wsSecret` + `wsTime` 签名，但签名由服务端生成并直接下发。
- 另外，分类列表中的 `cha_high_url`（预览 URL）与 EP1 正片 URL 为同一文件，且不带签名参数也能直接访问。

### 4.3 建议

如该分析用于向平台方提交安全报告，建议平台修复点：

1. `getFreeVideoDrama` 在返回邻近窗口前，应对窗口内每一集校验当前用户是否已购买（`is_purchased` 校验）。
2. 对未购买的付费集，不应返回带签名的播放 URL。
3. 预览视频 `cha_high_url` 不应与 EP1 正片共用同一 URL，或应对预览 URL 增加独立鉴权/有效期。

---

## 5. 法律与合规风险

| 行为 | 风险 |
|---|---|
| 爬取剧名、简介、封面、播放量等元数据 | 较低，但仍可能违反平台 ToS |
| 下载/缓存免费集视频 | 可能违反平台 ToS，存在版权灰色地带 |
| 利用服务端漏洞下载付费集 | **侵犯著作权，可能触犯法律，平台可追责** |
| 将绕过方案集成到爬虫项目并对外提供服务 | **高风险，可能构成帮助侵权或非法经营** |

---

## 6. 结论

- **元数据和免费剧集**：技术上可稳定爬取，鉴权简单，接口清晰。
- **付费剧集**：服务端存在授权缺陷，技术上可以绕开，但这属于利用漏洞获取付费内容。
- **项目建议**：如果 `short-drama-crawl` 项目面向公开/商业用途，只应爬取免费集及元数据；付费漏洞部分建议仅作为安全报告提交给平台，不应作为爬虫功能实现。

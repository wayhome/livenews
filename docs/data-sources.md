# LiveNews 页面结构与数据源调研

调研日期：2026-08-14（北京时间）。本文只引用服务提供方的官方文档、官方源码或官方 API；官方没有公布的限制会明确注明。

## 推荐页面结构

| 页面主题 | 数据源 | 最小展示内容 |
| --- | --- | --- |
| 技术社区 | Hacker News、Lobsters | 标题、分数、评论数、标签、原文与讨论链接 |
| 开源生态 | GitHub Trending、GitHub Releases | 热门仓库；关注仓库的新正式版本 |
| 新产品 | Product Hunt | 产品名、简介、作者与产品链接 |
| 前沿论文 | arXiv q-fin、arXiv AI | 英文标题、中文摘要、作者、分类及 HTML/PDF 链接 |
| 金融动态 | BLS、美国财政部、SEC EDGAR、Polymarket | 月度通胀与就业、日度收益率曲线、自选股公告、热门预测市场 |

所有来源都应独立抓取和降级：一个来源超时、限流或改变响应格式时，不能阻止其他来源生成页面。低频 GitHub Actions 每天运行两次，适合缓存结果并使用条件请求。

## Lobsters

### 接口与字段

- 热门内容：`GET https://lobste.rs/hottest.json`
- 最新内容：`GET https://lobste.rs/newest.json`
- 常用字段：`short_id`、`created_at`、`title`、`url`、`score`、`comment_count`、`description_plain`、`submitter_user`、`tags`、`short_id_url`、`comments_url`。

正式站点的 JSON 响应与 Lobsters 官方开源项目的路由相符：[官方 routes.rb](https://github.com/lobsters/lobsters/blob/master/config/routes.rb)。公开读取无需认证。官方没有发布独立、版本化的 API 契约，也没有公布固定请求额度或 User-Agent 格式，因此稳定性评为中等。

### 最小接入

每次取 `hottest.json` 前 15～20 条即可；用 `url` 链接原文、`comments_url` 链接讨论区，并展示 `tags`。每天两次的请求非常克制，但仍应设置能识别项目的 User-Agent，且单源失败只隐藏 Lobsters 区域。

## GitHub Releases

### 接口与字段

```text
GET https://api.github.com/repos/{owner}/{repo}/releases?per_page=3
```

常用字段包括 `html_url`、`tag_name`、`name`、`body`、`draft`、`prerelease`、`created_at`、`published_at`、`author` 和 `assets`。官方说明见 [List releases](https://docs.github.com/en/rest/releases/releases#list-releases)。

公开仓库可匿名读取。不过 GitHub Actions 中应直接使用自动生成的 `${{ secrets.GITHUB_TOKEN }}`，并声明最小权限 `permissions: contents: read`；这不需要用户创建额外 PAT。官方说明见 [Use GITHUB_TOKEN for authentication in workflows](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token)。请求应发送：

```text
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2022-11-28
Authorization: Bearer <GITHUB_TOKEN>
```

匿名 REST API 的主要额度为每 IP 每小时 60 次；认证用户通常为每小时 5,000 次。Actions 的 `GITHUB_TOKEN` 通常按仓库每小时 1,000 次（GitHub Enterprise Cloud 某些资源可为 15,000）。应读取 `X-RateLimit-*` 响应头，遇到限流不要继续请求。完整规则见 [REST API rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)。GitHub 也支持 `ETag` / `If-None-Match` 条件请求。

### 最小接入

维护一个小型关注仓库列表，或只对当前 Trending 结果请求 release；每仓 `per_page=3`，排除 `draft` 和 `prerelease`，合并后按 `published_at` 倒序，最终保留约 10 条。对动态 Trending 仓库逐个调用会增加请求数；固定关注列表的内容连续性和限流可控性更好。

## arXiv AI

### 接口、分类与字段

```text
GET https://export.arxiv.org/api/query
  ?search_query=(cat:cs.AI OR cat:cs.LG OR cat:cs.CL)
  &start=0
  &max_results=15
  &sortBy=submittedDate
  &sortOrder=descending
```

- `cs.AI`：Artificial Intelligence
- `cs.LG`：Machine Learning
- `cs.CL`：Computation and Language

分类定义来自 [arXiv Category Taxonomy](https://arxiv.org/category_taxonomy)，查询和排序来自 [arXiv API User Manual](https://info.arxiv.org/help/api/user-manual.html)。Atom entry 可读取 `id`、`title`、`updated`、`published`、`summary`、`author`、`category`、`link` 和 `arxiv:primary_category`。

无需认证。官方条款要求所有受调用者控制的机器合计每三秒最多一次请求，同时只能建立一个连接；参见 [API Terms of Use: rate limits](https://info.arxiv.org/help/api/tou.html#rate-limits)。官方没有规定固定 User-Agent 格式，项目可主动提供带仓库或联系地址的可识别 UA。

### 最小接入

复用已有 q-fin Atom 解析、中文翻译和缓存逻辑。单次组合查询取 10～15 篇，用去掉版本号的 arXiv ID 去重，缓存键继续使用论文 ID 与 `updated`；金融与 AI 两次 arXiv 请求之间至少间隔三秒。

## 股市相关宏观数据：BLS Public Data API v2

### 接口与字段

BLS 的月度 CPI、失业率和非农就业比 World Bank 年度指标更适合股市信息页。三组系列可合并为一次 POST：

```http
POST https://api.bls.gov/publicAPI/v2/timeseries/data/
Content-Type: application/json

{
  "seriesid": ["CUSR0000SA0", "LNS14000000", "CES0000000001"],
  "startyear": "2025",
  "endyear": "2026"
}
```

推荐系列：

- `CUSR0000SA0`：CPI-U、All items、U.S. city average，季调。适合计算最新月环比；如果要展示不会因季节因子例行更新的原始指数，改用未季调的 `CUUR0000SA0`。
- `LNS14000000`：16 岁以上失业率，季调，单位为百分比。
- `CES0000000001`：Total nonfarm payroll employment，季调，单位为千人。市场通常所说的“新增非农”应由最新月减上月计算，不能直接把就业存量当新增值。

响应顶层包含 `status`、`responseTime`、`message`、`Results`；`Results.series[]` 包含 `seriesID` 和 `data[]`，观测项常用字段是 `year`、`period`、`periodName`、`latest`、`value`、`footnotes`。开启可选参数时还可返回 `catalog`、`calculations`、`annualaverage`、`aspects`。接口签名和请求字段见 [BLS Public Data API v2](https://www.bls.gov/developers/api_signature_v2.htm)，系列可从 [BLS Series Report](https://data.bls.gov/cgi-bin/srgate) 核对。

注册 key 是可选的：未注册模式无需 key，官方限制为每天 25 次查询、每次最多 25 个系列、每个系列最多 10 年；注册模式为每天 500 次、每次 50 个系列、最多 20 年。每天运行两次且合并查询三个系列，远低于免密额度。版本和限制见 [BLS API features](https://www.bls.gov/bls/api_features.htm)。

### 发布时间、修订与股市用途边界

CPI 和 Employment Situation 在预先排期的发布日通常于美国东部时间 08:30 发布，具体日期应引用 [BLS release calendar](https://www.bls.gov/schedule/news_release/)，不能硬编码成“每月第几个周五”。

- CPI 未季调指数通常不例行修订，但发现错误时可纠正；季调指数会因季节因子更新而修订。见 [CPI FAQ](https://www.bls.gov/cpi/questions-and-answers.htm)。
- CES 非农最新月份是初值，随后两个月会例行修订，并有年度基准修订。见 [CES revisions](https://www.bls.gov/web/empsit/cesnaicsrev.htm)。
- CPS 失业率的季调历史也可能随年度季调更新而修订。

页面应按观测月份 upsert，允许同一月份被新发布值覆盖，并展示最新值、上月值、变化和观测月份。BLS 发布的是已发生的月度数据，不是实时数据或预测；官方源也不提供市场共识预期，因此不能据此标记“超预期”“利好”或“利空”。

## 美国财政部日度国债收益率

### 接口与字段

```text
GET https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml
  ?data=daily_treasury_yield_curve
  &field_tdr_date_value=2026
```

这是美国财政部正式的 Atom/XML feed，无需 API key 或其他认证。官方数据页没有公布固定请求额度；每天两次读取、设置应用 User-Agent 并缓存结果即可。数据页见 [Daily Treasury Par Yield Curve Rates](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve)。

关键 XML 字段是日期 `NEW_DATE`，以及 `BC_1MONTH`、`BC_1_5MONTH`、`BC_2MONTH`、`BC_3MONTH`、`BC_4MONTH`、`BC_6MONTH`、`BC_1YEAR`、`BC_2YEAR`、`BC_3YEAR`、`BC_5YEAR`、`BC_7YEAR`、`BC_10YEAR`、`BC_20YEAR`、`BC_30YEAR`。最小页面只需展示 2Y、10Y、30Y，并计算 `10Y - 2Y`；完整曲线可以后续展开。

### 发布时间、方法与股市用途边界

这是工作日的日终快照，官方页面通常约美国东部时间 15:30 更新；周末和美国假日没有新记录，不是盘中实时行情。值可能被官方纠正，因此同样应按 `NEW_DATE` upsert。页面应明确标注“美国财政部日度收益率（非实时）”。

财政部说明这些 daily par yield curve rates 是根据市场报价估算出的收益率曲线，不是某一只可交易国债的逐笔成交价，参见 [Treasury yield curve methodology](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology)。2Y 可以粗略反映政策利率预期，10Y 是重要折现率，2s10s 展示曲线形态；它们本身不是交易信号，也不能仅凭倒挂判断经济衰退或股票涨跌。

财政部 [Fiscal Data API](https://fiscaldata.treasury.gov/api-documentation/) 同样无需 key，但其中 `avg_interest_rates` 是政府债务的平均利率，不是每日市场收益率曲线，不能用它替代上述 XML feed。

## 季度 GDP：BEA Data API 暂不接入

BEA 官方 API 需要有效 API key。注册页要求提供姓名或组织、有效邮箱并同意条款：[BEA API signup](https://apps.bea.gov/API/signup/)。因此“无需 key”的季度美国 GDP 接入不可行，不能使用空 key、示例 key或共享 key规避认证。

取得 key 后的 NIPA 请求形式如下：

```text
GET https://apps.bea.gov/api/data/
  ?UserID={BEA_API_KEY}
  &method=GetData
  &datasetname=NIPA
  &TableName=T10101
  &Frequency=Q
  &Year=2026
  &ResultFormat=JSON
```

响应结构为 `BEAAPI.Request.RequestParam` 和 `BEAAPI.Results.Data[]`；数据常用字段包括 `TableName`、`SeriesCode`、`LineNumber`、`LineDescription`、`TimePeriod`、`MetricName`、`CL_UNIT`、`UNIT_MULT`、`DataValue`、`NoteRef`。具体表和行必须通过 [BEA API documentation](https://apps.bea.gov/API/docs/index.htm) 的参数元数据确认；市场 headline 通常关注实际 GDP 较上期的年化百分比变化，不能从名义 GDP 水平自行替代计算。

BEA 对同一季度依次发布 advance、second、third estimate，之后还会年度或综合修订；具体日期见 [BEA release schedule](https://www.bea.gov/news/schedule)。因此即使以后配置 `BEA_API_KEY`，也必须显示估计轮次和发布日期，并允许同季度数据覆盖。GDP 是季度且多轮修订的数据；没有共识预期时不能标记“超预期”或据此直接判断股市方向。

### 最小接入

本轮使用 BLS 三系列和财政部收益率曲线；BEA 暂缓，除非用户愿意新增 `BEA_API_KEY` secret。World Bank 年度 CPI、GDP 与失业率可以保留作跨国长期比较，但不应作为面向股市的主宏观卡片。

## SEC EDGAR

### 接口、字段与详情链接

- ticker 到 CIK：`https://www.sec.gov/files/company_tickers.json`
- 公司 submissions：`https://data.sec.gov/submissions/CIK##########.json`，CIK 左补零至 10 位。
- 申报详情：`https://www.sec.gov/Archives/edgar/data/{cik_without_leading_zeroes}/{accession_without_hyphens}/{primaryDocument}`

公司元数据包括 `name`、`tickers`、`exchanges`。`filings.recent` 以并行数组提供 `accessionNumber`、`filingDate`、`reportDate`、`acceptanceDateTime`、`form`、`fileNumber`、`primaryDocument`、`primaryDocDescription`；实现必须按相同索引组合字段。历史分片由 `filings.files` 指向，但仅展示近期公告时无需下载。

以上来自 [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)。接口无需 key。SEC 要求声明式 User-Agent 标识应用或组织以及联系信息；公平访问上限目前为每秒 10 次，超限可能被暂时阻断，参见 [Accessing EDGAR Data](https://www.sec.gov/os/accessing-edgar-data)。

### 最小接入

用有限自选股名单，不扫描全市场；每家公司串行请求 submissions，仅保留 `8-K`、`10-K`、`10-Q`、`6-K`、`20-F`，合并后按日期倒序取 10～15 条。User-Agent 联系信息应由 Actions variable 配置，重试须指数退避。

## Polymarket

### 接口与字段

发现热门活跃事件使用 Gamma 公共接口：

```text
GET https://gamma-api.polymarket.com/events
  ?active=true
  &closed=false
  &limit=15
  &order=volume24hr
  &ascending=false
```

event 常用字段包括 `id`、`title`、`slug`、`description`、`startDate`、`endDate`、`active`、`closed`、`volume`、`volume24hr`、`liquidity`、`markets`；嵌套 market 可使用 `question`、`slug`、`outcomes`、`outcomePrices`、`volume24hr`、`liquidity`、`active`、`closed`。部分数值和数组可能以字符串返回，解析时需要容错。官方说明见 [Gamma Markets API overview](https://docs.polymarket.com/developers/gamma-markets-api/overview) 和 [List events](https://docs.polymarket.com/api-reference/events/list-events)。

Gamma 公共读接口无需认证；交易及部分 CLOB 操作才需要签名，本项目不应调用交易接口。官方 [Rate limits](https://docs.polymarket.com/quickstart/introduction/rate-limits) 说明请求经 Cloudflare 限流/排队；实现应处理 HTTP 429 并退避。官方未规定 User-Agent 格式。

### 最小接入

按 `volume24hr` 取 10～15 个活跃未关闭事件，页面展示事件标题、24 小时交易量、流动性以及主要 outcome 概率，链接构造为 `https://polymarket.com/event/{slug}`。Gamma schema 的产品属性较强，应对字段缺失和类型变化做防御性解析，并让该来源独立降级。

## 实施顺序与边界

1. 先完成五个主题 Tab 和独立失败降级。
2. Lobsters、arXiv AI 可低成本复用现有列表与论文能力。
3. GitHub Releases 使用 Actions 自带 token 和小型关注范围，避免匿名共享 IP 限额。
4. 股市宏观数据使用 BLS 月度三系列和美国财政部日度收益率；BEA GDP 因需要 key 暂缓。
5. SEC 只抓自选股的重要表单，并严格遵守 User-Agent 与速率约束。
6. Polymarket 只读 Gamma 公共发现接口，不接交易能力。

World Bank 年度指标更适合跨国长期比较，其时效性不足以支撑股市动态页面。免密的结构化基线应是 BLS 月度通胀/就业与美国财政部日度收益率曲线；两者都必须标明观测日期、非实时属性和修订边界。

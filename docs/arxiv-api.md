# arXiv API 调研：金融与量化论文

调研日期：2026-08-14（北京时间）。本文只采用 arXiv 官方文档、官方分类表和官方 API 的实际响应。

## 结论与建议

- API 地址使用 `https://export.arxiv.org/api/query`。官方旧版手册中的多数示例仍写成 HTTP，但当前 HTTP 请求会返回 `301 Moved Permanently` 并跳转到同一 HTTPS URL；HTTPS 实测返回 `200` 和 `application/atom+xml`。
- 金融主集合应以 Quantitative Finance 的八个实质分类为准：`q-fin.CP`、`q-fin.GN`、`q-fin.MF`、`q-fin.PM`、`q-fin.PR`、`q-fin.RM`、`q-fin.ST`、`q-fin.TR`。其中量化交易最直接对应 `q-fin.TR`，策略/组合、统计模型、计算方法还分别对应 `q-fin.PM`、`q-fin.ST`、`q-fin.CP`。
- `q-fin.EC` 是 `econ.GN` 的别名，范围是一般经济学，不建议无条件并入金融论文 Tab。若希望覆盖金融计量论文，可额外查询 `econ.EM`，同时用金融关键词约束，避免把一般计量经济学全部收入。
- 取“最新论文”使用 `sortBy=submittedDate&sortOrder=descending`；不要使用默认的相关性排序。
- 当前产品只需 15 篇最新论文，应一次请求取完（`start=0&max_results=15`），无需分页，也避免触碰限流。
- 官方要求所有受调用者控制的机器合计 **每三秒最多一次请求**，并且 **同一时间只能有一个连接**。如果必须分页或重试，每次请求间隔至少三秒，禁止用并发或多机器绕过限制。
- API 原生返回英文摘要 `<summary>`。中文摘要不是 arXiv 字段，应在获取后由项目现有翻译/摘要服务生成，并缓存结果；展示时保留原论文链接、作者、原始标题或英文摘要作为可追溯信息。

官方依据：

- [API User Manual](https://info.arxiv.org/help/api/user-manual.html)
- [API Terms of Use：Rate limits](https://info.arxiv.org/help/api/tou.html#rate-limits)
- [arXiv Category Taxonomy](https://arxiv.org/category_taxonomy)
- [HTTPS API 实例（q-fin.TR，最新一条）](https://export.arxiv.org/api/query?search_query=cat:q-fin.TR&start=0&max_results=1&sortBy=submittedDate&sortOrder=descending)

## 分类选择

官方分类表对 Quantitative Finance 的定义如下：

| 分类 | 官方名称 | 对本项目的用途 |
| --- | --- | --- |
| `q-fin.CP` | Computational Finance | 蒙特卡洛、PDE、格点等金融建模计算方法 |
| `q-fin.GN` | General Finance | 一般量化金融方法 |
| `q-fin.MF` | Mathematical Finance | 随机、概率、泛函等金融数学方法 |
| `q-fin.PM` | Portfolio Management | 选股、优化、资产配置、投资策略和业绩衡量 |
| `q-fin.PR` | Pricing of Securities | 证券、衍生品和结构化产品定价与对冲 |
| `q-fin.RM` | Risk Management | 交易、银行、保险等场景的金融风险管理 |
| `q-fin.ST` | Statistical Finance | 金融市场与经济数据的统计、计量和经济物理分析 |
| `q-fin.TR` | Trading and Market Microstructure | 市场微观结构、流动性、自动交易、做市等 |
| `econ.EM` | Econometrics | 计量理论、微观/宏观计量及经济数据统计推断；范围比金融更宽 |

来源：[arXiv Category Taxonomy](https://arxiv.org/category_taxonomy)。分类表还明确指出 `q-fin.EC` 是 `econ.GN` 的别名，因此它不应被误认为独立的金融细分类。

建议的基础类别表达式（显式枚举，避免依赖官方手册没有记载的通配符行为）：

```text
(cat:q-fin.CP OR cat:q-fin.GN OR cat:q-fin.MF OR cat:q-fin.PM OR
 cat:q-fin.PR OR cat:q-fin.RM OR cat:q-fin.ST OR cat:q-fin.TR)
```

如果产品确实希望纳入金融计量，可在上述表达式之外增加受关键词约束的 `econ.EM`，例如：

```text
OR (cat:econ.EM AND
    (all:finance OR all:financial OR all:trading OR all:portfolio OR
     all:asset OR all:market))
```

这部分关键词是产品检索策略，不是 arXiv 官方分类定义；需要通过实际结果持续评估召回率和噪声。

## 查询语法

查询接口接受 GET 或 POST。GET 参数用 `&` 分隔，主要参数是：

| 参数 | 含义 | 默认值 |
| --- | --- | --- |
| `search_query` | 字段查询及布尔表达式 | 无 |
| `id_list` | 逗号分隔的 arXiv ID | 无 |
| `start` | 返回结果的起始位置，0-based | `0` |
| `max_results` | 本次返回条数 | `10` |

官方支持的检索字段为：`ti`（标题）、`au`（作者）、`abs`（摘要）、`co`（评论）、`jr`（期刊引用）、`cat`（分类）、`rn`（报告号）、`id`（ID，官方建议改用 `id_list`）以及 `all`（以上所有字段）。

布尔操作符是大写的 `AND`、`OR`、`ANDNOT`。括号用于控制优先级，短语用双引号包裹。手写 URL 时：空格编码为 `+`，左右括号编码为 `%28`/`%29`，双引号编码为 `%22`；代码中应让 HTTP 客户端负责参数编码。

例如，专门检索自动/算法交易：

```text
cat:q-fin.TR AND
(all:"algorithmic trading" OR all:"automated trading" OR
 all:"quantitative trading" OR all:"market making")
```

官方还支持提交日期范围过滤：

```text
submittedDate:[YYYYMMDDHHMM TO YYYYMMDDHHMM]
```

日期时间使用 GMT、24 小时制，精确到分钟。URL 编码示例可见官方手册给出的查询：
[作者与 submittedDate 范围查询](https://export.arxiv.org/api/query?search_query=au:del_maestro+AND+submittedDate:%5B202301010600+TO+202401010600%5D)。

来源：[API User Manual：Details of Query Construction](https://info.arxiv.org/help/api/user-manual.html#51-details-of-query-construction)。

## 排序与“最新”的含义

查询支持：

- `sortBy=relevance|lastUpdatedDate|submittedDate`
- `sortOrder=ascending|descending`

最新提交排序应明确传入：

```text
sortBy=submittedDate&sortOrder=descending
```

完整示例：

```text
https://export.arxiv.org/api/query
  ?search_query=cat:q-fin.TR
  &start=0
  &max_results=15
  &sortBy=submittedDate
  &sortOrder=descending
```

来源：[API User Manual：sort order for return results](https://info.arxiv.org/help/api/user-manual.html#3113-sort-order-for-return-results)。Atom 条目中的 `<published>` 是论文 v1 的提交时间，`<updated>` 是当前返回版本的提交时间；v1 时两者相同。因此实现应将“新论文”与“最近修订”区分开，前者使用 `submittedDate`/`published`，后者才使用 `lastUpdatedDate`/`updated`。来源：[API User Manual：Details of Atom Results Returned](https://info.arxiv.org/help/api/user-manual.html#52-details-of-atom-results-returned)。

## 分页与结果上限

- `start` 是总结果集中首条返回结果的 0-based 索引。
- `max_results` 是本次请求返回的条数，默认 10。
- 官方称总共最多可取 30,000 条，但必须按每批最多 2,000 条分页。
- `max_results > 30000` 会返回 HTTP 400。
- 官方建议把超过 1,000 条的查询进一步收窄，或至少使用更小的切片；大量元数据采集应改用 OAI-PMH。

分页例子是 `start=0&max_results=10`、`start=10&max_results=10`、`start=20&max_results=10`。本项目只展示最新 15 条，单次 `max_results=15` 即可。

来源：[API User Manual：start and max_results paging](https://info.arxiv.org/help/api/user-manual.html#3112-start-and-max_results-paging)。

## Atom 1.0 响应字段

API 的成功和错误响应都使用 Atom 1.0 XML。解析时需要处理三个命名空间：默认 Atom、`opensearch` 与 `arxiv`。

Feed 级字段：

| 字段 | 含义 |
| --- | --- |
| `<title>` | 包含规范化查询字符串的 feed 标题 |
| `<id>` | 此查询的唯一 ID |
| `<updated>` | 此查询结果的更新时间；手册称设为当天午夜 |
| `<link>` | 可重新获取该 feed 的 URL |
| `<opensearch:totalResults>` | 匹配总数 |
| `<opensearch:startIndex>` | 当前页首项的 0-based 索引 |
| `<opensearch:itemsPerPage>` | 当前返回条数 |

Entry 级字段：

| 字段 | 含义 |
| --- | --- |
| `<title>` | 论文标题 |
| `<id>` | arXiv 摘要页 ID/URL，实际响应可能带版本号 |
| `<published>` | v1 提交时间 |
| `<updated>` | 当前返回版本提交时间 |
| `<summary>` | 英文摘要 |
| `<author><name>` | 作者；每位作者一个 `<author>` |
| `<link>` | 摘要页、PDF，存在时还可能有 DOI 链接 |
| `<category>` | arXiv、ACM 或 MSC 分类，可有多个 |
| `<arxiv:primary_category>` | arXiv 主分类 |
| `<arxiv:comment>` | 作者评论，可选 |
| `<arxiv:affiliation>` | 作者机构，位于 `<author>` 下，可选 |
| `<arxiv:journal_ref>` | 期刊引用，可选 |
| `<arxiv:doi>` | DOI，可选 |

解析器不应依赖元素的展示顺序，并应把可选扩展字段视为可缺失。

来源：[API User Manual：Outline of an Atom feed](https://info.arxiv.org/help/api/user-manual.html#33-outline-of-an-atom-feed) 与 [Details of Atom Results Returned](https://info.arxiv.org/help/api/user-manual.html#52-details-of-atom-results-returned)。

## 请求频率、并发和 User-Agent

官方 Terms of Use 对 legacy APIs（明确包括 arXiv API）规定：

1. 所有受调用者控制的机器合计，每三秒最多一个请求；
2. 同时只允许一个连接；
3. 不得通过增加机器数量绕过限制；需要更高频率时应联系 arXiv 支持。

来源：[API Terms of Use：Rate limits](https://info.arxiv.org/help/api/tou.html#rate-limits)。User Manual 也建议连续调用之间加入三秒延迟：[start and max_results paging](https://info.arxiv.org/help/api/user-manual.html#3112-start-and-max_results-paging)。

截至调研日，官方 [API Terms of Use](https://info.arxiv.org/help/api/tou.html)、[API User Manual](https://info.arxiv.org/help/api/user-manual.html) 和 [API Basics](https://info.arxiv.org/help/api/basics.html) **没有给出 User-Agent 的固定格式，也没有明文要求必须包含邮箱**。因此不能把第三方客户端的 User-Agent 约定写成 arXiv 官方规范。

项目仍可主动设置稳定、可识别的 User-Agent，例如 `livenews/<version> (<repository-or-contact-url>)`，便于服务端定位问题；这是项目建议，不是上述官方文档明示的要求。

## HTTP/HTTPS 端点现状

官方 User Manual 仍把基础 URL 写为：

```text
http://export.arxiv.org/api/{method_name}?{parameters}
```

来源：[API User Manual：Calling the API](https://info.arxiv.org/help/api/user-manual.html#31-calling-the-api)。

但在 2026-08-14（北京时间）的官方端点实测中：

- `http://export.arxiv.org/api/query?...` 返回 HTTP 301，`Location` 指向对应的 `https://export.arxiv.org/api/query?...`；
- `https://export.arxiv.org/api/query?...` 返回 HTTP 200，`Content-Type: application/atom+xml; charset=utf-8`，并包含正常 Atom feed。

可复核的官方 API URL：[q-fin.TR 最新一条](https://export.arxiv.org/api/query?search_query=cat:q-fin.TR&start=0&max_results=1&sortBy=submittedDate&sortOrder=descending)。实现应直接使用 HTTPS，避免一次不必要的重定向，也避免某些客户端在跳转时改变请求行为。

## 面向本项目的最小实现约束

1. 单次 HTTPS 请求取最近 15 条，不并发分页。
2. 查询显式枚举八个 `q-fin` 分类；是否扩展 `econ.EM + 金融关键词` 应作为独立产品选择。
3. 使用 `sortBy=submittedDate&sortOrder=descending`。
4. 解析 Atom 的命名空间、`entry` 列表、`summary`、作者、分类、`published`、`updated` 及链接。
5. 网络失败时保留上一版缓存，不用空结果覆盖页面。
6. 英文摘要翻译后缓存；翻译失败时回退显示英文摘要，而不是丢弃论文。
7. 后续任何重试或分页都必须串行，并保证请求起始时间至少相隔三秒。

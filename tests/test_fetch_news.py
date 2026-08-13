import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

# 在导入模块前先模拟环境变量
os.environ["OPENAI_API_KEY"] = "test_key"
os.environ["OPENAI_API_BASE"] = "https://api.test.com/v1"
os.environ["OPENAI_MODEL"] = "test-model"

# 导入要测试的模块
from scripts.fetch_news import (
    ARXIV_AI_SEARCH_QUERY,
    ARXIV_PAPER_LIMIT,
    ARXIV_SEARCH_QUERY,
    ArxivTranslationCache,
    HN_STORY_LIMIT,
    StoryCache,
    _process_html_content,
    clean_html_text,
    fetch_arxiv_ai_papers,
    fetch_arxiv_papers,
    fetch_github_releases,
    fetch_github_trending,
    fetch_lobsters,
    fetch_polymarket_markets,
    fetch_product_hunt,
    fetch_bls_market_indicators,
    fetch_sec_filings,
    fetch_treasury_yields,
    generate_html,
    get_article_content,
    main,
)

# 测试数据
MOCK_STORY = {
    "data": {
        "title": "Test Story",
        "url": "https://example.com",
        "author": "test_user",
        "score": 100,
        "time": datetime.now().isoformat(),
        "comments_count": 10,
        "article_summary": "Test summary",
        "comments_summary": "Test comments",
        "comments_url": "https://news.ycombinator.com/item?id=123",
    },
    "article_content": "Test content",
    "article_summary": "Test summary",
    "comments_summary": "Test comments",
    "cache_time": datetime.now().isoformat(),
}


@pytest.fixture
def cache():
    """创建临时缓存文件"""
    cache_file = "tests/test_cache.json"
    cache = StoryCache(cache_file=cache_file)
    yield cache
    # 清理测试文件
    if os.path.exists(cache_file):
        os.remove(cache_file)


@pytest.fixture(autouse=True)
def mock_env():
    """自动设置测试环境变量"""
    with patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test_key",
            "OPENAI_API_BASE": "https://api.test.com/v1",
            "OPENAI_MODEL": "test-model",
        },
    ):
        yield


def test_story_cache_init(cache):
    """测试缓存初始化"""
    assert isinstance(cache.cache, dict)
    assert cache.max_age_hours == 24


def test_story_cache_set_get(cache):
    """测试缓存的设置和获取"""
    story_id = "123"
    cache.set(story_id, MOCK_STORY["data"])
    result = cache.get(story_id)
    assert result is not None
    assert result["data"]["title"] == "Test Story"


def test_story_cache_expiration(cache):
    """测试缓存过期"""
    story_id = "123"
    # 创建一个过期的缓存条目
    expired_story = MOCK_STORY.copy()
    expired_story["cache_time"] = (datetime.now() - timedelta(hours=25)).isoformat()
    cache.cache[story_id] = expired_story

    result = cache.get(story_id)
    assert result is None


def test_clean_html_text():
    """测试HTML清理功能"""
    html = "<p>Test <b>content</b></p>"
    result = clean_html_text(html)
    assert result == "Test content"


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://example.com", None),  # 模拟请求失败
        ("https://nytimes.com", None),  # 测试付费墙网站
    ],
)
def test_get_article_content(url, expected):
    """测试文章内容获取"""
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            headers={"content-type": "text/html"},
            text="<html><body>Test content</body></html>",
        )
        result = get_article_content(url)
        assert result == expected


def test_process_html_content():
    """测试HTML内容处理"""
    mock_response = MagicMock(
        headers={"content-type": "text/html"},
        text="""
        <html>
            <body>
                <article>
                    Test content with more text to pass the length check.
                    This is a longer piece of content that should be processed correctly.
                    Adding more text to ensure it passes the minimum length requirement.
                </article>
            </body>
        </html>
        """,
    )
    result = _process_html_content(mock_response)
    assert result is not None
    assert "Test content" in result


def test_process_html_content_non_html():
    """测试非HTML内容处理"""
    mock_response = MagicMock(
        headers={"content-type": "application/pdf"}, text="Test content"
    )
    result = _process_html_content(mock_response)
    assert result is None


def test_main_fails_when_no_stories_are_fetched():
    """抓取失败时必须阻止空目录覆盖线上站点。"""
    with patch("scripts.fetch_news.fetch_top_stories", return_value=[]):
        with pytest.raises(RuntimeError, match="未获取到任何故事"):
            main()


def test_hacker_news_is_limited_to_30_stories():
    assert HN_STORY_LIMIT == 30


def test_arxiv_is_limited_to_15_papers():
    assert ARXIV_PAPER_LIMIT == 15


def test_fetch_github_trending():
    html = """
    <article class="Box-row">
      <h2><a href="/octocat/hello-world">octocat   /\n hello-world</a></h2>
      <p>A friendly repository</p>
      <span itemprop="programmingLanguage">Python</span>
      <a href="/octocat/hello-world/stargazers">1,234</a>
      <a href="/octocat/hello-world/forks">56</a>
      <span>321 stars today</span>
    </article>
    """
    response = MagicMock(text=html)
    response.raise_for_status.return_value = None

    with patch("requests.get", return_value=response):
        repositories = fetch_github_trending(limit=1)

    assert repositories == [
        {
            "name": "octocat/hello-world",
            "url": "https://github.com/octocat/hello-world",
            "description": "A friendly repository",
            "language": "Python",
            "stars": "1,234",
            "forks": "56",
            "stars_today": "321 stars today",
        }
    ]


def test_fetch_product_hunt():
    feed = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>Useful Product</title>
        <link rel="alternate" href="https://www.producthunt.com/products/useful" />
        <published>2026-08-13T10:00:00-07:00</published>
        <content type="html">&lt;p&gt;It does useful things&lt;/p&gt;</content>
        <author><name>A Maker</name></author>
      </entry>
    </feed>"""
    response = MagicMock(content=feed.encode())
    response.raise_for_status.return_value = None

    with patch("requests.get", return_value=response):
        products = fetch_product_hunt(limit=1)

    assert products == [
        {
            "name": "Useful Product",
            "url": "https://www.producthunt.com/products/useful",
            "description": "It does useful things",
            "maker": "A Maker",
            "published": "2026-08-13",
        }
    ]


def test_fetch_lobsters():
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = [
        {
            "title": "Deep modules",
            "url": "https://example.com/deep-modules",
            "comments_url": "https://lobste.rs/s/abc/deep_modules",
            "score": 42,
            "comment_count": 7,
            "submitter_user": {"username": "alice"},
            "tags": ["programming"],
            "created_at": "2026-08-14T01:00:00.000Z",
        }
    ]

    with patch("requests.get", return_value=response):
        stories = fetch_lobsters(limit=1)

    assert stories[0]["title"] == "Deep modules"
    assert stories[0]["submitter"] == "alice"
    assert stories[0]["tags"] == ["programming"]


def test_fetch_lobsters_accepts_string_submitter():
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = [
        {"title": "Story", "submitter_user": "alice", "tags": []}
    ]

    with patch("requests.get", return_value=response):
        stories = fetch_lobsters(limit=1)

    assert stories[0]["submitter"] == "alice"


def test_fetch_github_releases_skips_repositories_without_releases():
    release_response = MagicMock(status_code=200)
    release_response.raise_for_status.return_value = None
    release_response.json.return_value = {
        "name": "Version 2",
        "tag_name": "v2.0.0",
        "html_url": "https://github.com/octocat/hello/releases/tag/v2.0.0",
        "published_at": "2026-08-14T01:00:00Z",
        "prerelease": False,
    }
    missing_response = MagicMock(status_code=404)

    with patch("requests.get", side_effect=[release_response, missing_response]):
        releases = fetch_github_releases(
            [
                {"name": "octocat/hello", "url": "https://github.com/octocat/hello"},
                {"name": "octocat/no-releases", "url": "https://github.com/octocat/no-releases"},
            ]
        )

    assert releases == [
        {
            "repository": "octocat/hello",
            "name": "Version 2",
            "tag": "v2.0.0",
            "url": "https://github.com/octocat/hello/releases/tag/v2.0.0",
            "published": "2026-08-14",
            "prerelease": False,
        }
    ]


def test_fetch_bls_market_indicators_calculates_market_sensitive_values():
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "status": "REQUEST_SUCCEEDED",
        "Results": {
            "series": [
                {"seriesID": "CUSR0000SA0", "data": [{"year": "2026", "period": "M07", "value": "324"}, {"year": "2025", "period": "M07", "value": "315"}]},
                {"seriesID": "LNS14000000", "data": [{"year": "2026", "period": "M07", "value": "4.2"}]},
                {"seriesID": "CES0000000001", "data": [{"year": "2026", "period": "M07", "value": "159000"}, {"year": "2026", "period": "M06", "value": "158850"}]},
            ]
        },
    }

    with patch("requests.post", return_value=response):
        indicators = fetch_bls_market_indicators()

    assert [indicator["value"] for indicator in indicators] == ["2.9", "4.2", "+150"]
    assert indicators[2]["unit"] == "千人"


def test_fetch_treasury_yields_calculates_curve_spread():
    feed = """<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"
      xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">
      <entry><content type="application/xml"><m:properties>
        <d:NEW_DATE>2026-08-12T00:00:00</d:NEW_DATE>
        <d:BC_2YEAR>4.20</d:BC_2YEAR><d:BC_10YEAR>4.68</d:BC_10YEAR>
      </m:properties></content></entry>
    </feed>"""
    response = MagicMock(content=feed.encode())
    response.raise_for_status.return_value = None

    with patch("requests.get", return_value=response):
        yields = fetch_treasury_yields()

    assert [item["value"] for item in yields] == ["4.20", "4.68", "+0.48"]


def test_fetch_sec_filings_filters_forms_and_sorts():
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "name": "Example Corp",
        "filings": {
            "recent": {
                "form": ["4", "10-Q", "8-K"],
                "accessionNumber": ["0001-26-000001", "0001-26-000002", "0001-26-000003"],
                "primaryDocument": ["form4.htm", "quarter.htm", "current.htm"],
                "filingDate": ["2026-08-14", "2026-08-13", "2026-08-14"],
                "primaryDocDescription": ["Form 4", "Quarterly report", "Current report"],
            }
        },
    }

    with (
        patch.dict("scripts.fetch_news.SEC_WATCHLIST", {"EX": "0000000001"}, clear=True),
        patch("requests.get", return_value=response),
    ):
        filings = fetch_sec_filings()

    assert [filing["form"] for filing in filings] == ["8-K", "10-Q"]
    assert filings[0]["url"].endswith("/1/000126000003/current.htm")


def test_fetch_polymarket_markets_parses_outcomes():
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = [
        {
            "title": "Will it happen?",
            "slug": "will-it-happen",
            "volume24hr": 12345.6,
            "liquidity": 5000,
            "endDate": "2026-12-31T00:00:00Z",
            "markets": [
                {
                    "active": True,
                    "closed": False,
                    "outcomes": '["Yes", "No"]',
                    "outcomePrices": '["0.62", "0.38"]',
                    "volume24hr": 10000,
                }
            ],
        }
    ]

    with (
        patch.dict("scripts.fetch_news.POLYMARKET_TAGS", {"120": "金融"}, clear=True),
        patch("requests.get", return_value=response) as request,
    ):
        markets = fetch_polymarket_markets(limit=1)

    assert request.call_args.kwargs["params"]["tag_id"] == "120"
    assert markets[0]["topics"] == ["金融"]
    assert markets[0]["outcomes"] == [
        {"name": "Yes", "probability": 62.0},
        {"name": "No", "probability": 38.0},
    ]
    assert markets[0]["url"].endswith("/will-it-happen")


def test_fetch_polymarket_markets_deduplicates_topics_and_sorts_by_volume():
    shared_event = {
        "id": "shared",
        "title": "Will AI company valuation rise?",
        "slug": "ai-valuation",
        "volume24hr": 200,
        "markets": [],
    }
    crypto_event = {
        "id": "crypto",
        "title": "Will Bitcoin rise?",
        "slug": "bitcoin-rise",
        "volume24hr": 300,
        "markets": [],
    }
    responses = []
    for events in ([shared_event], [shared_event], [crypto_event]):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = events
        responses.append(response)

    with (
        patch.dict(
            "scripts.fetch_news.POLYMARKET_TAGS",
            {"120": "金融", "439": "AI", "21": "加密市场"},
            clear=True,
        ),
        patch("requests.get", side_effect=responses),
    ):
        markets = fetch_polymarket_markets(limit=10)

    assert [market["question"] for market in markets] == [
        "Will Bitcoin rise?",
        "Will AI company valuation rise?",
    ]
    assert markets[1]["topics"] == ["AI", "金融"]


def test_fetch_arxiv_papers_translates_and_caches_abstract(tmp_path):
    feed = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>http://arxiv.org/abs/2608.12345v1</id>
        <title>  Quantitative Trading\n with Signals </title>
        <summary>  An English abstract about quantitative trading. </summary>
        <published>2026-08-13T10:00:00Z</published>
        <updated>2026-08-13T10:00:00Z</updated>
        <link href="https://arxiv.org/abs/2608.12345v1" rel="alternate" type="text/html" />
        <link href="https://arxiv.org/pdf/2608.12345v1" rel="related" type="application/pdf" title="pdf" />
        <category term="q-fin.TR" />
        <arxiv:primary_category term="q-fin.TR" />
        <author><name>Alice Researcher</name></author>
        <author><name>Bob Quant</name></author>
      </entry>
    </feed>"""
    response = MagicMock(content=feed.encode())
    response.raise_for_status.return_value = None
    cache = ArxivTranslationCache(cache_file=str(tmp_path / "arxiv_cache.json"))

    with (
        patch("requests.get", return_value=response) as mock_get,
        patch("scripts.fetch_news.get_summary", return_value="中文量化交易摘要") as translate,
    ):
        papers = fetch_arxiv_papers(limit=1, cache=cache)
        cached_papers = fetch_arxiv_papers(limit=1, cache=cache)

    assert papers == cached_papers
    assert papers == [
        {
            "id": "2608.12345v1",
            "title": "Quantitative Trading with Signals",
            "url": "https://arxiv.org/abs/2608.12345v1",
            "html_url": "https://arxiv.org/html/2608.12345v1",
            "pdf_url": "https://arxiv.org/pdf/2608.12345v1",
            "authors": ["Alice Researcher", "Bob Quant"],
            "categories": ["q-fin.TR"],
            "primary_category": "q-fin.TR",
            "published": "2026-08-13",
            "updated": "2026-08-13T10:00:00Z",
            "summary_zh": "中文量化交易摘要",
            "translation_available": True,
        }
    ]
    assert mock_get.call_args.kwargs["params"]["sortBy"] == "submittedDate"
    assert mock_get.call_args.kwargs["params"]["sortOrder"] == "descending"
    assert "q-fin.TR" in ARXIV_SEARCH_QUERY
    assert "q-fin.*" not in ARXIV_SEARCH_QUERY
    assert translate.call_count == 1


def test_fetch_arxiv_papers_falls_back_to_english_abstract(tmp_path):
    feed = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>https://arxiv.org/abs/2608.54321v1</id>
        <title>Market Microstructure</title>
        <summary>An English abstract.</summary>
        <published>2026-08-13T10:00:00Z</published>
        <updated>2026-08-13T10:00:00Z</updated>
        <arxiv:primary_category term="q-fin.TR" />
      </entry>
    </feed>"""
    response = MagicMock(content=feed.encode())
    response.raise_for_status.return_value = None
    cache = ArxivTranslationCache(cache_file=str(tmp_path / "arxiv_cache.json"))

    with (
        patch("requests.get", return_value=response),
        patch(
            "scripts.fetch_news.get_summary",
            return_value="摘要生成失败（网络错误）",
        ),
    ):
        papers = fetch_arxiv_papers(limit=1, cache=cache)

    assert papers[0]["summary_zh"] == "An English abstract."
    assert papers[0]["translation_available"] is False
    assert cache.cache == {}


def test_fetch_arxiv_ai_papers_uses_ai_categories(tmp_path):
    cache = ArxivTranslationCache(cache_file=str(tmp_path / "arxiv_cache.json"))
    with patch("scripts.fetch_news.fetch_arxiv_papers", return_value=[]) as fetch:
        fetch_arxiv_ai_papers(limit=3, cache=cache)

    assert "cat:cs.AI" in ARXIV_AI_SEARCH_QUERY
    fetch.assert_called_once_with(
        limit=3,
        cache=cache,
        search_query=ARXIV_AI_SEARCH_QUERY,
    )


def test_generate_html_renders_topic_tabs_and_sources(tmp_path, monkeypatch):
    template = os.path.join(os.path.dirname(__file__), "..", "templates", "index.html")
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "index.html").write_text(
        open(template, encoding="utf-8").read(), encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)

    generate_html(
        [],
        github_repositories=[{"name": "octocat/hello-world", "url": "https://github.com/octocat/hello-world", "description": "Hello", "language": "Python", "stars": "1", "forks": "0", "stars_today": "1 star today"}],
        product_hunt_products=[{"name": "Useful Product", "url": "https://example.com", "description": "Useful", "maker": "Maker", "published": "2026-08-13"}],
        arxiv_papers=[{"id": "2608.12345v1", "title": "Quant Paper", "url": "https://arxiv.org/abs/2608.12345v1", "html_url": "https://arxiv.org/html/2608.12345v1", "pdf_url": "https://arxiv.org/pdf/2608.12345v1", "authors": ["Researcher"], "categories": ["q-fin.TR"], "primary_category": "q-fin.TR", "published": "2026-08-13", "updated": "2026-08-13T10:00:00Z", "summary_zh": "中文摘要", "translation_available": True}],
        lobsters_stories=[{"title": "Lobsters Story", "url": "https://example.com/lobsters", "comments_url": "https://lobste.rs/s/test", "score": 10, "comment_count": 2, "submitter": "alice", "tags": ["python"], "created_at": "2026-08-14"}],
        github_releases=[{"repository": "octocat/hello-world", "name": "Version 2", "tag": "v2", "url": "https://github.com/octocat/hello-world/releases/tag/v2", "published": "2026-08-14", "prerelease": False}],
        arxiv_ai_papers=[{"id": "2608.54321v1", "title": "AI Paper", "url": "https://arxiv.org/abs/2608.54321v1", "html_url": "https://arxiv.org/html/2608.54321v1", "pdf_url": "", "authors": ["AI Researcher"], "categories": ["cs.AI"], "primary_category": "cs.AI", "published": "2026-08-14", "updated": "2026-08-14T10:00:00Z", "summary_zh": "AI 中文摘要", "translation_available": True}],
        macro_indicators=[{"id": "LNS14000000", "name": "美国失业率", "value": "4.2", "unit": "%", "date": "2026-07", "detail": "最新公布值", "url": "https://data.bls.gov/timeseries/LNS14000000"}],
        sec_filings=[{"ticker": "AAPL", "company": "Apple Inc.", "form": "8-K", "date": "2026-08-14", "description": "Current report", "url": "https://www.sec.gov/example"}],
        polymarket_markets=[{"question": "Will it happen?", "url": "https://polymarket.com/event/test", "topics": ["AI", "金融"], "outcomes": [{"name": "Yes", "probability": 62.0}], "volume_24h": 1000, "liquidity": 500, "end_date": "2026-12-31"}],
    )

    html = (tmp_path / "public" / "index.html").read_text(encoding="utf-8")
    assert 'id="tech-community-tab"' in html
    assert 'id="open-source-tab"' in html
    assert 'id="new-products-tab"' in html
    assert 'id="research-tab"' in html
    assert 'id="finance-tab"' in html
    assert "octocat/hello-world" in html
    assert "Useful Product" in html
    assert "中文摘要" in html
    assert "Lobsters Story" in html
    assert "Version 2" in html
    assert "AI Paper" in html
    assert "美国失业率" in html
    assert "AAPL" in html
    assert "Will it happen?" in html
    assert "Polymarket · 金融与 AI 预测市场" in html
    assert 'href="https://arxiv.org/html/2608.12345v1"' in html
    assert "HTML 在线版" in html
    assert not (tmp_path / "public" / "page").exists()

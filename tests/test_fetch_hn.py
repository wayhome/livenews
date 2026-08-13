import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

# 在导入模块前先模拟环境变量
os.environ["OPENAI_API_KEY"] = "test_key"
os.environ["OPENAI_API_BASE"] = "https://api.test.com/v1"
os.environ["OPENAI_MODEL"] = "test-model"

# 导入要测试的模块
from scripts.fetch_hn import (
    HN_STORY_LIMIT,
    StoryCache,
    _process_html_content,
    clean_html_text,
    fetch_github_trending,
    get_article_content,
    fetch_product_hunt,
    generate_html,
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
    with patch("scripts.fetch_hn.fetch_top_stories", return_value=[]):
        with pytest.raises(RuntimeError, match="未获取到任何故事"):
            main()


def test_hacker_news_is_limited_to_30_stories():
    assert HN_STORY_LIMIT == 30


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


def test_generate_html_renders_source_tabs(tmp_path, monkeypatch):
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
    )

    html = (tmp_path / "public" / "index.html").read_text(encoding="utf-8")
    assert 'id="hacker-news-tab"' in html
    assert 'id="github-trending-tab"' in html
    assert 'id="product-hunt-tab"' in html
    assert "octocat/hello-world" in html
    assert "Useful Product" in html
    assert not (tmp_path / "public" / "page").exists()

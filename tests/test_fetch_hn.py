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
    StoryCache,
    _process_html_content,
    clean_html_text,
    get_article_content,
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

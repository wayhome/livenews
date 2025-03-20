import json
import os
import re
import time
from datetime import datetime, timedelta

import pytz
import requests
from bs4 import BeautifulSoup
from dateutil import parser
from dotenv import load_dotenv
from jinja2 import Template
from markupsafe import Markup
from openai import OpenAI

# 加载环境变量
load_dotenv(override=True)

# OpenAI 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# 确保 API 基础 URL 格式正确
if OPENAI_API_BASE and not (
    OPENAI_API_BASE.startswith("http://") or OPENAI_API_BASE.startswith("https://")
):
    OPENAI_API_BASE = "https://" + OPENAI_API_BASE

# 初始化 OpenAI 客户端
try:
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)
except Exception as e:
    print(f"初始化 OpenAI 客户端时出错: {e}")
    raise


# 创建一个自定义的JSON编码器来处理datetime对象
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def _process_html_content(response):
    """处理 HTML 响应内容"""
    content_type = response.headers.get("content-type", "").lower()
    if "text/html" not in content_type:
        print(f"跳过非HTML内容: (Content-Type: {content_type})")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # 移除不需要的元素
    for element in soup(
        ["script", "style", "nav", "header", "footer", "iframe", "noscript"]
    ):
        element.decompose()

    # 尝试找到主要内容
    main_content = None
    content_candidates = soup.select(
        "article, main, .article-content, .post-content, .entry-content"
    )
    if content_candidates:
        main_content = content_candidates[0]

    if not main_content:
        main_content = soup.find("body")

    if not main_content:
        main_content = soup

    # 获取文本
    text = main_content.get_text(separator="\n", strip=True)

    # 清理文本
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)

    if len(text) < 50:
        print("跳过内容过短的文章")
        return None

    return text[:5000]


def get_article_content(url):
    """获取文章内容"""
    try:
        # 跳过已知的无法访问的网站
        blocked_domains = ["nytimes.com", "wsj.com", "bloomberg.com", "ft.com"]
        if any(domain in url.lower() for domain in blocked_domains):
            print(f"跳过付费墙网站: {url}")
            return None

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status()
        return _process_html_content(response)

    except requests.exceptions.SSLError:
        print(f"SSL错误，尝试不验证证书: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            response.raise_for_status()
            return _process_html_content(response)
        except Exception as e:
            print(f"二次尝试仍然失败: {e}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"获取文章内容失败: {e}")
        return None
    except Exception as e:
        print(f"处理文章内容时出错: {e}")
        return None


def get_summary(
    text, prompt="请用中文简明扼要地总结以下内容，限制在100字以内。", max_retries=3
):
    """使用 OpenAI 生成摘要"""
    if not text or not text.strip():
        return "暂无内容"

    for attempt in range(max_retries):
        try:
            print(f"正在生成摘要，第 {attempt + 1} 次尝试...")

            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text},
                ],
                temperature=0.7,
                max_tokens=3000,
                timeout=30,  # 设置超时时间
            )
            return response.choices[0].message.content

        except ValueError as e:
            print(f"配置错误: {e}")
            return "摘要生成失败（配置错误）"

        except requests.exceptions.ConnectionError as e:
            print(f"连接错误 (尝试 {attempt + 1}/{max_retries}):")
            print(f"  - 错误详情: {str(e)}")

        except requests.exceptions.Timeout as e:
            print(f"请求超时 (尝试 {attempt + 1}/{max_retries}): {str(e)}")

        except requests.exceptions.RequestException as e:
            print(f"请求错误 (尝试 {attempt + 1}/{max_retries}): {str(e)}")

        except Exception as e:
            print(f"未预期的错误 (尝试 {attempt + 1}/{max_retries}):")
            print(f"  - 错误类型: {type(e).__name__}")
            print(f"  - 错误详情: {str(e)}")
            import traceback

            traceback.print_exc()

        if attempt < max_retries - 1:
            sleep_time = (attempt + 1) * 5  # 递增等待时间
            print(f"等待 {sleep_time} 秒后重试...")
            time.sleep(sleep_time)
        else:
            print("已达到最大重试次数")
            return "摘要生成失败（网络错误）"


def fetch_hn_item(item_id):
    """获取 HN 单个项目的详细信息"""
    try:
        response = requests.get(
            f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"获取项目 {item_id} 时出错: {e}")
        return None


def clean_html_text(html_text):
    """清理HTML文本，返回纯文本"""
    if not html_text:
        return ""
    try:
        # 使用BeautifulSoup清理HTML
        soup = BeautifulSoup(html_text, "html.parser")
        # 获取纯文本
        text = soup.get_text()
        # 清理空白字符
        text = " ".join(text.split())
        return text
    except Exception as e:
        print(f"清理HTML文本时出错: {e}")
        return html_text


class StoryCache:
    def __init__(self, cache_file="public/story_cache.json", max_age_hours=24):
        self.cache_file = cache_file
        self.max_age_hours = max_age_hours
        self.cache = self._load_cache()
        self._clean_expired()  # 初始化时清理过期缓存

    def _clean_expired(self):
        """清理所有过期的缓存条目"""
        now = datetime.now()
        expired_keys = []

        for story_id, story in self.cache.items():
            try:
                cache_time = datetime.fromisoformat(story["cache_time"])
                if now - cache_time > timedelta(hours=self.max_age_hours):
                    expired_keys.append(story_id)
            except Exception as e:
                print(f"检查缓存条目 {story_id} 时出错: {e}")
                expired_keys.append(story_id)  # 错误的条目也清理掉

        # 删除过期条目
        if expired_keys:
            print(f"清理 {len(expired_keys)} 个过期缓存条目...")
            for key in expired_keys:
                del self.cache[key]
            self._save_cache()

    def _load_cache(self):
        """加载缓存文件"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    try:
                        return json.load(f)
                    except json.JSONDecodeError as e:
                        print(f"缓存文件格式错误: {e}，将创建新缓存")
                        # 备份损坏的缓存文件
                        backup_file = f"{self.cache_file}.bak"
                        try:
                            os.rename(self.cache_file, backup_file)
                            print(f"已将损坏的缓存文件备份为: {backup_file}")
                        except Exception as rename_err:
                            print(f"备份损坏的缓存文件失败: {rename_err}")
            return {}
        except Exception as e:
            print(f"加载缓存文件失败: {e}")
            return {}

    def _save_cache(self):
        """保存缓存文件"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(
                    self.cache, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder
                )
        except Exception as e:
            print(f"保存缓存文件失败: {e}")

    def get(self, story_id):
        """获取缓存的故事，如果评论数量增加且原数量小于20，返回需要更新摘要的标志"""
        if str(story_id) not in self.cache:
            return None

        story = self.cache[str(story_id)]
        try:
            cache_time = datetime.fromisoformat(story["cache_time"])

            # 检查缓存是否过期
            if datetime.now() - cache_time > timedelta(hours=self.max_age_hours):
                del self.cache[str(story_id)]
                self._save_cache()
                return None

            # 转换时间格式
            if "data" in story and isinstance(story["data"].get("time"), str):
                story["data"]["time"] = datetime.fromisoformat(story["data"]["time"])

            # 添加一个标志，表示是否需要更新评论摘要
            story["needs_comment_update"] = False

            return story
        except Exception as e:
            print(f"处理缓存数据出错: {e}")
            return None

    def set(
        self,
        story_id,
        story_data,
        article_content=None,
        article_summary=None,
        comments_summary=None,
        comments_count=0,  # 新增参数：评论数量
    ):
        """缓存故事数据"""
        # 设置新数据前先清理过期缓存
        if len(self.cache) > 100:  # 如果缓存条目过多，触发清理
            self._clean_expired()

        # 确保story_data中的时间是字符串格式
        if isinstance(story_data.get("time"), datetime):
            story_data["time"] = story_data["time"].isoformat()

        self.cache[str(story_id)] = {
            "data": story_data,
            "article_content": article_content,
            "article_summary": article_summary,
            "comments_summary": comments_summary,
            "comments_count": comments_count,  # 保存评论数量
            "cache_time": datetime.now().isoformat(),
        }
        self._save_cache()


def fetch_top_stories():
    """获取 HN 热门故事"""
    try:
        print("\n=== 环境信息 ===")
        print(f"OpenAI API Base: {OPENAI_API_BASE}")
        print(f"OpenAI Model: {OPENAI_MODEL}")
        print(f"API Key 长度: {len(OPENAI_API_KEY) if OPENAI_API_KEY else 0}")
        print("================\n")

        if not OPENAI_API_KEY:
            raise ValueError("未设置 OPENAI_API_KEY")

        # 验证 API 配置
        try:
            # 测试 API 连接
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": "测试连接"}],
                max_tokens=5,
            )
            print("API 连接测试成功")
        except Exception as e:
            print(f"API 连接测试失败: {e}")
            raise

        # 初始化缓存
        cache = StoryCache()

        print("开始获取热门故事...")
        response = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json")
        response.raise_for_status()
        story_ids = response.json()[:100]  # 获取前100条热门故事
        print(f"成功获取到 {len(story_ids)} 个故事ID")

        comments_prompt = """请分析以下评论，总结出主要的不同观点和讨论要点。
要求：
1. 识别并区分不同的观点立场
2. 保留重要的论据和例子
3. 注意捕捉评论之间的讨论关系
4. 如果有争议，请指出争议的焦点
5. 用中文输出，限制在500字以内
6. 分点列出不同观点，使用"•"作为列表符号

格式示例：
主要讨论点：[概括讨论的核心主题]

不同观点：
• [第一种观点]
• [第二种观点]
• [其他重要观点]

补充讨论：[其他值得注意的讨论点]"""

        stories = []
        for i, story_id in enumerate(story_ids, 1):
            try:
                print(f"正在处理第 {i}/100 个故事 (ID: {story_id})...")

                # 获取故事数据（无论是否缓存）
                story = fetch_hn_item(story_id)
                if not story:
                    continue

                # 获取当前评论数量
                current_comments_count = len(story.get("kids", []))

                # 检查缓存
                cached_data = cache.get(story_id)

                # 判断是否需要更新评论摘要
                need_update_comments = False

                if cached_data:
                    # 检查评论数量是否增加且原数量小于20
                    cached_comments_count = cached_data.get("comments_count", 0)
                    if (
                        cached_comments_count < 20
                        and current_comments_count > cached_comments_count
                    ):
                        print(
                            f"评论数量从 {cached_comments_count} 增加到 {current_comments_count}，将重新生成摘要"
                        )
                        need_update_comments = True
                    else:
                        print(f"使用缓存的故事数据 (ID: {story_id})")
                        # 确保缓存中取出的数据格式正确
                        story_data = cached_data["data"]
                        if isinstance(story_data.get("time"), str):
                            story_data["time"] = datetime.fromisoformat(
                                story_data["time"]
                            )
                        stories.append(story_data)
                        continue

                # 获取文章内容并生成摘要
                article_content = None
                article_summary = "无法获取文章内容"

                # 如果有缓存且只需更新评论，复用文章内容和摘要
                if cached_data and need_update_comments:
                    article_content = cached_data.get("article_content")
                    article_summary = cached_data["data"].get(
                        "article_summary", "无法获取文章内容"
                    )
                # 否则获取新的文章内容和摘要
                elif "url" in story:
                    print(f"获取文章内容: {story['url']}")
                    article_content = get_article_content(story["url"])
                    if article_content:
                        article_summary = get_summary(
                            article_content,
                            "请用中文简明扼要地总结这篇文章的主要内容，限制在200字以内。",
                        )

                # 获取评论文本 - 如果缓存需要更新或无缓存
                comments_summary = "暂无评论"
                if need_update_comments or not cached_data:
                    print("获取评论内容...")
                    comments_texts = []
                    if "kids" in story:
                        for comment_id in story["kids"][:15]:
                            comment = fetch_hn_item(comment_id)
                            if (
                                comment
                                and not comment.get("deleted")
                                and not comment.get("dead")
                            ):
                                clean_text = clean_html_text(comment.get("text", ""))
                                if clean_text:
                                    author = comment.get("by", "匿名")
                                    comments_texts.append(f"[{author}]: {clean_text}")

                    comments_text = "\n\n---\n\n".join(comments_texts)
                    if comments_text:
                        comments_summary = get_summary(comments_text, comments_prompt)
                else:
                    # 使用缓存的评论摘要
                    comments_summary = cached_data["data"].get(
                        "comments_summary", "暂无评论"
                    )

                story_data = {
                    "title": story.get("title", "无标题"),
                    "url": story.get(
                        "url", f"https://news.ycombinator.com/item?id={story_id}"
                    ),
                    "author": story.get("by", "匿名"),
                    "score": story.get("score", 0),
                    "time": datetime.fromtimestamp(story.get("time", 0)).isoformat(),
                    "comments_count": current_comments_count,
                    "article_summary": article_summary,
                    "comments_summary": comments_summary,
                    "comments_url": f"https://news.ycombinator.com/item?id={story_id}",
                }

                # 缓存新数据，包括文章内容和摘要
                cache.set(
                    story_id,
                    story_data,
                    article_content=article_content,
                    article_summary=article_summary,
                    comments_summary=comments_summary,
                    comments_count=current_comments_count,  # 保存当前评论数量
                )

                # 转换时间格式以适应模板
                story_data["time"] = datetime.fromisoformat(story_data["time"])
                stories.append(story_data)

                time.sleep(1)  # 避免请求过快

            except Exception as e:
                print(f"处理故事 {story_id} 时出错: {e}")
                continue

        return stories
    except Exception as e:
        print(f"获取热门故事时出错: {e}")
        return []


def generate_html(stories):
    """生成 HTML 页面"""
    try:
        with open("templates/index.html") as f:
            template = Template(f.read())

        # 计算页数，每页10条故事
        stories_per_page = 10
        total_pages = (
            len(stories) + stories_per_page - 1
        ) // stories_per_page  # 向上取整

        beijing_tz = pytz.timezone("Asia/Shanghai")
        current_time = datetime.now(beijing_tz).strftime("%Y-%m-%d %H:%M")

        # 创建输出目录
        os.makedirs("public", exist_ok=True)

        # 生成首页 (第1页)
        first_page_stories = stories[:stories_per_page]
        html_content = template.render(
            stories=first_page_stories,
            update_time=current_time,
            current_page=1,
            total_pages=total_pages,
            has_next=total_pages > 1,
            has_prev=False,
            is_index=True,  # 标记这是首页
        )
        with open("public/index.html", "w", encoding="utf-8") as f:
            f.write(html_content)

        # 生成其他页面
        for page in range(2, total_pages + 1):
            start_idx = (page - 1) * stories_per_page
            end_idx = min(page * stories_per_page, len(stories))
            page_stories = stories[start_idx:end_idx]

            html_content = template.render(
                stories=page_stories,
                update_time=current_time,
                current_page=page,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=True,
                is_index=False,  # 标记这不是首页
            )

            # 创建页面子目录
            os.makedirs("public/page", exist_ok=True)
            with open(f"public/page/{page}.html", "w", encoding="utf-8") as f:
                f.write(html_content)

        print(f"成功生成 {total_pages} 个页面")
    except Exception as e:
        print(f"生成HTML时出错: {e}")


def main():
    print("开始执行程序...")
    stories = fetch_top_stories()
    if stories:
        print("正在生成 HTML...")
        generate_html(stories)
        print("程序执行完成！")
    else:
        print("未获取到任何故事，请检查网络连接和API状态")


if __name__ == "__main__":
    main()

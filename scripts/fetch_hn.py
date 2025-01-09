import requests
import json
from datetime import datetime
from jinja2 import Template
from markupsafe import Markup
import os
from dateutil import parser
import pytz
import re
from openai import OpenAI
from dotenv import load_dotenv
import time
from bs4 import BeautifulSoup

# 加载环境变量
load_dotenv(override=True)

# OpenAI 配置
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_API_BASE = os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')

# 确保 API 基础 URL 格式正确
if OPENAI_API_BASE and not (OPENAI_API_BASE.startswith('http://') or OPENAI_API_BASE.startswith('https://')):
    OPENAI_API_BASE = 'https://' + OPENAI_API_BASE

# 初始化 OpenAI 客户端
try:
    client = OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE
    )
except Exception as e:
    print(f"初始化 OpenAI 客户端时出错: {e}")
    raise

def _process_html_content(response):
    """处理 HTML 响应内容"""
    content_type = response.headers.get('content-type', '').lower()
    if 'text/html' not in content_type:
        print(f"跳过非HTML内容: (Content-Type: {content_type})")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 移除不需要的元素
    for element in soup(['script', 'style', 'nav', 'header', 'footer', 'iframe', 'noscript']):
        element.decompose()
    
    # 尝试找到主要内容
    main_content = None
    content_candidates = soup.select('article, main, .article-content, .post-content, .entry-content')
    if content_candidates:
        main_content = content_candidates[0]
    
    if not main_content:
        main_content = soup.find('body')
    
    if not main_content:
        main_content = soup
    
    # 获取文本
    text = main_content.get_text(separator='\n', strip=True)
    
    # 清理文本
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = '\n'.join(lines)

    if len(text) < 50:
        print("跳过内容过短的文章")
        return None
    
    return text[:5000]

def get_article_content(url):
    """获取文章内容"""
    try:
        # 跳过已知的无法访问的网站
        blocked_domains = ['nytimes.com', 'wsj.com', 'bloomberg.com', 'ft.com']
        if any(domain in url.lower() for domain in blocked_domains):
            print(f"跳过付费墙网站: {url}")
            return None

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        response = requests.get(
            url, 
            headers=headers, 
            timeout=10,
            allow_redirects=True
        )
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

def get_summary(text, prompt="请用中文简明扼要地总结以下内容，限制在100字以内。", max_retries=3):
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
                    {"role": "user", "content": text}
                ],
                temperature=0.7,
                max_tokens=2000,
                timeout=30  # 设置超时时间
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
        response = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json")
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
        soup = BeautifulSoup(html_text, 'html.parser')
        # 获取纯文本
        text = soup.get_text()
        # 清理空白字符
        text = ' '.join(text.split())
        return text
    except Exception as e:
        print(f"清理HTML文本时出错: {e}")
        return html_text

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
                max_tokens=5
            )
            print("API 连接测试成功")
        except Exception as e:
            print(f"API 连接测试失败: {e}")
            raise
        
        print("开始获取热门故事...")
        response = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json")
        response.raise_for_status()
        story_ids = response.json()[:10]  # 只取前10个
        print(f"成功获取到 {len(story_ids)} 个故事ID")
        
        stories = []
        for i, story_id in enumerate(story_ids, 1):
            try:
                print(f"正在处理第 {i}/10 个故事 (ID: {story_id})...")
                story = fetch_hn_item(story_id)
                if not story:
                    continue
        
                # 获取文章内容并生成摘要
                article_content = None
                article_summary = "无法获取文章内容"
                if 'url' in story:
                    print(f"获取文章内容: {story['url']}")
                    article_content = get_article_content(story['url'])
                    if article_content:
                        article_summary = get_summary(
                            article_content, 
                            "请用中文简明扼要地总结这篇文章的主要内容，限制在200字以内。"
                        )
                
                # 获取评论文本
                print(f"获取评论内容...")
                comments_texts = []
                if 'kids' in story:
                    for comment_id in story['kids'][:10]:
                        comment = fetch_hn_item(comment_id)
                        if comment and not comment.get('deleted') and not comment.get('dead'):
                            clean_text = clean_html_text(comment.get('text', ''))
                            if clean_text:
                                comments_texts.append(clean_text)
                
                # 合并评论文本，添加分隔符
                comments_text = "\n---\n".join(comments_texts)
                comments_summary = "暂无评论"
                if comments_text:
                    comments_summary = get_summary(
                        comments_text, 
                        "请用中文总结这些评论的主要观点，限制在200字以内。"
                    )
                
                stories.append({
                    'title': story.get('title', '无标题'),
                    'url': story.get('url', f"https://news.ycombinator.com/item?id={story_id}"),
                    'author': story.get('by', '匿名'),
                    'score': story.get('score', 0),
                    'time': datetime.fromtimestamp(story.get('time', 0)),
                    'comments_count': len(story.get('kids', [])),
                    'article_summary': article_summary,
                    'comments_summary': comments_summary
                })
                time.sleep(1)  # 避免请求过快
            except Exception as e:
                print(f"处理故事 {story_id} 时出错: {e}")
                continue  # 跳过这个故事，继续处理下一个
        
        return stories
    except Exception as e:
        print(f"获取热门故事时出错: {e}")
        return []

def generate_html(stories):
    """生成 HTML 页面"""
    try:
        with open('templates/index.html') as f:
            template = Template(f.read())
        
        beijing_tz = pytz.timezone('Asia/Shanghai')
        current_time = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M')
        
        html_content = template.render(
            stories=stories,
            update_time=current_time
        )
        
        os.makedirs('public', exist_ok=True)
        with open('public/index.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
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

if __name__ == '__main__':
    main() 
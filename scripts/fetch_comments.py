import requests
import json
from datetime import datetime
from jinja2 import Template
import os
from dateutil import parser
import pytz

def format_time(time_str):
    # 解析时间字符串
    dt = parser.parse(time_str)
    # 转换为北京时间
    beijing_tz = pytz.timezone('Asia/Shanghai')
    dt_beijing = dt.astimezone(beijing_tz)
    return dt_beijing.strftime('%Y-%m-%d %H:%M')

def fetch_comments():
    url = 'https://notes.services.box.com/get_file_comments'
    
    params = {
        'fileId': '1718977038547',
        'offset': '0',
        'limit': '1000'
    }
    
    # 从环境变量获取 express_sid
    express_sid = os.environ.get('EXPRESS_SID')
    if not express_sid:
        raise ValueError("EXPRESS_SID environment variable is required")
    
    headers = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'cookie': f'express_sid={express_sid}'
    }
    
    response = requests.get(url, params=params, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch comments: {response.status_code} - {response.text}")
    
    data = response.json()
    # 为每条评论添加格式化的时间
    for entry in data['entries']:
        entry['formatted_time'] = format_time(entry['created_at'])
        # 添加原始LA时间
        la_time = parser.parse(entry['created_at']).strftime('%I:%M %p LA')
        entry['la_time'] = la_time
    
    return data

def generate_html(data):
    with open('templates/index.html') as f:
        template = Template(f.read())
    
    # 使用北京时间作为更新时间
    beijing_tz = pytz.timezone('Asia/Shanghai')
    current_time = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M')
    
    html_content = template.render(
        comments=data['entries'],
        total_count=data['total_count'],
        update_time=current_time
    )
    
    # 确保 public 目录存在
    os.makedirs('public', exist_ok=True)
    
    # 将文件写入 public 目录
    with open('public/index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

def main():
    data = fetch_comments()
    generate_html(data)

if __name__ == '__main__':
    main() 
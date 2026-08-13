# LiveNews 开发者热点

[![Tests](https://github.com/wayhome/livenews/actions/workflows/test.yml/badge.svg)](https://github.com/wayhome/livenews/actions/workflows/test.yml)

这是一个聚合 Hacker News、GitHub Trending、Product Hunt 和 arXiv 金融论文的开发者热点项目，使用 OpenAI 生成 Hacker News 摘要并翻译论文摘要，通过 GitHub Pages 展示。

## 功能

- 每天北京时间 07:00 和 19:00 自动刷新全部来源
- 获取 30 条 Hacker News 热门故事及评论摘要
- 获取 GitHub Trending 每日热门仓库
- 获取 Product Hunt 热门产品
- 获取最新 arXiv 金融与量化研究论文，并将摘要翻译为中文
- 使用独立 Tab 切换不同来源
- 收集每个故事的前 15 条评论
- 使用 OpenAI API 生成评论摘要
- 生成静态 HTML 页面展示
- 通过 GitHub Pages 发布

## 使用方法

1. Fork 本仓库
2. 在仓库的 Settings -> Secrets and variables -> Actions 中添加以下 secrets：
   - `OPENAI_API_KEY`: 必填，你的 OpenAI API 密钥
   - `OPENAI_API_BASE`: 可选，自定义 OpenAI API 地址（默认为官方API）
   - `OPENAI_MODEL`: 可选，使用的模型名称（默认为 gpt-3.5-turbo）
3. 启用 GitHub Pages（设置为 gh-pages 分支）
4. 确保 Actions 权限已开启
5. 访问 `https://<你的用户名>.github.io/<仓库名>` 查看结果

## 本地开发

```bash
# 安装 Python 并同步锁定依赖
uv python install
uv sync

# 创建 .env 文件并添加配置
cat << EOF > .env
OPENAI_API_KEY=你的OpenAI API密钥
OPENAI_API_BASE=https://api.openai.com/v1  # 可选，自定义API地址
OPENAI_MODEL=gpt-3.5-turbo  # 可选，自定义模型
EOF

# 运行脚本
uv run python scripts/fetch_news.py

# 运行测试
uv run pytest tests/
```

## 注意事项

- 数据每天在北京时间 07:00 和 19:00 更新
- 可以在 Actions 页面手动触发更新
- OpenAI API 调用会产生费用，请注意控制使用频率
- 建议在 `.env` 文件中设置配置，不要直接写在代码中
- 确保 API 密钥不会被提交到代码仓库

## 环境变量说明

| 变量名          | 必填 | 默认值                    | 说明            |
| --------------- | ---- | ------------------------- | --------------- |
| OPENAI_API_KEY  | 是   | -                         | OpenAI API 密钥 |
| OPENAI_API_BASE | 否   | https://api.openai.com/v1 | OpenAI API 地址 |
| OPENAI_MODEL    | 否   | gpt-3.5-turbo             | 使用的模型名称  |

## 技术栈

- Python
- HackerNews API
- OpenAI API
- GitHub Actions
- GitHub Pages
- Bootstrap 5

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可

MIT License

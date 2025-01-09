# HackerNews 热门故事摘要

这是一个自动抓取 HackerNews 热门故事及其评论的项目，使用 OpenAI 生成评论摘要，并通过 GitHub Pages 展示。

## 功能

- 每 6 小时自动抓取一次 HackerNews 热门内容
- 获取 Top 10 热门故事
- 收集每个故事的前 10 条评论
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
# 安装依赖
pip install -r requirements.txt

# 创建 .env 文件并添加配置
cat << EOF > .env
OPENAI_API_KEY=你的OpenAI API密钥
OPENAI_API_BASE=https://api.openai.com/v1  # 可选，自定义API地址
OPENAI_MODEL=gpt-3.5-turbo  # 可选，自定义模型
EOF

# 运行脚本
python scripts/fetch_hn.py
```

## 注意事项

- 数据每 6 小时更新一次
- 可以在 Actions 页面手动触发更新
- OpenAI API 调用会产生费用，请注意控制使用频率
- 建议在 `.env` 文件中设置配置，不要直接写在代码中
- 确保 API 密钥不会被提交到代码仓库

## 环境变量说明

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| OPENAI_API_KEY | 是 | - | OpenAI API 密钥 |
| OPENAI_API_BASE | 否 | https://api.openai.com/v1 | OpenAI API 地址 |
| OPENAI_MODEL | 否 | gpt-3.5-turbo | 使用的模型名称 |

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
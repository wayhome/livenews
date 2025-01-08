# Box Comments Viewer

这是一个自动抓取 Box 评论并展示的项目。

## 功能

- 每3小时自动抓取一次评论数据
- 生成静态HTML页面展示评论
- 通过 GitHub Pages 发布

## 使用方法

1. Fork 本仓库
2. 在仓库的 Settings -> Secrets and variables -> Actions 中添加名为 `EXPRESS_SID` 的 secret
   - 获取方法：从浏览器 Cookie 中复制 `express_sid` 的值
3. 启用 GitHub Pages（设置为 gh-pages 分支）
4. 确保 Actions 权限已开启
5. 访问 `https://<你的用户名>.github.io/<仓库名>` 查看结果

## 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export EXPRESS_SID='你的express_sid值'

# 运行脚本
python scripts/fetch_comments.py
```

## 注意事项

- 评论数据每6小时更新一次
- 可以在 Actions 页面手动触发更新
- Cookie 可能会过期，需要定期更新 `EXPRESS_SID` secret 
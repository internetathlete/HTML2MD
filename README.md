# HTML转Markdown工具

这是一个强大的HTML转Markdown工具，支持从本地HTML文件、文件夹或URL（包括CSDN、知乎专栏、微信公众号等）转换为Markdown格式。该工具特别优化了对CSDN、知乎专栏和微信公众号文章的处理，能够自动提取文章内容、元数据和图片。

## 主要功能

1. **多源支持**：
   - 本地HTML文件转换
   - 文件夹批量转换
   - URL直接转换（支持CSDN、知乎专栏、微信公众号等）

2. **智能内容提取**：
   - 自动识别文章类型（CSDN、知乎专栏、微信公众号等）
   - 提取文章主体内容
   - 自动处理图片下载和链接更新
   - 移除广告和无关内容

3. **元数据提取**：
   - 自动提取文章标题
   - 提取作者信息
   - 提取发布时间和编辑时间
   - 生成标准YAML格式的元数据

4. **图片处理**：
   - 自动下载文章中的图片
   - 支持多种图片格式（jpg、png、gif、svg、webp等）
   - 自动处理图片命名和存储
   - 支持base64编码的图片

5. **特殊网站支持**：
   - CSDN文章优化处理
   - 知乎专栏文章优化处理
   - 微信公众号文章优化处理
   - 自动处理登录弹窗
   - 自动展开"阅读全文"内容

## 安装说明

1. 确保已安装Python 3.6或更高版本
2. 安装Chrome浏览器
3. 安装依赖包：
   ```bash
   pip install -r requirements.txt
   ```

## 使用方法

### 命令行使用

1. 运行程序：
   ```bash
   python html2md.py
   ```

2. 根据提示输入：
   - HTML文件路径
   - 包含HTML文件的文件夹路径
   - 文章URL（支持CSDN、知乎专栏、微信公众号等）

3. 选择输出目录（可选）

### 作为模块使用

```python
from html2md import convert_url_to_md, convert_file_to_md, convert_directory_to_md

# 转换URL
result = convert_url_to_md("https://mp.weixin.qq.com/...")  # 微信公众号文章
result = convert_url_to_md("https://blog.csdn.net/...")     # CSDN文章
result = convert_url_to_md("https://zhuanlan.zhihu.com/...") # 知乎专栏

# 转换单个文件
result = convert_file_to_md("input.html")

# 转换整个目录
convert_directory_to_md("input_dir", "output_dir")
```

## 输出格式

转换后的Markdown文件包含：

1. YAML格式的元数据：
   ```yaml
   ---
   title: 文章标题
   updated: 2025-03-14T17:35:00
   created: 2025-03-14T17:35:00
   author: 作者名称
   ---
   ```

2. 文章内容：
   - 保留原始格式
   - 图片自动下载并更新链接
   - 移除广告和无关内容

## 特殊网站处理说明

### 微信公众号文章
- 自动提取文章标题（`activity-name`）
- 自动提取作者信息
- 自动下载文章中的图片
- 移除赞赏按钮、广告等无关内容
- 保持文章格式和排版

### CSDN文章
- 自动提取文章主体内容（`content_views`）
- 自动提取标题、作者、发布时间
- 移除广告、评论区等无关内容
- 自动展开"阅读全文"内容

### 知乎专栏
- 自动提取文章主体内容（`RichText`）
- 自动提取标题、作者、编辑时间
- 移除广告、评论区等无关内容
- 保持文章格式和排版

## 注意事项

1. 使用URL转换功能时，需要稳定的网络连接
2. 图片下载可能需要一定时间，请耐心等待
3. 对于需要登录的网站，可能无法获取完整内容
4. 建议定期更新依赖包以获取最新功能

## 依赖项

- beautifulsoup4>=4.12.2
- requests>=2.31.0
- html2text>=2024.2.26
- urllib3>=2.1.0
- selenium>=4.15.2

## 更新日志

### v1.0.0
- 初始版本发布
- 支持基本的HTML转Markdown功能
- 支持本地文件和URL转换

### v1.1.0
- 添加CSDN文章特殊处理
- 优化图片下载功能
- 添加元数据提取

### v1.2.0
- 添加知乎专栏支持
- 改进内容提取算法
- 优化错误处理

### v1.3.0
- 使用Selenium优化网页抓取
- 添加更多网站支持
- 改进图片处理机制

### v1.4.0
- 添加微信公众号文章支持
- 优化文章内容提取
- 改进图片处理机制

## 许可证

MIT License 
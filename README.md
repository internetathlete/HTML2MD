# HTML2MD

一个强大的HTML转Markdown工具，特别优化了对微信公众号文章的转换支持。

## 功能特点

- 支持从URL直接转换网页内容为Markdown
- 支持本地HTML文件转换
- 支持批量转换整个目录下的HTML文件
- 特别优化了微信公众号文章的转换：
  - 自动提取文章标题、作者、发布时间等元数据
  - 自动下载和本地化文章中的图片
  - 智能过滤不需要的内容（如广告、赞赏按钮等）
  - 保持图片的正确顺序
- 自动处理文件名和图片名称的冲突
- 支持多种输入格式和编码
- 生成干净、规范的Markdown文件

## 安装

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/HTML2MD.git
cd HTML2MD
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

运行程序：
```bash
python html2md.py
```

程序支持三种输入方式：
1. 直接输入微信公众号文章或其他网页的URL
2. 输入本地HTML文件的路径
3. 输入包含多个HTML文件的目录路径

### URL转换
直接粘贴文章URL，程序会：
- 自动下载网页内容
- 提取文章元数据（标题、作者、发布时间等）
- 下载文章中的图片到本地
- 生成对应的Markdown文件

### 本地文件转换
输入本地HTML文件路径，程序会：
- 解析HTML文件
- 提取文章元数据
- 处理文件中的图片
- 生成Markdown文件

### 批量转换
输入目录路径，程序会：
- 递归查找目录下所有HTML文件
- 批量转换为Markdown
- 保持原有的目录结构

## 输出说明

转换后的文件将保存在：
- 默认输出目录：程序所在目录下的 `output` 文件夹
- 可以在运行时指定自定义输出目录

每个转换后的Markdown文件包含：
- YAML格式的元数据（标题、作者、时间等）
- 文章正文内容
- 本地化的图片（保存在 `resources` 文件夹中）

## 注意事项

1. 确保有足够的磁盘空间存储图片
2. 部分网站可能需要登录或有访问限制
3. 批量转换大量文件时可能需要较长时间

## 依赖项

- beautifulsoup4
- requests
- html2text
- urllib3

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！ 
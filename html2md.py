import os
import re
import hashlib
import requests
import html2text
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote, urlparse
import shutil
from pathlib import Path

def create_resources_dir(output_dir):
    """创建 resources 目录"""
    resources_dir = os.path.join(output_dir, "resources")
    if not os.path.exists(resources_dir):
        os.makedirs(resources_dir)
    return resources_dir

def download_image(url, save_path):
    """下载图片并保存到指定路径"""
    try:
        # 如果是base64编码的图片
        if url.startswith('data:image'):
            import base64
            header, encoded = url.split(",", 1)
            image_data = base64.b64decode(encoded)
            with open(save_path, "wb") as f:
                f.write(image_data)
            return True
        
        # 如果是本地文件路径
        elif os.path.exists(url):
            shutil.copy2(url, save_path)
            return True
            
        # 如果是网络URL
        else:
            # 添加用户代理和引用来源
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://mp.weixin.qq.com/'
            }
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(response.content)
                return True
    except Exception:
        # 静默处理错误，不打印错误信息
        pass
    return False

def clean_filename(filename, index=None):
    """清理并生成有效的文件名"""
    try:
        filename = unquote(filename)
    except Exception:
        pass
    
    # 如果文件名过长或包含大量特殊字符，使用哈希值作为文件名
    if len(filename) > 100 or len(re.findall(r'[^a-zA-Z0-9\-_\.]', filename)) > len(filename) / 2:
        # 使用MD5哈希，取前16位作为文件名
        hash_object = hashlib.md5(filename.encode())
        filename = hash_object.hexdigest()[:16]
    
    # 移除URL查询参数和锚点
    filename = filename.split('?')[0].split('#')[0]
    
    # 获取文件名部分
    if '/' in filename or '\\' in filename:
        filename = os.path.basename(filename)
    
    # 移除不适合作为文件名的字符
    filename = re.sub(r'[\\/:*?"<>|]', '_', filename)
    
    # 确保文件名不为空
    if not filename:
        filename = 'image'
    
    # 添加文件扩展名
    if not re.search(r'\.(jpg|jpeg|png|gif|svg|webp|JPG|JPEG|PNG|GIF|SVG|WEBP)$', filename):
        filename += '.png'
    
    # 处理重复文件名
    if index is not None:
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{index}{ext}"
    
    return filename

def process_images(html_content, html_file_path, resources_dir):
    """处理HTML中的所有图片，下载并更新链接"""
    soup = BeautifulSoup(html_content, 'html.parser')
    base_path = os.path.dirname(os.path.abspath(html_file_path))
    used_filenames = {}
    image_mappings = {}
    position_counter = 0  # 添加位置计数器

    def process_image_url(url, alt_text="", img_id=""):
        """处理单个图片URL"""
        nonlocal position_counter
        position_counter += 1  # 增加位置计数
        
        if not url:
            return None
            
        # 处理base64编码的图片
        if url.startswith('data:image'):
            # 为base64图片生成唯一的文件名
            # 使用URL内容和位置信息生成哈希
            hash_input = f"{url[:100]}_{position_counter}_{alt_text}"
            hash_object = hashlib.md5(hash_input.encode())
            base_filename = f"img_{hash_object.hexdigest()[:8]}"
            
            # 尝试从header中获取图片格式
            try:
                format_match = re.search(r'data:image/([a-zA-Z]+);base64', url)
                if format_match:
                    img_format = format_match.group(1).lower()
                    if img_format in ['jpeg', 'jpg', 'png', 'gif', 'webp', 'svg']:
                        base_filename += f".{img_format}"
                    else:
                        base_filename += ".png"
                else:
                    base_filename += ".png"
            except:
                base_filename += ".png"
                
            filename = base_filename
            
        else:
            # 处理微信图片链接
            if 'mmbiz.qpic.cn' in url:
                # 使用图片ID（如果有）和位置信息生成文件名
                if img_id:
                    filename = f"wx_img_{img_id}_{position_counter}.png"
                else:
                    # 从URL中提取文件名部分
                    url_parts = url.split('/')
                    if len(url_parts) > 0:
                        wx_filename = url_parts[-1].split('?')[0]
                        filename = f"wx_img_{wx_filename}_{position_counter}.png"
                    else:
                        filename = f"wx_img_{position_counter}.png"
            else:
                # 处理其他URL
                if not url.startswith(('http://', 'https://')):
                    url = os.path.join(base_path, url)
                    
                # 生成文件名，包含位置信息
                original_filename = clean_filename(url)
                name, ext = os.path.splitext(original_filename)
                filename = f"{name}_{position_counter}{ext}"
            
        # 保存路径
        save_path = os.path.join(resources_dir, filename)
        
        # 如果这个URL和位置的组合之前处理过，直接返回映射的文件名
        mapping_key = f"{url}_{position_counter}"
        if mapping_key in image_mappings:
            return image_mappings[mapping_key]
            
        # 下载图片
        if download_image(url, save_path):
            image_mappings[mapping_key] = filename
        return filename
    
    # 处理<img>标签
    for img in soup.find_all('img'):
        src = img.get('src', '')
        data_src = img.get('data-src', '')  # 获取data-src属性
        alt = img.get('alt', '')
        img_id = img.get('data-imgfileid', '')  # 获取微信图片ID
        
        # 优先使用data-src
        if data_src:
            filename = process_image_url(data_src, alt, img_id)
            if filename:
                img['src'] = f'./resources/{filename}'
        elif src and not src.startswith('data:image/svg+xml'):  # 忽略SVG占位图
            filename = process_image_url(src, alt, img_id)
            if filename:
                img['src'] = f'./resources/{filename}'
                
    # 处理背景图片
    for elem in soup.find_all(lambda tag: tag.get('style') and 'background-image' in tag.get('style', '')):
        style = elem['style']
        urls = re.findall(r'url\([\'"]?(.*?)[\'"]?\)', style)
        for url in urls:
            filename = process_image_url(url)
            if filename:
                style = style.replace(url, f'./resources/{filename}')
                elem['style'] = style

    return str(soup)

def download_html_from_url(url):
    """从URL下载HTML内容"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://mp.weixin.qq.com/'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # 如果请求失败则抛出异常
        
        # 优先使用网页声明的编码
        if response.encoding.upper() in ['UTF-8', 'UTF8']:
            response.encoding = 'UTF-8'
        else:
            # 检查是否有charset声明
            content_type = response.headers.get('content-type', '').lower()
            if 'charset=' in content_type:
                charset = content_type.split('charset=')[-1].strip()
                response.encoding = charset
            else:
                # 尝试从内容中检测编码
                content = response.content
                soup = BeautifulSoup(content, 'html.parser')
                meta_charset = soup.find('meta', charset=True)
                if meta_charset:
                    response.encoding = meta_charset['charset']
                else:
                    meta_content_type = soup.find('meta', {'http-equiv': lambda x: x and x.lower() == 'content-type'})
                    if meta_content_type and 'charset=' in meta_content_type.get('content', '').lower():
                        charset = meta_content_type['content'].lower().split('charset=')[-1].strip()
                        response.encoding = charset
                    else:
                        # 如果都没有找到，使用apparent_encoding
                        response.encoding = response.apparent_encoding
        
        return response.text
    except Exception as e:
        print(f"下载页面失败: {str(e)}")
        return None

def convert_url_to_md(url, output_dir):
    """将URL转换为Markdown"""
    try:
        # 下载HTML内容
        html_content = download_html_from_url(url)
        if not html_content:
            return None
            
        # 创建临时HTML文件，使用UTF-8编码保存
        temp_html_file = os.path.join(output_dir, "temp.html")
        with open(temp_html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        # 检查是否是微信公众号文章并获取标题
        soup = BeautifulSoup(html_content, 'html.parser')
        is_wechat = bool(soup.find('div', class_=lambda x: x and 'rich_media_area_primary' in x))
        title = ''
        if is_wechat:
            title_elem = soup.find('h1', id='activity-name')
            if title_elem:
                title = title_elem.get_text().strip()
                # 清理标题中的非法字符
                title = re.sub(r'[\\/:*?"<>|]', '_', title)
                # 如果标题太长，截取前50个字符
                if len(title) > 50:
                    title = title[:50]
        
        # 转换为Markdown
        result = convert_html_to_md(temp_html_file, output_dir)
        
        # 如果转换成功，根据情况重命名文件
        if result:
            base_dir = os.path.dirname(result)
            if is_wechat and title:
                # 使用文章标题命名
                new_filename = f"{title}.md"
            else:
                # 使用当前时间命名
                from datetime import datetime
                current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_filename = f"{current_time}.md"
            
            # 构建新的文件路径
            new_file_path = os.path.join(base_dir, new_filename)
            
            # 如果目标文件已存在，添加序号
            counter = 1
            while os.path.exists(new_file_path):
                if is_wechat and title:
                    new_filename = f"{title}_{counter}.md"
                else:
                    new_filename = f"{current_time}_{counter}.md"
                new_file_path = os.path.join(base_dir, new_filename)
                counter += 1
            
            # 重命名文件
            try:
                os.rename(result, new_file_path)
                result = new_file_path
            except Exception as e:
                print(f"重命名文件失败: {str(e)}")
        
        # 删除临时HTML文件
        try:
            os.remove(temp_html_file)
        except:
            pass
            
        return result
    except Exception as e:
        print(f"转换URL失败: {str(e)}")
        return None

def convert_html_to_md(html_file, output_dir):
    """将HTML文件转换为Markdown"""
    # 创建resources目录
    resources_dir = create_resources_dir(output_dir)
    
    # 读取HTML文件
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 提取元数据
    metadata = {
        'title': '',
        'author': '',
        'created': '',
        'updated': ''
    }
    
    # 提取标题
    title_elem = soup.find('h1', id='activity-name')
    if title_elem:
        metadata['title'] = title_elem.get_text().strip()
    
    # 提取时间
    time_patterns = [
        (r'(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2})', '%Y-%m-%d %H:%M'),  # 2024年3月19日 17:20
        (r'(\d{4})-(\d{2})-(\d{2})\s*(\d{2}):(\d{2})', '%Y-%m-%d %H:%M'),  # 2024-03-19 17:20
        (r'(\d{4})年(\d{1,2})月(\d{1,2})日', '%Y-%m-%d'),  # 2024年3月19日
        (r'(\d{4})-(\d{2})-(\d{2})', '%Y-%m-%d')  # 2024-03-19
    ]
    
    def format_time(time_str):
        """格式化时间字符串"""
        for pattern, format_str in time_patterns:
            match = re.search(pattern, time_str)
            if match:
                if '年' in pattern:
                    # 处理中文日期格式
                    groups = match.groups()
                    if len(groups) == 5:  # 带时间
                        year, month, day, hour, minute = groups
                        formatted = f"{year}-{month.zfill(2)}-{day.zfill(2)} {hour.zfill(2)}:{minute}"
                    else:  # 只有日期
                        year, month, day = groups
                        formatted = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    return formatted
                else:
                    # 标准格式直接返回匹配部分
                    return match.group(0)
        return None
    
    # 首先尝试从publish_time获取时间
    time_elem = soup.find('em', id='publish_time')
    if time_elem:
        time_str = time_elem.get_text().strip()
        formatted_time = format_time(time_str)
        if formatted_time:
            metadata['created'] = formatted_time
            metadata['updated'] = formatted_time
    
    # 如果没有找到，尝试其他可能的时间元素
    if not metadata['created']:
        for elem in soup.find_all(['em', 'span'], class_='rich_media_meta rich_media_meta_text'):
            time_str = elem.get_text().strip()
            formatted_time = format_time(time_str)
            if formatted_time:
                metadata['created'] = formatted_time
                metadata['updated'] = formatted_time
                break
    
    # 提取作者
    author_elem = soup.find('span', class_='rich_media_meta rich_media_meta_text')
    if author_elem:
        author_text = author_elem.get_text().strip()
        # 如果文本包含时间格式，则不是作者信息
        if not re.match(r'\d{4}', author_text):
            metadata['author'] = author_text
    
    # 检测是否是微信公众号页面
    is_wechat_article = False
    if soup.find('div', class_=lambda x: x and 'rich_media_area_primary' in x):
        is_wechat_article = True
        print("检测到微信公众号文章，将过滤部分内容...")
        
        # 移除微信公众号相关的元素
        elements_to_remove = [
            'div.wx_profile.weui-flex',  # 公众号资料卡片
            'div.wx_profile_card_inner',  # 公众号资料卡片内层
            'div.reward_area',  # 赞赏区域
            'div.reward_qrcode_area',  # 赞赏二维码
            'div.reward_area_wrp',  # 赞赏包装区
            'div.weui-loadmore',  # 加载更多
            'div.weui-dialog',  # 对话框
            'div.weui-mask',  # 遮罩层
            'div#js_pc_qr_code',  # PC端二维码
            'div.qr_code_pc',  # PC端二维码
            'div.qr_code_pc_outer',  # PC端二维码外层
            'div#js_profile_qrcode',  # 个人资料二维码
            'div.profile_container',  # 个人资料容器
            'div.author_profile',  # 作者资料
            'div.author_profile_inner',  # 作者资料内层
            'div.author_profile_toast',  # 作者资料提示
            'div.author_profile-pay_area',  # 作者赞赏区域
            'div.discuss_container',  # 评论区容器
            'div.rich_media_tool',  # 底部工具栏
            'div.rich_media_extra',  # 额外信息
            'div.rich_media_tips',  # 提示信息
            'div.weui-desktop-popover',  # 桌面端弹窗
            'div.weui-desktop-mask',  # 桌面端遮罩
            'div#js_tags',  # 标签区域
            'div#js_tags_preview_toast',  # 标签预览提示
            'div.article_modify_area',  # 文章修改区域
            'div.like_comment_wrp',  # 点赞评论区域
            'div.like_comment_primary_wrp',  # 主要点赞评论区域
            'div.like_comment_extra_wrp',  # 额外点赞评论区域
            'div#content_bottom_interaction',  # 底部互动区域
            'div.wx_bottom_modal_group',  # 底部模态框组
            'span.weui-a11y_ref',  # 无障碍引用
            'span#js_a11y_comma'  # 无障碍逗号
        ]
        
        # 移除所有匹配的元素
        for selector in elements_to_remove:
            for element in soup.select(selector):
                element.decompose()
                
        # 更新HTML内容
        html_content = str(soup)
    
    # 处理图片
    html_content = process_images(html_content, html_file, resources_dir)
    
    # 使用html2text进行转换
    h = html2text.HTML2Text()
    h.body_width = 0  # 不限制行宽
    h.ignore_images = False
    h.ignore_emphasis = False
    h.ignore_links = False
    h.ignore_tables = False
    
    # 转换为Markdown
    markdown_content = h.handle(html_content)
    
    # 如果是微信公众号文章，进行额外的清理
    if is_wechat_article:
        # 移除多余的空行
        markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)
        # 移除特定的文本块
        markdown_content = re.sub(r'微信扫一扫关注该公众号.*?$', '', markdown_content, flags=re.MULTILINE | re.DOTALL)
        markdown_content = re.sub(r'长按识别前往小程序.*?$', '', markdown_content, flags=re.MULTILINE | re.DOTALL)
        markdown_content = re.sub(r'点击关注我们.*?$', '', markdown_content, flags=re.MULTILINE | re.DOTALL)
        markdown_content = re.sub(r'长按图片保存并使用微信扫一扫.*?$', '', markdown_content, flags=re.MULTILINE | re.DOTALL)
        # 移除底部互动相关文本
        markdown_content = re.sub(r'阅读.*?$', '', markdown_content, flags=re.MULTILINE | re.DOTALL)
        markdown_content = re.sub(r'点赞.*?$', '', markdown_content, flags=re.MULTILINE | re.DOTALL)
        markdown_content = re.sub(r'在看.*?$', '', markdown_content, flags=re.MULTILINE | re.DOTALL)
    
    # 生成YAML格式的元数据
    yaml_metadata = "---\n"
    for key, value in metadata.items():
        if value:  # 只添加非空的元数据
            yaml_metadata += f"{key}: {value}\n"
    yaml_metadata += "---\n\n"
    
    # 将元数据添加到Markdown内容前
    markdown_content = yaml_metadata + markdown_content
    
    # 生成输出文件路径
    base_name = os.path.splitext(os.path.basename(html_file))[0]
    md_file = os.path.join(output_dir, f"{base_name}.md")
    
    # 保存Markdown文件时确保使用UTF-8编码
    with open(md_file, 'w', encoding='utf-8', errors='ignore') as f:
        f.write(markdown_content)
        
    return md_file

def process_directory(input_dir, output_dir):
    """处理目录中的所有HTML文件"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith(('.html', '.htm')):
                html_file = os.path.join(root, file)
                relative_path = os.path.relpath(root, input_dir)
                current_output_dir = os.path.join(output_dir, relative_path)
                
                if not os.path.exists(current_output_dir):
                    os.makedirs(current_output_dir)
                    
                try:
                    result = convert_html_to_md(html_file, current_output_dir)
                    print(f"已转换: {html_file} -> {result}")
                except Exception as e:
                    print(f"转换失败 {html_file}: {str(e)}")

def main():
    """主函数，处理用户输入和程序流程"""
    print("欢迎使用HTML转Markdown工具")
    print("=" * 50)
    print("\n支持以下输入格式：")
    print("1. HTML文件路径")
    print("2. 包含HTML文件的文件夹路径")
    print("3. 文章URL（支持微信公众号文章）")
    
    while True:
        input_path = input("\n请输入要转换的HTML文件路径、文件夹路径或URL（输入q退出）: ").strip()
        
        if input_path.lower() == 'q':
            print("程序已退出")
            break
            
        if not input_path:
            print("输入不能为空，请重新输入")
            continue
            
        # 移除路径中的引号
        input_path = input_path.strip('"\'')
        
        # 设置默认输出目录
        default_output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
        
        # 获取用户指定的输出目录
        output_dir = input(f"\n请输入输出目录路径（直接回车使用默认路径 {default_output_dir}）: ").strip()
        if not output_dir:
            output_dir = default_output_dir
        else:
            # 移除输出目录中的引号
            output_dir = output_dir.strip('"\'')
            
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"已创建输出目录: {output_dir}")
        
        try:
            # 判断输入是否为URL
            if input_path.startswith(('http://', 'https://')):
                print(f"\n开始从URL转换: {input_path}")
                result = convert_url_to_md(input_path, output_dir)
                if result:
                    print(f"转换成功！输出文件: {result}")
                else:
                    print("转换失败")
            # 处理本地文件或目录
            elif os.path.exists(input_path):
                if os.path.isfile(input_path):
                    if input_path.endswith('.html') or input_path.endswith('.htm'):
                        print(f"\n开始转换文件: {input_path}")
                        result = convert_html_to_md(input_path, output_dir)
                        if result:
                            print(f"转换成功！输出文件: {result}")
                        else:
                            print("转换失败")
                    else:
                        print("错误：输入文件必须是HTML文件（.html或.htm）")
                elif os.path.isdir(input_path):
                    print(f"\n开始处理目录: {input_path}")
                    process_directory(input_path, output_dir)
                    print(f"目录处理完成！输出目录: {output_dir}")
            else:
                print(f"错误：'{input_path}' 不是有效的文件、目录或URL")
        except Exception as e:
            print(f"发生错误: {str(e)}")
            
        print("\n" + "=" * 50)
        
        # 询问是否继续
        choice = input("\n是否继续转换其他文件？(y/n): ").strip().lower()
        if choice != 'y':
            print("程序已退出")
            break

if __name__ == "__main__":
    main()
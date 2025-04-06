import os
import re
import hashlib
import requests
import html2text
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote, urlparse
import shutil
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import logging

def create_resources_dir(output_dir):
    """创建 resources 目录"""
    resources_dir = os.path.join(output_dir, "resources")
    if not os.path.exists(resources_dir):
        os.makedirs(resources_dir)
    return resources_dir

def download_image(url, save_path, driver=None):
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
            # 对于CSDN的图片，使用selenium的cookies
            if 'csdn.net' in url and driver:
                cookies = driver.get_cookies()
                session = requests.Session()
                for cookie in cookies:
                    session.cookies.set(cookie['name'], cookie['value'])
                
                headers = {
                    'User-Agent': driver.execute_script('return navigator.userAgent'),
                    'Referer': 'https://blog.csdn.net/'
                }
                response = session.get(url, headers=headers, timeout=30)
            # 对于知乎的图片，使用特定的请求头
            elif 'zhihu.com' in url or 'zhimg.com' in url:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://www.zhihu.com/',
                    'accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                    'accept-encoding': 'gzip, deflate, br',
                    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                    'sec-fetch-dest': 'image',
                    'sec-fetch-mode': 'no-cors',
                    'sec-fetch-site': 'cross-site'
                }
                # 如果有driver，添加cookies
                if driver:
                    cookies = driver.get_cookies()
                    session = requests.Session()
                    for cookie in cookies:
                        session.cookies.set(cookie['name'], cookie['value'])
                    response = session.get(url, headers=headers, timeout=30)
                else:
                    response = requests.get(url, headers=headers, timeout=30)
            else:
                # 添加用户代理和引用来源
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://blog.csdn.net/'
                }
                response = requests.get(url, headers=headers, timeout=30)
                
            if response.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(response.content)
                return True
    except Exception as e:
        print(f"下载图片失败 {url}: {str(e)}")
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

def process_images(html_content, html_file_path, resources_dir, driver=None):
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
            # 处理图片链接
            if not url.startswith(('http://', 'https://')):
                if url.startswith('//'):
                    url = 'https:' + url
                else:
                    url = urljoin('https://blog.csdn.net/', url)
                    
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
        if download_image(url, save_path, driver):
            image_mappings[mapping_key] = filename
            print(f"成功下载图片: {url}")
        else:
            print(f"下载图片失败: {url}")
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

def get_chrome_driver():
    """配置并返回Chrome WebDriver"""
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')  # 新版本的无界面模式
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--disable-software-rasterizer')  # 禁用软件光栅器
    chrome_options.add_argument('--disable-gpu-sandbox')  # 禁用GPU沙箱
    chrome_options.add_argument('--disable-gpu-driver-bug-workarounds')  # 禁用GPU驱动程序错误解决方法
    chrome_options.add_argument('--disable-webgl')  # 禁用WebGL
    chrome_options.add_argument('--disable-webgl2')  # 禁用WebGL 2.0
    chrome_options.add_argument('--disable-logging')  # 禁用日志记录
    chrome_options.add_argument('--disable-in-process-stack-traces')  # 禁用进程内堆栈跟踪
    chrome_options.add_argument('--disable-dev-shm-usage')  # 禁用/dev/shm使用
    chrome_options.add_argument('--log-level=3')  # 仅显示致命错误
    chrome_options.add_argument('--silent')  # 静默模式
    chrome_options.add_argument('--disable-extensions')  # 禁用扩展
    chrome_options.add_argument('--disable-notifications')  # 禁用通知
    chrome_options.add_argument('--disable-popup-blocking')  # 禁用弹出窗口阻止
    chrome_options.add_argument('--ignore-certificate-errors')  # 忽略证书错误
    chrome_options.add_argument('--disable-plugins')  # 禁用插件
    chrome_options.add_argument('--disable-gpu-watchdog')  # 禁用GPU监视程序
    chrome_options.add_argument('--disable-gl-drawing-for-tests')  # 禁用GL绘图
    chrome_options.add_argument('--disable-software-rasterizer')  # 禁用软件光栅器
    chrome_options.add_argument('--force-color-profile=srgb')  # 强制使用sRGB颜色配置文件
    chrome_options.add_argument('--disable-accelerated-2d-canvas')  # 禁用加速2D画布
    chrome_options.add_argument('--disable-accelerated-jpeg-decoding')  # 禁用加速JPEG解码
    chrome_options.add_argument('--disable-accelerated-mjpeg-decode')  # 禁用加速MJPEG解码
    chrome_options.add_argument('--disable-accelerated-video-decode')  # 禁用加速视频解码
    chrome_options.add_argument('--disable-d3d11')  # 禁用D3D11
    chrome_options.add_argument('--disable-gpu-compositing')  # 禁用GPU合成
    
    # 添加实验性选项
    chrome_options.add_experimental_option('excludeSwitches', [
        'enable-automation',  # 禁用自动化提示
        'enable-logging',  # 禁用日志记录
        'enable-blink-features',  # 禁用blink特性
    ])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # 添加性能日志选项
    chrome_options.set_capability(
        'goog:loggingPrefs', {
            'browser': 'OFF',
            'driver': 'OFF',
            'performance': 'OFF'
        }
    )
    
    # 添加自定义 User-Agent
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        # 禁用所有日志输出
        import logging
        selenium_logger = logging.getLogger('selenium')
        selenium_logger.setLevel(logging.CRITICAL)  # 只显示严重错误
        
        # 禁用 urllib3 的警告
        import urllib3
        urllib3.disable_warnings()
        
        # 禁用所有 selenium 相关的日志
        for logger_name in ['selenium', 'selenium.webdriver.remote.remote_connection', 'selenium.webdriver.common.selenium_manager']:
            logging.getLogger(logger_name).setLevel(logging.CRITICAL)
            
        # 禁用 Chrome 日志输出
        import os
        os.environ['WDM_LOG_LEVEL'] = '0'
        os.environ['WDM_PRINT_FIRST_LINE'] = 'False'
        
        # 创建 WebDriver
        driver = webdriver.Chrome(options=chrome_options)
        
        # 设置页面加载超时时间
        driver.set_page_load_timeout(30)
        # 设置脚本执行超时时间
        driver.set_script_timeout(30)
        
        return driver
    except Exception as e:
        print(f"创建Chrome WebDriver失败: {str(e)}")
        return None

def download_html_from_url(url):
    """使用Selenium从URL下载HTML内容"""
    try:
        print("正在启动浏览器...")
        driver = get_chrome_driver()
        if not driver:
            return None
            
        try:
            print(f"正在访问页面: {url}")
            driver.get(url)
            
            # 等待页面加载完成
            print("等待页面加载...")
            time.sleep(3)  # 基础等待时间
            
            # 对于CSDN文章，等待特定元素并处理
            if 'csdn.net' in url:
                try:
                    # 等待文章主体内容加载
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "content_views"))
                    )
                    
                    # 展开阅读全文
                    try:
                        read_more = driver.find_element(By.CLASS_NAME, "hide-article-box")
                        if read_more:
                            driver.execute_script("arguments[0].remove()", read_more)
                    except:
                        pass
                        
                    # 尝试移除登录弹窗
                    try:
                        driver.execute_script("""
                            var elements = document.getElementsByClassName('passport-login-container');
                            for (var i = 0; i < elements.length; i++) {
                                elements[i].remove();
                            }
                        """)
                    except:
                        pass
                        
                except Exception as e:
                    print(f"等待CSDN元素时出错: {str(e)}")
                    
            # 获取页面内容
            print("获取页面内容...")
            html_content = driver.page_source
            
            return html_content
            
        finally:
            print("关闭浏览器...")
            driver.quit()
            
    except Exception as e:
        print(f"下载页面失败: {str(e)}")
        return None

def process_html_content(html_content):
    """处理HTML内容，根据不同网站进行特殊处理"""
    soup = BeautifulSoup(html_content, 'html.parser')
    metadata = {
        'title': '',
        'author': '',
        'created': '',
        'updated': ''
    }
    
    # 检测是否是知乎专栏文章
    zhihu_header = soup.find('div', class_="ColumnPageHeader-content")
    if zhihu_header:
        print("检测到知乎专栏文章，提取文章主体内容...")
        
        # 提取标题
        title_elem = soup.find('h1', class_="Post-Title")
        if title_elem:
            metadata['title'] = title_elem.get_text().strip()
            print(f"文章标题: {metadata['title']}")
            
        # 提取作者
        author_elem = soup.find('a', class_="UserLink-link")
        if author_elem:
            metadata['author'] = author_elem.get_text().strip()
            print(f"作者: {metadata['author']}")
            
        # 提取发布时间
        time_elem = soup.find('div', class_="ContentItem-time")
        if time_elem:
            time_text = time_elem.get_text().strip()
            # 提取时间字符串
            time_match = re.search(r'发布于 ([\d-]+ [\d:]+)', time_text)
            if time_match:
                time_str = time_match.group(1)
                try:
                    from datetime import datetime
                    dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
                    formatted_time = dt.strftime('%Y-%m-%dT%H:%M:%S')
                    metadata['created'] = formatted_time
                    metadata['updated'] = formatted_time
                    print(f"发布时间: {time_str}")
                except Exception:
                    metadata['created'] = time_str
                    metadata['updated'] = time_str
                    
        # 查找文章主体内容
        article_content = soup.find('div', class_="RichText ztext Post-RichText css-ob6uua")
        if article_content:
            print("找到文章主体内容，开始处理...")
            
            # 处理图片链接
            for img in article_content.find_all('img'):
                # 优先使用原始图片链接
                src = img.get('data-original') or img.get('src', '')
                if src:
                    # 如果是相对路径，转换为绝对路径
                    if not src.startswith(('http://', 'https://')):
                        if src.startswith('//'):
                            src = 'https:' + src
                        else:
                            src = 'https://www.zhihu.com' + (src if src.startswith('/') else '/' + src)
                    img['src'] = src
                    
            # 创建新的HTML文档
            new_soup = BeautifulSoup('<html><body></body></html>', 'html.parser')
            new_soup.body.append(article_content)
            print("已提取文章主体内容，处理完成")
            
            return str(new_soup), metadata
        else:
            print("未找到文章主体内容，将处理整个页面")
            
    # 检测是否是CSDN文章
    csdn_logo = soup.find('img', title="CSDN首页")
    if csdn_logo:
        print("检测到CSDN文章，提取文章主体内容...")
        
        # 提取标题
        title_elem = soup.find('h1', class_="title-article")
        if title_elem:
            metadata['title'] = title_elem.get_text().strip()
            print(f"文章标题: {metadata['title']}")
            
        # 提取发布时间
        time_elem = soup.find('span', class_="time")
        if time_elem:
            time_str = time_elem.get('data-time', '')
            if time_str:
                # 转换时间格式为ISO 8601
                try:
                    from datetime import datetime
                    dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                    formatted_time = dt.strftime('%Y-%m-%dT%H:%M:%S')
                    metadata['created'] = formatted_time
                    metadata['updated'] = formatted_time
                    print(f"发布时间: {time_str}")
                except Exception:
                    metadata['created'] = time_str
                    metadata['updated'] = time_str
                
        # 提取作者
        author_elem = soup.find('a', class_="follow-nickName")
        if author_elem:
            metadata['author'] = author_elem.get_text().strip()
            print(f"作者: {metadata['author']}")
            
        # 查找文章主体内容
        article_content = soup.find('div', id="content_views")
        if not article_content:
            article_content = soup.find('div', class_="blog-content-box")
            
        if article_content:
            print("找到文章主体内容，开始处理...")
            
            # 需要移除的元素选择器列表
            elements_to_remove = [
                {'class': 'article-info-box'},  # 文章信息框
                {'id': 'blogColumnPayAdvert'},  # 付费专栏广告
                {'class': 'recommend-box'},  # 推荐阅读
                {'class': 'article-copyright'},  # 版权信息
                {'class': 'article-footer-copyright'},  # 底部版权
                {'class': 'comment-box'},  # 评论区
                {'class': 'template-box'},  # 模板区域
                {'class': 'hide-article-box'},  # 隐藏文章提示
                {'id': 'marketingBox'},  # 营销广告框
                {'class': 'csdn-side-toolbar'},  # 侧边工具栏
                {'id': 'toolBarBox'},  # 工具栏
                {'class': 'blog-tags-box'},  # 标签区域
                {'class': 'article-info-box'},  # 文章信息框
                {'class': 'article-bar-top'},  # 顶部工具栏
                {'class': 'blog-tags-box'},  # 博客标签
                {'class': 'operating'},  # 操作按钮
                {'id': 'csdn-shop-window-top'},  # 顶部商店窗口
                {'id': 'csdn-shop-window'},  # 商店窗口
                {'class': 'more-toolbox'},  # 更多工具箱
                {'class': 'person-messagebox'},  # 个人消息框
            ]
            
            # 移除所有指定的元素
            for selector in elements_to_remove:
                elements = article_content.find_all(**selector)
                for element in elements:
                    element.decompose()
                    
            # 处理图片链接
            for img in article_content.find_all('img'):
                # 优先使用data-src属性
                src = img.get('data-src') or img.get('src', '')
                if src:
                    # 如果是相对路径，转换为绝对路径
                    if not src.startswith(('http://', 'https://')):
                        if src.startswith('//'):
                            src = 'https:' + src
                        else:
                            src = 'https://blog.csdn.net' + (src if src.startswith('/') else '/' + src)
                    img['src'] = src
                    
            # 创建新的HTML文档
            new_soup = BeautifulSoup('<html><body></body></html>', 'html.parser')
            new_soup.body.append(article_content)
            print("已移除无关内容，处理完成")
            
            return str(new_soup), metadata
        else:
            print("未找到文章主体内容，将处理整个页面")
            
    return html_content, {}

def convert_url_to_md(url, output_dir=None):
    """将URL转换为Markdown"""
    driver = None
    try:
        # 如果未提供输出目录，使用当前目录
        if output_dir is None:
            output_dir = os.getcwd()
            
        # 启动浏览器
        print("正在启动浏览器...")
        driver = get_chrome_driver()
        if not driver:
            return None
            
        print(f"正在访问页面: {url}")
        driver.get(url)
        
        # 等待页面加载完成
        print("等待页面加载...")
        time.sleep(3)  # 基础等待时间
        
        # 对于CSDN文章，等待特定元素并处理
        if 'csdn.net' in url:
            try:
                # 等待文章主体内容加载
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "content_views"))
                )
                
                # 展开阅读全文
                try:
                    read_more = driver.find_element(By.CLASS_NAME, "hide-article-box")
                    if read_more:
                        driver.execute_script("arguments[0].remove()", read_more)
                except:
                    pass
                    
                # 尝试移除登录弹窗
                try:
                    driver.execute_script("""
                        var elements = document.getElementsByClassName('passport-login-container');
                        for (var i = 0; i < elements.length; i++) {
                            elements[i].remove();
                        }
                    """)
                except:
                    pass
                    
            except Exception as e:
                print(f"等待CSDN元素时出错: {str(e)}")
                
        # 获取页面内容
        print("获取页面内容...")
        html_content = driver.page_source
            
        # 处理HTML内容
        html_content, metadata = process_html_content(html_content)
            
        # 创建临时HTML文件，使用UTF-8编码保存
        temp_html_file = os.path.join(output_dir, "temp.html")
        with open(temp_html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        # 检查是否是微信公众号文章并获取标题
        soup = BeautifulSoup(html_content, 'html.parser')
        is_wechat = bool(soup.find('div', class_=lambda x: x and 'rich_media_area_primary' in x))
        title = ''
        
        # 根据不同类型的文章决定文件名
        if is_wechat:
            title_elem = soup.find('h1', id='activity-name')
            if title_elem:
                title = title_elem.get_text().strip()
                # 清理标题中的非法字符
                title = re.sub(r'[\\/:*?"<>|]', '_', title)
                # 如果标题太长，截取前50个字符
                if len(title) > 50:
                    title = title[:50]
        elif metadata.get('title'):  # 使用CSDN文章标题
            title = metadata['title']
            # 清理标题中的非法字符
            title = re.sub(r'[\\/:*?"<>|]', '_', title)
            # 如果标题太长，截取前50个字符
            if len(title) > 50:
                title = title[:50]
        
        # 转换为Markdown，传入driver实例和元数据
        result = convert_html_to_md(temp_html_file, output_dir, driver)
        
        # 如果转换成功，根据情况重命名文件
        if result:
            base_dir = os.path.dirname(result)
            if title:
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
                name, ext = os.path.splitext(new_filename)
                new_filename = f"{name}_{counter}{ext}"
                new_file_path = os.path.join(base_dir, new_filename)
                counter += 1
            
            # 如果有元数据，添加到文件内容中
            if metadata:
                with open(result, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 生成YAML格式的元数据
                yaml_metadata = "---\n"
                # 按照指定顺序添加元数据
                for key in ['title', 'updated', 'created', 'author']:
                    if metadata.get(key):
                        yaml_metadata += f"{key}: {metadata[key]}\n"
                yaml_metadata += "---\n\n"
                
                # 将元数据添加到文件开头
                with open(result, 'w', encoding='utf-8') as f:
                    f.write(yaml_metadata + content)
            
            # 重命名文件
            try:
                os.rename(result, new_file_path)
                result = new_file_path
                print(f"已重命名文件为: {new_file_path}")
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
    finally:
        # 在函数结束时关闭浏览器
        if driver:
            try:
                driver.quit()
                print("已关闭浏览器")
            except:
                pass

def convert_html_to_md(html_file, output_dir, driver=None):
    """将HTML文件转换为Markdown"""
    try:
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # 创建resources目录
        resources_dir = create_resources_dir(output_dir)
        
        # 读取HTML文件
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        # 处理HTML内容
        html_content, metadata = process_html_content(html_content)
            
        # 处理图片，传入driver实例
        html_content = process_images(html_content, html_file, resources_dir, driver)
        
        # 使用html2text转换为Markdown
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.ignore_emphasis = False
        h.ignore_tables = False
        h.body_width = 0
        markdown_content = h.handle(html_content)
        
        # 生成YAML格式的元数据
        if metadata:
            yaml_metadata = "---\n"
            # 按照指定顺序添加元数据
            for key in ['title', 'updated', 'created', 'author']:
                if metadata.get(key):
                    yaml_metadata += f"{key}: {metadata[key]}\n"
            yaml_metadata += "---\n\n"
            markdown_content = yaml_metadata + markdown_content
        
        # 生成输出文件名
        input_filename = os.path.basename(html_file)
        output_filename = os.path.splitext(input_filename)[0] + '.md'
        output_file = os.path.join(output_dir, output_filename)
        
        # 保存Markdown文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
            
        print(f"已保存Markdown文件: {output_file}")
        return output_file
        
    except Exception as e:
        print(f"转换失败: {str(e)}")
        return None

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

def convert_file_to_md(html_file, output_dir=None):
    """将单个HTML文件转换为Markdown"""
    if output_dir is None:
        # 如果未指定输出目录，使用输入文件的目录
        output_dir = os.path.dirname(os.path.abspath(html_file))
    return convert_html_to_md(html_file, output_dir)

def convert_directory_to_md(input_dir, output_dir=None):
    """将目录中的所有HTML文件转换为Markdown"""
    if output_dir is None:
        # 如果未指定输出目录，使用输入目录
        output_dir = input_dir
    return process_directory(input_dir, output_dir)

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
else:
    # 导出函数供GUI使用
    __all__ = ['convert_url_to_md', 'convert_file_to_md', 'convert_directory_to_md']
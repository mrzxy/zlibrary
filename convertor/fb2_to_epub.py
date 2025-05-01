from ebooklib import epub
from lxml import etree
import os

def fb2_to_epub(fb2_file_path, output_path=None):
    """
    将 FB2 文件转换为 EPUB 格式
    :param fb2_file_path: FB2 文件路径
    :param output_path: 输出 EPUB 文件路径，如果不指定则使用相同的文件名
    :return: 输出文件路径
    """
    # 解析 FB2 文件
    with open(fb2_file_path, 'r', encoding='utf-8') as f:
        fb2_content = f.read()
    
    # 使用 lxml 解析 XML
    root = etree.fromstring(fb2_content.encode('utf-8'))
    
    # 创建 EPUB 书籍
    book = epub.EpubBook()
    
    # 从 FB2 文件中提取元数据
    description = root.find('.//{http://www.gribuser.ru/xml/fictionbook/2.0}description')
    title_info = description.find('.//{http://www.gribuser.ru/xml/fictionbook/2.0}title-info')
    
    # 设置标题
    title = title_info.find('.//{http://www.gribuser.ru/xml/fictionbook/2.0}book-title')
    if title is not None:
        book.set_title(title.text)
    
    # 设置作者
    author = title_info.find('.//{http://www.gribuser.ru/xml/fictionbook/2.0}author')
    if author is not None:
        first_name = author.find('.//{http://www.gribuser.ru/xml/fictionbook/2.0}first-name')
        last_name = author.find('.//{http://www.gribuser.ru/xml/fictionbook/2.0}last-name')
        if first_name is not None and last_name is not None:
            book.add_author(f"{first_name.text} {last_name.text}")
    
    # 提取正文内容
    body = root.find('.//{http://www.gribuser.ru/xml/fictionbook/2.0}body')
    if body is not None:
        # 创建章节
        chapter = epub.EpubHtml(title='Chapter 1', file_name='chap_1.xhtml', lang='en')
        chapter.content = etree.tostring(body, encoding='unicode')
        book.add_item(chapter)
        
        # 添加章节到目录
        book.toc = (epub.Link('chap_1.xhtml', 'Chapter 1', 'chap1'),)
        
        # 添加默认的 NCX 和 Nav 文件
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        
        # 定义基本样式
        style = '''
        @namespace epub "http://www.idpf.org/2007/ops";
        body {
            font-family: Cambria, Liberation Serif, Bitstream Vera Serif, Georgia, Times, Times New Roman, serif;
        }
        h2 {
            text-align: left;
            text-transform: uppercase;
            font-weight: 200;
        }
        '''
        
        # 添加 CSS 文件
        nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
        book.add_item(nav_css)
        
        # 设置基本 spine
        book.spine = ['nav', chapter]
    
    # 设置输出路径
    if output_path is None:
        output_path = os.path.splitext(fb2_file_path)[0] + '.epub'
    
    # 写入 EPUB 文件
    epub.write_epub(output_path, book, {})
    return output_path

if __name__ == '__main__':
    # 使用示例
    fb2_file = 'convertor/424384'  # 你的 FB2 文件路径
    output_file = fb2_to_epub(fb2_file)
    print(f'转换完成，输出文件：{output_file}') 
from flask import Flask, jsonify, request
import re
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

def get_redirected_url(url):
    # 如果链接是以 // 开头，需要加上 https:
    if url.startswith('//'):
        url = 'https:' + url
    try:
        response = requests.head(url, allow_redirects=True)  # 只发送头请求来获取重定向
        return response.url  # 获取重定向后的最终 URL
    except requests.RequestException:
        return url  # 如果出错，返回原始 URL

def parse_mod_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    # 提取模组名称
    title = soup.find("h3").text if soup.find("h3") else None
    
    # 提取模组英文名称
    subtitle = soup.find("h4").text if soup.find("h4") else None

    # 提取封面图片
    cover_image = soup.find("div", class_="class-cover-image").find("img")["src"] if soup.find("div", class_="class-cover-image") else None
    if cover_image.startswith('//'):
        cover_image = 'https:' + cover_image

    # 提取模组描述
    description_meta = soup.find("meta", {"name": "description"})
    description = description_meta["content"] if description_meta else None

    # **提取支持的MC版本**
    supported_versions = {}
    mcver_section = soup.find("li", class_="col-lg-12 mcver")
    if mcver_section:
        current_loader = None  # 记录当前加载器类型
        for element in mcver_section.find_all(["li", "a"]):
            if element.name == "li":
                text = element.text.strip()
                if text.endswith(":"):  # 检测是否是加载器类型，例如 "Forge:"
                    current_loader = text[:-1]  # 去掉 `:` 作为键
                    supported_versions[current_loader] = []  # 初始化列表
            elif element.name == "a" and current_loader:
                version = element.text.strip()
                supported_versions[current_loader].append(version)  # 加入对应加载器的版本列表

    # 提取 common-link-frame 相关链接
    related_links = []
    link_frame = soup.find("div", class_="common-link-frame")
    if link_frame:
        for link_item in link_frame.find_all("a"):
            link_text = link_item.get("data-original-title") or link_item.text.strip()
            link_url = link_item.get("href")
            if link_url:
                if link_url.startswith("//link.mcmod.cn"):
                    link_url = get_redirected_url(link_url)
                related_links.append({"text": link_text, "url": link_url})

    # 提取 keywords
    keywords_meta = soup.find("meta", {"name": "keywords"})
    keywords = keywords_meta["content"] if keywords_meta else None

    # 提取运行环境
    operating_environment = None
    match = re.search(r'<li class="col-lg-4">运行环境:\s*(.*?)</li>', html_content)
    if match:
        operating_environment = match.group(1)

    # 提取 class="tag" 中的链接
    tag_links = []
    tag_section = soup.find("li", class_="col-lg-12 tag")
    if tag_section:
        for tag_item in tag_section.find_all("a"):
            tag_link = tag_item.get("href")
            tag_text = tag_item.text.strip()
            if tag_link:
                tag_links.append({"text": tag_text, "url": tag_link})

    # 提取 short-name
    short_name = soup.find("span", class_="short-name").text if soup.find("span", class_="short-name") else None

    # 正则表达式提取时间信息
    def extract_timestamp(text):
        match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', text)
        return match.group(1) if match else None
    
    # 提取 Mod 作者/开发团队
    authors = []
    author_section = soup.find("li", class_="col-lg-12 author")
    if author_section:
        for author_item in author_section.find_all("li"):
            # 获取作者的链接和名称
            author_link = author_item.find("a")["href"] if author_item.find("a") else None
            author_name = author_item.find("span", class_="name").text.strip() if author_item.find("span", class_="name") else None
            author_position = author_item.find("span", class_="position").text.strip() if author_item.find("span", class_="position") else None
            if author_link and author_name:
                authors.append({
                    "name": author_name,
                    "link": author_link,
                    "position": author_position
                })

    recorded_time = None
    last_edit_time = None
    last_recommend_time = None
    edit_count = None

    for li in soup.find_all("li", class_="col-lg-4"):
        text = li.text.strip()
        tooltip = li.get("data-original-title", "")

        if "收录时间" in text:
            recorded_time = extract_timestamp(tooltip)

        elif "最后编辑" in text:
            last_edit_time = extract_timestamp(tooltip)

        elif "最后推荐" in text:
            last_recommend_time = extract_timestamp(tooltip)

        elif "编辑次数" in text:
            match = re.search(r'(\d+)次', text)
            if match:
                edit_count = match.group(1)

    return {
        "title": title,
        "subtitle": subtitle,
        "cover_image": cover_image,
        "description": description,
        "supported_versions": supported_versions,
        "related_links": related_links,
        "keywords": keywords,
        "operating_environment": operating_environment,
        "tag_links": tag_links,
        "short_name": short_name,
        "recorded_time": recorded_time,
        "last_edit_time": last_edit_time,
        "last_recommend_time": last_recommend_time,
        "edit_count": edit_count,
        "authors": authors
    }

@app.route('/d/<type>/<id>', methods=['GET'])
def get_mod_info(type, id):
    url = f"https://www.mcmod.cn/{type}/{id}.html"
    response = requests.get(url)
    
    if response.status_code != 200:
        return jsonify({"error": "无法获取数据"}), 500

    mod_data = parse_mod_data(response.text)
    return jsonify(mod_data)

if __name__ == '__main__':
    app.run(debug=True)

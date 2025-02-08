from flask import Flask, jsonify
import re
import requests
from bs4 import BeautifulSoup
import base64
import urllib.parse
from flask_caching import Cache

app = Flask(__name__)

# 配置缓存，使用 SimpleCache，超时时间 5 分钟
app.config["CACHE_TYPE"] = "simple"
app.config["CACHE_DEFAULT_TIMEOUT"] = 300  # 5 分钟
cache = Cache(app)

def get_redirected_url(url):
    if url.startswith('//'):
        url = 'https:' + url

    if url.startswith("https://link.mcmod.cn/target/"):
        encoded_part = url[len("https://link.mcmod.cn/target/"):]
        try:
            decoded_bytes = base64.urlsafe_b64decode(encoded_part)
            decoded_url = decoded_bytes.decode('utf-8') 
            return urllib.parse.unquote(decoded_url)
        except Exception:
            return url  # 解码失败则返回原始 URL

    return url

def parse_mod_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    title = soup.find("h3").text if soup.find("h3") else None
    subtitle = soup.find("h4").text if soup.find("h4") else None

    cover_image = soup.find("div", class_="class-cover-image").find("img")["src"] if soup.find("div", class_="class-cover-image") else None
    if cover_image and cover_image.startswith('//'):
        cover_image = get_redirected_url(cover_image)

    # description_meta = soup.find("meta", {"name": "description"})
    # description = description_meta["content"] if description_meta else None

    supported_versions = {}
    mcver_section = soup.find("li", class_="col-lg-12 mcver")
    if mcver_section:
        current_loader = None
        for element in mcver_section.find_all(["li", "a"]):
            if element.name == "li":
                text = element.text.strip()
                if text.endswith(":"):
                    current_loader = text[:-1]
                    supported_versions[current_loader] = []
            elif element.name == "a" and current_loader:
                version = element.text.strip()
                supported_versions[current_loader].append(version)

    mod_relations = {}
    relation_list = soup.find("ul", class_="class-relation-list")
    if relation_list:
        for fieldset in relation_list.find_all("fieldset"):
            category = fieldset.find("legend").text.strip() if fieldset.find("legend") else "未知分类"
            mod_relations[category] = []

            for relation_item in fieldset.find_all("li", class_="relation"):
                relation_type = relation_item.find("span").text.strip() if relation_item.find("span") else "未知关系"

                related_mods = []
                for mod in relation_item.find_all("a"):
                    mod_name = mod.text.strip()
                    mod_link = mod.get("href")
                    if mod_name and mod_link:
                        related_mods.append({"name": mod_name, "link": mod_link})

                if related_mods:
                    mod_relations[category].append({
                        "relation_type": relation_type,
                        "mods": related_mods
                    })

    related_links = []
    link_frame = soup.find("div", class_="common-link-frame")
    if link_frame:
        for link_item in link_frame.find_all("a"):
            link_text = link_item.get("data-original-title") or link_item.text.strip()
            link_url = link_item.get("href")
            if link_url and link_url.startswith("//"):
                link_url = get_redirected_url(link_url)
            related_links.append({"text": link_text, "url": link_url})

    # keywords_meta = soup.find("meta", {"name": "keywords"})
    # keywords = keywords_meta["content"] if keywords_meta else None

    operating_environment = None
    match = re.search(r'<li class="col-lg-4">运行环境:\s*(.*?)</li>', html_content)
    if match:
        operating_environment = match.group(1)

    tag_links = []
    tag_section = soup.find("li", class_="col-lg-12 tag")
    if tag_section:
        for tag_item in tag_section.find_all("a"):
            tag_link = tag_item.get("href")
            tag_text = tag_item.text.strip()
            if tag_link:
                tag_links.append({"text": tag_text, "url": tag_link})

    short_name = soup.find("span", class_="short-name").text if soup.find("span", class_="short-name") else None

    def extract_timestamp(text):
        match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', text)
        return match.group(1) if match else None
    
    authors = []
    author_section = soup.find("li", class_="col-lg-12 author")
    if author_section:
        for author_item in author_section.find_all("li"):
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
        # "description": description,
        "supported_versions": supported_versions,
        "related_links": related_links,
        # "keywords": keywords,
        "operating_environment": operating_environment,
        "tag_links": tag_links,
        "short_name": short_name,
        "recorded_time": recorded_time,
        "last_edit_time": last_edit_time,
        "last_recommend_time": last_recommend_time,
        "edit_count": edit_count,
        "authors": authors,
        "mod_relations": mod_relations
    }

@cache.cached(timeout=300, key_prefix="mod_info_{type}_{id}")
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

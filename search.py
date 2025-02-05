from flask import Flask, jsonify, current_app
from flask_caching import Cache
import requests
from bs4 import BeautifulSoup
import logging
from typing import Dict, List, Optional

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
cache = Cache(app, config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_THRESHOLD': 500  # 限制缓存条目数
})

# 请求配置
REQUEST_TIMEOUT = 10
HEADERS = {
    'User-Agent': 'mcmod-api/1.0 (github.com/zkitefly/mcmod-api)'
}

def extract_item_data(result_item) -> Dict:
    """从搜索结果项中提取数据"""
    item_data = {}
    data = {}  # 新建 data 字典
    
    try:
        # 提取地址
        info_span = result_item.find('span', class_='info')
        address = info_span.find('a')['href'].replace("//center.mcmod.cn", "https://center.mcmod.cn")
        item_data['address'] = address
        data['mcmod_id'] = address.split('/')[-1].replace('.html', '')

        # 提取标题和相关信息
        title = result_item.find('div', class_='head').text.strip()
        item_data['title'] = title
        
        # 处理标题信息
        if title.startswith('['):
            data['abbr'] = title.split('] ')[0][1:]
            main_title = title.split('] ')[-1]
        else:
            data['abbr'] = None
            main_title = title

        # 提取中文名和副标题
        if ' (' in main_title:
            chinese_name, sub_name = main_title.split(' (', 1)
            data['chinese_name'] = chinese_name
            data['sub_name'] = sub_name.rsplit(')', 1)[0]
        else:
            data['chinese_name'] = main_title
            data['sub_name'] = None

        # 提取类别
        category_link = result_item.find('a')['href']
        data['category'] = (category_link.replace("//www.mcmod.cn/class/category/", "")
                          .replace("-1.html", "") if 'category' in category_link else None)

        # 提取描述和快照时间
        item_data['description'] = result_item.find('div', class_='body').text.strip()
        item_data['snapshot_time'] = result_item.find_all('span', class_='info')[1].find('span', class_='value').text.strip()

        # 特殊情况处理
        if 'mcmod.cn/class' not in address and 'mcmod.cn/modpack' not in address:
            data.update({
                'chinese_name': None,
                'sub_name': None,
                'abbr': None,
                'mcmod_id': None,
                'category': None
            })
        
        # 将 data 添加到 item_data
        item_data['data'] = data

    except Exception as e:
        logger.error(f"Error extracting data from item: {e}")
        return None

    return item_data

@app.route('/s/<path:search>')
@cache.cached(timeout=300)
def get_mcmod_search_result(search: str) -> tuple:
    """处理搜索请求并返回结果"""
    url = f'https://search.mcmod.cn/s?{search}'
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.text, 'html.parser')
        search_result_list = soup.find('div', class_='search-result-list')
        
        if not search_result_list:
            return jsonify([])
        
        results = []
        for result_item in search_result_list.find_all('div', class_='result-item'):
            item_data = extract_item_data(result_item)
            if item_data:
                results.append(item_data)
        
        return jsonify(results)

    except requests.Timeout:
        logger.error(f"Request timeout for URL: {url}")
        return jsonify({'error': 'Request timeout', 'url': url}), 504
    
    except requests.RequestException as e:
        logger.error(f"Request failed for URL {url}: {str(e)}")
        return jsonify({'error': str(e), 'url': url}), 500
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True)

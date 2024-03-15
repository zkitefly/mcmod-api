from flask import Flask, jsonify
from flask_caching import Cache
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple', 'CACHE_DEFAULT_TIMEOUT': 300})  # 300 seconds = 5 minutes

@app.route('/s/<path:search>')
@cache.cached(timeout=300)  # Cache the response for 5 minutes
def get_mcmod_search_result(search):
    try:
        # 构建URL
        url = 'https://search.mcmod.cn/s?' + search
        
        # 设置请求头部，模拟浏览器行为
        headers = {
            'User-Agent': 'mcmod-api/1.0 (github.com/zkitefly/mcmod-api)'
        }
        
        # 发起请求
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找class为search-result-list的div元素
        search_result_list = soup.find('div', class_='search-result-list')
        
        # 如果没有搜索结果，直接返回空列表
        if not search_result_list:
            return jsonify([])
        
        # 初始化结果列表
        results = []
        
        # 提取每个result-item的信息
        for result_item in search_result_list.find_all('div', class_='result-item'):
            item_data = {}
            
            # 提取地址和检查 info
            address = result_item.find('span', class_='info').find('a')['href'].replace("//center.mcmod.cn", "https://center.mcmod.cn")
            
            item_data['address'] = address

            if 'mcmod.cn/class' not in address and 'mcmod.cn/modpack' not in address:
                item_data['info'] = []
                results.append(item_data)
                continue
            
            # 创建 mcmod_id 属性
            item_data['mcmod_id'] = address.split('/')[-1].replace('.html', '')
            
            # 提取标题
            title = result_item.find('div', class_='head').text.strip()

            item_data['title'] = title
            
            # 创建 abbr 属性
            if title.startswith('['):
                item_data['abbr'] = title.split('] ')[0][1:]
            else:
                item_data['abbr'] = None
            
            # 创建 sub_name 属性
            if ' (' in title:
                sub_name = title.split(' (', 1)[-1].rsplit(')', 1)[0]
                item_data['sub_name'] = sub_name
            else:
                item_data['sub_name'] = title.split('] ')[-1]
            
            # 创建 chinese_name 属性
            chinese_name = title.split('] ')[-1].split(' (')[0]
            item_data['chinese_name'] = chinese_name
            
            # 提取类别
            category_link = result_item.find('a')['href']
            if 'category' in category_link:
                item_data['category'] = category_link.replace("//www.mcmod.cn/class/category/", "").replace("-1.html", "")
            else:
                item_data['category'] = None
            
            # 提取描述
            item_data['description'] = result_item.find('div', class_='body').text.strip()
            
            # 提取快照时间
            item_data['snapshot_time'] = result_item.find_all('span', class_='info')[1].find('span', class_='value').text.strip()
            
            results.append(item_data)
        
        # 返回处理后的结果
        return jsonify(results)
    except requests.exceptions.HTTPError as e:
        # 如果远程服务器返回4xx或5xx错误，则返回500服务端错误
        return jsonify({'errorMessage': f'Get \'{url}\' Error.', 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

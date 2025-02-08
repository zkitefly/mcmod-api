# mcmod-api

非官方 MCMOD API，提供 MCMOD 网站的搜索和详情数据查询功能。

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fzkitefly%2Fmcmod-api)

## API 端点

### 1. 搜索 API

**请求格式：**
```
GET /s/{search_params}
```

搜索参数支持 MCMOD 网站原有的所有参数格式，例如：
- 基础搜索：`/s/key=关键词`
- 高级搜索：`/s/key=关键词&site=&filter=1&mold=1`

**示例：**
```
https://mcmod-api.zkitefly.eu.org/s/key=Fabulously%20Optimized
```

### 2. 详情 API

**请求格式：**
```
GET /d/{type}/{id}
```

- `type`: 内容类型 (class/modpack)
- `id`: 内容 ID

**示例：**
```
https://mcmod-api.zkitefly.eu.org/d/class/1234
```

## 返回数据

### 搜索 API 返回字段
- `address`: 条目链接
- `title`: 标题
- `description`: 描述
- `snapshot_time`: 快照时间
- `data`: 
  - `mcmod_id`: MCMOD ID
  - `abbr`: 简称（如有）
  - `chinese_name`: 中文名称
  - `sub_name`: 副标题
  - `category`: 分类

### 详情 API 返回字段
- `title`: 标题
- `subtitle`: 英文标题
- `cover_image`: 封面图片
- `supported_versions`: 支持的游戏版本
- `related_links`: 相关链接
- `operating_environment`: 运行环境
- `tag_links`: 标签
- `short_name`: 简称
- `recorded_time`: 收录时间
- `last_edit_time`: 最后编辑时间
- `last_recommend_time`: 最后推荐时间
- `edit_count`: 编辑次数
- `authors`: 作者信息
- `mod_relations`: 关联模组

## 部署

点击上方的 "Deploy with Vercel" 按钮即可快速部署。

## 注意事项

1. 本 API 为非官方实现，仅供学习交流使用
2. 请合理使用，避免频繁请求
3. API 数据来源于 MCMOD 网站，版权归原网站所有

## 许可证

MIT License

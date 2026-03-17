# 妙想金融数据 API 响应结构参考

## 一级：`data`

| 字段路径 | 类型 | 释义 |
|----------|------|------|
| `data.questionId` | 字符串 | 查数请求唯一标识 ID |
| `data.dataTableDTOList` | 数组 | 标准化后的证券指标数据列表，每元素 = 1 证券 + 1 指标 |
| `data.rawDataTableDTOList` | 数组 | 原始未加工数据，结构与 dataTableDTOList 一致 |
| `data.condition` | 对象 | 查询条件（关键词、时间范围等） |
| `data.entityTagDTOList` | 数组 | 本次查询关联的证券主体汇总（去重） |

## 二级：`data.dataTableDTOList[]`（单指标对象）

### 证券基础信息

| 字段路径 | 类型 | 释义 |
|----------|------|------|
| `code` | 字符串 | 证券完整代码（如 300059.SZ） |
| `entityName` | 字符串 | 证券全称（如 东方财富 (300059.SZ)） |
| `title` | 字符串 | 本指标数据标题（如 东方财富最新价） |

### 表格数据（渲染用）

| 字段路径 | 类型 | 释义 |
|----------|------|------|
| `table` | 对象 | 标准化表格：键=指标编码，值=指标数值数组；`headName` 为时间/维度列 |
| `rawTable` | 对象 | 原始表格，结构同 table |
| `nameMap` | 对象 | 列名映射（指标编码→业务中文名），`headNameSub` 为时间列名 |
| `indicatorOrder` | 数组 | 指标列展示顺序（指标编码数组） |

### 指标元信息

| 字段路径 | 类型 | 释义 |
|----------|------|------|
| `dataType` | 字符串 | 数据来源类型（如 行情数据/数据浏览器） |
| `dataTypeEnum` | 字符串 | HQ=行情，DATA_BROWSER=数据浏览器 |
| `dataTableType` | 字符串 | 表格类型，如 NORM_TABLE |
| `field` | 对象 | 当前指标元信息（编码、名称、时间、粒度等） |
| `fieldSet` | 数组 | 指标元信息集合，单指标时为单元素数组 |

### 证券标签

| 字段路径 | 类型 | 释义 |
|----------|------|------|
| `entityTagDTO` | 对象 | 本指标关联证券的主体属性 |
| `entityTagDTOList` | 数组 | 主体属性集合 |

## 三级：`field`（指标元信息）

| 字段路径 | 类型 | 释义 |
|----------|------|------|
| `field.returnCode` | 字符串 | 指标唯一编码 |
| `field.returnName` | 字符串 | 指标业务中文名（如 最新价/收盘价） |
| `field.returnSourceCode` | 字符串 | 原始来源编码（如 f2/CLOSE） |
| `field.startDate/endDate` | 字符串 | 查询时间范围 |
| `field.dateGranularity` | 字符串 | 粒度：DAY/MIN 等 |
| `field.classCode` | 字符串 | 指标分类编码 |

## 三级：`entityTagDTO`（证券主体属性）

| 字段路径 | 类型 | 释义 |
|----------|------|------|
| `entityTagDTO.secuCode` | 字符串 | 证券纯代码（如 300059） |
| `entityTagDTO.marketChar` | 字符串 | 市场标识（.SZ/.SH 等） |
| `entityTagDTO.entityTypeName` | 字符串 | 证券类型（A 股/港股/债券等） |
| `entityTagDTO.fullName` | 字符串 | 证券完整中文名 |
| `entityTagDTO.entityId` | 字符串 | 系统内主体 ID |
| `entityTagDTO.className` | 字符串 | 证券大类（如 沪深京股票/创业板股票） |

## 其他：`condition` 与 `entityTagDTOList`

- **`data.condition`**：如 `condition.search_data_task_0` 为本次查数的原始条件数组（证券名+指标名+时间范围等）。
- **`data.entityTagDTOList`**：与 `dataTableDTOList[].entityTagDTO` 结构一致，为本次查询涉及证券的去重汇总。

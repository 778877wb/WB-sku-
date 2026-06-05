# WB运营管理系统项目架构设计

## 1. 项目定位

WB运营管理系统（Wildberries Operation Management System）是一套面向俄罗斯 Wildberries 电商团队的内部运营自动化系统。系统第一阶段以 Windows 本地运行为前提，使用 SQLite 作为开发期数据库，并通过定时同步机制对接 Wildberries Official API 与飞书多维表格（Feishu Bitable）。

系统目标是替代当前钉钉表格中的人工登记流程，解决大 SKU 量、多店铺、多运营人员场景下的数据卡顿、上架状态滞后、绩效统计困难、运营数据分散等问题。

## 2. 规模与扩展目标

| 项目 | 当前规模 | 未来规模 | 设计要求 |
| --- | ---: | ---: | --- |
| 运营人员 | 3 人 | 7 人 | 分配算法需可插拔，支持离职人员排除 |
| SKU 数量 | 6000+ | 20000+ | 所有 SKU 查询字段必须建立索引 |
| WB 店铺 | 7 家 | 20 家 | SKU 与店铺是一对多关系 |
| 数据源 | SQLite + API | Feishu Bitable 为最终数据源 | 同步模块需支持增量同步与失败重试 |

## 3. 总体架构

```text
Windows 本地运行程序
├── CLI / 简易桌面入口 / 后续 Web Dashboard
├── 业务服务层
│   ├── SKU分配服务
│   ├── WB上架检测服务
│   ├── WB运营数据同步服务
│   ├── 绩效统计服务
│   ├── 爆款监控服务
│   └── 异常商品监控服务
├── API接入层
│   ├── Wildberries API Client
│   └── Feishu Bitable API Client
├── 数据访问层
│   ├── SQLite Repository
│   └── Feishu Sync Repository
├── 定时任务层
│   ├── 每10分钟：WB上架检测
│   ├── 每小时：WB数据同步
│   └── 每日：排行与异常快照
└── SQLite 本地数据库
    └── 自动同步到 Feishu Bitable
```

## 4. 技术选型

| 模块 | 技术 | 说明 |
| --- | --- | --- |
| 语言 | Python 3.12+ | 兼容 Windows，本地部署简单 |
| 本地数据库 | SQLite | 第一阶段开发与本地运行使用 |
| ORM | SQLAlchemy 2.x | 便于后续迁移 PostgreSQL/MySQL |
| 数据校验 | Pydantic 2.x | API 入参、配置、同步数据结构校验 |
| 定时任务 | APScheduler | Windows 本地稳定运行，支持间隔任务 |
| HTTP Client | httpx | 支持超时、重试、异步扩展 |
| 配置管理 | python-dotenv + Pydantic Settings | 管理 WB、飞书 Token 与运行参数 |
| 日志 | logging / loguru | 本地运行排错与同步审计 |
| 仪表盘 | Streamlit 或 FastAPI + Vue | 第一阶段建议 Streamlit 快速上线 |
| 打包 | PyInstaller | 生成 Windows 可执行文件 |

## 5. 推荐目录结构

```text
WB-sku-
├── README.md
├── pyproject.toml
├── .env.example
├── data/
│   └── wb_ops.sqlite3
├── docs/
│   └── PROJECT_ARCHITECTURE.md
├── src/
│   └── wb_ops/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── db/
│       │   ├── session.py
│       │   ├── models.py
│       │   ├── migrations/
│       │   └── repositories/
│       │       ├── sku_pool_repo.py
│       │       ├── operator_repo.py
│       │       ├── assignment_repo.py
│       │       ├── wb_listing_repo.py
│       │       ├── optimization_repo.py
│       │       └── wb_metrics_repo.py
│       ├── services/
│       │   ├── sku_assignment_service.py
│       │   ├── wb_listing_detection_service.py
│       │   ├── performance_service.py
│       │   ├── wb_metrics_sync_service.py
│       │   ├── hot_selling_service.py
│       │   └── anomaly_service.py
│       ├── integrations/
│       │   ├── wb/
│       │   │   ├── client.py
│       │   │   ├── schemas.py
│       │   │   └── mapper.py
│       │   └── feishu/
│       │       ├── client.py
│       │       ├── bitable_mapper.py
│       │       ├── sync_service.py
│       │       └── schemas.py
│       ├── scheduler/
│       │   ├── jobs.py
│       │   └── runner.py
│       ├── dashboard/
│       │   ├── app.py
│       │   └── views/
│       │       ├── overview.py
│       │       ├── performance.py
│       │       ├── ranking.py
│       │       └── anomalies.py
│       └── utils/
│           ├── time.py
│           ├── logging.py
│           └── retry.py
└── tests/
    ├── test_sku_assignment.py
    ├── test_listing_detection.py
    ├── test_performance.py
    ├── test_hot_selling.py
    └── test_anomaly.py
```

## 6. 数据库设计

### 6.1 `sku_pool`：SKU总池

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | integer | primary key autoincrement | 主键 |
| sku | varchar(128) | unique not null | 全局唯一 SKU 编码 |
| product_name | varchar(255) | not null | 商品名称 |
| brand | varchar(128) | index | 品牌 |
| category | varchar(128) | index | 品类 |
| warehouse_stock | integer | default 0 | 仓库库存 |
| arrival_date | datetime | index | 到货时间 |
| owner | varchar(128) | index | 当前负责人 |
| assign_status | varchar(32) | index | 待分配、已分配、已完成、暂停 |
| listing_status | varchar(32) | index | 未上架、已上架 |
| shop_count | integer | default 0 | 已上架店铺数 |
| sales_30d | integer | default 0 | 近30日销量 |
| review_count | integer | default 0 | 评论数 |
| question_count | integer | default 0 | 提问数 |
| rating | decimal(3,2) | default 0 | 评分 |
| needs_optimization | boolean | default false | 异常监控标记 |
| created_at | datetime | not null | 创建时间 |
| updated_at | datetime | not null | 更新时间 |

业务约束：

- `sku` 必须全局唯一。
- `listing_status` 根据 `shop_count` 自动计算：`shop_count > 0` 为 `已上架`，否则为 `未上架`。
- `warehouse_stock > 0` 且 `assign_status = 待分配` 的 SKU 才允许进入自动分配队列。
- 建议索引：`sku`、`brand`、`category`、`assign_status`、`listing_status`、`owner`、`arrival_date`。

### 6.2 `operators`：运营人员

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | integer | primary key autoincrement | 主键 |
| name | varchar(128) | unique not null | 运营姓名 |
| status | varchar(32) | index | 在职、离职 |
| created_at | datetime | not null | 创建时间 |

业务约束：

- 自动分配时只选择 `status = 在职` 的运营人员。
- 运营离职后保留历史绩效数据，但不再参与新 SKU 分配。

### 6.3 `sku_assignment`：SKU分配记录

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | integer | primary key autoincrement | 主键 |
| sku | varchar(128) | foreign key / index | SKU 编码 |
| operator | varchar(128) | index | 被分配运营 |
| assign_time | datetime | index | 分配时间 |
| assign_by | varchar(128) |  | 分配人或系统 |
| status | varchar(32) | index | 待上架、已上架、已优化、完成 |

业务约束：

- 一个 SKU 可以有多次历史分配记录。
- 当前负责人以 `sku_pool.owner` 为准，历史记录用于追溯。

### 6.4 `wb_listing`：WB商品上架记录

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | integer | primary key autoincrement | 主键 |
| sku | varchar(128) | index | SKU 编码 |
| shop_name | varchar(128) | index | WB 店铺名 |
| nm_id | varchar(64) | index | WB 商品 nmID |
| vendor_code | varchar(128) | index | WB vendorCode |
| listing_time | datetime | index | 首次检测到上架时间 |
| status | varchar(32) | index | 已上架、已下架 |
| last_sync_time | datetime | index | 最近同步时间 |

业务约束：

- 建议唯一约束：`unique(shop_name, nm_id)`。
- 建议唯一约束：`unique(shop_name, vendor_code)`，避免同店铺重复写入。
- 同一个 SKU 可以出现在多个店铺，因此不能对 `sku` 单独设置唯一约束。

### 6.5 `optimization_record`：优化记录

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | integer | primary key autoincrement | 主键 |
| sku | varchar(128) | index | SKU 编码 |
| operator | varchar(128) | index | 运营人员 |
| optimize_time | datetime | index | 优化时间 |
| optimize_type | varchar(32) | index | 标题优化、主图优化、详情优化、价格优化、广告优化、评价维护 |
| remark | text |  | 备注 |

业务约束：

- 优化记录允许多次写入。
- 绩效统计按 `operator` 与 `optimize_time` 聚合。

### 6.6 `wb_metrics`：WB运营数据

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | integer | primary key autoincrement | 主键 |
| sku | varchar(128) | index | SKU 编码 |
| shop_name | varchar(128) | index | 店铺名 |
| date | date | index | 数据日期 |
| sales_qty | integer | default 0 | 销量 |
| sales_amount | decimal(12,2) | default 0 | 销售额 |
| stock | integer | default 0 | WB 库存 |
| review_count | integer | default 0 | 评论数 |
| question_count | integer | default 0 | 提问数 |
| rating | decimal(3,2) | default 0 | 评分 |
| created_at | datetime | not null | 创建时间 |

业务约束：

- 建议唯一约束：`unique(sku, shop_name, date)`。
- 每小时同步时对当天数据执行 upsert，避免重复行。
- 历史数据用于计算近7天销量、近30天销量和商品趋势。

### 6.7 推荐扩展表

#### `shops`：店铺配置

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer | 主键 |
| shop_name | varchar(128) | 店铺名称 |
| wb_api_key_alias | varchar(128) | API Key 配置别名，不直接存明文 |
| status | varchar(32) | 启用、停用 |
| created_at | datetime | 创建时间 |

#### `sync_log`：同步审计日志

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer | 主键 |
| sync_type | varchar(64) | wb_listing、wb_metrics、feishu_push 等 |
| direction | varchar(32) | pull、push |
| status | varchar(32) | success、failed、partial |
| started_at | datetime | 开始时间 |
| finished_at | datetime | 结束时间 |
| success_count | integer | 成功数量 |
| failed_count | integer | 失败数量 |
| error_message | text | 错误信息 |

## 7. 核心业务模块设计

### 7.1 SKU自动分配模块

模块文件：`src/wb_ops/services/sku_assignment_service.py`

#### 输入

- 分配模式：`round_robin`、`brand`、`category`。
- 分配数量：可选，默认分配全部符合条件 SKU。
- 分配人：默认 `system`。

#### 筛选条件

```sql
select * from sku_pool
where warehouse_stock > 0
  and assign_status = '待分配'
order by arrival_date asc, id asc;
```

#### 轮询分配逻辑

```python
operators = get_active_operators()
skus = get_assignable_skus()
for index, sku in enumerate(skus):
    operator = operators[index % len(operators)]
    assign_sku(sku, operator)
```

#### 写入动作

- 更新 `sku_pool.owner = operator.name`。
- 更新 `sku_pool.assign_status = 已分配`。
- 插入 `sku_assignment`，状态为 `待上架`。

#### 扩展策略

| 策略 | 适用场景 | 实现方式 |
| --- | --- | --- |
| 平均分配 | 当前默认策略 | 按在职运营轮询 |
| 按品牌分配 | 指定运营负责指定品牌 | 增加 `operator_brand_rule` 配置 |
| 按品类分配 | 指定运营负责指定品类 | 增加 `operator_category_rule` 配置 |
| 加权分配 | 人员能力不同 | 为运营增加 `weight` 字段 |

### 7.2 WB自动检测上架模块

模块文件：`src/wb_ops/services/wb_listing_detection_service.py`

#### 调度周期

- 每 10 分钟执行一次。

#### 处理流程

```text
读取启用店铺列表
    ↓
逐店铺调用 WB 商品卡片 API
    ↓
读取 vendorCode 与 nmID
    ↓
用 vendorCode 匹配 sku_pool.sku
    ↓
匹配成功则 upsert wb_listing
    ↓
重新计算 sku_pool.shop_count
    ↓
更新 sku_pool.listing_status
    ↓
同步到 Feishu Bitable
```

#### 匹配逻辑

```python
if card.vendor_code in sku_pool_sku_set:
    upsert_wb_listing(
        sku=card.vendor_code,
        shop_name=shop.name,
        nm_id=card.nm_id,
        vendor_code=card.vendor_code,
        status="已上架",
    )
```

#### 状态更新逻辑

```sql
update sku_pool
set shop_count = (
    select count(*) from wb_listing
    where wb_listing.sku = sku_pool.sku
      and wb_listing.status = '已上架'
),
listing_status = case
    when (
        select count(*) from wb_listing
        where wb_listing.sku = sku_pool.sku
          and wb_listing.status = '已上架'
    ) > 0 then '已上架'
    else '未上架'
end;
```

### 7.3 运营绩效统计模块

模块文件：`src/wb_ops/services/performance_service.py`

#### 统计维度

- 今日。
- 本周。
- 本月。

#### 今日上架 SQL

```sql
select sp.owner as operator, count(*) as listing_count
from wb_listing wl
join sku_pool sp on sp.sku = wl.sku
where date(wl.listing_time) = date('now', 'localtime')
  and wl.status = '已上架'
group by sp.owner;
```

#### 今日优化 SQL

```sql
select operator, count(*) as optimize_count
from optimization_record
where date(optimize_time) = date('now', 'localtime')
group by operator;
```

#### 输出结构

```json
{
  "operator": "运营A",
  "today_listing": 12,
  "week_listing": 48,
  "month_listing": 170,
  "today_optimization": 8,
  "week_optimization": 39,
  "month_optimization": 155
}
```

### 7.4 WB运营数据同步模块

模块文件：`src/wb_ops/services/wb_metrics_sync_service.py`

#### 调度周期

- 每小时执行一次。

#### 同步字段

- 销量：`sales_qty`。
- 销售额：`sales_amount`。
- 库存：`stock`。
- 评论数：`review_count`。
- 提问数：`question_count`。
- 评分：`rating`。

#### 写入规则

- 以 `sku + shop_name + date` 作为 upsert 键。
- 当天数据每小时覆盖更新。
- 历史日期数据只追加或校正，不做删除。
- 同步完成后回写 `sku_pool.sales_30d`、`review_count`、`question_count`、`rating`。

### 7.5 爆款监控模块

模块文件：`src/wb_ops/services/hot_selling_service.py`

#### Top Selling View SQL

```sql
select
    sku,
    sum(sales_qty) as sales_7d,
    avg(rating) as avg_rating,
    max(review_count) as review_count,
    max(question_count) as question_count
from wb_metrics
where date >= date('now', '-7 day', 'localtime')
group by sku
order by sales_7d desc
limit 20;
```

#### 输出字段

- SKU。
- 近7天销量。
- 评分。
- 评论数。
- 提问数。

### 7.6 异常商品监控模块

模块文件：`src/wb_ops/services/anomaly_service.py`

#### 判定条件

```text
rating < 4.5
or question_count > 50
```

#### 自动标记逻辑

```sql
update sku_pool
set needs_optimization = case
    when rating < 4.5 or question_count > 50 then 1
    else 0
end;
```

#### 输出视图

- 低评分 TOP20：按 `rating asc` 排序。
- 提问 TOP20：按 `question_count desc` 排序。
- 需要优化清单：`needs_optimization = true`。

## 8. Wildberries API模块设计

### 8.1 模块职责

`src/wb_ops/integrations/wb/client.py` 负责封装 Wildberries Official API 的所有调用，业务服务层不得直接拼接 API URL。

### 8.2 Client 接口设计

```python
class WildberriesClient:
    def __init__(self, api_key: str, timeout: int = 30):
        ...

    def get_product_cards(self, cursor: dict | None = None) -> list[WBProductCard]:
        """获取商品卡片，返回 vendorCode、nmID 等核心字段。"""

    def get_stocks(self, date_from: str | None = None) -> list[WBStockItem]:
        """获取库存数据。"""

    def get_sales(self, date_from: str, date_to: str) -> list[WBSalesItem]:
        """获取销量与销售额数据。"""

    def get_feedbacks(self) -> list[WBFeedbackItem]:
        """获取评价数据。"""

    def get_questions(self) -> list[WBQuestionItem]:
        """获取提问数据。"""
```

### 8.3 多店铺支持

- 每个店铺配置独立 API Key。
- 配置文件只保存 Key 别名，真实 Key 使用 `.env` 保存。
- 同步任务按店铺循环执行，单店铺失败不影响其他店铺。
- 每个店铺同步结果写入 `sync_log`。

### 8.4 API可靠性设计

- 所有请求设置超时时间。
- 对 429、5xx 错误进行指数退避重试。
- 记录 API 请求失败原因。
- 保留 `last_sync_time`，失败后下次可继续增量同步。

## 9. 飞书多维表格同步模块设计

### 9.1 同步目标

系统最终数据源为 Feishu Bitable，第一阶段采用 SQLite 本地写入，再自动推送到飞书多维表格。

```text
SQLite
  ↓
Feishu Bitable
```

### 9.2 同步表

- `sku_pool`。
- `operators`。
- `sku_assignment`。
- `wb_listing`。
- `optimization_record`。
- `wb_metrics`。

### 9.3 Feishu 模块职责

| 文件 | 职责 |
| --- | --- |
| `client.py` | 获取 tenant access token、封装 Bitable API 调用 |
| `schemas.py` | 飞书字段结构与数据校验 |
| `bitable_mapper.py` | SQLite 字段到飞书字段的映射 |
| `sync_service.py` | 批量同步、增量同步、失败重试 |

### 9.4 字段映射策略

每张 SQLite 表维护一个映射配置：

```python
SKU_POOL_FIELD_MAP = {
    "sku": "SKU",
    "product_name": "商品名称",
    "brand": "品牌",
    "category": "品类",
    "warehouse_stock": "仓库库存",
    "owner": "负责人",
    "assign_status": "分配状态",
    "listing_status": "上架状态",
    "shop_count": "上架店铺数",
    "sales_30d": "近30日销量",
    "review_count": "评论数",
    "question_count": "提问数",
    "rating": "评分",
    "needs_optimization": "需要优化",
}
```

### 9.5 增量同步方案

推荐所有业务表都包含 `updated_at` 或可推导的更新时间。同步服务维护本地 `sync_log` 或 `sync_state`，记录每张表的上次成功同步时间。

```text
读取 table 上次成功同步时间
    ↓
查询 SQLite 中 updated_at 大于该时间的数据
    ↓
按唯一业务键查找 Feishu record_id
    ↓
存在则 update，不存在则 create
    ↓
写入同步日志
```

### 9.6 Feishu record_id 管理

建议增加本地扩展表 `feishu_record_map`：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer | 主键 |
| local_table | varchar(64) | 本地表名 |
| local_key | varchar(255) | 本地唯一业务键，如 SKU 或 `sku|shop|date` |
| feishu_table_id | varchar(128) | 飞书表 ID |
| feishu_record_id | varchar(128) | 飞书记录 ID |
| updated_at | datetime | 更新时间 |

这样可以避免每次同步都全表搜索飞书记录，提高 20000+ SKU 场景下的同步效率。

## 10. 仪表盘设计

### 10.1 数据概览

展示指标：

- SKU 总数：`count(sku_pool)`。
- 待上架 SKU：`listing_status = 未上架`。
- 已上架 SKU：`listing_status = 已上架`。
- 库存预警 SKU：`warehouse_stock <= 预警阈值`。
- 今日新增上架：`date(wb_listing.listing_time) = today`。
- 今日新增优化：`date(optimization_record.optimize_time) = today`。

### 10.2 运营排行

字段：

- 运营姓名。
- 今日上架。
- 本周上架。
- 本月上架。
- 今日优化。
- 本周优化。
- 本月优化。

### 10.3 产品排行

榜单：

- 销量 TOP20：近 7 天 `sum(sales_qty)`。
- 评论 TOP20：`review_count desc`。
- 提问 TOP20：`question_count desc`。
- 低评分 TOP20：`rating asc`，排除无评分商品。

### 10.4 异常监控

展示：

- 评分低于 4.5 的商品。
- 提问数大于 50 的商品。
- 同时低评分且高提问的高优先级商品。
- 建议增加“处理状态”和“处理备注”，用于后续闭环管理。

## 11. 配置设计

### 11.1 `.env.example`

```env
APP_ENV=development
SQLITE_DB_PATH=data/wb_ops.sqlite3

FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_BITABLE_APP_TOKEN=xxx

WB_SHOP_1_NAME=shop_a
WB_SHOP_1_API_KEY=xxx
WB_SHOP_2_NAME=shop_b
WB_SHOP_2_API_KEY=xxx

LISTING_DETECTION_INTERVAL_MINUTES=10
WB_METRICS_SYNC_INTERVAL_MINUTES=60
LOW_STOCK_THRESHOLD=10
```

### 11.2 配置类

```python
class Settings(BaseSettings):
    app_env: str = "development"
    sqlite_db_path: str = "data/wb_ops.sqlite3"
    feishu_app_id: str
    feishu_app_secret: str
    feishu_bitable_app_token: str
    listing_detection_interval_minutes: int = 10
    wb_metrics_sync_interval_minutes: int = 60
    low_stock_threshold: int = 10
```

## 12. 定时任务设计

| 任务 | 周期 | 模块 | 说明 |
| --- | --- | --- | --- |
| WB上架检测 | 每10分钟 | `wb_listing_detection_service` | 自动发现 vendorCode 已上架商品 |
| WB数据同步 | 每小时 | `wb_metrics_sync_service` | 同步销量、库存、评论、提问、评分 |
| 飞书同步 | 每10-30分钟 | `feishu.sync_service` | 将 SQLite 增量推送到 Feishu |
| 异常商品扫描 | 每小时 | `anomaly_service` | 标记需要优化 SKU |
| 榜单刷新 | 每日或每小时 | `hot_selling_service` | 刷新爆款与排行数据 |

## 13. API边界与内部接口

### 13.1 Repository 层

Repository 只负责数据库读写，不包含业务规则。

```python
class SkuPoolRepository:
    def list_assignable(self, limit: int | None = None) -> list[SkuPool]:
        ...

    def update_assignment(self, sku: str, owner: str, status: str) -> None:
        ...

    def recalculate_listing_status(self, sku: str) -> None:
        ...
```

### 13.2 Service 层

Service 负责业务规则、事务与跨表操作。

```python
class SkuAssignmentService:
    def assign(self, strategy: str = "round_robin", limit: int | None = None) -> AssignmentResult:
        ...
```

### 13.3 Integration 层

Integration 只负责外部 API，不直接操作数据库。

```python
class FeishuBitableClient:
    def batch_create_records(self, table_id: str, records: list[dict]) -> list[str]:
        ...

    def batch_update_records(self, table_id: str, records: list[dict]) -> None:
        ...
```

## 14. 开发计划

### Phase 1：数据库模型、SKU总池、运营人员、SKU分配

目标：搭建系统骨架，实现可运行的本地数据管理与自动分配。

任务：

1. 初始化 Python 项目结构。
2. 创建 SQLite 数据库连接与 SQLAlchemy 模型。
3. 实现 `sku_pool`、`operators`、`sku_assignment` 三张核心表。
4. 实现 SKU 导入功能，支持 CSV/Excel 导入。
5. 实现运营人员维护功能。
6. 实现轮询自动分配。
7. 编写单元测试：SKU 唯一性、分配过滤条件、轮询公平性。

交付物：

- 本地可运行 CLI。
- SQLite 数据库。
- SKU 自动分配结果。

### Phase 2：WB API接入、自动检测上架

目标：运营无需手工登记上架状态。

任务：

1. 封装 Wildberries API Client。
2. 增加店铺配置管理。
3. 实现商品卡片拉取。
4. 根据 `vendorCode` 匹配 `sku_pool.sku`。
5. upsert `wb_listing`。
6. 自动更新 `shop_count` 与 `listing_status`。
7. 增加每 10 分钟定时任务。
8. 编写接口模拟测试。

交付物：

- 自动上架检测任务。
- 上架记录表。
- SKU 上架状态自动更新。

### Phase 3：绩效统计、优化记录

目标：按运营人员自动统计上架与优化绩效。

任务：

1. 实现 `optimization_record` 模型。
2. 提供优化记录新增入口。
3. 实现今日、本周、本月绩效统计。
4. 将上架数量与优化数量按运营人员聚合。
5. 增加绩效报表导出。

交付物：

- 运营绩效统计接口。
- 今日、本周、本月运营排行。

### Phase 4：销量、评分、评论、提问同步

目标：形成商品运营数据仓库。

任务：

1. 实现 `wb_metrics` 模型。
2. 对接 WB 销量、库存、评论、提问、评分数据。
3. 每小时同步并 upsert 当天指标。
4. 回写 `sku_pool.sales_30d`、`rating`、`review_count`、`question_count`。
5. 记录同步日志并处理失败重试。

交付物：

- 商品指标数据表。
- 每小时数据同步任务。
- 近 30 日销量与评分等核心字段自动更新。

### Phase 5：仪表盘、排行榜、异常监控、爆款监控

目标：为运营管理提供可视化决策支持。

任务：

1. 实现数据概览页面。
2. 实现运营排行页面。
3. 实现销量 TOP20、评论 TOP20、提问 TOP20、低评分 TOP20。
4. 实现近 7 天爆款监控。
5. 实现异常商品自动标记。
6. 接入 Feishu Bitable 增量同步。
7. 打包 Windows 可执行程序。

交付物：

- 本地仪表盘。
- 飞书多维表格自动同步。
- Windows 可运行版本。

## 15. 关键风险与建议

| 风险 | 影响 | 建议 |
| --- | --- | --- |
| WB API 限流 | 同步失败或数据延迟 | 使用重试、分店铺串行、记录同步状态 |
| 飞书字段变更 | 同步失败 | 字段映射配置化，启动时校验字段 |
| Windows 本地机器关机 | 定时任务中断 | 第一阶段接受，后续迁移服务器或云函数 |
| SKU 编码不一致 | 无法匹配上架 | 导入时清洗 SKU，统一大小写与空格规则 |
| 数据量增长 | 查询变慢 | 建索引、增量同步、分页拉取、避免全量扫描 |
| 人员变化 | 分配不公平 | 只分配在职人员，保留历史记录 |

## 16. 第一阶段最小可用版本（MVP）范围

MVP 建议只做以下能力：

1. SKU 导入到 SQLite。
2. 运营人员维护。
3. 轮询自动分配 SKU。
4. WB 商品卡片自动拉取。
5. vendorCode 匹配 SKU 并自动更新上架状态。
6. 今日、本周、本月上架数量统计。
7. SQLite 到 Feishu Bitable 的 `sku_pool` 与 `wb_listing` 同步。

该范围可以最快替代人工登记上架状态，并为后续绩效统计和数据分析打基础。

## 17. 后续服务器化演进方向

当 SKU 达到 20000+、店铺达到 20 家后，建议升级为：

```text
FastAPI 后端
PostgreSQL 数据库
Redis 任务队列
Celery / Dramatiq 后台任务
Feishu Bitable 双向同步
Web Dashboard
Docker 部署
```

升级后可以支持多人同时访问、权限管理、任务监控、API Webhook、服务端定时任务和更完整的数据分析能力。

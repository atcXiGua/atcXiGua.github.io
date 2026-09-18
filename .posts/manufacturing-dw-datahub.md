---
title: 用 DataHub 管理制造业数据资产：元数据、血缘与治理
slug: manufacturing-dw-datahub
cover: /medias/featureimages/8.jpg
tags:
  - DataHub
  - 元数据
  - 数据治理
categories:
  - 大数据
summary: 用 DataHub 管理制造业数仓数据资产：Ingestion Recipe 元数据采集、全链路血缘、术语表与数据分级治理落地。
description: 用 DataHub 管理制造业数仓的数据资产：元数据采集、全链路血缘、术语表与数据分级治理
date: 2026-09-18
---

<h2 id="为什么制造业数仓需要-DataHub"><a href="#为什么制造业数仓需要-DataHub" class="headerlink" title="为什么制造业数仓需要 DataHub"></a>为什么制造业数仓需要 DataHub</h2>
<p>前两篇搭好了分层架构、数据模型和指标体系。但表越建越多之后，新问题来了：数据在哪、谁负责、从哪来到哪去、口径对不对——这些靠人和 Excel 是管不住的。DataHub 是 LinkedIn 开源的第三代元数据平台，核心定位就是企业级数据资产目录与元数据管理平台，让数据<strong>可发现、可理解、可信任、可治理</strong>。</p>
<p>制造业数仓的典型痛点，DataHub 都有对应的解法：</p>
<table>
<thead>
<tr><th>痛点</th><th>DataHub 的解决方式</th></tr>
</thead>
<tbody>
<tr><td>数据孤岛，不知道数据在哪</td><td>统一数据资产目录，一站式搜索</td></tr>
<tr><td>报表口径不一致</td><td>术语表（Glossary）+ 指标口径统一管理</td></tr>
<tr><td>数据来源不清楚</td><td>全链路血缘，从 ERP/MES 追溯到报表</td></tr>
<tr><td>改字段影响范围不明</td><td>影响分析，查看下游所有依赖</td></tr>
<tr><td>数据质量不可见</td><td>集成数据质量框架，展示质量评分</td></tr>
<tr><td>数据权限难管理</td><td>集成 Ranger，标签化敏感数据</td></tr>
</tbody>
</table>
<h2 id="核心功能"><a href="#核心功能" class="headerlink" title="核心功能"></a>核心功能</h2>
<ul>
<li><strong>数据资产目录</strong>：按表名、字段、标签、Owner、主题域搜索；资产详情页一站式看 Schema、Sample Data、Properties、Ownership、Lineage；支持收藏和订阅变更通知</li>
<li><strong>全链路血缘</strong>：表级、列级、任务级（Airflow DAG / Spark Job / Flink Job）三种粒度，支持从 ERP/MES 源系统到 ADS 报表的完整跨系统链路</li>
<li><strong>数据治理</strong>：术语表统一管理业务术语和指标口径；分类标签标记敏感性、主题域、业务线；明确数据 Owner；数据分级（公开/内部/机密/秘密）</li>
<li><strong>数据质量集成</strong>：与 Great Expectations、dbt tests、Apache Griffin 集成，在资产页面展示质量评分和历史趋势，异常自动告警</li>
<li><strong>元数据自动采集</strong>：80+ 数据源连接器（Iceberg、Hive、Doris、Kafka、MySQL、PostgreSQL 等），支持 Python / YAML / REST API 三种方式定义 Ingestion Recipe，可对接 Airflow 或 Cron 定时调度</li>
</ul>
<h2 id="在本项目中的落地"><a href="#在本项目中的落地" class="headerlink" title="在本项目中的落地"></a>在本项目中的落地</h2>
<p>POC 里 DataHub 承担三个角色：资产目录、血缘中心、治理入口。采集配置放在 <code>configs/datahub-ingestion.yml</code>，把 Iceberg（ODS/DWD/DWS 各层表）、Doris（ADS 报表）、Kafka（实时 Topic）、Airflow（DAG 任务）的元数据统一抽取进来。</p>
<p>一套完整的血缘链路在 DataHub 里长这样：</p>
```text
ERP/MES 源表
   │  (SeaTunnel 采集任务)
   ▼
Kafka Topic: ods_erp
   │  (Spark Structured Streaming)
   ▼
Iceberg ODS 表
   │  (Airflow DAG: dag_dwd_transform)
   ▼
Iceberg DWD 表 ──▶ Doris ADS 报表
```
<p>这条链路上任何一个节点改字段，都能在 DataHub 里向上看影响、向下追溯来源，不用再靠人肉梳理依赖。</p>
<h2 id="元数据采集：Ingestion-Recipe"><a href="#元数据采集：Ingestion-Recipe" class="headerlink" title="元数据采集：Ingestion Recipe"></a>元数据采集：Ingestion Recipe</h2>
<p>采集元数据用 YAML Recipe 描述，比如抽取 Iceberg 表的元数据：</p>
```yaml
source:
  type: iceberg
  config:
    platform_instance: manufacturing-dw
    warehouse: s3a://manufacturing-dw/warehouse
    env: PROD
    catalog:
      type: rest
      url: http://rest-catalog:8181

sink:
  type: datahub-rest
  config:
    server: http://datahub-gms:8080
```
<p>Recipe 用 Airflow 定时调度（建议每日全量 + 变更增量），元数据变更会自动同步到 DataHub。项目文档里给出了三种采集方式的取舍：YAML 适合简单场景，Python Recipe 适合需要逻辑加工的场景，REST API 适合自研系统定制推送。</p>
<h2 id="数据治理怎么真正落地"><a href="#数据治理怎么真正落地" class="headerlink" title="数据治理怎么真正落地"></a>数据治理怎么真正落地</h2>
<h3 id="术语表：统一指标口径"><a href="#术语表：统一指标口径" class="headerlink" title="术语表：统一指标口径"></a>术语表：统一指标口径</h3>
<p>把上一篇指标体系里的核心指标录入术语表，每个术语关联到实际的表和字段。比如"一次合格率"这个术语，关联到 <code>fct_quality_detail.pass_rate</code>，写明计算公式和统计频率。之后任何人想用这个指标，先在术语表里查口径，而不是问同事、猜算法。</p>
<h3 id="分类标签与数据分级"><a href="#分类标签与数据分级" class="headerlink" title="分类标签与数据分级"></a>分类标签与数据分级</h3>
<p>给资产打两类标签：</p>
<ul>
<li><strong>业务标签</strong>：主题域（生产/质量/成本/设备）、业务线</li>
<li><strong>敏感度标签</strong>：按数据标准里的分级——公开/内部/机密/秘密</li>
</ul>
<p>敏感度标签是和 Ranger 联动的桥梁：DataHub 里给字段打上"机密"标签，Ranger 里对应的行列权限策略自动生效（项目里 <code>configs/ranger-policies.json</code> 定义了这些策略），实现"标签即权限"。</p>
<h3 id="数据质量可视化"><a href="#数据质量可视化" class="headerlink" title="数据质量可视化"></a>数据质量可视化</h3>
<p>数据质量检查结果（主键唯一性、空值率、枚举合法性等）推送到 DataHub，资产页面直接展示质量评分。质量分低的表会在目录里被标记，谁用谁知道——这一步把"数据可信"从口头承诺变成可量化的指标。</p>
<h2 id="运营与自动化"><a href="#运营与自动化" class="headerlink" title="运营与自动化"></a>运营与自动化</h2>
<p>元数据管理要持续运营，不能是一次性导入。项目文档里给出了运营手册的要点：</p>
<ul>
<li><strong>采集调度</strong>：Ingestion Recipe 纳入 Airflow 统一调度，失败重试 + 告警</li>
<li><strong>Owner 认领</strong>：每张表必须有 Owner，未认领的资产定期通报</li>
<li><strong>文档补全率</strong>：把表/字段文档完成率当作治理 KPI，逐步提升</li>
<li><strong>血缘巡检</strong>：定期检查血缘断链（有下游无上游、有任务无产出），<code>scripts/check_lineage.sh</code> 就是干这个的</li>
</ul>
<h2 id="小结"><a href="#小结" class="headerlink" title="小结"></a>小结</h2>
<p>数仓建设到后面，拼的不是建表速度，是治理能力。DataHub 在这套架构里的价值是把"数据有什么、怎么来的、谁在用、可不可信"这四件事变成了可搜索、可追溯、可度量。对制造业这种系统多、口径多、历史包袱重的场景，先把资产目录和血缘跑起来，后面的指标治理、权限管控才有抓手。</p>
<p>DataHub 完整文档（产品定位、架构、配置、自动化、运营、最佳实践）：<a target="_blank" rel="noopener" href="https://github.com/atcXiGua/personal/tree/main/manufacturing-dw-poc/docs/datahub">manufacturing-dw-poc/docs/datahub</a>。</p>

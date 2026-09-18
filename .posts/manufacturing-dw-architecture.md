---
title: 制造业数据仓库 POC：架构设计与落地实践
slug: manufacturing-dw-architecture
cover: /medias/featureimages/2.jpg
tags:
  - 数据仓库
  - 湖仓一体
  - Doris
categories:
  - 大数据
summary: 基于湖仓一体架构的制造业数据仓库 POC：五层分层设计、离线 + 实时双链路、Iceberg/Doris/SeaTunnel 技术选型与一键部署方案。
description: 面向制造业数字化转型的数据仓库 POC：湖仓一体五层架构、离线与实时双链路数据流、技术选型与部署方案
date: 2026-09-18
---

<h2 id="项目背景"><a href="#项目背景" class="headerlink" title="项目背景"></a>项目背景</h2>
<p>传统制造业数字化转型，最先卡住的往往不是设备，而是数据：ERP、MES、IoT/SCADA、WMS、QMS 五六个系统各自为政，口径不一致、口径对不上，报表靠人手工导 Excel 拼。这个 POC 就是面向这个痛点做的一套数据仓库建设验证，覆盖供应链、生产、质量、成本、设备、财务六大主题域，目标是给制造企业一套可落地、可扩展的数据驱动决策底座。</p>
<h2 id="整体架构：五层分层"><a href="#整体架构：五层分层" class="headerlink" title="整体架构：五层分层"></a>整体架构：五层分层</h2>
<p>架构采用经典的数仓分层，从数据源到应用一共五层：</p>
<table>
<thead>
<tr><th>分层</th><th>职责</th><th>存储 / 引擎</th></tr>
</thead>
<tbody>
<tr><td>ODS 原始数据层</th><td>原始数据落地，保持与源系统一致的结构</td><td>Apache Iceberg on MinIO</td></tr>
<tr><td>DWD 明细数据层</td><td>清洗、标准化、维度建模（星型模型）</td><td>Iceberg + Spark ETL</td></tr>
<tr><td>DWS 汇总数据层</td><td>按主题域轻度汇总，面向分析主题</td><td>Iceberg + Spark SQL</td></tr>
<tr><td>ADS 应用数据层</td><td>面向具体业务场景的最终报表数据</td><td>写入 Doris</td></tr>
<tr><td>数据服务层</td><td>即席查询、实时总线、资产目录、权限管控</td><td>Doris / Kafka / DataHub / Ranger</td></tr>
</tbody>
</table>
<p>整体的数据链路是：<strong>数据源 → Kafka 消息总线 → ODS（Iceberg）→ Spark ETL → DWD → DWS → ADS → Doris → 报表/大屏</strong>。</p>
<h2 id="关键技术选型"><a href="#关键技术选型" class="headerlink" title="关键技术选型"></a>关键技术选型</h2>
<h3 id="为什么用-Iceberg-做湖格式"><a href="#为什么用-Iceberg-做湖格式" class="headerlink" title="为什么用 Iceberg 做湖格式"></a>为什么用 Iceberg 做湖格式</h3>
<ul>
<li><strong>ACID 事务</strong>：并发写入场景下保证数据一致性</li>
<li><strong>时间旅行</strong>：回溯任意时间点的数据，审计和纠错很方便</li>
<li><strong>高效小文件管理</strong>：后台 Compaction 和 Snapshot 清理</li>
<li><strong>Schema Evolution</strong>：改字段不需要重写全量数据</li>
<li><strong>与 Spark 深度集成</strong>：原生支持读写</li>
</ul>
<h3 id="为什么用-Doris-做-OLAP"><a href="#为什么用-Doris-做-OLAP" class="headerlink" title="为什么用 Doris 做 OLAP"></a>为什么用 Doris 做 OLAP</h3>
<ul>
<li><strong>MPP + 向量化</strong>：列式存储 + 向量化执行，查询性能好</li>
<li><strong>实时写入</strong>：Stream Load / Routine Load，适合实时数仓</li>
<li><strong>SQL 兼容</strong>：高度兼容 MySQL 协议，BI 工具接入零成本</li>
<li><strong>物化视图</strong>：自动优化查询路径</li>
</ul>
<h3 id="为什么用-SeaTunnel-做集成"><a href="#为什么用-SeaTunnel-做集成" class="headerlink" title="为什么用 SeaTunnel 做集成"></a>为什么用 SeaTunnel 做集成</h3>
<p>ERP/MES/WMS/QMS 这些系统年代跨度大，接口五花八门。SeaTunnel 连接器丰富、支持 CDC（Debezium 模式）实时捕获变更、内置数据质量检查规则，还提供 Web UI 可视化编排 ETL 作业，是统一集成层的合适选择。</p>
<h2 id="数据流设计：离线-实时双链路"><a href="#数据流设计：离线-实时双链路" class="headerlink" title="数据流设计：离线 + 实时双链路"></a>数据流设计：离线 + 实时双链路</h2>
<h3 id="离线链路-T-1"><a href="#离线链路-T-1" class="headerlink" title="离线链路 (T+1)"></a>离线链路（T+1）</h3>
```bash
[ERP/MES/WMS/QMS]
       │
       ▼
  [SeaTunnel Sync]
       │
       ▼
  [Kafka ( Topic: ods_* )]
       │
       ▼
  [Spark Structured Streaming / Batch]
       │
       ▼
  [Iceberg ODS Tables]
       │
       ▼
  [Spark SQL ETL Job (Airflow 调度)]
       │
       ├──▶ DWD 明细层 (维度建模 + 清洗)
       │
       ▼
  [DWS 汇总层 (主题汇总)]
       │
       ▼
  [ADS 应用层 (报表计算)]
       │
       ▼
  [写入 Doris]
```
<h3 id="实时链路"><a href="#实时链路" class="headerlink" title="实时链路"></a>实时链路</h3>
<p>IoT/SCADA 设备数据走另一条路：通过 OPC-UA / MQTT 采集进 Flink DataStream，实时计算 OEE 和告警，结果一路写 Doris Realtime Table 供实时看板，一路以微批写回 Iceberg ODS 归档。</p>
```bash
[IoT/SCADA 设备]
       │ OPC-UA / MQTT
       ▼
  [Flink DataStream]
       │ 实时计算 OEE / 告警
       ▼
  [Kafka ( Topic: iot_realtime )]
       │
       ├──▶ [Flink OEE Realtime Job] ──▶ [Doris Realtime Table]
       │
       └──▶ [Iceberg ODS (微批)]
```
<h2 id="部署方案"><a href="#部署方案" class="headerlink" title="部署方案"></a>部署方案</h2>
<h3 id="POC-环境：一键-Docker-Compose"><a href="#POC-环境：一键-Docker-Compose" class="headerlink" title="POC 环境：一键 Docker Compose"></a>POC 环境：一键 Docker Compose</h3>
```bash
# 复制环境变量
cp docker/.env.example docker/.env

# 启动所有服务
docker compose -f docker/docker-compose.yml up -d

# 初始化平台（建库建表、建 Topic、注册 DataHub 元数据）
bash scripts/init_platform.sh
```
<p>POC 单机建议 16 核 / 64GB+ 内存；如果只想验证核心存储和计算，还有最小化编排 <code>docker-compose-minimal.yml</code>，只部署 MinIO + Doris + Kafka。</p>
<h3 id="生产环境集群规划"><a href="#生产环境集群规划" class="headerlink" title="生产环境集群规划"></a>生产环境集群规划</h3>
<table>
<thead>
<tr><th>组件</th><th>节点数</th><th>配置</th></tr>
</thead>
<tbody>
<tr><td>Doris (FE)</td><td>3</td><td>16 核 / 64GB / 500GB SSD</td></tr>
<tr><td>Doris (BE)</td><td>3+</td><td>32 核 / 128GB / 2TB HDD</td></tr>
<tr><td>Kafka</td><td>3</td><td>8 核 / 16GB / 500GB SSD</td></tr>
<tr><td>MinIO</td><td>4（纠删码）</td><td>8 核 / 16GB / 10TB HDD × 4</td></tr>
<tr><td>Spark / Flink</td><td>3+ Workers</td><td>按负载弹性伸缩</td></tr>
<tr><td>Airflow</td><td>1 Scheduler + N Workers</td><td>Workers 按需伸缩</td></tr>
</tbody>
</table>
<h2 id="ETL-流水线编排"><a href="#ETL-流水线编排" class="headerlink" title="ETL 流水线编排"></a>ETL 流水线编排</h2>
<p>Airflow 里按分层拆成 4 个 DAG，逐层依赖：</p>
<ol>
<li><code>dag_ods_daily_sync</code> — ODS 层数据同步（ERP/MES/WMS/QMS → Kafka → Iceberg）</li>
<li><code>dag_dwd_transform</code> — DWD 层数据加工（清洗 + 维度建模）</li>
<li><code>dag_dws_summary</code> — DWS 层数据汇总</li>
<li><code>dag_ads_report</code> — ADS 层报表生成</li>
</ol>
<p>每个 DAG 里都会先做 <code>create_batch_context</code>（生成批次 ID、同步时间窗）和 <code>validate_connections</code>（校验源系统连通性），失败重试 3 次、单次执行超时 2 小时，跑批失败有邮件告警。</p>
<h2 id="运维与回滚"><a href="#运维与回滚" class="headerlink" title="运维与回滚"></a>运维与回滚</h2>
<p>得益于 Iceberg 的时间旅行，数据回滚和 Schema 变更都很轻量：</p>
```sql
-- Schema 变更（向后兼容，天然支持）
ALTER TABLE dwd.production_detail ADD COLUMNS (new_column STRING);

-- 时间旅行：回滚到指定快照查数据
SELECT * FROM dwd.production_detail
FOR SYSTEM_VERSION AS OF '2026-09-14';
```
<p>备份策略上，Iceberg 每小时快照保留最近 7 天，Doris 每日全量导出到 MinIO，配置文件全部 Git 管理。<code>scripts/monitor.sh</code> 负责监控 Kafka 消费延迟、ETL 任务状态、Doris 查询性能、MinIO 存储使用率和数据质量检查结果。</p>
<h2 id="小结"><a href="#小结" class="headerlink" title="小结"></a>小结</h2>
<p>这套 POC 的核心思路其实就一句话：<strong>用湖仓一体统一存储，用分层架构隔离变化，用实时链路补上 T+1 覆盖不到的场景</strong>。真正落地时，架构反而不是最难的——难点在源系统接口协商、数据口径统一和指标体系治理。后面的文章会分别展开讲数据模型与指标体系，以及如何用 DataHub 把数据资产管起来。</p>
<p>项目源码：<a target="_blank" rel="noopener" href="https://github.com/atcXiGua/personal/tree/main/manufacturing-dw-poc">github.com/atcXiGua/personal — manufacturing-dw-poc</a>。</p>

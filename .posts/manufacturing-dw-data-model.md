---
title: 制造业数据仓库的维度建模与指标体系
slug: manufacturing-dw-data-model
cover: /medias/featureimages/5.jpg
tags:
  - 维度建模
  - 指标体系
  - OEE
categories:
  - 大数据
summary: 制造业数仓的维度建模实践：事实表与维度表设计、六大主题域指标体系、OEE 三要素与黄红双阈值预警。
description: 制造业数仓的数据模型设计：Kimball 维度建模、事实表与维度表、六大主题域指标体系、OEE 与预警阈值
date: 2026-09-18
---

<h2 id="建模方法论：Kimball-维度建模"><a href="#建模方法论：Kimball-维度建模" class="headerlink" title="建模方法论：Kimball 维度建模"></a>建模方法论：Kimball 维度建模</h2>
<p>数仓的分层架构搭好之后，最关键的就是建模。本项目采用 <strong>Kimball 维度建模</strong>：以业务过程为中心构建事实表，以业务实体构建维度表，形成星型模型。相比范式建模（三范式），维度建模牺牲一点冗余换来查询性能和业务可理解性——对以分析为主的数仓场景更合适。</p>
<p>建模流程分五步：</p>
<ol>
<li><strong>业务过程识别</strong>：识别核心业务过程（生产、质量、库存、成本）</li>
<li><strong>粒度定义</strong>：确定每张事实表的业务粒度</li>
<li><strong>事实表设计</strong>：确定事实（度量值）和维度外键</li>
<li><strong>维度表设计</strong>：确定维度属性和代理键</li>
<li><strong>退化维度</strong>：把高频过滤字段冗余进事实表，减少 Join</li>
</ol>
<h2 id="主题域与事实表映射"><a href="#主题域与事实表映射" class="headerlink" title="主题域与事实表映射"></a>主题域与事实表映射</h2>
<table>
<thead>
<tr><th>主题域</th><th>事实表</th><th>粒度</th><th>核心度量</th></tr>
</thead>
<tbody>
<tr><td>生产</td><td>fct_production_detail</td><td>秒级 / 分钟级</td><td>产量、工时、产出合格数</td></tr>
<tr><td>质量</td><td>fct_quality_detail</td><td>批次级</td><td>合格数、不良数、缺陷数</td></tr>
<tr><td>库存</td><td>fct_inventory_detail</td><td>日级 / 班次级</td><td>库存量、出入库量、库龄</td></tr>
<tr><td>成本</td><td>fct_cost_detail</td><td>日级 / 订单级</td><td>材料成本、人工成本、制造费用</td></tr>
<tr><td>设备</td><td>（嵌入生产事实表）</td><td>秒级 / 分钟级</td><td>设备状态、稼动率、故障时长</td></tr>
</tbody>
</table>
<p>注意设备主题没有独立事实表——设备状态、稼动率、故障时长直接作为度量嵌入生产明细事实表，因为设备数据和生产数据天然同粒度（设备级 · 分钟级），拆开反而要多一次 Join。</p>
<h2 id="维度表设计"><a href="#维度表设计" class="headerlink" title="维度表设计"></a>维度表设计</h2>
<p>一共六张维度表：工厂（dim_factory）、设备（dim_equipment）、供应商（dim_supplier）、工人（dim_worker）、产品（dim_product）、日期（dim_date）。</p>
<p>设计上有几个共通的约定：</p>
<ul>
<li><strong>代理键 + 业务主键并存</strong>：<code>factory_sk</code>（自增代理键） + <code>factory_id</code>（业务编码），事实表只存代理键</li>
<li><strong>统一三时间戳</strong>：<code>create_time</code>（源系统创建）、<code>update_time</code>（源系统更新）、<code>dw_insert_time</code>（数仓插入），方便追溯数据新鲜度</li>
<li><strong>状态字段枚举化</strong>：如设备状态固定为 运行/停机/待机/维修</li>
</ul>
<p>以设备维度为例，它同时携带组织层级（工厂外键、车间、产线）和设备属性（型号、制造商、类型、产能、功率），并且有 <code>is_iot_connected</code> 标记是否已接入 IoT——这个标记很关键，决定了该设备能不能参与实时 OEE 计算。</p>
<p>日期维度除了年季度月周、是否周末/假日，还额外做了 <strong>班次类型</strong>（单班/两班/三班）和 <strong>财务期间</strong>。制造业的月度经营分析通常按财务期间而非自然月，这个字段能省掉大量口径争论。</p>
<h2 id="事实表设计"><a href="#事实表设计" class="headerlink" title="事实表设计"></a>事实表设计</h2>
<h3 id="生产明细事实表"><a href="#生产明细事实表" class="headerlink" title="生产明细事实表"></a>生产明细事实表</h3>
<p>粒度是 <strong>设备级 · 分钟级</strong>（每台设备每分钟一条），这是整套模型里粒度最细、数据量最大的表。核心字段：</p>
```sql
-- 产量与质量
plan_quantity      DECIMAL(18,2)  -- 计划产量
actual_quantity    DECIMAL(18,2)  -- 实际产量
good_quantity      DECIMAL(18,2)  -- 合格产量
bad_quantity       DECIMAL(18,2)  -- 不合格产量
yield_rate         DECIMAL(5,4)   -- 良率

-- 时间与效率（OEE 计算的输入）
run_time_minutes     DECIMAL(10,2)  -- 运行时间
idle_time_minutes    DECIMAL(10,2)  -- 空闲时间
setup_time_minutes   DECIMAL(10,2)  -- 换模/调试时间
downtime_minutes     DECIMAL(10,2)  -- 停机时间
downtime_reason      STRING         -- 停机原因
cycle_time_seconds   DECIMAL(10,2)  -- 实际周期时间
```
<p>把计划产量、实际产量、合格产量、各类时间放在同一张表，OEE 的三个要素（开动率 / 性能 / 合格率）就能在同一行内算出来，不用跨表 Join。</p>
<h3 id="质量明细事实表"><a href="#质量明细事实表" class="headerlink" title="质量明细事实表"></a>质量明细事实表</h3>
<p>粒度是 <strong>批次级</strong>。除了抽样数、合格数、缺陷数、合格率，还专门做了缺陷治理：<code>defect_category</code>（缺陷类别）、<code>defect_code</code>（缺陷代码）、<code>defect_description</code>（缺陷描述）三段式，方便做帕累托分析（哪些缺陷类别贡献了 80% 的不良）。<code>inspection_type</code> 区分来料/过程/终检/出货四个环节，合格率因此可以按环节拆开看，而不是只看一个笼统的合格率。</p>
<h3 id="库存与成本事实表"><a href="#库存与成本事实表" class="headerlink" title="库存与成本事实表"></a>库存与成本事实表</h3>
<p>库存明细粒度是 <strong>SKU · 仓库 · 日级</strong>，除了常规的收发存数量，重点做了呆滞/临期治理：<code>days_in_stock</code>（库龄）、<code>is_overdue</code>（是否临期）、<code>is_slow_moving</code>（是否呆滞）、<code>safety_stock</code>（安全库存）、<code>reorder_point</code>（补货点）——这些字段直接支撑呆滞料预警和补货建议两个业务场景。</p>
<p>成本明细粒度是 <strong>产品 · 日级</strong>，按成本类别（直接材料/直接人工/制造费用）和成本类型（标准/实际/差异）双维度组织，<code>cost_variance</code>（成本差异）和 <code>variance_rate</code>（差异率）是标准成本制企业的核心分析对象。</p>
<h2 id="指标体系：六大主题域"><a href="#指标体系：六大主题域" class="headerlink" title="指标体系：六大主题域"></a>指标体系：六大主题域</h2>
<p>光有表没有指标，数据还是用不起来。指标体系围绕生产、质量、成本、设备、供应链、财务六大维度构建，每条指标都带编码、计算公式、单位和统计频率，比如：</p>
<table>
<thead>
<tr><th>指标编码</th><th>指标名称</th><th>计算公式</th><th>频率</th></tr>
</thead>
<tbody>
<tr><td>PROD_T004</td><td>计划完成率</td><td>SUM(actual) / SUM(plan)</td><td>日</td></tr>
<tr><td>QUAL_F002</td><td>缺陷 PPM</td><td>defect_count / actual × 1,000,000</td><td>日</td></tr>
<tr><td>INV_T003</td><td>库存周转率</td><td>出库总量 / 平均库存量</td><td>月</td></tr>
<tr><td>COST_T005</td><td>单位成本</td><td>total_cost / production_quantity</td><td>日</td></tr>
</tbody>
</table>
<p>指标编码是整套体系的骨架：<code>主题域_类型_序号</code>（如 <code>PROD_T001</code> 生产-产量类、<code>QUAL_F001</code> 质量-不良类），有了编码才能在 DataHub 术语表里做指标口径统一管理，避免同一个"合格率"在不同报表里算法不同。</p>
<h2 id="OEE：设备综合效率的三要素"><a href="#OEE：设备综合效率的三要素" class="headerlink" title="OEE：设备综合效率的三要素"></a>OEE：设备综合效率的三要素</h2>
<p>制造业绕不开 OEE（Overall Equipment Effectiveness），它是设备主题的核心指标，由三个要素相乘：</p>
<table>
<thead>
<tr><th>编码</th><th>要素</th><th>公式</th><th>目标值</th></tr>
</thead>
<tbody>
<tr><td>OEE_A001</td><td>时间开动率 Availability</td><td>运行时间 / (运行时间 + 停机时间)</td><td>≥ 90%</td></tr>
<tr><td>OEE_P001</td><td>性能开动率 Performance</td><td>(实际产量 × 理论节拍) / 运行时间</td><td>≥ 95%</td></tr>
<tr><td>OEE_Q001</td><td>合格品率 Quality</td><td>合格产量 / 实际产量</td><td>≥ 99%</td></tr>
<tr><td>OEE_T001</td><td><strong>设备综合效率</strong></td><td><strong>A × P × Q</strong></td><td><strong>≥ 85%</strong></td></tr>
</tbody>
</table>
<p>三要素拆开看的价值在于<strong>定位问题</strong>：OEE 低，先看是开动率低（停机多）、性能低（节拍慢）还是合格率低（质量差），这三个的改善动作完全不同。指标体系里还派生了稼动率、MTBF、MTTR、产能利用率，以及按设备加权聚合的线体 OEE 和工厂 OEE，形成从单机到工厂的完整效率视图。</p>
<h2 id="指标分层与预警阈值"><a href="#指标分层与预警阈值" class="headerlink" title="指标分层与预警阈值"></a>指标分层与预警阈值</h2>
<p>指标按管理层次分三层，服务不同场景：</p>
<table>
<thead>
<tr><th>层级</th><th>说明</th><th>使用场景</th><th>指标示例</th></tr>
</thead>
<tbody>
<tr><td>L1 战略层</td><td>高层关注的核心指标</td><td>经营分析会、战略规划</td><td>工厂 OEE、综合成本、准时交付率</td></tr>
<tr><td>L2 管理层</td><td>部门级运营指标</td><td>月度经营分析</td><td>产量、合格率、库存周转率</td></tr>
<tr><td>L3 执行层</td><td>岗位级操作指标</td><td>班组看板、实时监控</td><td>设备 OEE、班次产量、一次合格率</td></tr>
</tbody>
</table>
<p>光定义指标不够，还得告诉业务什么是异常。每条关键指标都配了黄色预警和红色告警双阈值：</p>
<table>
<thead>
<tr><th>指标</th><th>黄色预警</th><th>红色告警</th></tr>
</thead>
<tbody>
<tr><td>OEE</td><td>&lt; 85%</td><td>&lt; 75%</td></tr>
<tr><td>一次合格率</td><td>&lt; 98%</td><td>&lt; 95%</td></tr>
<tr><td>计划完成率</td><td>&lt; 95%</td><td>&lt; 85%</td></tr>
<tr><td>不良率</td><td>&gt; 2%</td><td>&gt; 5%</td></tr>
<tr><td>库存周转天数</td><td>&gt; 60 天</td><td>&gt; 90 天</td></tr>
<tr><td>设备故障频次</td><td>&gt; 2 次/日</td><td>&gt; 5 次/日</td></tr>
</tbody>
</table>
<h2 id="数据标准：让指标算得明白"><a href="#数据标准：让指标算得明白" class="headerlink" title="数据标准：让指标算得明白"></a>数据标准：让指标算得明白</h2>
<p>指标体系要落地，前提是数据标准先行。项目里专门有一份数据标准文档，覆盖：</p>
<ul>
<li><strong>编码标准</strong>：工厂编码、设备编码、物料编码、工单号、批次号的统一编码规则</li>
<li><strong>命名规范</strong>：表名（<code>层_主题_实体</code>，如 <code>dwd_fct_production_detail</code>）、字段名、任务名的规则</li>
<li><strong>数据类型规范</strong>：金额统一 DECIMAL(18,4)、比例统一 DECIMAL(5,4)、时间统一 TIMESTAMP + 时区</li>
<li><strong>数据质量规则</strong>：主键唯一性、外键完整性、枚举值合法性、空值率阈值</li>
<li><strong>数据安全标准</strong>：分级（公开/内部/机密/秘密）、脱敏规则、与 Ranger 权限的映射</li>
<li><strong>度量单位与币种</strong>：重量单位、计量单位、币种与汇率口径</li>
</ul>
<p>举个最容易被忽视的坑：<strong>时间标准化</strong>。车间三班倒，夜班跨零点，"某班次产量"按自然日切还是按班次切？标准里明确按班次时间窗切分，日期维度里的 <code>shift_type</code> 就是配合这个用的。这种口径不定清楚，L3 执行层的班次看板永远对不上。</p>
<h2 id="小结"><a href="#小结" class="headerlink" title="小结"></a>小结</h2>
<p>数据模型和指标体系是数仓的"里子"：模型决定了数据怎么存、查询好不好跑；指标体系决定了数据怎么用、业务能不能看懂。这套设计的核心取舍是——<strong>用维度建模的冗余换分析效率，用指标编码的规范化换口径统一</strong>。下一篇会讲怎么用 DataHub 把这些表和指标纳入元数据管理，把血缘、术语表和权限治理真正跑起来。</p>
<p>数据模型与指标体系完整文档：<a target="_blank" rel="noopener" href="https://github.com/atcXiGua/personal/tree/main/manufacturing-dw-poc/docs">manufacturing-dw-poc/docs</a>。</p>

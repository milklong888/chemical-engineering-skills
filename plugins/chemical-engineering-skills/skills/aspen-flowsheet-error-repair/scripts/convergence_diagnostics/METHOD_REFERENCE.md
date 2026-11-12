> Active owner: aspen-flowsheet-error-repair. Offline observations only; current authority and strict precision lock override historical source guidance.

# 二分定位、内外层精度核查与冷启动验证

类型：用户明确要求公开的方法与离线代码参考；priority：normal。
此条目不承接原项目的工程成功标签，不构成正式inbox准入、默认参数或自动改模型规则。
文字采用CC BY 4.0；[工具](README.md)采用仓库MIT许可。

## 1. 二分定位：冻结条件，再比较有效分支

先列清物理设备与物流连接、独立进料、初始估计、控制读写和执行顺序、目标、单位、物性/反应、相态检查、各层容差。物理回流与数值tear分别记账。记录原输入、有效运行前导出及实际运行身份；内存修改后的有效输入与导入源分别绑定。

将可疑控制或数值设置分组，保留完整基准与每个对照。每个变体从同一受保护源生成，只施加显式编辑。将边界冻结为已收敛结果时，标明这是诊断初估，不把它等同原始冷启动。

先比较完整组与移除组；再分成两个子组。如果两个子组都不复现而合并后复现，转查耦合与依赖顺序。新出现导入失败、无效tear、控制不收敛或物理失效的分支保留为失败对照，不能用来排除原警告。设备、压力、相态或工况发生变化时，重新走专业变更审查。

对最终关键对照核实际输入差异与同次原生Control Panel/history。没有正文的警告按[原生图谱→官方知识库→最后websearch](https://github.com/milklong888/chemical-engineering-experience-inbox/blob/1e0a6c7a50b2233de02fb214f258444b1e0d33ab/proposals/EXP-20261022-knowledge-escalation-p0.md)取证。具体故障文本消失、总警告状态改变和工程验收分别核验。

`make_isolation_variants.py`只按精确字面编辑生成文件与哈希清单，不选择物理切断点，不决定分组因果，也不运行Aspen。变体是否保留必要物理服务及有效控制，由当前专业owner检查。

## 2. 内外层精度：核量定义和残差传递

记录外层目标表达式、操纵量、边界、单位、绝对容差及每轮实际响应；记录内层tear/块的收敛变量、相对或绝对准则、单位、缩放和真实回读容差。先检查实际自由度、变量写入者及计算顺序。

外层残差下降后停在平台时，先核内层已接受的残差、外层试探步及实际产品响应。相对tear准则与有量纲的产品容差不能直接比较大小。非零目标的“绝对容差/目标绝对值”仅为量级背景，不代替灵敏度和误差传递分析。

The current operations/error-repair precision lock governs execution: do not tighten, loosen, add or delete frozen solver tolerance cards to gain convergence. This helper audits supplied observations; historical source advice about exploring stricter inner tolerances is not an authorization to edit them. Preserve input/export identity, readback and counterexamples under the active task contract. Any separately explicit case-local relaxation remains outside shared success/evolution evidence.

只有在同变量、同准则及同单位时，离线工具才比较内层容差是否收紧。它不从残差平台自动推断根因，也不设置任何推荐精度。**1e-6不是本包的通用默认值；所有精度、步长、目标和判据由当前项目明确给出。**

`audit_precision_trials.py`核查调用者给定的试验观测与量定义，不运行新计算，不把输入JSON中的声明自动当成Aspen原生事实。

## 3. 冷启动：证明实际响应，保留初值身份

冷启动使用明确冻结的原始初估、当前边界和新建自有会话，记录导入/初始化的真实范围。保存了收敛结果的文件可带入已有估计；文件名与初始化标签本身不证明冷启动。遵守既有共享资源准入与关闭规则。

在授权边界内对操纵量的初始猜值作有界扰动，保持目标、控制关系和独立物理边界。分别记录初始/最终操纵量、同单位的移动阈值、实际目标值与误差。初始即达标的运行可以提供该点的结果证据；控制响应还需要确实发生位移的试验。warm start只覆盖其已观察初估。

每次运行绑定输入、有效运行前导出、结果、原生报告/审核回执及文件哈希；随后检查同次物热衡算、全相反应转化和当前必要门。有限初值扰动不证明整个工况包络或动态稳定性。最后分别验证精确交付路径文件的无编辑复开运行，并核源文件身份未变。

`audit_cold_starts.py`只核调用者数据中的目标误差、操纵量位移、声明的启动类型覆盖以及证据文件哈希。哈希一致不证明观测值是从该文件正确提取的，也不证明初始化标签真实。实际提取、原生洁净性和工程接受继续由现有owner验证。

## 权威与实现归属

- Aspen Plus V14安装帮助：`Diagnosing Design Specification Convergence`、`Options Defaults Sequencing Sheet`、`Tear Specifications Sheet`、`Calculator Input Sequence Sheet`。应在有权使用的当前安装中核字段与适用性；本仓库不转载受限正文、截图或示例模型。
- [AspenTech KB000056985](https://esupport.aspentech.com/S_Article?id=000056985)提供逐对象消息检索入口；文章不证明任何当前警告的特定原因。
- 实际Aspen运行、FIFO准入、会话所有权与完整原生证据审查继续使用现有[操作owner](https://github.com/milklong888/chemical-engineering-skills/tree/98a2ea53a127cad7e2fecd0df447a89f5ca014a0/plugins/chemical-engineering-skills/skills/aspen-plus-operations)。本包不另造COM管理、锁或原生错误计数解析器。

## 共享边界

本次按用户明确授权共享通用方法与新整理的离线脚本。原项目模型、原始日志、具体运行结果、客户/私人路径及完整确认记录不随包发布；原项目谱系与验收状态保留原样。公共脚本的合成测试仅验证声明的离线代码行为。提交、合并、CI通过、功能修复与工程验收分别记录，不自动写入canonical Skill或默认检索。

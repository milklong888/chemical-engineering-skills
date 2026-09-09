# L3-08 工艺与设备互相约束：合理流程要能落实、能复核、能追溯

- `knowledge_layer`: L3_worldview
- `status`: active_source_backed
- `source_scope`: 用户明确的设计工作流；教材的系统耦合、设计与校核思想；已审计设备程序

## 思想

流程不是先画完、再被动找设备的单向清单。工艺给出物料状态、处理量、温压、
传递任务与目标；设备的真实适用范围又约束可采用的工况和模块。两者需要迭代，
但共同服从产品目标、守恒、热力学、可操作性和当前项目方法。

“选不出”是诊断起点，不是统一结论。缺输入先推导或提取，单位错误先修正，
没有目录不能冒充容量极限；有适用证据的单机限制才支持多台/分级等修改候选。
换热器并联分流、串联分段，压缩机并联分流、串联分级，解决的问题并不相同。
选定方案必须回到流程重算，不能只把一行设备改成多行设备。

好的初步设计因此要回答：每个模块完成什么物理任务；为什么该工况适合所选
设备；改变设备后哪些消费者必须复算；每台设备的依据能否回到同一版工况。
这是一项全系统校核门，不是“有型号即合理”，也不是缺厂家数据就停止一切设计。

## 下行证据

- `CEPR-UPPER-WANG-HE`, PDF p13–14：单元操作与流程开发、强化和整体优化的关系。
- `CEPR-UPPER-WANG-HE`, PDF p18：流动与传热、传质和反应的耦合。
- `chapter_nodes/CEPR-CH02-fluid-flow-and-transport.md`、
  `chapter_nodes/CEPR-CH04-heat-transfer-and-exchangers.md`：输送和传热机制与设备方法入口；不提供通用设备上限。
- 用户 2026-09-09 的设备选型反馈与逐设备追溯要求是行为权威，非教材逐字主张。
- `../../../skill_packages/chemical-engineering-expert/references/PROCESS_EQUIPMENT_FEEDBACK.md`：完整闭环与证据边界。
- `../../../integrations/github_20260909/reviews/selector_audit.md`：冻结版本程序实际支持与未覆盖能力。

## 下钻

执行路线：`../method_nodes/L1-05-process-equipment-iteration.md`。
公式、数值、能力包络进入当前设备的来源账本，不写入本思想节点作为默认值。

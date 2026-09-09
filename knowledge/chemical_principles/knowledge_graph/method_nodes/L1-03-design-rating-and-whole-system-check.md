# L1-03 设计、校核与全系统复核不可混为一件事

- `knowledge_layer`: L1_method
- `status`: active_cross_source_method

## 三种问题

- **设计**：给定任务和边界，求设备能力、面积/高度、操作量或候选形式。
- **校核**：给定现有设备/结构和工况，判断能否完成任务及余量/限制。
- **系统复核**：判断该设备放入流程后，物料、能量、压力、控制、安全和
  上下游负荷是否仍合理。

三者的已知量、未知量和验收证据不同。设计结果不能充当同设备性能证据；
局部校核通过也不能证明流程是好设计。

## 路线

1. 冻结任务类型、系统边界、基准和验收量；
2. 选择 L2 机制和适用 L1 模型；
3. 列出直接输入、可推导量、条件性估计和真实缺口；
4. 完成设计或校核方程并检查单位、极限、敏感性；
5. 回到全系统检查压降、热负荷、循环、控制、终端、安全和维护；
6. 按证据成熟度给出 `accepted/provisional/bounded/blocked`，而非只给一个数。

## 来源与边界

- `CEPR-UPPER-WANG-HE`, PDF p18–120、p177–331：CH02–CH05 的
  设备设计/校核方法族。
- 代表性 L0 锚点：`../../source_pages/upper/page_0255.txt`（换热器
  设计/校核章节）与 `../../source_pages/upper/page_0302.txt`（蒸发设计
  衡算入口）。
- L3：`../concept_nodes/L3-03-unit-operations-as-a-coupled-system.md`。
- 宏观检查：
  `../../../skill_packages/chemical-engineering-expert/references/MACRO_DESIGN_QUALITY.md`。

设备型号、几何、效率、污垢、压降和软件结果必须来自当前项目/同设备证据
或现行适用标准，不能由教材例题填入。

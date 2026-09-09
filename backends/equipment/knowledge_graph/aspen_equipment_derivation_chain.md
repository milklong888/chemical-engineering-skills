# Aspen 到设备设计的确定性推导链

## 位置

本节点属于顶层“设备设计图谱与脚本”的流程数据入口：

```text
设备设计图谱与脚本
└─ Aspen导出适配
   ├─ aspen-equipment-export-v1
   ├─ aspen-run-status-evidence-v1
   └─ aspen_equipment_derivation.py
      -> equipment_design_match.py
      -> 标准/公式/型号状态
```

Aspen skill 负责机械导出和运行证据，本节点负责把导出结果转换为设备设计参数；设备/塔 skill 只审核或继续执行，不能替代这条主链。

## 不依赖大模型的主链

```text
实际JSON导出文件
-> 重读文件并核对内存对象
-> 导出文件SHA256
-> 原始.his及SHA256
-> Run Status四类非负整数计数和问题行
-> 流股/模块/连接字段
-> 同义字段冲突检查
-> 显式单位与绝压/表压换算
-> 设备参数及逐项lineage
-> 目标量=公式=代入式=答案
-> 设备族/公式/标准/证据状态
```

每条 lineage 至少包括 source file path/hash、object type/id、source field、raw value/unit、transform、target field/value/unit 和 equation chain。传入内存对象与实际哈希文件不一致时直接阻断。

## 多选规则

- 同一设备族有多个子型、公式分支或型号都可行：保留共同支持的最泛用设备族/型式及候选集，停在 `type_selected`。
- 跨设备族、单位、压力基准或物理方向冲突：返回 `BLOCKED_*`，不构造虚假父类结论。
- 不允许按模型偏好、标签得分或旧项目习惯选择专用结构。

## 压力和动力硬门

- 压力必须声明 `absolute` 或 `gauge`；表压必须给当地大气压。
- 压缩比：`Pout_abs/Pin_abs`；膨胀比：`Pin_abs/Pout_abs`。
- 泵升压必须满足 `Pout>Pin`；反向时不得继续算扬程或功率。
- 水力功率：`Ph=rho*g*Q*H`；轴功率：`Pshaft=Ph/eta`，不得混名。
- 负表压/真空设计不得使用 `Pdesign=Pop*k`，转入外压设计分支。
- 筒体/封头厚度分母非正、NPSHa<NPSHr、非正物性/尺寸、非整数计数均为硬阻断。

## 正式使用和型号状态

Aspen clean-run 只证明流程侧工况可作为 process basis，不证明设计压力/温度、材料、腐蚀裕量、机械强度、塔内件或厂家性能。

`formal_use_gate` 只有在以下条件全部满足时才为 `ELIGIBLE_AS_PROCESS_BASIS`：

1. Run Status JSON、原始 `.his` 和各自 SHA256 一致；
2. terminal/severe/error/warning 计数全零且为整数；
3. 原始问题行为空；
4. 设备身份、端口基数、必需计算和 Aspen 对账无阻断。

型号升级另需 `equipment-evidence-manifest-v1` 逐 gate 关联同位号、同设备族、同候选型号的不同工件；`final_model` 还需 `equipment-audit-approval-v1` 独立审核批准记录。大模型只允许生成或核查该审核记录，不能修改确定性匹配结果。

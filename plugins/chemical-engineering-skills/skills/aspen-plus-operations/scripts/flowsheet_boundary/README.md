> Main-library relocation: plugins/chemical-engineering-skills/skills/aspen-plus-operations/scripts/flowsheet_boundary. Source and transformations: [RELOCATION.json](RELOCATION.json). Historical source/admission statements below retain their original scope; current parent skill owns routing and acceptance.

# 普通脚本池：流程边界、原生结果与受控末端设备修改

条目ID：EXP-20261018-flowsheet-boundary-tools
priority：normal / script
状态：公开代码与方法候选，非inbox准入或工程验收
代码许可：MIT（见仓库根LICENSE）
说明许可：CC BY 4.0
作者/公开署名：milklong888，由助手按本次明确上传请求整理

## 工具与依赖

| 文件 | 用途 | 依赖与边界 |
| --- | --- | --- |
| `native_results.py` | 叶节点索引、MIXED标量、一级组分叶、原生HeatX温焓配对 | Python 3.10+标准库；完整且有单位的原生树快照 |
| `boundary_compare.py` | 指定保留流股逐项差分；明确列举外部热服务及轴功 | 标准库及同目录`native_results.py`；不自动选择能耗边界 |
| `com_operations.py` | 明确批准的末端HEATER删除、原生HCurve卡片创建 | 已安装且有许可的Aspen Plus；兼容的COM桥和既有受控调用者；卡片/端口基于V14观察 |

不含Aspen模型、厂商手册、原始日志、私有工作路径、具体原料/设备参数或独立COM启动器。不会选择物性、工艺路线、产品指标、压缩压力或工程容差。固定换算`1163 kW/(Gcal/hr)`只适用于Aspen的cal（4.1868J），不是tcal。

## 只读输入格式

输入为调用者从自己拥有的案例读取的JSON。`probes`将完整输出根路径映射为行数组；每行包含`path`、`Value`和`UnitString`。树容器可能有数字值，只有没有后代路径的明确叶节点才可使用。快照必须完整，不要把截断容器当标量。

HeatX读取器要求同一输出根下四套`TEMP_HOT/INLET/N`、`TEMP_CLD/INLET/N`、`DUTY_HOT/INLET/N`、`DUTY_CLD/INLET/N`；温度单位`C`、热负荷单位`Gcal/hr`。按整数点号配对，四套点号必须相同，冷热累计Q网格逐点差不得超过`1e-10 Gcal/hr`。该容差是只读网格一致性检查，不是Aspen求解器精度设置。保存原生Q的符号与温度次序，负温差照实返回。

    python native_results.py snapshot.json --heatx-output "\Data\Blocks\HX\Output"

结果包含每点Q、热冷温度与最小温差；它不是全厂Pinch、EDR或全曲线连续极值的严格证明。曲线采样之外的行为仍由专业owner判断。

版本比较CLI：

    python boundary_compare.py before.json after.json contract.json

两个快照包含`results.streams`和`results.blocks`，行格式同上。合同明确列出`retained_streams`，以及`before_utilities`/`after_utilities`中的`external_heat_fields`（块ID、结果字段二元数组）和`shaft_blocks`（WNET）。只比较指定流股，不把被排除或无定义的零流股说成通过；缺数值或单位不符就报错。内部HeatX不要列为外部热服务，换了产品出口状态不要自动宣称同边界节能。

## COM调用合同

复用已安装操作层的`aspen_run_supervisor`/`aspen_runtime`创建自有会话和排队，不绕过资源准入。回调本身不打开/附着/运行/保存/关闭应用，不停止进程。

`remove_terminal_heaters(app, requests, input_guard_paths=..., expected_counts=...)`要求：

- 每项明确`block`、`inlet`、`outlet`和`confirmed_no_outlet_conditioning_requirement: true`。这个布尔值必须由已完成的工程审查提供，不能由脚本按“末端”自动判定。
- 调用者给出前后块/流股计数和需要保护的输入树根。所有请求先核对，再修改。
- 仅覆盖V14 HEATER的`F(IN)`、`P(OUT)`单入口/单出口路径；其他已连接端口、下游消费者、重复请求或保护输入中的死流股引用均拒绝。ID限制为简单标识符，其他合法Aspen名称需单独扩展和验证。
- 删除只操作父集合，保留原上游流股作为外送，删除原下游死流股。保护输入改变或计数异常即失败。中途COM失败时丢弃受保护候选，本工具不承诺在活案例中原子回滚。
- 未在保护树内的Calculator、Design Spec或其他引用仍由调用者审查。之后必须检查Engine.Ready、运行、产品/循环/衡算、PFD、保存和无编辑复开，不能以回调返回当交付通过。

`enable_hcurves(app, specifications)`接受`block`、`kind`、`curve_id`、`points`。kind为`condenser`、`reboiler`或`heater_or_flash`。它只创建DUTY/NPOINT/恒压曲线卡；已有曲线拒绝覆写。调用者先确认真实服务存在，创建后仍须运行并读取曲线。空塔没有的冷凝/再沸服务不能靠加分析卡变出来。

兼容COM环境需要调用者提供。`ASPEN_RUNTIME_OWNER_TOKEN`只用来拒绝明显绕过既有调用者的使用，不构成会话所有权或授权的密码学证明。

## 测试与验证范围

从仓库根目录运行：

    python -B -X utf8 -m unittest discover -s plugins/chemical-engineering-skills/skills/aspen-plus-operations/scripts/flowsheet_boundary/tests -v

测试使用明确的合成树、数值、端口和对象，不是Aspen热力学模型。它们核查叶节点容器陷阱、重复/缺点、单位/finite、Q网格、负温差、边界变化、重复能耗、缺授权/下游消费者/额外热流端口/残留引用及不匹配计数等拒绝路径。COM模拟对象不证明原生Aspen接受这些操作。

另在本地受控Aspen会话中对当前`com_operations.py`执行了批准的删除回调及`heater_or_flash` HCurve建卡并读取运行后的原生对象；当前`native_results.py`和`boundary_compare.py`也对私有快照做了只读对照。原始案例/记录留本地，公开CI仅重放合成测试；本地原生检查不能由本包独立公开复现。`condenser`/`reboiler`通用回调尚未对当前通用版本逐一原生重放，不能沿用早期项目脚本的执行作为同代码证明。精确代码及测试摘要见`SOURCE_METADATA.json`。

原项目严格Summary/history证据不完整；不宣称严格求解干净、完整工程验收、EDR、真实压降/机图/电机效率、动态或通用可迁移性。保留原专业owner，不另造严格错误计数解析器。正式准入仍需维护者独立核对，而不是读取本README的自报。

## 来源与相关候选

本目录为本次明确授权后整理的原创通用适配与只读工具，具体输入从参数提供。已有操作层、资源准入和证据解析继续归 [chemical-engineering-skills](https://github.com/milklong888/chemical-engineering-skills/tree/98a2ea53a127cad7e2fecd0df447a89f5ca014a0/plugins/chemical-engineering-skills/skills/aspen-plus-operations)，本包不捆绑该仓库或第三方代码。

- [P0/Bug级：无依据的产品末端调温](https://github.com/milklong888/chemical-engineering-experience-inbox/blob/1e0a6c7a50b2233de02fb214f258444b1e0d33ab/proposals/EXP-20261018-terminal-product-conditioning.md)
- [普通背景/方法：热泵单岛及回接边界](https://github.com/milklong888/chemical-engineering-experience-inbox/blob/1e0a6c7a50b2233de02fb214f258444b1e0d33ab/proposals/EXP-20261018-heat-pump-flow-boundaries.md)

内容许可、代码许可、P0优先级、普通池和正式inbox准入相互独立；本PR不修改`inbox/`或正式Skill。

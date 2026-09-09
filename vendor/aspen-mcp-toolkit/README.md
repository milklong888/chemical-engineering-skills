# Aspen Plus MCP

通过自然语言操控 Aspen Plus 进行化工流程模拟——参数调优、批量运行、读取结果，全部由 AI 代理完成。

## 工作模式

```
你在 GUI 里搭好流程拓扑 → MCP 接管参数调优和运行分析
```

**MCP 不负责画流程图。** 你需要在 Aspen Plus GUI 中手动放置模块和物流（或用 `connect`/`connect_port` 工具通过代码建立连接），然后 MCP 用来：

- ✅ 批量改参数、跑灵敏度分析
- ✅ 运行模拟、检查收敛状态
- ✅ 读取物流和模块结果数据
- ✅ 导出报告

---

## 安装（给同学用）

### 环境要求

- Windows（COM 自动化依赖）
- Aspen Plus v15 已安装（GUI 41.0 / 40.0）
- Python 3.10+

### 步骤

```bash
# 1. 克隆或解压项目
cd aspen-mcp

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境并安装依赖
venv\Scripts\pip install -e .

# 4. 启动（验证安装）
venv\Scripts\aspen-mcp
```

启动后 MCP 服务器会通过 stdio 通信，适用于任何支持 MCP 协议的客户端（如 Reasonix、Claude Desktop、VS Code）。

### 在 Reasonix 中使用

在 `reasonix.toml` 中添加：

```toml
[[plugins]]
name    = "aspen-mcp"
command = "path\\to\\aspen-mcp\\venv\\Scripts\\python.exe"
args    = ["-m", "aspen_mcp.server"]
```

### 在 Claude Desktop / VS Code 中使用

```json
{
  "mcpServers": {
    "aspen-mcp": {
      "command": "path\\to\\aspen-mcp\\venv\\Scripts\\python.exe",
      "args": ["-m", "aspen_mcp.server"]
    }
  }
}
```

---

## 工具总览

<!-- 保持原有工具总览内容不变 -->

---

## 工具总览

### 模拟生命周期

| 工具 | 说明 |
|---|---|
| `open_file(path)` | 打开 `.apw` 文件 |
| `new_simulation()` | **创建空白新模拟（复制纯净模板到临时文件，避开 InitNew COM 稳定性问题）** |
| `close_file()` | 关闭当前文件 |
| `run()` | 运行模拟（同步） |
| `run_async()` | 异步运行 |
| `stop_simulation()` | **停止当前运行** |
| `save(path?)` | 保存文件 |
| `reinit()` | 重置结果（重新运行前调用） |
| `reinit_and_run()` | **Reinit + Run 一步完成（推荐）** |
| `status()` | 查看连接和引擎状态 |
| `probe()` | **诊断 COM 状态（app / root / tree 三级检查）** |
| `visible(show)` | **显示/隐藏 Aspen 窗口** |
| `batch_refresh(off)` | **开关 GUI 刷新（批量操作加速）** |
| `run_script(path)` | **在 Aspen 内部执行 Python 脚本** |

### 流程拓扑

| 工具 | 说明 |
|---|---|
| `list_all_blocks()` | 列出所有模块 |
| `list_all_streams()` | 列出所有物流 |
| `explore(path)` | 探索数据树节点 |
| `add_block(name, type)` | 添加模块（如 `HEATER`, `ICON1`） |
| `remove_block(name)` | 删除模块 |
| `add_stream(name)` | 添加物流 |
| `remove_stream(name)` | 删除物流 |
| `connect(source, dest, stream?)` | **连接源块→目标块**（自动创建流） |
| `connect_port(block, port, stream)` | **连接到指定端口**（用于非标准端口） |
| `disconnect(stream_name)` | **断开流并从流程中移除** |
| `list_block_ports(block)` | **查看块的端口和连接情况** |
| `flowsheet_topology()` | **显示流程拓扑：源块 --[流名]--> 目标块** |

### 参数与结果

> ⚠️ **注意：`set_param` 只适用于模块参数，物流参数必须用 `set_stream_param`。** 详情见下方"流股参数设置"章节。

| 工具 | 说明 |
|---|---|
| `get_block(name)` | 读取模块规格和结果 |
| `block_status(name)` | **读取模块收敛状态（BLKSTAT / PER_ERROR / PROPSTAT）** |
| `set_param(block, param, value)` | 设置模块参数 |
| `get_stream(name)` | 读取物流属性（温度、压力、流量等） |
| `set_stream_param(name, param, value)` | **设置物流参数（如 TEMP, PRES, TOTAL）** |
| `set_stream_composition(name, component, flow)` | **设置物流中某组分的摩尔流量** |
| `get_stream_composition_info(name)` | 读取物流组成信息 |

### 组分与物性

| 工具 | 说明 |
|---|---|
| `list_components()` | 列出所有组分 |
| `add_component(id)` | 添加组分（如 WATER, ETHANOL） |
| `remove_component(id)` | 删除组分 |
| `get_property_method()` | 读取当前全局物性方法 |
| `set_property_method(method)` | 设置物性方法（如 NRTL, PENG-ROB） |

### 反应与动力学

| 工具 | 说明 |
|---|---|
| `list_reaction_sets()` | 列出所有反应集 |
| `add_reaction_set(name, type)` | 创建反应集（POWERLAW/LHHW/EQUILIBRIUM） |
| `remove_reaction_set(name)` | 删除反应集 |
| `add_reaction(set, no, reactants, products, phase, exponents?)` | 添加反应及计量系数 |
| `remove_reaction(set, no)` | 删除单个反应 |

### 分析

| 工具 | 说明 |
|---|---|
| `sensitivity(block, variable, values)` | 手动灵敏度分析 |
| `export_report_file(path)` | 导出 `.rep` 报告 |
| `generate_input_summary(path)` | **导出输入摘要 (.bkp)** |
| `find_incomplete_inputs()` | **扫描未填写的输入节点** |
| `diagnose(keywords)` | 搜索收敛故障知识库 |
| `search_convergence_knowledge(keywords)` | 详细收敛知识搜索 |

### 通用路径访问

| 工具 | 说明 |
|---|---|
| `get_value(path)` | **按反斜杠路径读值（如 `\\Data\\Streams\\3\\Output\\RES_TEMP`）** |
| `set_value(path, value)` | **按反斜杠路径写值** |

### 流程查看与 RadFrac 侧线

| 工具 | 说明 |
|---|---|
| `flowsheet_topology()` | **展示完整拓扑：源块 --[流名]--> 目标块** |
| `add_side_duty(block, stage, duty)` | **设置 RadFrac 侧线换热器热负荷** |
| `remove_side_duty(block, stage)` | **删除 RadFrac 侧线换热器** |

---

## 常见工作流

### 1. 打开文件并运行

```
open_file("甲醇.apw")
run()
status()
```

### 2. 改参数后重新运行

```
set_param("HEATER", "TEMP", 150)
set_param("HEATER", "PRES", 5)
run()
get_stream("C-OUT")
```

### 3. 从零搭建流程（拓扑+参数+运行）

> ⚠️  **重要：`set_param` 只能设模块参数，物流参数必须用 `set_stream_param`。**
> 详情见下方"流股参数设置"章节。

```
# 步骤1：添加模块
add_block("MIXER", "MIXER")
add_block("REACTOR", "RPLUG")
add_block("SEP", "FLASH2")

# 步骤2：添加物流并连接
connect("MIXER", "REACTOR", "FEED")
connect("REACTOR", "SEP", "R-OUT")

# 步骤3：设参数（模块用 set_param，物流用 set_stream_param）
set_param("MIXER", "TEMP", 100)
set_param("REACTOR", "LENGTH", 5)

# 物流参数必须用 set_stream_param（通过 MIXED 子节点写入）
set_stream_param("FEED", "TEMP", 150)
set_stream_param("FEED", "PRES", 5)
set_stream_param("FEED", "TOTAL", 100)

# 步骤4：运行并看结果（先用 reinit 清缓存，再 run）
reinit()
run()
get_stream("R-OUT")
```

更方便的替代：**直接用 `reinit_and_run()` 一步完成**。

### 4. 添加组分并切换物性方法

```
# 添加新组分
add_component("METHANE")
add_component("ETHANOL")

# 查看现有组分
list_components()

# 切换物性方法
set_property_method("NRTL")
get_property_method()
```

---

## 操作要点（COM 经验总结）

### 删除块和物流的顺序 ⚠️

**先删块，再清物流。** 绝不能反过来。

✅ 正确：
```
remove_block B1          # 块先删，连接自动断裂
disconnect CL2           # 清理残余孤儿物流
disconnect H2O
```

❌ 错误（会导致 COM 服务器异常，无法恢复）：
```
disconnect CL2           # 块还在但进料少了一条 → 块变无效
disconnect H2O           # 块完全孤零零
remove_block B1          # 💥 COM 服务器异常
```

**原理**：Mixer 等块要求至少有一条连接才能存在。全拔光后再删块，Aspen 内部校验不通过，COM 直接崩。

### COM 错误分级

| 错误现象 | 含义 | 应对 |
|---|---|---|
| `尚未调用 CoInitialize。` | 子线程未初始化 COM | 修复代码即可，不致命 |
| `发生意外。` + (0, None, ...) | 参数/操作型错误 | 可重试，COM 状态不受影响 |
| `服务器出现异常情况。` | COM 服务器状态已脏 | ❌ **立即 close_file → open_file** |
| `远程过程调用失败。` | Aspen Plus 未运行 | 检查 Aspen Plus 是否已打开 |
| `对象没有连接到服务器` | COM 代理已过期（InitNew / 进程重启后） | 调用 `reconnect()` 或重启 MCP 插件 |

**`close_file() → open_file()` 可解决绝大多数 COM 稳定性问题。**
`_is_dead()` 机制会检测引用失效并自动 reconnect，但某些情况下仍需要手动恢复。

### 合法搭建流程（已验证）

```
1. open_file → reinit_and_run       # 稳定状态
2. set_property_method               # 先改物性
3. add/remove_component              # 改组分
4. 先加自己的块（模板的 B1 先留着）  # 保证流程至少有一个块
5. add_stream + connect               # 搭自己的流程
6. 设参数（模块用 set_param，物流用 set_stream_param）
7. remove_block B1 + disconnect 孤儿 # 最后删模板残留
8. run / reinit_and_run
```

### HEATER 的温度设置

HEATER 默认 `HEATOPT=CONST-DUTY`（按热负荷计算）。要用温度设参需先改为 `CONST-TEMP`：
```
aspen.set_value(r"\Data\Blocks\PREHEAT\Input\HEATOPT", "CONST-TEMP")
```

### 流股参数（MIXED 子节点）⚠️

> 以下为原有内容，保持不变

### 保存文件
`save()` — 原地保存（覆盖当前文件）  
`save("路径.apw")` — 另存为新文件  
两种方式均已验证可用。保存后 Aspen 会临时持有文件锁，不影响保存结果。

### 流连接
物流连接不走 `Connections`（只读），而走 **`Block → Ports → {port名} → Elements.Add(流名)`**。  
- 连接前如果端口已有流，会自动断开旧连接  
- 标准端口名：`F(IN)` 输入物流、`P(OUT)` 输出物流、`V(OUT)` 汽相出口、`L(OUT)` 液相出口  
- 不确定端口名时先用 `list_block_ports("模块名")` 查看

### 添加/删除组分
组分通过 `Components → Specifications → Input → TYPE` 表操作。该表为 **2 列**：列 0 为组分标签，列 1 为组分类型（Aspen Plus 自动填充 `CONV`）。只需用 `InsertRow` + `SetLabel(0,0)` 设置名称即可，**不要手动设置第 2 列**（会导致该值被当作新增组分名）。  
长名称组分（>8字符）会自动生成短标签并写入 `ANAME`，Aspen 自动从数据库解析别名。
重复名称会自动追加编号后缀确保唯一。

### 设置物性方法
`set_property_method("NRTL")` 会同时写 `GBASEOPSET` 和 `GOPSETNAME` 两个节点。  
建议先设好物性方法再添加模块，避免模块级 `OPSETNAME` 与全局设置冲突。

### 反应动力学完整流程

> ⚠️ **重要：`add_reaction` 函数创建 2D 计量系数表（COEF/COEF1）时，标签设置有时会失败。**  
> 如果计量系数写入后验证为空（`COEF\\1` 下的 Elements 为空或值为 None），需要**手动补填**。  
> 下面提供了两种方式，推荐用**方式二（手动填表）**，更可靠。

#### 方式一：用工具函数（快速，但不一定写进去）
```
add_reaction_set("R-METH", "POWERLAW")
add_reaction("R-METH", 1, reactants={"CO2":1, "H2":4}, products={"CH4":1, "H2O":2}, phase="V")
# 设动力学
aspen.find_node(r"\Data\Reactions\Reactions\R-METH\Input\PRE_EXP\1").SetValue(0, 1.0e8)
aspen.find_node(r"\Data\Reactions\Reactions\R-METH\Input\ACT_ENERGY\1").SetValue(0, 14300)
```
**运行后必须验证**计量系数是否写入：
```
coef = aspen.find_node(r"\Data\Reactions\Reactions\R-METH\Input\COEF\1")
print(f"COEF Count={coef.Elements.Count}")  # 应为 >0，且能读到组分名
```

#### 方式二：手动填表（推荐，100%可靠）

完整示例 —— 在一个已打开的模拟中添加甲烷化副反应：

```python
from aspen_mcp.tools.components import tool_add_component
from aspen_mcp.tools.reactions import *

# 1. 添加新组分（原文件有的组分不需要再加）
tool_add_component("CH4")

# 2. 创建反应集
rxns = aspen.find_node(r"\Data\Reactions\Reactions")
rxns.Elements.Add("R-METH!POWERLAW")

# 3. 设置反应类型和相态
rt = aspen.find_node(r"\Data\Reactions\Reactions\R-METH\Input\REACTYPE")
rt.Elements.InsertRow(0, 0)
rt.Elements.SetLabel(0, 0, False, "1")
aspen.find_node(r"\Data\Reactions\Reactions\R-METH\Input\REACTYPE\1").SetValue(0, "KINETIC")
aspen.find_node(r"\Data\Reactions\Reactions\R-METH\Input\PHASE\1").SetValue(0, "V")

# 4. 填充 COEF（反应物计量系数，正值 = 消耗）
coef1 = aspen.find_node(r"\Data\Reactions\Reactions\R-METH\Input\COEF\1")
for i in range(2): coef1.Elements.InsertRow(0, i)
coef1.Elements.SetLabel(0, 0, False, "CO2")
coef1.Elements.SetLabel(1, 0, False, "MIXED")
coef1.Elements.SetLabel(0, 1, False, "H2")
coef1.Elements.SetLabel(1, 1, False, "MIXED")
aspen.find_node(r"\Data\Reactions\Reactions\R-METH\Input\COEF\1\CO2\MIXED").SetValue(0, 1.0)
aspen.find_node(r"\Data\Reactions\Reactions\R-METH\Input\COEF\1\H2\MIXED").SetValue(0, 4.0)

# 5. 填充 COEF1（产物计量系数）
coef1_1 = aspen.find_node(r"\Data\Reactions\Reactions\R-METH\Input\COEF1\1")
for i in range(2): coef1_1.Elements.InsertRow(0, i)
coef1_1.Elements.SetLabel(0, 0, False, "CH4")
coef1_1.Elements.SetLabel(1, 0, False, "MIXED")
coef1_1.Elements.SetLabel(0, 1, False, "H2O")
coef1_1.Elements.SetLabel(1, 1, False, "MIXED")
aspen.find_node(r"\Data\Reactions\Reactions\R-METH\Input\COEF1\1\CH4\MIXED").SetValue(0, 1.0)
aspen.find_node(r"\Data\Reactions\Reactions\R-METH\Input\COEF1\1\H2O\MIXED").SetValue(0, 2.0)

# 6. 设动力学参数
aspen.find_node(r"\Data\Reactions\Reactions\R-METH\Input\PRE_EXP\1").SetValue(0, 1.0e8)
aspen.find_node(r"\Data\Reactions\Reactions\R-METH\Input\ACT_ENERGY\1").SetValue(0, 14300)
```

#### 分配反应集到反应器模块

RPLUG/RCSTR 通过 `RXN_ID` 表分配反应集。**必须先清空再添加**：

```python
rxn_id = aspen.find_node(r"\Data\Blocks\RPLUG\Input\RXN_ID")
els = rxn_id.Elements
# 清空所有现有行
while els.Count > 0: els.RemoveRow(0, 0)
# 添加第一个反应集
els.InsertRow(0, 0)
aspen.find_node(r"\Data\Blocks\RPLUG\Input\RXN_ID\#0").SetValue(0, "R-1")
# 添加第二个反应集（可有多个）
els.InsertRow(0, 1)
aspen.find_node(r"\Data\Blocks\RPLUG\Input\RXN_ID\#1").SetValue(0, "R-METH")
```

RXN_ID 表**不支持** `SetLabel`（会报错"该维度无标签"），直接用 `#0`, `#1` 索引路径赋值。

#### 读取反应结果

反应器出口的详细组成在 `Streams → {name} → Output → MOLEFLOW → MIXED → {组分名}`：

```python
mf = aspen.find_node(r"\Data\Streams\R-OUT\Output\MOLEFLOW")
for i in range(10):
    c = mf.Elements(0).Elements(i)  # Elements(0) = MIXED 子流
    if c.Value and float(c.Value) > 0:
        print(f"  {c.Name} = {c.Value}")
```

总摩尔流量变化（R-IN vs R-OUT）可以判断反应是否发生：若出口总摩尔数 < 入口，说明发生了分子数减少的反应。

#### 温度对反应的影响

RPLUG 的 `TYPE` 参数决定温度模式：
- `ADIABATIC` — 绝热（不设温度，由反应热决定）
- `T-SPEC` — 指定温度剖面（需要设 `TEMP`）
- `CONSTANT-T` — 恒温（注意：`CONSTANT-T` 不是有效值，实际用 `T-SPEC`）

设温度：`aspen.find_node(r"\Data\Blocks\RPLUG\Input\TEMP").SetValue(0, 350.0)`

### 批量操作加速
大批量改参数前调 `batch_refresh(True)` 关闭 GUI 刷新，改完再 `batch_refresh(False)` 恢复。

### 流股参数设置（MIXED 子节点）⚠️ 关键

**`set_param` 只能设模块参数。** 物流参数（TEMP、PRES、TOTAL 等）必须用专门的 **`set_stream_param`** 工具。

为什么需要专用工具？Aspen COM 的流股参数节点都有一个 `MIXED` 子节点：

```
Data\Streams\H2O\Input\TEMP       ← 直接 SetValue 会报 AE_UNDERSPEC
Data\Streams\H2O\Input\TEMP\MIXED  ← 必须在这里写入值
```

`set_stream_param` 自动处理这个逻辑——它尝试通过 MIXED 子节点写入，失败时回退到直接 SetValue。

✅ 正确用法：
```
set_stream_param("H2O", "TEMP", 140)
set_stream_param("H2O", "PRES", 1)
set_stream_param("H2O", "TOTAL", 200)
```

❌ 错误用法（会报 AE_UNDERSPEC）：
```
set_param("H2O", "TEMP", 140)       # set_param 走 Blocks 路径，找不到 H2O
aspen.set_value(...)  # 直接 SetValue 不行
```

---

### 运行策略：Reinit + Run2

修改参数或拓扑后，运行的正确流程是：

```
reinit()   → 清空旧计算结果和引擎缓存
run()      → 执行计算
```

或一步到位：
```
reinit_and_run()   → Reinit() + Run2(0) 组合
```

**实测验证：** `Reinit()` 可以强制 Aspen 引擎在下一步 `Run2()` 时重建计算顺序（Calculation Order）和撕裂流股（Tear Streams），不需要人工手动运行。

之前有用户反馈"必须在 GUI 中手动运行一次后才能自动运行"——这个问题的原因是：
1. 参数通过直接 `SetValue` 写入失败（AE_UNDERSPEC），实际参数没写入
2. 缺少 `Reinit()` 步骤，旧缓存与修改后的拓扑不匹配

**解决这两个问题后，模拟可以完全通过 COM 自动化运行，无需人工干预。**

---

### 启动策略：`new_simulation()` 纯净模板 ✅

`new_simulation()` 不再使用 `InitNew()`（在 MCP 长进程中 COM 引用不稳定），而是：
1. `close_file()`（安全关闭已打开文件）
2. 复制纯净空白模板到 `%TEMP%`（带 PID 后缀，唯一文件名）
3. `open_file()` 打开副本

**模板初始状态：**
- **单元制**：METCBAR  
- **组分**：none（0 组分，通过 `add_component` 添加）
- **物性方法**：PENG-ROB（可用 `set_property_method` 更改）
- **拓扑**：空（无模块、无物流）

```
new_simulation()       → close_file + 复制模板 + open_file
add_component(...)     → 添加组分
add_block / connect    → 搭建流程拓扑
reinit_and_run()       → 运行
```

> ⚠️ **首次使用 `new_simulation()` 前**：如果已有文件打开，工具会自动关闭后再创建空白模拟。

---

### COM 单例限制
MCP 服务器持有一个全局 Aspen Plus COM 会话。每次重启 Reasonix（或 MCP 插件）会丢失之前的所有状态，需要重新 `open_file` 或 `new_simulation`。  
同一进程内的文件切换（close + open_file / new_simulation）可正常进行，不受影响。

### 模块参数文档
项目 `docs/blocks/` 目录下有 70 种 Aspen Plus 模块的详细参数文档（含 Input 路径、Output 路径、典型设置、注意事项），来源于 Aspen Plus v15 官方模板。

## Requirements

- Windows（COM 自动化依赖）
- Aspen Plus v15 已安装（GUI 41.0 / 40.0）
- Python 3.10+

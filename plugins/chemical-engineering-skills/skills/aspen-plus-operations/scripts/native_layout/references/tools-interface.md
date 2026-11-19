# 排布tools接口与原生图形格式

文字许可：CC BY 4.0。代码接口以`pfs_layout.py --help`和各子命令`--help`为准。本文将图形变换、原生文件操作、运行验收分开；经验库候选不自动安装MCP服务或改变用户模型。

## 1. 工具能力与调用顺序

先使用当前可见的Aspen工具查询/导出或已有owned runtime。MCP的open/run/get/set、place_block/place_stream能力不意味着提供位置、方向或折点编辑；实际工具schema未暴露图形字段时，不发明`SetPosition`之类接口。走已验证的Export18图形文本桥，完成后用原生复开结果核对。

本工具包的三项离线能力为：inspect读取当前原生图形与canonical端点；apply把显式JSON布局计划写成新输入；verify比较布局、完整真实物理输入和端点。具体CLI参数、plan字段和成功/拒绝结果见README与程序帮助。CLI只读调用者明确给出的文件，不扫描整个机器、不执行INP内容或提交者命令。

已有专业层的原生操作接口：

| 目的 | COM/文件接口 | 核验对象 |
|---|---|---|
| 打开APW文档 | `InitFromFile2(path)` | 本机V14已实证文档入口；与Archive入口分开 |
| 打开BKP备份 | `InitFromArchive2(path)` | 保护副本身份、打开方法、版本 |
| 导入含图形INP | `InitFromFile2(path)` | 完整原生config/icon/PFS必须保留；错误不直接归咎许可 |
| 取得真实模型卡 | `Export(4, path)` | 所有非comment卡，包括PFS后出现的报告卡 |
| 取得含图形文本 | `Export(18, path)` | At、Scale/Modifier、Label、ROUTE、原生header/config |
| 输出备份 | `Export(1, path)` | 存在、非空、后续精确文件复开 |
| 保存文档 | `SaveAs(new_apw_path)` | 新文件身份与同名依赖实际需求 |
| 复开/无编辑运行 | 现有runtime与严格审核脚本 | 图面与运行/产品/设备门分别判断 |

COM会话、锁和阶段超时由已有operations runtime/supervisor负责，不另造全机进程终止器。不接管用户已打开的会话，不编辑二进制内部存储。只在Windows且软件/依赖可用时走真实原生操作；离线测试不声称完成了这一步。

## 2. 朝向、缩放和$D

PFS全局坐标x向右、y向上。对一个未缩放、未旋转的native anchor `c`，显示端点为：

`p = a + s M c + D`

其中`a`是BLOCK At、`s`是Scale、`M`是Modifier变换、`D`是流股显示附着点的全局偏移。恢复canonical端点时，先减At与D，再除Scale，最后乘M的逆矩阵。忽略D再推矩阵，会把手工移动的附着点误认为原图标端口。

本机V14的独立样例坐标核查得到以下映射：

| Modifier | 变换 | 矩阵 |
|---|---|---|
| 0 | 原向 | `[[1,0],[0,1]]` |
| 1 | 左右镜像 | `[[-1,0],[0,1]]` |
| 2 | 上下镜像 | `[[1,0],[0,-1]]` |
| 3 | 逆时针90° | `[[0,-1],[1,0]]` |
| 4 | 顺时针90° | `[[0,1],[-1,0]]` |
| 5 | 180° | `[[-1,0],[0,-1]]` |
| 6 | 反对角镜像 | `[[0,-1],[-1,0]]` |
| 7 | 主对角镜像 | `[[0,1],[1,0]]` |

这不是所有版本的盲用保证。canonical anchor从同案/同图标的真实原生导出提取，不能把其它图标或示例的端口坐标硬编码成默认值。多入口/多出口即使属于同一角色，也可能有不同的native anchor，不压成一个公共点。

ROUTE 0对应源端，ROUTE 1对应目的端；两支在存储中都由中间anchor走向各自端点，源支需反转才是整体流向。`t l/r/u/d`是图形接近方向，不单凭它决定物理端口角色或Modifier。方向随实际路径和图形端点核验。

官方帮助允许移动流股显示连接位置而保持当前物理port。非零偏移的本机实证语法为`t ...`后接`$ D dx dy`、`$ C 0.000000 0.0`、`$ $ 0.0 0.0`。新显示位置不是新增真实port，不可据此增加流股连接。偏移是全局坐标，不应再乘Scale。零偏移则保留对应原生固定端点记录。

## 3. 文件桥中容易丢失的内容

Export18可能先给PFSVData，再给PFS/config/icon定义；不能只截PFS之前的文本就丢掉后方定义。`STREAM-REPOR`等真实卡也可能在PFS之后，物理一致性比较应覆盖全文件真实卡，而不是只比较前缀。

Export18特有的`E_LINK`边界标记不能未经验证地当普通输入卡拼回。仅在识别到当前已支持的完整导出结构、与同案Export4全量真实卡一致后，按已验证导入格式处理；未知结构明确拒绝。不能泛删所有包含该词的行，不能用忽略差异来掩盖物理变更。

保留所支持格式的完整config、图标ID与块/流股集合，输出新路径；不修改APW/BKP二进制。其它图元、注释对象或非空图层若尚不支持，停止受影响变换，不把它们静默裁掉。只保留源文件哈希不能证明图面未丢。

## 4. 保存、复开与包内验证

原生导入和导出调用返回后检查实际输出文件存在且非空；结果回执有error就失败，即使supervisor显示进程已结束。DXF/PDF导出若没有产物，状态保持未证，不能以调用返回代替图像。

先核候选的完整物理卡，再核原生读回的模块集合、ICON、位置、方向、Scale、Label、所有流股TYPE/anchor/端点/折点/偏移。检查路由形状、共线重叠、跨线是否有实际接点，以及管线/文字穿过设备。程序图只能展示坐标预览，不能冒称软件界面截图或原生字体目视核验。

核对SIZE与LEGEND VIEWPORT等图框字段；对象坐标相同而视窗裁掉设备，仍是布局未保持。真实卡的数值拼写等价必须精确比较，不借Decimal上下文或浮点舍入忽略小变化；引号内字符串保持原文，图形比较阈值不延伸到模型卡。

精确用户路径的APW/BKP分别复开；用户要压缩包时按明确成员集打包，独立解压，先逐文件核哈希，再按声称范围重新打开/运行并读回PFS。不要只核压缩包CRC或旧目录回执。是否需要ADS/DEF等依赖，按实际格式与复开证据判断；无证据不把它们缺失归为根因。

运行验收继续由操作 owner 核实运行完成、完整且无实际错警的 Control Panel/history，并由相应专业核验产品和设备。原生 Summary 用于诊断或按显式要求证明全零计数。布局操作须保留求解容差。

## 5. 来源定位与后续接入

机械机制以合法本机Aspen Plus V14 Help的以下主题核查：初始化方法、Input Files (.inp)、Rotating Icons、Moving Stream Connection Locations、Saving an Aspen Plus Document、Saving a Backup File、Compound Document Files (.apwz)。这里仅列主题，不附商业正文或样例原件。

候选接入点为现有aspen-plus-operations的`case-io`/`delivery-qa`/原生PFD触发；上层压力/PFD文档技能只作路由，不复制另一套脚本。接入后以短请求进行独立forward-test，确认无需使用者再给“修改Modifier/Export18/$D”的提示词即可找到本能力。This relocated helper has no nested skill discovery metadata. The parent operations skill owns routing; source publication does not prove local installation or native capability.

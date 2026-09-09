# UG10-CH33 Detail Operation Index - 第33章 泄压计算

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH33-D001

PDF page: 480; original JSON pointer: `/5732`

l 根据由用户规定的明火或热量输入来动态模拟泄压容器

## UG10-CH33-D002

PDF page: 480; original JSON pointer: `/5733`

l 规定何时停止模拟 停止准则

## UG10-CH33-D003

PDF page: 480; original JSON pointer: `/5734`

l 规定过压因子和管压降原则

## UG10-CH33-D004

PDF page: 480; original JSON pointer: `/5735`

Emergency Relief System DIERS Users Group(紧急泄压系统设计院)所开发的技术创建的

## UG10-CH33-D005

PDF page: 480; original JSON pointer: `/5736`

程序将计算出容器和管子的压力分布 另外 你还必须做如下规定

## UG10-CH33-D006

PDF page: 480; original JSON pointer: `/5737`

l 被保护设备尺寸和相连接的管嘴 如果存在 的尺寸

## UG10-CH33-D007

PDF page: 480; original JSON pointer: `/5738`

每个 Pressure Relief 模块模拟一个方案和一个容器 在 ASPEN PLUS运行中 要模拟多

## UG10-CH33-D008

PDF page: 480; original JSON pointer: `/5739`

个方案或高压容器 模拟时就必须包括多个 Pressure Relief 模块 Pressure Relief 模块不是模

## UG10-CH33-D009

PDF page: 480; original JSON pointer: `/5740`

Pressure Relief 分析规定的方案和报告

## UG10-CH33-D010

PDF page: 480; original JSON pointer: `/5741`

l 结果分布 温度 压力 气体馏分

## UG10-CH33-D011

PDF page: 480; original JSON pointer: `/5742`

l 系统是否满足你选的设计规定或适用标准 如 ASME 的规定

## UG10-CH33-D012

PDF page: 480; original JSON pointer: `/5743`

1. 从 Data 数据 菜单中 单击 Flowsheeting Options 流程 然后单击 Pres-Relief

## UG10-CH33-D013

PDF page: 480; original JSON pointer: `/5744`

2. 在 Pressure Relief Object Manager 泄压对象管理器 中 单击 New 新的

## UG10-CH33-D014

PDF page: 480; original JSON pointer: `/5745`

3. 在 Create New ID 生成新的标识号 对话框 输入 ID 标识号 或使用缺省的 ID

## UG10-CH33-D015

PDF page: 480; original JSON pointer: `/5746`

4. 单击 OK 关于完成 Pressure Relief 规定的信息 参见本章余下各节

## UG10-CH33-D016

PDF page: 481; original JSON pointer: `/5748`

Pressure Relief 方案是通过泄压系统中放空的方案 有四种类型的一般方案可以选择

## UG10-CH33-D017

PDF page: 481; original JSON pointer: `/5749`

l 动态运行明火加热的容器

## UG10-CH33-D018

PDF page: 481; original JSON pointer: `/5750`

l 动态运行规定输入热量的容器

## UG10-CH33-D019

PDF page: 481; original JSON pointer: `/5751`

个阀及管件 在本方案中 泄压模型通过规定的系统计算稳态流率

## UG10-CH33-D020

PDF page: 481; original JSON pointer: `/5752`

l 泄压设备必须是一个 Process Safety Valve PSV (安全阀)或一个 Process Safety

## UG10-CH33-D021

PDF page: 481; original JSON pointer: `/5753`

动态运行明火加热容器方案

## UG10-CH33-D022

PDF page: 481; original JSON pointer: `/5754`

所选的明火标准决定用哪个规则计算明火方案系数如容器浸湿面积 输入能量和可信因

## UG10-CH33-D023

PDF page: 481; original JSON pointer: `/5755`

Pressure Relief 假定在整个放空过程中 计算出的能量输入是常数 如果合适的话 你

## UG10-CH33-D024

PDF page: 481; original JSON pointer: `/5756`

可以分别规定对排水 喷淋和绝热的可信因子以减少能量输入 或者你也可以规定一个全局

## UG10-CH33-D025

PDF page: 481; original JSON pointer: `/5757`

动态运行有规定热流输入容器方案

## UG10-CH33-D026

PDF page: 481; original JSON pointer: `/5758`

热量输入方案除以下两点外 其它与明火方案类似

## UG10-CH33-D027

PDF page: 481; original JSON pointer: `/5759`

在整个事件中没有中断时间 指定的热流可以是来自恒定温度源的常数或关于时间的函

## UG10-CH33-D028

PDF page: 481; original JSON pointer: `/5760`

l 通过选择 Constant Duty 恒定负荷 热量输入方法 来模拟整个电加热炉或其它恒

## UG10-CH33-D029

PDF page: 481; original JSON pointer: `/5761`

l 通过使用 Constant Duty 恒定负荷 热量输入方法和规定热负荷的值为 0 来模拟

## UG10-CH33-D030

PDF page: 481; original JSON pointer: `/5762`

l 通过选择 Calculated from the Heat Soure(由热源方法所计算的)和给出源温度 热传

## UG10-CH33-D031

PDF page: 481; original JSON pointer: `/5763`

递系数及表面积 来模拟由一个热源比如换热所得到的热量输入

## UG10-CH33-D032

PDF page: 482; original JSON pointer: `/5765`

1 在 Pressure Relief Setup Scenario 泄压设置方案 页上 可选四个泄压方案中的一 个

## UG10-CH33-D033

PDF page: 482; original JSON pointer: `/5766`

2 从 Capacity 选项列表 选择 Code 或 Actual 选择该项 在下述能力下运行模型 含义 该项适用于 标准 缺省 标准能力 由美国的 ASME 标准 所规定泄压设备的排 放能力 如果给出安全阀或防 爆板尺寸 确定选择方 案是很充分的 实际值 实际能力 给出泄压系统流出的 最优值 而不给出排 放能力 检查入口或尾管段是 否满足标准所要求的

## UG10-CH33-D034

PDF page: 482; original JSON pointer: `/5767`

3. 规定 Vent Discharge Pressure 排放压力 你必须为所有泄压方案规定排放压力 如果在泄压设备后面有尾管段 排放压力参考管子末端的压力 也就是明火头背压 的大气压

## UG10-CH33-D035

PDF page: 482; original JSON pointer: `/5768`

4. 如果你选择了稳态流方案 就输入 Estimated Flow Rate 估计流率 你输入的值 作为起点用来确定泄压系统或安全阀的额定值 你可以以质量 摩尔或标准液相体 积基准输入该流股 你在 Set Scenario 设置方案 页上所选的方案决定剩下的哪个 Pressure Relief 表和页是 你需要用来定义系统的 所需要的表并不完全显示在 Data Browser Forms 数据浏览器窗口 的左屏中 并且那些不适用与你所选方案的页不能激活 为稳态方案规 定入口物流

## UG10-CH33-D036

PDF page: 482; original JSON pointer: `/5769`

对于安全阀或泄压系统的稳态方案核算 你必须给出进入安全阀或系统的物流组成

## UG10-CH33-D037

PDF page: 483; original JSON pointer: `/5771`

l 通过参考流程的一股物流来规定一股物流的组成或容器

## UG10-CH33-D038

PDF page: 483; original JSON pointer: `/5772`

l 在泄压模块中直接规定物流组成

## UG10-CH33-D039

PDF page: 483; original JSON pointer: `/5773`

这些规定在 Pressure Relief Setup(泄压设置)窗口的 Stream 物流 页上输入

## UG10-CH33-D040

PDF page: 483; original JSON pointer: `/5774`

通过参考流程的一股物流来规定一股物流的组成或容器

## UG10-CH33-D041

PDF page: 483; original JSON pointer: `/5775`

1. 从 Pressure Relief Stream 窗口中选择 Stream 标签

## UG10-CH33-D042

PDF page: 483; original JSON pointer: `/5776`

2. 在 Stream 页上 单击 Reference Stream Composition 复选框

## UG10-CH33-D043

PDF page: 483; original JSON pointer: `/5777`

3. 在该复选框下面区域 选择所需要的物流 在泄压模块中直接规定物流组成

## UG10-CH33-D044

PDF page: 483; original JSON pointer: `/5778`

1. 从 Pressure Relief Setup 窗口选 Stream 标签来打开页

## UG10-CH33-D045

PDF page: 483; original JSON pointer: `/5779`

2. 在 Stream 页的 Stream Composition框内 从 Basic 列表中选择一组成基准

## UG10-CH33-D046

PDF page: 483; original JSON pointer: `/5780`

3. 在 Fraction 区域物流中的组分旁边输入组分分率 另外对于组成 你必须规定入口物流的热力学条件 包括规定三个变量的组合 温度 压力和摩尔气相分率 这些值可以在 Stream 页上直接输入 或者如果你已经参考了物流组 成 可以通过参考得到 从流程物流参考一个入口物流状态变量

## UG10-CH33-D047

PDF page: 483; original JSON pointer: `/5781`

1. 在 Stream 页上 先确保你已检查过 Reference Stream Composition 参考物流组成 复选框 如果你没有参考组成 你就不能参考物流状态变量

## UG10-CH33-D048

PDF page: 483; original JSON pointer: `/5782`

2. 在 Stream 页的 Reference Stream 窗口中 单击复选框指出你想参考的物流变量

## UG10-CH33-D049

PDF page: 483; original JSON pointer: `/5783`

直接在泄压模块中为入口物流规定状态变量

## UG10-CH33-D050

PDF page: 483; original JSON pointer: `/5784`

1. 在 Stream 页上 在 User Flash Specifications 用户闪蒸规定 窗口的一个区域当中 输入一个值

## UG10-CH33-D051

PDF page: 483; original JSON pointer: `/5785`

2. 为输入值选择相应的单元 如果你愿意的话 可以参考一个状态变量或直接输入

## UG10-CH33-D052

PDF page: 484; original JSON pointer: `/5787`

为动态方案规定初始容器状态

## UG10-CH33-D053

PDF page: 484; original JSON pointer: `/5788`

对于明火或热量输入的动态方案 你必须在 Pressure Relief Setup 窗口的 Vessel Contents

## UG10-CH33-D054

PDF page: 484; original JSON pointer: `/5789`

容器的初始条件可以在如下项中规定

## UG10-CH33-D055

PDF page: 484; original JSON pointer: `/5790`

对于所有泄压模块 必须规定容器的组成 而剩下的规定可以用以下三项的组合来进行

## UG10-CH33-D056

PDF page: 484; original JSON pointer: `/5791`

泄压模块使用该信息和你在 Pressure Relief ReliefDevice 泄压设备 窗口中定义的体积

## UG10-CH33-D057

PDF page: 484; original JSON pointer: `/5792`

l 在 Vessel Contents 容器容积 页上直接规定值

## UG10-CH33-D058

PDF page: 484; original JSON pointer: `/5793`

通过从流程中参考一股物流来定义容器的组成

## UG10-CH33-D059

PDF page: 484; original JSON pointer: `/5794`

1. 从 Pressure Relief Setup 窗口中选择 Vessel Contents 标签

## UG10-CH33-D060

PDF page: 484; original JSON pointer: `/5795`

2. 在 Vessel Contents 页上单击 Reference Stream Composition 复选框

## UG10-CH33-D061

PDF page: 484; original JSON pointer: `/5796`

3. 在复选框下面区域 选择所需要的物流 ID 在泄压模块中直接规定物流组成

## UG10-CH33-D062

PDF page: 484; original JSON pointer: `/5797`

2. 在 Vessel Contents 页的 Vessel Composition框上 从 Basic 列表中选择组成基准

## UG10-CH33-D063

PDF page: 484; original JSON pointer: `/5798`

3. 在 Fraction 分率 区域每个物流组分下面输入组分分率 为动态方案定义热力学条件 定义热力学条件 你必须规定状态变量温度 压力或气相分率的组合定义 其组合依据 你是否规定 fillage和 pad 气体组分 在规定温度 压力和气体摩尔分率时 你也可以

## UG10-CH33-D064

PDF page: 485; original JSON pointer: `/5800`

l 在 Vessel Contents 页上直接输入值

## UG10-CH33-D065

PDF page: 485; original JSON pointer: `/5801`

从流程物流参考容器状态变量

## UG10-CH33-D066

PDF page: 485; original JSON pointer: `/5802`

1. 在 Vessel Contents 页上 先确保你已检查过 Reference Stream Composition 复选框 如果你没有参考组成 你就不能参考物流状态变量

## UG10-CH33-D067

PDF page: 485; original JSON pointer: `/5803`

2. 在 Vessel Contents 页的 Reference Stream 窗口上 单击复选框表明你想参考哪个物 流变量

## UG10-CH33-D068

PDF page: 485; original JSON pointer: `/5804`

在 Vessel Contents 页上直接规定容器的状态变量

## UG10-CH33-D069

PDF page: 485; original JSON pointer: `/5805`

1. 在 Vessel Contents 页上的 User Flash Specifications 框的一个区域中输入一个值

## UG10-CH33-D070

PDF page: 485; original JSON pointer: `/5806`

2. 为所输入值选择相应的单元 如果你愿意 可以参考一个状态变量 并且直接输入另一个变量 Fillage Fillage是充满液体容器的体积初始分率 液体藏量 fillage必须大于 0 且比 0.994 小 如果你规定 fillage 但不规定 pad-gas 充压气体 组成 温度或压力的规定将用来确定 初始量的泡点 纯组分的蒸汽压 规定 fillage

## UG10-CH33-D071

PDF page: 485; original JSON pointer: `/5807`

Ø 在 Vessel Contents 页上的在 Vessel Fillage窗口中的 Fillage区域上输入一个值

## UG10-CH33-D072

PDF page: 485; original JSON pointer: `/5808`

Pad Gas Component 表示的组分用来把压力提高到规定的水平 例如 在烃贮罐中经常

## UG10-CH33-D073

PDF page: 485; original JSON pointer: `/5809`

规定 Pad 充压气体组成

## UG10-CH33-D074

PDF page: 485; original JSON pointer: `/5810`

Ø 在 Vessel Contents 页上 从 Vessel Fillage窗口的 Pad 充压 Gas Component 列表

## UG10-CH33-D075

PDF page: 485; original JSON pointer: `/5811`

使用 Pressure Relief Setup 窗口的 Rules 规则 页来定义规则 关于

## UG10-CH33-D076

PDF page: 486; original JSON pointer: `/5813`

除了最大容器压力的限制外 只有选择了 PSV 安全阀 或用于气相 两相的 PSV 与

## UG10-CH33-D077

PDF page: 486; original JSON pointer: `/5814`

Relief(泄压)将产生警告 然而 许多设计或安全分析说明包括这些规则在内 都应依据你自

## UG10-CH33-D078

PDF page: 486; original JSON pointer: `/5815`

对于明火或有热量输入的动态方案 你必须给出最大容器压力 该值在 User Specified

## UG10-CH33-D079

PDF page: 486; original JSON pointer: `/5816`

用户规定 区域里可以表示成绝对值 或者表示为在 Pressure Relief Dynamic Input 泄压

## UG10-CH33-D080

PDF page: 486; original JSON pointer: `/5817`

动态输入 窗口 Design Parameters 设计参数 页上输入的最大许可工作压力 MAWP 的

## UG10-CH33-D081

PDF page: 486; original JSON pointer: `/5818`

在使用 Percent of MAWP规定时 MAWP在输入 ASPEN PLUS 使用的百分数前转换成

## UG10-CH33-D082

PDF page: 486; original JSON pointer: `/5819`

用该区域输入最大入口管压力损失作为微分设定压力的百分数 如果没达到超压 10%

## UG10-CH33-D083

PDF page: 486; original JSON pointer: `/5820`

就按超压 10%或最大压力来计算 如果入口管线的总压力损失大于或等于规定的设定压力的

## UG10-CH33-D084

PDF page: 486; original JSON pointer: `/5821`

百分数 ASPEN PLUS 就产生警告 该规定值通常为 3 缺省 且该规则一般称为 3%

## UG10-CH33-D085

PDF page: 487; original JSON pointer: `/5823`

使用该窗口来规定用于设置许可尾管压力损失的方法 你可以做如下三项的一项

## UG10-CH33-D086

PDF page: 487; original JSON pointer: `/5824`

l 输入表示成微分设定压力的百分数的最大压力损失 所谓 X% Rule

## UG10-CH33-D087

PDF page: 487; original JSON pointer: `/5825`

l 规定 Pressure Relief 不模拟尾管压力损失

## UG10-CH33-D088

PDF page: 487; original JSON pointer: `/5826`

警告 在使用 X%规则时 如果阀后面的压力等于或大于阀微分设定压力的 X% ASPEN

## UG10-CH33-D089

PDF page: 487; original JSON pointer: `/5827`

平衡导向器或者排空导向器的自动调幅阀 X=40 的 X%规则

## UG10-CH33-D090

PDF page: 487; original JSON pointer: `/5828`

你可以规定在背压变化时 微分设定压力 DSP 是否变化 即阀是否平衡或放空

## UG10-CH33-D091

PDF page: 487; original JSON pointer: `/5829`

平衡导向器或者排空导向器的自动调幅阀 No

## UG10-CH33-D092

PDF page: 487; original JSON pointer: `/5830`

l 最多为连接安全设备的容器口入口管段的两个长度

## UG10-CH33-D093

PDF page: 487; original JSON pointer: `/5831`

在进行 Pressure Relief 计算时 不必包括所有的这些部分 但模块必须至少包括一个管

## UG10-CH33-D094

PDF page: 487; original JSON pointer: `/5832`

用 ReliefDivice 泄压设备 窗口的 Configuration 结构 页来规定

## UG10-CH33-D095

PDF page: 487; original JSON pointer: `/5833`

l 在动态运行时 容器口和管子是否应忽略

## UG10-CH33-D096

PDF page: 487; original JSON pointer: `/5834`

如果你选择 Open Vent Pipe 打开放空管 作为设备 那么

## UG10-CH33-D097

PDF page: 487; original JSON pointer: `/5835`

l 必须规定一个容器口 入口管或尾管

## UG10-CH33-D098

PDF page: 487; original JSON pointer: `/5836`

对于 Relief Valve方案的 Steady State Flow Rating 稳态物流核算 , 放空系统只包括一

## UG10-CH33-D099

PDF page: 488; original JSON pointer: `/5838`

l 打开的放空管 管段或容器口

## UG10-CH33-D100

PDF page: 488; original JSON pointer: `/5839`

在 Relief Divice窗口的 Configuration页上 通过单击上面的其中一个选项来选择你所希

## UG10-CH33-D101

PDF page: 488; original JSON pointer: `/5840`

望模拟的泄压设备类型 缺省的泄压设备是安全阀

## UG10-CH33-D102

PDF page: 488; original JSON pointer: `/5841`

依据你在 Relief Divice窗口的 Configuration页上所选的泄压设备类型 在 Relief Divice

## UG10-CH33-D103

PDF page: 488; original JSON pointer: `/5842`

表会有一个或多个附加页 标签 为进一步规定设备而变可激活的 例如 如果你在

## UG10-CH33-D104

PDF page: 488; original JSON pointer: `/5843`

Configuration页上选择 Rupture Disk 作为你的泄压设备 Rupture Disk 标签将被激活并显示一

## UG10-CH33-D105

PDF page: 488; original JSON pointer: `/5844`

个未结束符号来表示在本页上需要做进一步规定

## UG10-CH33-D106

PDF page: 488; original JSON pointer: `/5845`

l 在泄压计算中需要的所有机械规定和可信因子

## UG10-CH33-D107

PDF page: 488; original JSON pointer: `/5846`

你可以通过修改或增加阀 圆盘和放空特性表来修改 ASPEN PLUS 更详细的信息 参

## UG10-CH33-D108

PDF page: 488; original JSON pointer: `/5847`

l 输入你自己的规定和系数

## UG10-CH33-D109

PDF page: 488; original JSON pointer: `/5848`

对于液体阀 你可以规定全提升超压系数 它允许你模拟一些老式的阀 但当超压达到

## UG10-CH33-D110

PDF page: 488; original JSON pointer: `/5849`

如果你选择 Safety Relief Valve 或 Relief Valve/Rupture Disk Combination 安全阀/安全阀 与防爆板组合 作为泄压设备的类型 你必须完成 Safety Valve 页的规定在模拟中使用的安 全阀 PSV 在 Manufacturer’s Tables 厂商表 框中定义阀 一旦选择了 Type 类 型 ,Manufacturer 厂商 Series 序列号 和 Nominal Diameter 公称直径 , 阀就被唯 一的说明了 并且 ASPEN PLUS 在 Valve Parameters 框中填入如下数据

## UG10-CH33-D111

PDF page: 489; original JSON pointer: `/5851`

如果你想使用在 Manufacturer’s Tables 中没有列出的阀 则必须为在上面列出的 Valve Parameters 阀参数 键入值 如果你从表中选择了一个阀 那么将替换掉 Valve Parameters Manufacturer’s Tables 区域变成空白 为完成该表 要为阀输入微分设定点 它表明阀的压差对阀的启动是必须的 防爆板 如果你选择 Rupture Disk 防爆板 或 Rel ief Valve/Rupture Disk Combination 安全阀/

## UG10-CH33-D112

PDF page: 489; original JSON pointer: `/5852`

安全阀与防爆板组合 作为泄压设备的类型 你必须用 Rupture Disk 页来规定在模拟中使用

## UG10-CH33-D113

PDF page: 489; original JSON pointer: `/5853`

的防爆板 PSD 在 Manufacturer’s Tables 框中定义防爆板 一旦选择了 Manufacturer 厂

## UG10-CH33-D114

PDF page: 489; original JSON pointer: `/5854`

如果你想使用在 Manufacturer’s Tables 中没有列出的 PSD 则必须为在上面列出的参数 键入值 如果你从表中选择了一个防爆板 那么将替换掉所有防爆板参数 Manufacturer’s Tables 区域变成空白 为完成该表 需为防爆板输入微分设定点 它表明通过防爆板的压差对防爆板的破裂是 必须的 在实际负荷的运行中 用当量长度与直径比 L/D 把防爆板模拟成一个管子 如果没 有实验数据 在圆盘直径大于 2 英尺 5.08 cm 时就用 L/D=8 在直径等于或小于 2 英尺时

## UG10-CH33-D115

PDF page: 489; original JSON pointer: `/5855`

就用 15 在标准负荷运行中 用合适的排放系数把防爆板模拟为一个理想的管嘴 对于不

## UG10-CH33-D116

PDF page: 489; original JSON pointer: `/5856`

如果你选择 Emergency Relief Vent 紧急放空 作为泄压设备类型 则必须完成 Relief Vent 页来规定模拟中使用的紧急放空 ERV 在 Manufacturer’s Tables 窗口中定义放空 一旦 选择了 Manufacturer Style 和 Nominal Diameter, PSD 就被唯一的说明了 并且 ASPEN PLUS 将填入如下数据

## UG10-CH33-D117

PDF page: 489; original JSON pointer: `/5857`

l Recommended Setpoint(推荐的设定点)

## UG10-CH33-D118

PDF page: 489; original JSON pointer: `/5858`

为完成该表 需为放空输入微分设定点 它表明通过放空的压差对放空的启动是必须的

## UG10-CH33-D119

PDF page: 489; original JSON pointer: `/5859`

如果你想使用在 Manufacturer’s Tables 中没有列出的 ERV 则必须在 Vent Parameters 窗口中为直径和微分设定点输入值 如果你从表中选择了一个 ERV 那么将替换掉放空参数 Manufacturer’s Tables 区域全变成空白 通过用放空超压因子计算来模拟 ERVs 的逐渐打开直到全开 规定容器口 容器口是连接容器与入口管或者如果没有入口管就连接泄压设备的一段管段 如果你选 择了规定容器口 就要在 ReliefDevice 泄压设备 表的 Vessel Neck 容器口 页上输入相 关信息 说明容器口需要如下数据

## UG10-CH33-D120

PDF page: 489; original JSON pointer: `/5860`

下表列出 Vessel Neck 页的规定选项和与其相对应的缺省项

## UG10-CH33-D121

PDF page: 490; original JSON pointer: `/5862`

对于入口管段 用 Pressure Relief InletPipes 泄压入口管 表来描述连接容器口与泄压

## UG10-CH33-D122

PDF page: 490; original JSON pointer: `/5863`

Pipe 规定管子尺寸和可选管子参数

## UG10-CH33-D123

PDF page: 490; original JSON pointer: `/5864`

Thermal 规定与环境进行能量传递的热传递参数

## UG10-CH33-D124

PDF page: 490; original JSON pointer: `/5865`

Pipe 页对入口管的每一管段都是必须的

## UG10-CH33-D125

PDF page: 490; original JSON pointer: `/5866`

其余页用于可选规定的输入 每个页都在下面进行了说明

## UG10-CH33-D126

PDF page: 490; original JSON pointer: `/5867`

用 Pipe 页为每段管子输入管子直径和长度 对每个管段来说 管子直径和长度是必须

## UG10-CH33-D127

PDF page: 490; original JSON pointer: `/5868`

你可以通过增加或修改管子规格表来修改 ASPEN PLUS 关于更详细的信息 参见

## UG10-CH33-D128

PDF page: 490; original JSON pointer: `/5869`

从内置 Pipe Schedule Tables 管子规格表 选择管子直径

## UG10-CH33-D129

PDF page: 490; original JSON pointer: `/5870`

1. Pipe 页上部 从 Pipe Section 管段 区域选择一段管子

## UG10-CH33-D130

PDF page: 490; original JSON pointer: `/5871`

2. 在 Pipe Schedule 管子规格 窗口的 Material 材料 列表中选择管子的材质 可 用的材质包括碳钢和不锈钢

## UG10-CH33-D131

PDF page: 491; original JSON pointer: `/5873`

3. 在 Schedule 区域选择管子规格

## UG10-CH33-D132

PDF page: 491; original JSON pointer: `/5874`

4. 从 Nominal Diameter区域选择管子公称直径 经过以上步骤管子就被确定了 并且 Inner Diameter 内径 在 Pipe Parameters 页显示 如果你想使用 Pipe Schedule Tables没列出的管子 你必须在 Pipe Parameters 窗口的 Inner Diameter 区域输入管子的内径 注意如果你从表中选择一管子 那么就将替换掉内径 Pipe Schedule Tables 区域将变为空白

## UG10-CH33-D133

PDF page: 491; original JSON pointer: `/5875`

在 Pipe 页上可选的输入项包括

## UG10-CH33-D134

PDF page: 491; original JSON pointer: `/5876`

l Pipe Rise(标高改变)

## UG10-CH33-D135

PDF page: 491; original JSON pointer: `/5877`

如果你没有为这些可选输入项输入值 可以使用下面的缺省值 规定项 缺省值 Roundness 圆度 0.00015ft Pipe Rise 管子升高 0 Reducer K 缩小系数 0.04 Expander K 扩大系数 0.04 管件 用 Fittings 管件 页来说明在入口管段所包括的管件 下面的管件类型可以规定

## UG10-CH33-D136

PDF page: 491; original JSON pointer: `/5878`

另外 综合流动阻力可以通过输入相当于阻力的管子直径来确定

## UG10-CH33-D137

PDF page: 491; original JSON pointer: `/5879`

使用 Valves页规定在管段使用的通用阀 在页的顶部 从 Manufacturer’s Tab les 窗口中

## UG10-CH33-D138

PDF page: 491; original JSON pointer: `/5880`

选择一个阀 一旦选择了 Manufacturer 厂家 Style 类型 和 Nominal Diameter 公称

## UG10-CH33-D139

PDF page: 491; original JSON pointer: `/5881`

直径 ,阀就被唯一确定了 并且 ASPEN PLUS 在 Valves Parameters 窗口中输入下面数据

## UG10-CH33-D140

PDF page: 491; original JSON pointer: `/5882`

如果你想使用在 Manufacturer’s Tables 中没有列出的阀 你必须为上面列出的参数输入 值 如果你从表中选择了一个阀 那么将替换掉阀参数 Manufacturer’s Tables 区域全变成 空白 你也可以为在管段所包含的控制阀规定阀常数 可以在 Control Valves 控制阀 窗口 的 Valves Constant 阀内容 区域输入一个值 热量 如果你想模拟管子和环境间的热传递 可用 Thermal 热量 页来规定能量平衡参数

## UG10-CH33-D141

PDF page: 492; original JSON pointer: `/5884`

对于尾管段 用 Pressure Rlief TailPipes 泄压尾管 表来说明连接泄压设备和排放点的

## UG10-CH33-D142

PDF page: 492; original JSON pointer: `/5885`

能与 InletPipes 表相同 关于规定尾管的更详细信息 请参见前面的规定入口管段

## UG10-CH33-D143

PDF page: 492; original JSON pointer: `/5886`

用 DynamicInput 动态输入 窗口来说明与动态方案相关的紧急事件 必需数据包括

## UG10-CH33-D144

PDF page: 492; original JSON pointer: `/5887`

下面列出 DynamicInput 窗口中所包含的页

## UG10-CH33-D145

PDF page: 492; original JSON pointer: `/5888`

对于所有的动态方案 必须完成 Vessel和 Design Parameters 页 对于热输入方案 Heat

## UG10-CH33-D146

PDF page: 492; original JSON pointer: `/5889`

用该页通过以下规定来说明发生紧急事件的容器

## UG10-CH33-D147

PDF page: 492; original JSON pointer: `/5890`

l User Specified 用户规定

## UG10-CH33-D148

PDF page: 492; original JSON pointer: `/5891`

1. 在 Pressure Relief DynamicInput Vessel页上 从 Vessel Description 容器描述 窗 口的 Vessel Type 容器类型 列表中选择一容器类型

## UG10-CH33-D149

PDF page: 492; original JSON pointer: `/5892`

2. 对于 Horizontal Vertical API Tank 或 Heat Exchanger Shell的容器类型 在 Head Type 封头类型 列表中选择一封头类型 并在 Vessel Dimensions 容器尺寸 窗口 上输入长度和直径 对于封头类型可用的选项为 Flanged(带阀兰的),Ellipsoidal 椭 圆的 , 或 User Specified 用户规定的

## UG10-CH33-D150

PDF page: 492; original JSON pointer: `/5893`

3. 对于 Heat Exchanger Shell容器类型 在 Shell Orientation 壳体方向 列表中输入壳 体方向 卧式或立式

## UG10-CH33-D151

PDF page: 492; original JSON pointer: `/5894`

4. 对于 Sphere 容器类型 在 Vessel Dimensions窗口的 Diameter 区域输入半球直径

## UG10-CH33-D152

PDF page: 493; original JSON pointer: `/5896`

5. 对于 Vessel Jacket 容器类型 在 Vessel Dimension窗口上输入夹套体积

## UG10-CH33-D153

PDF page: 493; original JSON pointer: `/5897`

6. 对于 User Specified 容器类型 在 User Specifications 窗口上输入容器体积和封头体 积

## UG10-CH33-D154

PDF page: 493; original JSON pointer: `/5898`

7. 如果你选择了 User Specified 封头类型 在 User Specifications 窗口上输入封头体 积和封头面积 设计参数 使用 Design Parameters 页通过下面规定来说明容器设计特性

## UG10-CH33-D155

PDF page: 493; original JSON pointer: `/5899`

l 限制用户规定分离模型的均相气体分率

## UG10-CH33-D156

PDF page: 493; original JSON pointer: `/5900`

容器分离模型可以使你选择如何模拟离开容器的流体相态特性 下面的分离选项是可用

## UG10-CH33-D157

PDF page: 493; original JSON pointer: `/5901`

User specified 均项排放直到容器气相分率达到用户规定的值 然

## UG10-CH33-D158

PDF page: 493; original JSON pointer: `/5902`

为动态泄压方案规定设计参数

## UG10-CH33-D159

PDF page: 493; original JSON pointer: `/5903`

1. 在 Pressure Relief DynamicInput Design Parameters 页的 Vessel Design Pressure 窗口 上先输入 Maximum Allowable Working Pressure 最大许可压力 MAWP .

## UG10-CH33-D160

PDF page: 493; original JSON pointer: `/5904`

2. 在 MAWP Temperature 区域输入与规定最大许可工作压力相对应的温度

## UG10-CH33-D161

PDF page: 493; original JSON pointer: `/5905`

3. 在 Vessel Disengagement 容器分离 窗口 从 Disengagement Model 分离模型 列表选择一分离模型

## UG10-CH33-D162

PDF page: 493; original JSON pointer: `/5906`

4. 输入与所选分离模型相对应的容器分离参数 如果你选择 输入 Bubbly 泡点分离系数 缺省为 1.01 Churn-Turbulent Churn-Turbulent 分离系数 缺省为 1 User-specified 均相气体分率限制 无缺省 在页的底部 你可以有选择地在 Vessel Dead Volumn 容器无效体积 窗口输入 Volumn of Vessel Internals 容器内体积 它指出内部结构的体积如混合器和挡板应从计算的容器 体积中减掉 明火

## UG10-CH33-D163

PDF page: 493; original JSON pointer: `/5907`

用该页来描述明火加热容器的特性 必须选择 A Fire Standard 明火标准 , 以使 ASPEN

## UG10-CH33-D164

PDF page: 493; original JSON pointer: `/5908`

PLUS 能计算容器浸湿面积 输入能量和怎样取防火因子 Fire Credits 页 Pressure Relief

## UG10-CH33-D165

PDF page: 493; original JSON pointer: `/5909`

可以依据由下面标准计算的结果

## UG10-CH33-D166

PDF page: 494; original JSON pointer: `/5911`

从 Fire Scenario Parameters 窗口的 Fire Standard 列表选择所需要的标准

## UG10-CH33-D167

PDF page: 494; original JSON pointer: `/5912`

Fire 窗口上可选的规定包括

## UG10-CH33-D168

PDF page: 494; original JSON pointer: `/5913`

l 容器被明火包围的面积 当在 Vessel页上选择 Vessel Jacket 或 User Specified 时的

## UG10-CH33-D169

PDF page: 494; original JSON pointer: `/5914`

关于如何计算浸湿面积和能量输入的详细信息 参见在线帮助和 ASPEN PLUS 单元操

## UG10-CH33-D170

PDF page: 494; original JSON pointer: `/5915`

Pressure Relief 假定在整个的放空过程中计算的能量输入是常数 如果合适的话 你可

## UG10-CH33-D171

PDF page: 494; original JSON pointer: `/5916`

以用 Fire Credits 防火度 页来规定防火因子 它是 ASPEN PLUS 用以减少进入容器的能

## UG10-CH33-D172

PDF page: 494; original JSON pointer: `/5917`

量的 你可以直接规定防火因子或允许 ASPEN PLUS 依据以下系统来计算防火因子

## UG10-CH33-D173

PDF page: 494; original JSON pointer: `/5918`

使用本页为动态热量输入方案规定输入容器的热量流率 热量输入方法可以用三种方式

## UG10-CH33-D174

PDF page: 494; original JSON pointer: `/5919`

来规定 分别通过选择在 Heat Input 页的 Heat Input Method 窗口上的下列选项之一来实现

## UG10-CH33-D175

PDF page: 494; original JSON pointer: `/5920`

如果选择了恒定负荷 就在 Heat Input Method 窗口上输入恒定负荷 如果你选择从热源计算负荷 你必须在 Heat Source 窗口上规定温度 传热面积和传热系 数 U-值 如果你选择输入负荷随时间变化曲线图 用 Duty Profile 框输入与时间相对应的负荷 规定动态方案的反应系统 关于明火或热量输入的动态方案 如果 Vessel Type 容器类型 (DynamicInput Vessel 页)为下列之一 你可以模拟一个有反应的重要容器

## UG10-CH33-D176

PDF page: 494; original JSON pointer: `/5921`

在 Setup 文件夹的 Reaction(反应)页里 规定容器里发生的反应 如果是动力学或平衡

## UG10-CH33-D177

PDF page: 494; original JSON pointer: `/5922`

而不是电解质 类型的反应 你必须通过 Data Browser 数据浏览器 的 Reactions 文件

## UG10-CH33-D178

PDF page: 494; original JSON pointer: `/5923`

夹创建一个 Reaction ID 反应标识 通过 Chemistry 电解质 文件夹规定的电解质反应

## UG10-CH33-D179

PDF page: 494; original JSON pointer: `/5924`

自动包括在泄压计算中 而不需要在 Reactions 页中规定 关于如何规定 Reaction ID 的详细

## UG10-CH33-D180

PDF page: 495; original JSON pointer: `/5926`

1. 确信选择了 Setup Scenario 页上动态方案之一 明火加热或热量输入

## UG10-CH33-D181

PDF page: 495; original JSON pointer: `/5927`

2. 从 Pressure Relief Setup 窗口单击 Reactions

## UG10-CH33-D182

PDF page: 495; original JSON pointer: `/5928`

3. 在 Reactions 页上 单击 Vessel 复选框上的 Include Chemical Reactions.

## UG10-CH33-D183

PDF page: 495; original JSON pointer: `/5929`

4. 在 Vessel Reactions 窗口上 从 Available 可用的 列表选择所要的反应 ID 并用 右箭头按钮把它们移到 Selected 列表 要从 Selected 列表移出反应 选择它们并 单击左箭头按钮 在 Selected 列表中用双箭头按钮来移动所有的反应 停止动态计算时的规定 在模拟明火或热量输入的动态方案时 你必须用 Pressure Relief Operations 表来说明 ASPEN PLUS 用来终止动态模拟的判据

## UG10-CH33-D184

PDF page: 495; original JSON pointer: `/5930`

在 Operations 操作 表的 Stop Criteriay 终止判据 页上 定义一个或更多的终止判

## UG10-CH33-D185

PDF page: 495; original JSON pointer: `/5931`

据 你必须至少定义一个终止判据来完成该表 如果你定义多个终止判据 先满足一个判据

## UG10-CH33-D186

PDF page: 495; original JSON pointer: `/5932`

当定义一个终止判据时 你可以从以下变量类型中选择

## UG10-CH33-D187

PDF page: 495; original JSON pointer: `/5933`

l 总摩尔数或规定组分的摩尔数

## UG10-CH33-D188

PDF page: 495; original JSON pointer: `/5934`

l 总质量或规定组分的质量

## UG10-CH33-D189

PDF page: 495; original JSON pointer: `/5935`

l 在模拟结束时为规定输入一个值

## UG10-CH33-D190

PDF page: 495; original JSON pointer: `/5936`

l 为与组分相关的规定类型选择一个组分和子物流

## UG10-CH33-D191

PDF page: 495; original JSON pointer: `/5937`

l 规定终止模拟所采用的方向 上面或下面

## UG10-CH33-D192

PDF page: 495; original JSON pointer: `/5938`

规定动态泄压方案何时终止计算 可以如下操作

## UG10-CH33-D193

PDF page: 496; original JSON pointer: `/5940`

1. 打开 Pressure Relief Operations 泄压操作 窗口

## UG10-CH33-D194

PDF page: 496; original JSON pointer: `/5941`

2. 在 Stop Criteria 页上 输入终止判据 如果这是第一个终止判据 就在 Criterion No. 区域输入 1 当输入多个终止判据时 从 1 开始 按顺序输入序号

## UG10-CH33-D195

PDF page: 496; original JSON pointer: `/5942`

3. 从 Location 列表 选择一个位置 Vessel ,Vent 或 Accumulator 来计算用来定义为 终止判据的变量

## UG10-CH33-D196

PDF page: 496; original JSON pointer: `/5943`

4. 在 Variable Type列表中 从上面列出类型中选择一个终止判据变量

## UG10-CH33-D197

PDF page: 496; original JSON pointer: `/5944`

5. 在 Stop Value 区域 输入终止模拟的变量值

## UG10-CH33-D198

PDF page: 496; original JSON pointer: `/5945`

6. 对于相关组分规定类型 分别从 Component ID 列表和 Substream ID 列表选择一个 组分和一股子物流

## UG10-CH33-D199

PDF page: 496; original JSON pointer: `/5946`

7. 在 Approach Form 列表中 规定用来终止模拟的方向 上面或下面

## UG10-CH33-D200

PDF page: 496; original JSON pointer: `/5947`

8. 对于每个附加终止判据 重复步骤 2 到 7

## UG10-CH33-D201

PDF page: 496; original JSON pointer: `/5948`

9. 当定义完所有终止判据 单击 Times 标签

## UG10-CH33-D202

PDF page: 496; original JSON pointer: `/5949`

10. 在 Times 页上的 Maximum Time区域 规定方案模拟时间上限

## UG10-CH33-D203

PDF page: 496; original JSON pointer: `/5950`

11. 在 Time Intervals Between Result Points 两个结果点间的时间间隔 框 输入方案 报告结果的时间间隔 在 When Vent is Closed 关闭放空 区域输入该值 ASPEN PLUS 将在你规定的时间间隔内报告结果 当放空打开时如果你想用不同的时间间 隔 在 When Vent is Open 放空打开 区域输入该值 对于 When Vent is Open 如果你不输入值 When Vent is Closed 的规定间隔将用于所有方案

## UG10-CH33-D204

PDF page: 496; original JSON pointer: `/5951`

12. 在页底部的 Optional 可选 框 当泄压系统打开或关闭时 你可以要求包括分布 点 该选项在缺省情况下是选择的 单击该选项可取消它

## UG10-CH33-D205

PDF page: 496; original JSON pointer: `/5952`

13. 也在 Optional框 你可以通过在 Maximum No. of Result Points 结果点最大数目 区域输入一个值来限制分布图里结果点的最大数目 该值的缺省值是规定的最大时 间除以 When Vent is Closed的规定结果的报告时间间隔 如果规定的 When Vent is Open 结果时间间隔比 When Vent is Closed 小 你应该提高 Maximum No. of Result Points 的缺省值

## UG10-CH33-D206

PDF page: 496; original JSON pointer: `/5953`

检查泄压计算结果采取如下步骤

## UG10-CH33-D207

PDF page: 496; original JSON pointer: `/5954`

1 从 Data 菜单 指向 Flowsheeting Options, 然后单击 Pressure Relief.

## UG10-CH33-D208

PDF page: 496; original JSON pointer: `/5955`

2 在 Pressure Relief Object Manager 上 选择需要的 Pressure Relief ID 然后单击 Edit.

## UG10-CH33-D209

PDF page: 496; original JSON pointer: `/5956`

3 在 Data Browser 的左屏中 为所选的 Pressure Relief 模块单击相应结果表 对于稳态方案 单击 Steady State Results 表 对于动态方案 单击 Dynamic Results 表 稳态结果 用 Steady State Results 表来浏览稳态模拟的计算结果 Steady State Results 表包括两页 使用该页 浏览 Summary 汇总 输入汇总 是否满足标准要求 入口和尾管压力是否改变

## UG10-CH33-D210

PDF page: 496; original JSON pointer: `/5957`

Property Profiles 物性

## UG10-CH33-D211

PDF page: 496; original JSON pointer: `/5958`

l 输入汇总 Scenario Relief Device类型和 Capacity 选项

## UG10-CH33-D212

PDF page: 497; original JSON pointer: `/5960`

l 你在 Setup Scenario 页上给出的估算流率

## UG10-CH33-D213

PDF page: 497; original JSON pointer: `/5961`

如果标准的要求没满足 你应该检查状态信息 系统可能因为下述原因没满足标准的要 求

## UG10-CH33-D214

PDF page: 497; original JSON pointer: `/5962`

入口管压力损失作为在 Setup Rules 设置规则 页上规定不同设置压力的百分数所计算的值

## UG10-CH33-D215

PDF page: 497; original JSON pointer: `/5963`

明压力过压大于 10%或没使用 97%规则 允许压力损失是由在 Setup Rules 页上规定的最大

## UG10-CH33-D216

PDF page: 497; original JSON pointer: `/5964`

使用该页来浏览紧急泄压系统的物性分布曲线 给出如下物性

## UG10-CH33-D217

PDF page: 497; original JSON pointer: `/5965`

使用 DynamicResults 表来浏览动态模拟计算结果

## UG10-CH33-D218

PDF page: 497; original JSON pointer: `/5966`

DynamicResults 表包含七页

## UG10-CH33-D219

PDF page: 497; original JSON pointer: `/5967`

Summary 汇总 输入汇总 是否满足标准要求 入口和尾管压力是否改变

## UG10-CH33-D220

PDF page: 497; original JSON pointer: `/5968`

Parameter 参数 动态结果和容器压力及温度汇总

## UG10-CH33-D221

PDF page: 497; original JSON pointer: `/5969`

l 输入汇总 Scenario,Relief Device类型和 Capacity 选项

## UG10-CH33-D222

PDF page: 497; original JSON pointer: `/5970`

如果没达到所要求的 你应该检查状态信息 如果你的模拟没满足标准要求 可能的原

## UG10-CH33-D223

PDF page: 498; original JSON pointer: `/5972`

入口管压力损失作为在 Setup Rules 页上规定不同设置压力的百分数所计算的值

## UG10-CH33-D224

PDF page: 498; original JSON pointer: `/5973`

明压力大于 10%过压或 97%规则没使用 允许压力损失是由在 Setup Rules 页上规定的最大

## UG10-CH33-D225

PDF page: 498; original JSON pointer: `/5974`

l 操作时间 模拟运行时间

## UG10-CH33-D226

PDF page: 498; original JSON pointer: `/5975`

l 依据浸湿面积和防火因子的明火热量输入

## UG10-CH33-D227

PDF page: 498; original JSON pointer: `/5976`

容器的允许条件依据在 Setup Rules 页上输入的容器最大压力

## UG10-CH33-D228

PDF page: 498; original JSON pointer: `/5977`

该结果页显示相对于操作时间的容器物性表 下面给出容器物性

## UG10-CH33-D229

PDF page: 498; original JSON pointer: `/5978`

状态表指出如果不在设备里结焦 在哪发生结焦 下面给出的是可能状态符号的说明

## UG10-CH33-D230

PDF page: 498; original JSON pointer: `/5979`

本页使你浏览相对操作时间的泄压系统点分布曲线 给出如下物性

## UG10-CH33-D231

PDF page: 499; original JSON pointer: `/5981`

Accumulator 页可浏览相对于操作时间的累加器物性 下面给出累加器物性

## UG10-CH33-D232

PDF page: 499; original JSON pointer: `/5982`

X-Y-Z 页可浏览在以下相态和位置下相对于操作时间的组分摩尔分率

## UG10-CH33-D233

PDF page: 499; original JSON pointer: `/5983`

Vessel页使你对于你所选的子物流浏览容器中相对于操作时间的组分质量数

## UG10-CH33-D234

PDF page: 499; original JSON pointer: `/5984`

一个泄压系统的动态运行示例

## UG10-CH33-D235

PDF page: 499; original JSON pointer: `/5985`

该例子给出一个泄压系统动态运行后的结果 第一屏给出用 Summary 页显示的

## UG10-CH33-D236

PDF page: 499; original JSON pointer: `/5986`

DynamicResults

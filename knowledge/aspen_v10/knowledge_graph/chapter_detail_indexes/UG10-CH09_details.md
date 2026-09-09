# UG10-CH09 Detail Operation Index - 第9章 规定物流

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH09-D001

PDF page: 130; original JSON pointer: `/1599`

物流可以把一个流程中的各个单元操作模块连接起来 并能把物流和能流从一个单元

## UG10-CH09-D002

PDF page: 130; original JSON pointer: `/1600`

l 流程中的内部 内部连接 物流

## UG10-CH09-D003

PDF page: 130; original JSON pointer: `/1601`

采用物流方式可以输入进料物流数据并可以给出任何内部撕裂 循环 物流的初始估

## UG10-CH09-D004

PDF page: 130; original JSON pointer: `/1602`

对于所有的进料物流 必须规定

## UG10-CH09-D005

PDF page: 130; original JSON pointer: `/1603`

1. 双击流程图中的物流 或 打开Data (数据)菜单 单击Streams 物流 在 Streams Object Manager 物流对 象管理器 窗口中 选择物流并单击 Edit 编辑

## UG10-CH09-D006

PDF page: 130; original JSON pointer: `/1604`

2. 在 Specifications 规定 栏中 规定三个 State Variables 状态变量 中的任 意两个就可以设置物流的热状态 例如 你可以规定温度和压力 或温度和气相 分率 要了解其有效的选项 请参见第九章 可能的物流热状态规定一节

## UG10-CH09-D007

PDF page: 130; original JSON pointer: `/1605`

3. 使用流率或流率分率或组成表中的每种组分的浓度来规定物流组成 参见第九章 输入物流组成一节 如果物流中包括固体子物流 执行4-6步

## UG10-CH09-D008

PDF page: 131; original JSON pointer: `/1607`

4. 如果你要规定固体子物流 请用 Substreams.( 子物流)域显示不同的子物流

## UG10-CH09-D009

PDF page: 131; original JSON pointer: `/1608`

5. 规定每个固体子物流的温度 压力 和组成 每个子物流的压力必须相同

## UG10-CH09-D010

PDF page: 131; original JSON pointer: `/1609`

正文待来源表达/OCR边界复核；原文本 SHA256: `8a2ab50b89d59a727e9557338df0008f980994e794f96539a91c831d9a57f10f`。

## UG10-CH09-D011

PDF page: 131; original JSON pointer: `/1610`

ASPEN PLUS 会计算出没有规定的温度 压力或气相摩尔分率 以及物流的焓 熵和

## UG10-CH09-D012

PDF page: 131; original JSON pointer: `/1611`

1. 双击流程中的物流 或 打开 Data( 数据) 菜单 单击 Streams( 物流) 在 Streams Object Manager (物流对 象管理器)中选择物流并单击 Edit (编辑)按钮

## UG10-CH09-D013

PDF page: 131; original JSON pointer: `/1612`

2. 确保 Stream Input Flash Options(物流输入闪蒸选项 ) 页中的 Calculate Stream Properties(计算物流物性) 复选框是未选的

## UG10-CH09-D014

PDF page: 131; original JSON pointer: `/1613`

3 输入下列物性中的两个值 Temperature(温度) Presure 压力 , 和Stream Input Specifications 物流输入规定 页中的 Vapor Fraction as State Variables 气相分率 作为状态变量 要了解关于检查模块的物料平衡的有关信息 请参见第五章 ASPEN PLUS 不计算只 做质量平衡模拟的物流物性

## UG10-CH09-D015

PDF page: 132; original JSON pointer: `/1615`

你可以按照组分流率 分率或浓度来规定物流的组成

## UG10-CH09-D016

PDF page: 132; original JSON pointer: `/1616`

* 对于非常规组分,你可以只输入质量流率和分率

## UG10-CH09-D017

PDF page: 132; original JSON pointer: `/1617`

如果你规定了组分分率 那么还必须规定总的摩尔 质量 或标准液体体积流率 组 分分率的总和必须是1.0或100.0 你可以输入组分流率和总流率 ASPEN PLUS 会自动调整组分流率以满足总的流率 如果你规定了组分浓度 你还必须输入溶剂的组分ID和总流率 物流必须是单一相态 你可以在Stream Input Flash Options 物流输入闪蒸选项 页上的Valid Phases 有效相态 列表中选择Vapor-Only 只有气相 或 Liquid -Only 只有液相 选项 并在Stream Input

## UG10-CH09-D018

PDF page: 132; original JSON pointer: `/1618`

Specification 物流输入规定 页中选择温度和压力作为State Variables 状态变量 或者

## UG10-CH09-D019

PDF page: 132; original JSON pointer: `/1619`

规定物流为泡点温度 气相分率为0

## UG10-CH09-D020

PDF page: 132; original JSON pointer: `/1620`

如果你在输入组分流率 分率或总的物流流率时采用的是液体体积基准 你还需要在 Properties Parameters Pure Component Input 物性参数纯组分输入 中输入组分的标准液体 体积 VLSTD 要了解更多的信息 请参见第八章 数据库中的 VLSTD数值来自于API数据手册 在 ASPEN PLUS中 不采用标准液体体积来计算密度 标准液体体积流率 Stdvol-Flow 可能与物流的体积流率是不同的 标准液体体积流

## UG10-CH09-D021

PDF page: 132; original JSON pointer: `/1621`

率是在大约600F 1atm下定义的 如果物流是气体 或者含有大量的气体 物流的体积流

## UG10-CH09-D022

PDF page: 132; original JSON pointer: `/1622`

率会与标准液体体积流率有很大的不同 你可以以摩尔流率来输入标准气体体积流率 选

## UG10-CH09-D023

PDF page: 132; original JSON pointer: `/1623`

要在物流报告中输出 Std.liq. Volume Flow 标准液体体积流率 或 Std.liq.Volume

## UG10-CH09-D024

PDF page: 132; original JSON pointer: `/1624`

Fraction 标准液体体积分率 在 Setup ReportOptions Stream 设置报告选项物流 页

## UG10-CH09-D025

PDF page: 132; original JSON pointer: `/1625`

上选择合适的选项 你也可以计算这些 Property Sets 物性集

## UG10-CH09-D026

PDF page: 132; original JSON pointer: `/1626`

用于设计规定和Fortran模块中

## UG10-CH09-D027

PDF page: 132; original JSON pointer: `/1627`

Stream Input Specifications 物流输入规定 页显示了你输入给物流的总的组分流率

## UG10-CH09-D028

PDF page: 132; original JSON pointer: `/1628`

分率或浓度 使用该值可以检查你的输入

## UG10-CH09-D029

PDF page: 133; original JSON pointer: `/1630`

规定一个带有两个液相的物流的示例

## UG10-CH09-D030

PDF page: 134; original JSON pointer: `/1632`

要规定一个固体子物流的粒子尺寸

## UG10-CH09-D031

PDF page: 134; original JSON pointer: `/1633`

1. 双击流程图中的物流 或 打开 Data( 数据 菜单 单击 Streams 物流 在 Streams Object Manager 物 流对象管理器 中选择物流并单击Edit 编辑 按钮

## UG10-CH09-D032

PDF page: 134; original JSON pointer: `/1634`

2. 在 Stream Input 物流输入 窗口中 单击 Stream PSD 物流粒子尺寸分布 页

## UG10-CH09-D033

PDF page: 134; original JSON pointer: `/1635`

3. 输入粒子尺寸的重量分率 总数应该是1.0 要了解ASPEN PLUS 中关于粒子尺寸分布的更多的信息 以及怎样定义你自己的粒子 尺寸范围 请参阅第九章中的定义新的子物流 规定组分的属性值 用 Stream Input Component Attr. 物流输入组分属性 页来规定组分的属性值 在 Components Attr-Comps 组分属性 选择页或 Properties Advanced NC -Props PropertyMethods 物性高级的物性物性方法 页中定义的每一个属性值都必须规定 参见 第五章

## UG10-CH09-D034

PDF page: 134; original JSON pointer: `/1636`

1. 在 Stream Input (物流输入)窗口中 单击Component Attr.(组分属性) 页

## UG10-CH09-D035

PDF page: 134; original JSON pointer: `/1637`

2. 输入列出的每个属性的值 规定一个非常规子物流的 GENANAL组分属性的一个示例 在 Stream Input Component Attr. (物流输入组分属性)页中 GENANAL 组分属性元素 是NCPSD子物流的规定

## UG10-CH09-D036

PDF page: 135; original JSON pointer: `/1639`

在 Properties Advanced NC -Props(物性高级的NC物性) 窗口中 定义 GENANAL 组分

## UG10-CH09-D037

PDF page: 135; original JSON pointer: `/1640`

属性是所选的 Nonconventional Component Property (非常规物性)模型所必需的

## UG10-CH09-D038

PDF page: 135; original JSON pointer: `/1641`

在创建你的模拟模型的时候 你可以交互地计算并显示相互影响的物流物性 但你不

## UG10-CH09-D039

PDF page: 135; original JSON pointer: `/1642`

必先完成流程的定义或输入规定

## UG10-CH09-D040

PDF page: 135; original JSON pointer: `/1643`

例如 你可以在定义一个进料物流的时候闪蒸它 以检查你的物性模型 当你交互地

## UG10-CH09-D041

PDF page: 135; original JSON pointer: `/1644`

开发一个流程模型的时候 你可以通过检查中间物流的相态来帮助你确定可行的规定

## UG10-CH09-D042

PDF page: 136; original JSON pointer: `/1646`

有效的物性包括摩尔 质量和标准体积分率

## UG10-CH09-D043

PDF page: 136; original JSON pointer: `/1647`

息 请参见第九章, 生成PT封闭曲线

## UG10-CH09-D044

PDF page: 136; original JSON pointer: `/1648`

** 这些分析数据会自动显示曲线图

## UG10-CH09-D045

PDF page: 136; original JSON pointer: `/1649`

你也可以使用物性表来进行物流物性分析 这些分析数据会自动执行生成一个物性表

## UG10-CH09-D046

PDF page: 136; original JSON pointer: `/1650`

所必需的许多步骤 并定义适合于分析数据的内置曲线图

## UG10-CH09-D047

PDF page: 136; original JSON pointer: `/1651`

当Analysis(分析)命令不能提供给你足够的灵活性时 请用 Property Table (物性表)窗

## UG10-CH09-D048

PDF page: 136; original JSON pointer: `/1652`

要计算并显示相互影响的物流物性

## UG10-CH09-D049

PDF page: 136; original JSON pointer: `/1653`

1. 确信你的 Setup(设置),Components(组成)和 Properties(物性)规定已经完成

## UG10-CH09-D050

PDF page: 136; original JSON pointer: `/1654`

2. 确信你要分析的物流规定或结果已经完成 或者是物流的 Stream Input Specifications(物流输入规定)页必须完成 或者是物流必须有在当前部分计算的结 果

## UG10-CH09-D051

PDF page: 136; original JSON pointer: `/1655`

4. 在 Tools(工具)菜单中 单击 Analysis(分析) 然后单击 Stream(物流) 然后选择你 需要的计算类型 如果步骤 1 和 2 没有满足 那么该命令将无效

## UG10-CH09-D052

PDF page: 136; original JSON pointer: `/1656`

5. 你可以在适当的对话框中进行选择和规定

## UG10-CH09-D053

PDF page: 136; original JSON pointer: `/1657`

6. 单击 Go(执行)

## UG10-CH09-D054

PDF page: 136; original JSON pointer: `/1658`

7. 当计算完成时 打印或浏览出现的结果和曲线图

## UG10-CH09-D055

PDF page: 136; original JSON pointer: `/1659`

8. 当你确信你已完成了计算时 关闭窗口和图形 但是结果还没有保存 所以一旦 你关闭了窗口 如果你想再看的时候 必须重新计算

## UG10-CH09-D056

PDF page: 137; original JSON pointer: `/1661`

生成物流分析点的一个示例

## UG10-CH09-D057

PDF page: 138; original JSON pointer: `/1663`

生成 PV 曲线的一个示例

## UG10-CH09-D058

PDF page: 138; original JSON pointer: `/1664`

压力-温度 PT 封闭曲线是沿着恒定气相分率的曲线 通过临界点 再返回到补余分

## UG10-CH09-D059

PDF page: 138; original JSON pointer: `/1665`

支曲线而生成的 气相分率=0.75 的补余分支是 0.25 这些曲线是参数的 包括每个气相

## UG10-CH09-D060

PDF page: 138; original JSON pointer: `/1666`

除了电解质物性方法 你可以由任何物性方法生成 PT-封闭曲线 但是 由活度系数

## UG10-CH09-D061

PDF page: 138; original JSON pointer: `/1667`

和其它非状态方程物性方法生成的 PT-封闭曲线不通过临界点 相应地 每个气相分率和

## UG10-CH09-D062

PDF page: 139; original JSON pointer: `/1669`

由物流创建一个 PT-封闭曲线

## UG10-CH09-D063

PDF page: 139; original JSON pointer: `/1670`

要由一个物流创建一个 PT-封闭曲线

## UG10-CH09-D064

PDF page: 139; original JSON pointer: `/1671`

1. 确信你的 Setup (设置),Components (组分)和 Properties (物性)规定已经完成

## UG10-CH09-D065

PDF page: 139; original JSON pointer: `/1672`

2. 确信你要分析的物流规定或结果已经完成 物流的 Stream Input Specifications ( 物 流输入规定)页必须完成 或物流必须有在当前计算的结果

## UG10-CH09-D066

PDF page: 139; original JSON pointer: `/1673`

4. 在 Tools(工具)菜单中 单击 Analysis(分析) 然后单击 Stream(物流) 如果步骤 1 和 2 没有满足 那么 该命令将会无效

## UG10-CH09-D067

PDF page: 139; original JSON pointer: `/1674`

5. 选择 PT-封闭曲线

## UG10-CH09-D068

PDF page: 139; original JSON pointer: `/1675`

6. 选择气相分率分支 Dew/Bubble(露点/泡点)曲线相应的气相分率分别为 0 和 1.0 可以规定其它的气相 分率 每个规定的气相分率的补余气相分率会自动计算出来

## UG10-CH09-D069

PDF page: 139; original JSON pointer: `/1676`

7. 单击 Go (执行)以创建 PT-封闭曲线表和图形 要了解关于定制曲线的更多的信息 参见第十三章

## UG10-CH09-D070

PDF page: 139; original JSON pointer: `/1677`

8. 当你确信你已完成了计算时 关闭窗口和图形 但是结果还没有保存 所以一旦 你关闭了窗口 如果你想再看的时候 必须重新计算 在关闭 PT-封闭曲线分析 表之前 如要保存输入和结果表 单击 Save As Form (保存为表)按钮 一个带有 输入和结果的窗口将会保存在 Property Analysis (物性分析)文件夹中 创建一个 PT 封闭曲线的示 例 例如 物流 2 为乙烷和己烷按 50-50 混合的混合物 在气相分率为 0.0 0.2 0.4 0.6

## UG10-CH09-D071

PDF page: 139; original JSON pointer: `/1678`

0.8 和 1.0 时生成的数值表和 PT-封闭曲线图

## UG10-CH09-D072

PDF page: 140; original JSON pointer: `/1680`

在下列情况下 不需要规定物流类

## UG10-CH09-D073

PDF page: 140; original JSON pointer: `/1681`

l 仅有的固体是用 Chemistry(化学)窗口或 Electrolytes Expert System (电解质专家系

## UG10-CH09-D074

PDF page: 140; original JSON pointer: `/1682`

当存在固体时 物流类定义模拟物流的结构 固体包括

## UG10-CH09-D075

PDF page: 141; original JSON pointer: `/1684`

物流类定义物流结构的各项

## UG10-CH09-D076

PDF page: 141; original JSON pointer: `/1685`

用 Setup StreamClass 作用

## UG10-CH09-D077

PDF page: 141; original JSON pointer: `/1686`

流程图 把一个新的物流类分派给一个流程段 并定义一个物流

## UG10-CH09-D078

PDF page: 141; original JSON pointer: `/1687`

物流 指定物流为一个物流类 并定义物流类中的子物流

## UG10-CH09-D079

PDF page: 141; original JSON pointer: `/1688`

用 Stream Input PSD (物流输入 PSD)页来定义一个子物流的粒子尺寸分布重量分率

## UG10-CH09-D080

PDF page: 141; original JSON pointer: `/1689`

l 指定物流类为单个的物流

## UG10-CH09-D081

PDF page: 141; original JSON pointer: `/1690`

这些物流类在 ASPEN PLUS 中都是预定义的 对于大多数应用来说应该是够用了

## UG10-CH09-D082

PDF page: 141; original JSON pointer: `/1691`

CFuge,Filter,Swash CCD 至少有一个固体子物流

## UG10-CH09-D083

PDF page: 141; original JSON pointer: `/1692`

至少有一个带有粒子分布的固体子物流

## UG10-CH09-D084

PDF page: 141; original JSON pointer: `/1693`

Crystallizer 如果可以计算粒子尺寸 至少有一个带有粒子

## UG10-CH09-D085

PDF page: 141; original JSON pointer: `/1694`

你也可以自己指定全局的物流类 或者为流程段或单个的物流指定

## UG10-CH09-D086

PDF page: 142; original JSON pointer: `/1696`

要创建或修改一个物流类为

## UG10-CH09-D087

PDF page: 142; original JSON pointer: `/1697`

l 为 CISOLID 和 NC 类型的子物流创建一个带有 PSD 属性的物流类

## UG10-CH09-D088

PDF page: 142; original JSON pointer: `/1698`

l 在模拟中用两个或更多个粒子尺寸分布定义

## UG10-CH09-D089

PDF page: 142; original JSON pointer: `/1699`

子物流的数目和类型连同它们的属性一起定义一个物流类 一个物流类中可以有很多

## UG10-CH09-D090

PDF page: 142; original JSON pointer: `/1700`

子物流 但是 每个 Stream Class(物流类)的第一个子物流必须 MIXED 型

## UG10-CH09-D091

PDF page: 142; original JSON pointer: `/1701`

l 必须指定一个类型 MIXED CISOLID 或 NC

## UG10-CH09-D092

PDF page: 142; original JSON pointer: `/1702`

l 可以指定一个粒子尺寸分布 PSD

## UG10-CH09-D093

PDF page: 142; original JSON pointer: `/1703`

你可以通过列出所有子物流的方法来创建一个新的物流类 也可以在一个已存在的物

## UG10-CH09-D094

PDF page: 142; original JSON pointer: `/1704`

流类中修改子物流 但是不能修改一个 MIXED 类型的子物流

## UG10-CH09-D095

PDF page: 142; original JSON pointer: `/1705`

使用 Setup StreamClass ( 设置物流类)窗口中的 Flowsheet ( 流程) 或 Streams ( 物流)页中

## UG10-CH09-D096

PDF page: 142; original JSON pointer: `/1706`

的 Define StreamClass (定义物流类)按钮 通过列出构成它的子物流 或者在一个已存在的

## UG10-CH09-D097

PDF page: 142; original JSON pointer: `/1707`

物流类中修改其子物流,来给一个物流结构指定一个新的物流类

## UG10-CH09-D098

PDF page: 142; original JSON pointer: `/1708`

1. 打开 Data(数据 (数据 菜单 单击 Setup(设置)

## UG10-CH09-D099

PDF page: 142; original JSON pointer: `/1709`

2. 在 Data Browser( 数据浏览器 的左框中 选择 Setup Stream Class(设置物流类)窗 口

## UG10-CH09-D100

PDF page: 142; original JSON pointer: `/1710`

3. 在 Flowsheet(流程)页中 单击 Define StreamClass(定义物流类)按钮

## UG10-CH09-D101

PDF page: 142; original JSON pointer: `/1711`

4. 在 Define StreamClass(定义物流类)对话框中 从 Stream Class(物流类)域的列表中 选择<new>(新的) --或-- 用 StreamClass(物流类)框中的列表选择要修改的 Stream Class(物流类)名称

## UG10-CH09-D102

PDF page: 142; original JSON pointer: `/1712`

5. 从 Available(可用的)子物流表中选择要包括在物流类中的子物流 并用右箭头按 钮把它们移动到 Selected(已选择的)子物流表中 用双箭头可以同时移动表中的所 有物流

## UG10-CH09-D103

PDF page: 142; original JSON pointer: `/1713`

6. 用上下箭头可以重排列表 注意第一个子物流必须是 MIXED 类型

## UG10-CH09-D104

PDF page: 142; original JSON pointer: `/1714`

7. 完成时 在 Define StreamClass(定义物流类)对话框中单击 Close(关闭) 规定一个全局物流类 你可以给模拟中所有的物流规定一个缺省的全局级的物流类 你也可以将全局的缺省 替换为流程段或者是单个的物流 缺省的物流类是流程段 GLOBAL 的物流类 缺省的物流类是在创建一个新的运行时 由你所选择的 Application Type (应用类型)建立的 你可以在 Setup Specification(设置规定) 页中修改这个缺省

## UG10-CH09-D105

PDF page: 142; original JSON pointer: `/1715`

要使用 Setup Specifications Global(设置全局规定)页来规定缺省的物流类

## UG10-CH09-D106

PDF page: 142; original JSON pointer: `/1716`

1. 打开 Data(数据 菜单 单击 Setup(设置)

## UG10-CH09-D107

PDF page: 142; original JSON pointer: `/1717`

2. 在 Data Browser(数据浏览器)的左框中 单击 Specification(规定)文件夹

## UG10-CH09-D108

PDF page: 142; original JSON pointer: `/1718`

3. 在 Globa(全局级)l 页上 在 Stream Class(物流类)域中选择一个物流类

## UG10-CH09-D109

PDF page: 143; original JSON pointer: `/1720`

当模拟中使用了超过一种物流类时 把流程图分成了几段 并规定物流类为每一个流

## UG10-CH09-D110

PDF page: 143; original JSON pointer: `/1721`

一个连接来自不同流程段模块的物流,可以保持它最初所在的流程段的物流类

## UG10-CH09-D111

PDF page: 143; original JSON pointer: `/1722`

段 或者固体已经被除去 你可以指定上游物流段为 MIXCISLD 物流类 指定下游物流

## UG10-CH09-D112

PDF page: 143; original JSON pointer: `/1723`

必须使用 Mixer 和 ClChng 模型在指定为不同物流类的流程段之间进行转换

## UG10-CH09-D113

PDF page: 143; original JSON pointer: `/1724`

要给流程部分指定一个物流类

## UG10-CH09-D114

PDF page: 143; original JSON pointer: `/1725`

1. 打开 Data (数据)菜单 单击 Setup (设置)

## UG10-CH09-D115

PDF page: 143; original JSON pointer: `/1726`

2. 在 Data Browser (数据浏览器 窗口的左框中 选择 Stream Class(物流类)窗口

## UG10-CH09-D116

PDF page: 143; original JSON pointer: `/1727`

3. 单击 Flowsheet(流程)页

## UG10-CH09-D117

PDF page: 143; original JSON pointer: `/1728`

4. 使用列表选择一个与所给流程段相关的 Stream Class(物流类)名称 为单个物流规定物流类 通过为一个或多个单个物流指定物流类来替换全局级的或段物流类 要做到这一点 使用 StreamClass Stream(物流类物流)页 要指定一个物流的物流类

## UG10-CH09-D118

PDF page: 143; original JSON pointer: `/1729`

1. 打开 Data(数据 菜单 单击 Setup(设置)

## UG10-CH09-D119

PDF page: 143; original JSON pointer: `/1730`

2. 在 Data Browser(数据浏览器 窗口的左框中 选择 Stream Class(物流类)窗口

## UG10-CH09-D120

PDF page: 143; original JSON pointer: `/1731`

3. 单击 Streams(物流 页

## UG10-CH09-D121

PDF page: 143; original JSON pointer: `/1732`

4. 从 Available(可用的)物流表中选择要包括在物流类中的物流 并用右箭头按钮把 它们移动到 Selected(已选择的)物流表中 用左箭头可以把物流移出物流类 用双箭头可以同时移动表中的所有物流 留在 Available (有效的)物流表中的物流将会是流程段的物流类 (来自 Flowsheet(流程 页 ) 定义新的子物流 在下列情况下 你需要定义一个新的子物流

## UG10-CH09-D122

PDF page: 143; original JSON pointer: `/1733`

l 你想给一个子物流加一个新的 PSD 定义

## UG10-CH09-D123

PDF page: 143; original JSON pointer: `/1734`

2. 在 Data Browser(数据浏览器 窗口的左框中 选择 Substreams(子物流)文件夹

## UG10-CH09-D124

PDF page: 143; original JSON pointer: `/1735`

3. 在 Substreams(子物流)页中 输入一个 Substreams(子物流)域中的子物流名

## UG10-CH09-D125

PDF page: 143; original JSON pointer: `/1736`

4. 在 Type(类型)域中 选择一个子物流类

## UG10-CH09-D126

PDF page: 144; original JSON pointer: `/1738`

5. 如果子物流类是 CISOLID 或 NC 根据需要在 Attribute(属性)域中选择一个 PSD

## UG10-CH09-D127

PDF page: 144; original JSON pointer: `/1739`

6. 给子物流指定一个一个或多个物流类 要了解更多的信息, 参见第九章中的创建 或修改物流类 关于粒子尺寸分布 在 ASPEN PLUS 中 用每个粒子尺寸间隔的重量分率来表示粒子尺寸分布 给出间隔 数和每个间隔的尺寸范围 ASPEN PLUS 内部的粒子尺寸分布有 10 个预定义的尺寸间隔 通过改变间隔数或间 隔尺寸范围 可以修改内部的粒子尺寸分布 在某些模拟中你可能需要有两个或更多个具有不同尺寸范围的粒子尺寸分布定义 这 对于不同的流程工段具有不同的粒子尺寸来说是很有用的

## UG10-CH09-D128

PDF page: 144; original JSON pointer: `/1740`

要获得关于粒子尺寸分布的帮助 单击下列主题之一

## UG10-CH09-D129

PDF page: 144; original JSON pointer: `/1741`

l 改变粒子尺寸分布间隔

## UG10-CH09-D130

PDF page: 144; original JSON pointer: `/1742`

l 创建新的粒子尺寸分布

## UG10-CH09-D131

PDF page: 144; original JSON pointer: `/1743`

用 Setup Substreams(设置子物流)窗口来创建一个子物流的粒子尺寸分布 你可以规定

## UG10-CH09-D132

PDF page: 144; original JSON pointer: `/1744`

粒子尺寸分布将要分成的不连续的间隔数 并规定每个间隔尺寸的上下限

## UG10-CH09-D133

PDF page: 144; original JSON pointer: `/1745`

要规定粒子尺寸分布的间隔数

## UG10-CH09-D134

PDF page: 144; original JSON pointer: `/1746`

1. 打开 Data(数据 菜单 单击 Setup(设置)

## UG10-CH09-D135

PDF page: 144; original JSON pointer: `/1747`

2. 在 Data Browser(数据浏览器 窗口的左框中 选择 Substreams(子物流)文件夹

## UG10-CH09-D136

PDF page: 144; original JSON pointer: `/1748`

3. 在 PSD 页上的 Substreams Object Manager(子物流对象管理器)中 选择你要修改的 属性设置名称 并单击 Edit(编辑)

## UG10-CH09-D137

PDF page: 144; original JSON pointer: `/1749`

4. 输入粒子尺寸分布的间隔数 你也可以选择尺寸单位

## UG10-CH09-D138

PDF page: 144; original JSON pointer: `/1750`

5. 输入粒子尺寸限制在所有的间隔范围内

## UG10-CH09-D139

PDF page: 144; original JSON pointer: `/1751`

6. Lower(下限)会随着 Upper 上限 值自动更新为以前的间隔 反之亦然 创建新的粒子尺寸分布 你可以创建一个或更多个新的粒子尺寸分布属性 以及内部的 PSD

## UG10-CH09-D140

PDF page: 144; original JSON pointer: `/1752`

3. 在 PSD 页上的 Substreams Object Manager(子物流对象管理器)中 单击 New(新的)

## UG10-CH09-D141

PDF page: 144; original JSON pointer: `/1753`

4. 在 Create New ID(创建新的 ID)对话框中 输入一个 PSD ID 或确认缺省的 ID

## UG10-CH09-D142

PDF page: 145; original JSON pointer: `/1755`

5. 在 PSD 页中的 Interval Numbe(间隔数)栏中输入不连续的粒子尺寸分布的间隔数 你也可以选择尺寸单位

## UG10-CH09-D143

PDF page: 145; original JSON pointer: `/1756`

6. 在 Lower Limit(下限)栏中 规定每个间隔的尺寸下限 ASPEN PLUS 会自动填上 相应的上限值

## UG10-CH09-D144

PDF page: 145; original JSON pointer: `/1757`

7. 在 Upper Limit(上限)栏中 规定最后一个间隔的上限尺寸

## UG10-CH09-D145

PDF page: 145; original JSON pointer: `/1758`

8. 你必须在 SetupSubstreams Substreams(设置子物流子物流))页中给新的 PSD 属性指 定一个子物流类 要了解关于定义一个新的子物流的更多的信息 参见第九章的定义新的子物流或修改 物流类 规定热流 在 ASPEN PLUS 中 物料和能量平衡报告只考虑用物流代替的能流 任何不用热流或 功流表示的负荷或功率出现在报告中是不平衡的 模型 可以有 计算热负荷 出口热流 允许负荷入口规定 入口热流 你可以用一个入口热流来给单元操作模块输入一个热负荷规定

## UG10-CH09-D146

PDF page: 145; original JSON pointer: `/1759`

要显示热流的 Specification (规定)页

## UG10-CH09-D147

PDF page: 145; original JSON pointer: `/1760`

1. 双击流程中的物流以选择它 或打开 Data(数据 菜单 单击 Streams(物流 在 Streams Object Manager(物流对象管理器 窗口中选择物流并单击 Edit(编辑)

## UG10-CH09-D148

PDF page: 145; original JSON pointer: `/1761`

2. 在 Specification(规定)页中 规定热负荷 热负荷值 热流方向 正值 提供给模块 负值 从模块中移出

## UG10-CH09-D149

PDF page: 145; original JSON pointer: `/1762`

3. 在热流的目标模块中 留出相应的负荷空格 如果你要在目标模块中规定入口热 流和热负荷 使用模块规定 规定功流 在 ASPEN PLUS 中 物料和能量平衡报告只考虑用物流表示的能流 任何不用热流或 功流表示的负荷或功率出现在报告中是不平衡的 模型 可以有 允许功率输入规定 入口功流 需要计算功率 出口功流 要用一个入口功流来给一个泵或压缩机模块提供一个功率规定 要显示热流的 Specification(规定)页

## UG10-CH09-D150

PDF page: 146; original JSON pointer: `/1764`

1. 双击流程中的物流以选择它 或打开 Data(数据 菜单 单击 Streams(物流 在 Streams Object Manager(物流对象管理器)窗口中选择物流并单击 Edit(编辑)

## UG10-CH09-D151

PDF page: 146; original JSON pointer: `/1765`

2. 在 Specification(规定)页中 规定功率 功率值 功流方向 负值 模块获得功率 正值 从模块中除去功率

## UG10-CH09-D152

PDF page: 146; original JSON pointer: `/1766`

3. 在功流的目标模块中 留出相应的功率空格 如果你要在目标模块中规定入口功 流和功率 使用模块规定 热流进入一个塔的再沸器的一个示例 物流 PREB 提供 1MMBtu 的外部热负荷给一个 RADFRAC 模块

## UG10-CH09-D153

PDF page: 147; original JSON pointer: `/1768`

你可以定义虚拟物流来表示内部物流 组成和下面这些单元操作模型的热状态

## UG10-CH09-D154

PDF page: 147; original JSON pointer: `/1769`

你可以使用虚拟物流来表示相互连接的物流在

## UG10-CH09-D155

PDF page: 147; original JSON pointer: `/1770`

物流报告包括虚拟产品物流 模块的质量平衡计算不包括与虚拟物流有关的流率 虚

## UG10-CH09-D156

PDF page: 147; original JSON pointer: `/1771`

拟物流的存在不影响模块结果

## UG10-CH09-D157

PDF page: 147; original JSON pointer: `/1772`

一个模块的入口物流会导致在总的流程物料和能量平衡报告中的不平衡

## UG10-CH09-D158

PDF page: 147; original JSON pointer: `/1773`

1. 创建物流时 选择一个标记了 Pseudo Streams (虚拟物流)的端口

## UG10-CH09-D159

PDF page: 147; original JSON pointer: `/1774`

2. 对每个连有虚拟物流的模块来说 在规定模块时 还要完成 PseudoStream(虚拟物 流)页 关于物流库 物流库保存着物流组成和状态的有关信息 如果物流是在库中定义的 你可以从库中 检索信息 而不用在 Streams(物流 窗口中输入数据 在运行模拟之前 你必须在 Run Settings(运行设置)对话框中规定物流库 使用物流库可以

## UG10-CH09-D160

PDF page: 147; original JSON pointer: `/1775`

一个物流库可以包括多种情况 每种情况通常代表着前一个模拟的结果 当你要从一

## UG10-CH09-D161

PDF page: 147; original JSON pointer: `/1776`

个物流库中检索结果时 你应该规定

## UG10-CH09-D162

PDF page: 147; original JSON pointer: `/1777`

l 能从中检索出结果的工况

## UG10-CH09-D163

PDF page: 147; original JSON pointer: `/1778`

l 当前运行中物流库可以填充的物流

## UG10-CH09-D164

PDF page: 147; original JSON pointer: `/1779`

关于创建物流库的更多的信息 参见第三十五章

## UG10-CH09-D165

PDF page: 147; original JSON pointer: `/1780`

要规定一个运行从物流库中检索关于物流组成和状态的信息

## UG10-CH09-D166

PDF page: 148; original JSON pointer: `/1782`

1. 打开 Data(数据 菜单 单击 Flowsheet Options(流程选项) 再单击 Stream Library(物 流库)

## UG10-CH09-D167

PDF page: 148; original JSON pointer: `/1783`

2. 在 Specification(规定)页上 规定要检索的物流的工况

## UG10-CH09-D168

PDF page: 148; original JSON pointer: `/1784`

3. 如果你要检索一个单个物流的信息 从 Stream Name in Library (库中的物流名)框 的物流库中输入物流名

## UG10-CH09-D169

PDF page: 148; original JSON pointer: `/1785`

4. 如果你在第三步中规定了 Stream Name in Library(库中的物流名) 请用 Include Stream(包括物流)选项 并输入当前模拟中的物流名 或者 选择 Stream(物流)域 中的下列选项之一 选项 要检索所有匹配的物流 所有物流 物流 ID 包括物流 来自于你规定的表中的 ID

## UG10-CH09-D170

PDF page: 148; original JSON pointer: `/1786`

5. 在 Substream and Component (子物流和组分)域中 规定要从物流库中检索的子物 流和组分 或通过不规定域来检索所有的子物流和组分

## UG10-CH09-D171

PDF page: 148; original JSON pointer: `/1787`

6. 在 State Variables(状态变量)域中 规定你要从物流库中检索的物流状态变量

## UG10-CH09-D172

PDF page: 148; original JSON pointer: `/1788`

7. 在窗口的 Component Mapping for Current Case(当前工况的组分图)部分中 在当前 模拟中的 ID 和物流库中的组分 ID 之间 规定组分图 在左栏中 输入当前模拟 的组分 ID 在右栏中 输入相应的物流库中的组分 ID 或在 Default(缺省)页上 定义一个缺省的组分图 ASPEN PLUS 用这种图作为缺省 用于所有的工况

## UG10-CH09-D173

PDF page: 148; original JSON pointer: `/1789`

8. 每种情况重复步骤 2-8

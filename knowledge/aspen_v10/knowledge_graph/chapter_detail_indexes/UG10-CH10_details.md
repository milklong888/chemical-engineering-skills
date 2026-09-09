# UG10-CH10 Detail Operation Index - 第10章 单元操作模型

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH10-D001

PDF page: 149; original JSON pointer: `/1791`

见到 要运行一个流程模拟 必须至少规定一个单元操作模块

## UG10-CH10-D002

PDF page: 149; original JSON pointer: `/1792`

当定义你的模拟流程时 要选择流程模块的单元操作模型 参见第四章

## UG10-CH10-D003

PDF page: 149; original JSON pointer: `/1793`

ASPEN PLUS 有一个很宽的单元操作模型范围可供选择 本章将描述

## UG10-CH10-D004

PDF page: 149; original JSON pointer: `/1794`

l 选择正确的单元操作模型

## UG10-CH10-D005

PDF page: 149; original JSON pointer: `/1795`

l 在模块级上替换全局级规定

## UG10-CH10-D006

PDF page: 149; original JSON pointer: `/1796`

从下表中选择合适的单元操作模型

## UG10-CH10-D007

PDF page: 150; original JSON pointer: `/1798`

Compr 压缩机/透平

## UG10-CH10-D008

PDF page: 150; original JSON pointer: `/1799`

Mcompr 多级压缩机/透平

## UG10-CH10-D009

PDF page: 150; original JSON pointer: `/1800`

FSplit 混合物流 或热流或功流 并将结果物流分离成两个或更多个出口物流 所有

## UG10-CH10-D010

PDF page: 151; original JSON pointer: `/1802`

用 FSplit 模块可以模拟物流的分流 吹扫或放空 除了一个出口物流外 你必须给所

## UG10-CH10-D011

PDF page: 151; original JSON pointer: `/1803`

有的物流提供规定 FSplit 计算没有规定的物流流率

## UG10-CH10-D012

PDF page: 151; original JSON pointer: `/1804`

SSplit 将物流混合并将结果物流分成两个和更多个出口物流 SSplit 允许带有多个子物

## UG10-CH10-D013

PDF page: 151; original JSON pointer: `/1805`

除了一个出口物流外 你必须规定每个子物流的分流 SSplit 计算每个没有规定出口

## UG10-CH10-D014

PDF page: 151; original JSON pointer: `/1806`

例如 你可以用 SSplit 模块把一个含有固相和液相的物流分成两个物流 每个物流只

## UG10-CH10-D015

PDF page: 151; original JSON pointer: `/1807`

Separator Blocks (分离器模块), Sep 和 Sep2 都可以混合进料物流, 并根据你的规定分

## UG10-CH10-D016

PDF page: 151; original JSON pointer: `/1808`

流结果物流 当分离的详细情况不知道或不重要时 你可以用 Sep1 和 Sep2 代替严格的模

## UG10-CH10-D017

PDF page: 151; original JSON pointer: `/1809`

闪蒸模型 Flash2 和 Flash3决定了具有一个或多个入口物流的混合物的热状态和相态

## UG10-CH10-D018

PDF page: 151; original JSON pointer: `/1810`

你可以生成这些模型的冷热曲线表

## UG10-CH10-D019

PDF page: 151; original JSON pointer: `/1811`

闪蒸模型代表单级分离器 比如排空罐 这些模型根据你的规定进行相平衡闪蒸计算

## UG10-CH10-D020

PDF page: 151; original JSON pointer: `/1812`

通常 要固定入口物流的热力学状态 必须规定下列各项中的任意两项

## UG10-CH10-D021

PDF page: 151; original JSON pointer: `/1813`

下表列出了气相摩尔分率可以设置为

## UG10-CH10-D022

PDF page: 151; original JSON pointer: `/1814`

要确定 设置气相摩尔分率

## UG10-CH10-D023

PDF page: 151; original JSON pointer: `/1815`

在闪蒸模型中不允许同时规定热负荷和气相摩尔分率

## UG10-CH10-D024

PDF page: 151; original JSON pointer: `/1816`

它的单相分离器 你可以规定气相物流中的液相夹带的百分数

## UG10-CH10-D025

PDF page: 152; original JSON pointer: `/1818`

规定气相物流中的每个液相的夹带

## UG10-CH10-D026

PDF page: 152; original JSON pointer: `/1819`

倾析器决定了带有一个或多个入口物流的混合物在规定的温度或热负荷下的热状态和

## UG10-CH10-D027

PDF page: 152; original JSON pointer: `/1820`

l 用户提供的 Fortran 子程序

## UG10-CH10-D028

PDF page: 152; original JSON pointer: `/1821`

要了解关于写 Fortran 子程序的信息 参见 ASPEN PLUS 用户模型

## UG10-CH10-D029

PDF page: 152; original JSON pointer: `/1822`

因为 Decanter 模块假定没有气相生成 如果你怀疑有气相生成 请用 Flash3 模块

## UG10-CH10-D030

PDF page: 152; original JSON pointer: `/1823`

Sep 模块将进料混合 并根据你对每个组分所做的规定 将结果物流分离成两个或更

## UG10-CH10-D031

PDF page: 152; original JSON pointer: `/1824`

多个物流 你可以规定每个子物流的每个组分

## UG10-CH10-D032

PDF page: 152; original JSON pointer: `/1825`

你可以用 Sep 模型来表示组分分离操作 例如 当塔所要求的分馏法已知 但塔的具

## UG10-CH10-D033

PDF page: 152; original JSON pointer: `/1826`

Sep2 模型将进料混合 并将结果物流分离成两个或更多个物流 Sep2 和 Sep 相似 但

## UG10-CH10-D034

PDF page: 152; original JSON pointer: `/1827`

它提供了更宽的规定范围 比如组分纯度或回收率 这些规定可以使组分分离操作更容易

## UG10-CH10-D035

PDF page: 152; original JSON pointer: `/1828`

例如 当塔所要求的分馏法已知 但塔的具体的能量平衡未知或不重要时 你可以用蒸馏

## UG10-CH10-D036

PDF page: 152; original JSON pointer: `/1829`

所有的换热器都可以决定带有一个或更多的入口物流的混合物的热状态和相态 换热

## UG10-CH10-D037

PDF page: 152; original JSON pointer: `/1830`

器模型可以模拟加热器或两个或多个物流换热器的性能 你可以生成本节所描述的所有模

## UG10-CH10-D038

PDF page: 153; original JSON pointer: `/1832`

l 加入或移走任何数量的用户规定热负荷

## UG10-CH10-D039

PDF page: 153; original JSON pointer: `/1833`

加热器生成一个出口物流和一个可选的倾析水物流 热负荷规定可以由来自另一模块

## UG10-CH10-D040

PDF page: 153; original JSON pointer: `/1834`

l 当你不需要与功有关的结果时的阀和压缩机

## UG10-CH10-D041

PDF page: 153; original JSON pointer: `/1835`

你也可以 Heater 来设置或改变一个物流的热力学状态

## UG10-CH10-D042

PDF page: 153; original JSON pointer: `/1836`

简捷法总是采用用户规定的 或缺省的 总的传热系数值

## UG10-CH10-D043

PDF page: 153; original JSON pointer: `/1837`

你可以规定换热器的热侧或冷侧入口物流 以及下列性能规定之一

## UG10-CH10-D044

PDF page: 153; original JSON pointer: `/1838`

l 出口温度热物流或冷物流的温度改变

## UG10-CH10-D045

PDF page: 153; original JSON pointer: `/1839`

对于简捷方法 你可以规定换热器每侧的压降 HeatX 模型根据能量平衡和物料平衡

## UG10-CH10-D046

PDF page: 153; original JSON pointer: `/1840`

来确定出口物流状态 并用传热系数的一个常数值来估计所需的表面积 你也可以提供特

## UG10-CH10-D047

PDF page: 153; original JSON pointer: `/1841`

严格的热传递和压降计算 必须输入换热器的几何尺寸

## UG10-CH10-D048

PDF page: 154; original JSON pointer: `/1843`

对壳程和管程换热器规定的一个示例

## UG10-CH10-D049

PDF page: 154; original JSON pointer: `/1844`

规定壳程 TEMA 类型 尺寸和方向:

## UG10-CH10-D050

PDF page: 155; original JSON pointer: `/1846`

规定管程数据: 规定折流板类型 间距和尺寸: 规定壳程和管程管嘴直径:

## UG10-CH10-D051

PDF page: 156; original JSON pointer: `/1848`

2. 连接入口物流和出口物流

## UG10-CH10-D052

PDF page: 156; original JSON pointer: `/1849`

3. 给那个换热器的 B-JAC 输入文件规定一个名字和几个可选的参数 与换热器的结构和几何尺寸有关的信息是通过 Hetran 程序接口输入的 换热器规定保 存在 Hetran 输入文件中 你不必输入换热器的物理特性给这些模块 或通过输入语言输入 那些信息可以从你 规定的 B-JAC 输入文件中检索到 空冷器 Aerotran 是一个通往 B-JAC Aerotran 程序的接口 用于设计和模拟空冷换热器 用 Aerotran 可以模拟具有各种结构的空冷换热器 它也可用于模拟节能器和明火加热 器的对流段

## UG10-CH10-D053

PDF page: 157; original JSON pointer: `/1851`

2. 连接入口物流和出口物流

## UG10-CH10-D054

PDF page: 157; original JSON pointer: `/1852`

3. 给那个换热器的 B-JAC 输入文件规定一个名字和几个可选的参数 与换热器的结构和几何尺寸有关的信息是 Aerotran 程序接口输入的 换热器规定保存 在 Aerotran 输入文件中 你不必输入关于空气冷却器的物理特性 那些信息可以从你规定 的 B-JAC 输入文件中检索到 塔 能够进行简捷蒸馏的模型有 DSTWU Distl 和 SCFrac DSTWU 和 Distl

## UG10-CH10-D055

PDF page: 157; original JSON pointer: `/1853`

MultiFrac 一般的相互连接的多级蒸馏单元系统

## UG10-CH10-D056

PDF page: 157; original JSON pointer: `/1854`

Extract 是一个用于模拟液-液萃取塔的严格模型 它只能用于核算

## UG10-CH10-D057

PDF page: 157; original JSON pointer: `/1855`

进行 Winn-Underwood-Gilliland 简捷设计计算 对于已经规定的轻重关键组分的回收率

## UG10-CH10-D058

PDF page: 157; original JSON pointer: `/1856`

DSTWU 能够生成回流比对于级数的表和曲线

## UG10-CH10-D059

PDF page: 158; original JSON pointer: `/1858`

成两个产品物流 必须规定

## UG10-CH10-D060

PDF page: 158; original JSON pointer: `/1859`

Distl 估算冷凝器和再沸器的负荷 你可以规定一个部分的或全部冷凝器

## UG10-CH10-D061

PDF page: 158; original JSON pointer: `/1860`

根据你的产品规定和分馏指数 SCFrac 估算

## UG10-CH10-D062

PDF page: 158; original JSON pointer: `/1861`

SCFrac 不能处理固体

## UG10-CH10-D063

PDF page: 159; original JSON pointer: `/1863`

这些分布是根据已规定的塔参数 例如回流比 产品流率和热负荷

## UG10-CH10-D064

PDF page: 159; original JSON pointer: `/1864`

所有的核算模式的流率规定都可以以摩尔 质量或标准液体体积为单位

## UG10-CH10-D065

PDF page: 159; original JSON pointer: `/1865`

你可以规定组分或塔板效率

## UG10-CH10-D066

PDF page: 159; original JSON pointer: `/1866`

在设计模式下 你可以规定温度 流率 纯度 回收率或塔中任意物流的物性 例如

## UG10-CH10-D067

PDF page: 159; original JSON pointer: `/1867`

物流物性可以是体积流率和粘度 你可以以摩尔 质量或标准液体体积为单位来规定流率

## UG10-CH10-D068

PDF page: 159; original JSON pointer: `/1868`

规定一个有反应的三相蒸馏塔的示例

## UG10-CH10-D069

PDF page: 159; original JSON pointer: `/1869`

下面这个示例列出了一个没有塔底产品的 回流比为 45 的反应的三相蒸馏塔规定 该

## UG10-CH10-D070

PDF page: 160; original JSON pointer: `/1871`

在第十个平衡级上 返回总液体流率的 30% 规定一个液体倾析器

## UG10-CH10-D071

PDF page: 160; original JSON pointer: `/1872`

反应只发生在再沸器中 参考来自于 Reactions 文件夹中的 Reactions ID 反应速度和化

## UG10-CH10-D072

PDF page: 161; original JSON pointer: `/1874`

MultiFrac 是一个严格的用于模拟一般的相互连接的多级分馏单元系统 MultiFrac 模拟

## UG10-CH10-D073

PDF page: 161; original JSON pointer: `/1875`

l 在塔之间或塔内部可以有任意多个连接

## UG10-CH10-D074

PDF page: 161; original JSON pointer: `/1876`

l 任意的连接物流的分流和混合

## UG10-CH10-D075

PDF page: 162; original JSON pointer: `/1878`

来说 用 PetroFrac 会更方便 只有当要模拟的流程结构超出 PetroFrac 的功能时 才使用

## UG10-CH10-D076

PDF page: 162; original JSON pointer: `/1879`

尽管 MultiFrac 假定为平衡级计算 但你仍可以规定 Murphree 或汽化率 用 MultiFrac

## UG10-CH10-D077

PDF page: 162; original JSON pointer: `/1880`

尽管 PetroFrac 假定为平衡级计算 但你仍可以规定 Murphree 或汽化率

## UG10-CH10-D078

PDF page: 162; original JSON pointer: `/1881`

规定一个常压原油塔的示例

## UG10-CH10-D079

PDF page: 162; original JSON pointer: `/1882`

该示例说明了一个常压原油塔的规定 该塔的主塔中包括 25 个平衡级 其中包括一个

## UG10-CH10-D080

PDF page: 163; original JSON pointer: `/1884`

塔进料流经一个在 3.2atm 下操作的炉子 且规定过闪蒸物流为塔进料体积的 4%

## UG10-CH10-D081

PDF page: 164; original JSON pointer: `/1886`

第一个中段回流的速度是 7205 BPD 且有部分物流从第三级抽出 并返回到第二级

## UG10-CH10-D082

PDF page: 164; original JSON pointer: `/1887`

汽提出轻端 汽提出的气体再返回到主塔的第八级塔板上 再沸器负荷为 1.2MMkcal/hr

## UG10-CH10-D083

PDF page: 165; original JSON pointer: `/1889`

l 模拟单个的或相互连接的塔 包括气液分馏操作 例如吸收 蒸馏和汽提

## UG10-CH10-D084

PDF page: 165; original JSON pointer: `/1890`

l 有一个气相和一个液相的系统 RateFrac 只能检测冷凝器中的游离水相

## UG10-CH10-D085

PDF page: 165; original JSON pointer: `/1891`

RateFrac 假定热平衡只发生在分离接触相的气液交界处

## UG10-CH10-D086

PDF page: 165; original JSON pointer: `/1892`

BatchFrac 用一种十分有效的算法来求解非稳态的描述间歇蒸馏过程的热平衡方程和

## UG10-CH10-D087

PDF page: 166; original JSON pointer: `/1894`

l 使用平衡级 但你可以规定汽化率

## UG10-CH10-D088

PDF page: 166; original JSON pointer: `/1895`

Extract 抽提 是模拟液-液抽提塔的一个严格模型 它只适用于核算 抽提可以有多

## UG10-CH10-D089

PDF page: 166; original JSON pointer: `/1896`

l 一个能代表两相的状态方程

## UG10-CH10-D090

PDF page: 166; original JSON pointer: `/1897`

l 一个 Fortran 子程序

## UG10-CH10-D091

PDF page: 166; original JSON pointer: `/1898`

抽提接受组分或平衡级效率的规定

## UG10-CH10-D092

PDF page: 166; original JSON pointer: `/1899`

反应器来说都不需要反应热 ASPEN PLUS 用生成热来计算反应热

## UG10-CH10-D093

PDF page: 166; original JSON pointer: `/1900`

对于 RCSTR RPlug 和 RBatch 模块来说必须提供反应的动力学信息 可以使用下列

## UG10-CH10-D094

PDF page: 167; original JSON pointer: `/1902`

l 用户写入的 Fortran 子程序 要了解更多的信息 参见 ASPEN PLUS 用模户型

## UG10-CH10-D095

PDF page: 167; original JSON pointer: `/1903`

l 你可以规定反应程度或转化程度

## UG10-CH10-D096

PDF page: 167; original JSON pointer: `/1904`

RStoic 可以处理一系列反应器中独立发生的反应 它还能进行产品选择性和反应热的

## UG10-CH10-D097

PDF page: 167; original JSON pointer: `/1905`

RGibbs 模型用于模拟单相化学平衡或相平衡和化学平衡同时存在的情况 你必须规定

## UG10-CH10-D098

PDF page: 167; original JSON pointer: `/1906`

你还可以给平衡中的特别相态规定组分 对于每个液体或固体溶液相 你可以使用不

## UG10-CH10-D099

PDF page: 167; original JSON pointer: `/1907`

RGibbs 接受限制的平衡规定 你可以通过规定下列各项来限制平衡

## UG10-CH10-D100

PDF page: 168; original JSON pointer: `/1909`

模拟具有并流和逆流冷却剂物流的反应器 RPlug 只模拟基于速度的动力学反应

## UG10-CH10-D101

PDF page: 168; original JSON pointer: `/1910`

对于半间歇反应器 你可以规定一个连续的放空和任意多的连续的或延迟的进料

## UG10-CH10-D102

PDF page: 168; original JSON pointer: `/1911`

RBatch 只模拟基于速度的动力学反应

## UG10-CH10-D103

PDF page: 168; original JSON pointer: `/1912`

当需要或已知有关能量的信息例如功率需要时 泵和压缩机模块可以模拟改变压力

## UG10-CH10-D104

PDF page: 168; original JSON pointer: `/1913`

游离水可以从 Pump 或 Comp 产品中 或者从 MCompr 的中间冷却器中析出 如果仅计算

## UG10-CH10-D105

PDF page: 168; original JSON pointer: `/1914`

压力改变 可用其它模型 例如 Heater 或 Valve

## UG10-CH10-D106

PDF page: 168; original JSON pointer: `/1915`

Pipe 可以计算带有连接件的一段单独的管线的压降和热传递

## UG10-CH10-D107

PDF page: 168; original JSON pointer: `/1916`

Pump 用于模拟一个泵或液压透平 该模型可用于当给定出口压力规定时 计算所需的

## UG10-CH10-D108

PDF page: 168; original JSON pointer: `/1917`

功率或产生的功率 也可以在给定功率规定的时候 计算出口压力

## UG10-CH10-D109

PDF page: 169; original JSON pointer: `/1919`

Compr 可以在给定一个出口压力规定时计算所需的功率 或者在给定功率时 计算出

## UG10-CH10-D110

PDF page: 169; original JSON pointer: `/1920`

MCompr 在每个压缩级之间有一台中间冷却器 一个接在最后压缩级之后的后冷却器

## UG10-CH10-D111

PDF page: 170; original JSON pointer: `/1922`

Mult 通过你规定的一个因子来倍增物流 不能保持热量平衡和物料平衡 出口物流和

## UG10-CH10-D112

PDF page: 170; original JSON pointer: `/1923`

Dupl 可以把入口物流复制成任意数目的出口物流 该模型不能满足物料平衡和热量平

## UG10-CH10-D113

PDF page: 170; original JSON pointer: `/1924`

ClChng 用于在模块和流程段之间改变物流类 它把入口物流中的子物流复制成相应的

## UG10-CH10-D114

PDF page: 170; original JSON pointer: `/1925`

能量平衡的计算 你可以选择决定晶体尺寸分布的选项

## UG10-CH10-D115

PDF page: 170; original JSON pointer: `/1926`

结晶器假定留在结晶器中的产品淤浆处于平衡状态 产品淤浆中的母液是饱和的

## UG10-CH10-D116

PDF page: 171; original JSON pointer: `/1928`

网式过滤器会从你规定的筛网开孔尺寸来计算它的分离效率

## UG10-CH10-D117

PDF page: 172; original JSON pointer: `/1930`

这些模型可以模拟任何单元操作模型 你必须写一个 Fortran 子程序来计算出口物流的

## UG10-CH10-D118

PDF page: 172; original JSON pointer: `/1931`

值 该子程序是基于入口物流和你所规定的参数的

## UG10-CH10-D119

PDF page: 173; original JSON pointer: `/1933`

对于每个单元操作模块 你必须在 Block 模块 窗口上输入规定 要访问这些窗口

## UG10-CH10-D120

PDF page: 173; original JSON pointer: `/1934`

1. 在流程图上选择模块

## UG10-CH10-D121

PDF page: 173; original JSON pointer: `/1935`

2. 在模块上单击鼠标右键

## UG10-CH10-D122

PDF page: 173; original JSON pointer: `/1936`

3. 在出现的弹出式菜单中 单击 Input 输入

## UG10-CH10-D123

PDF page: 173; original JSON pointer: `/1937`

4. 选择合适的窗口和页 替换一个模块的全局规定 用一个模块的 BlockOptions 模块选项 窗口可以替换下列参数的全局值 选项 在页上规定全局级值 在 Block 页上规定局部值 Physical Property Method, Henry’s Components Properties Specifications Global BlockOptions Properties Simulation Diagnostic Message Level

## UG10-CH10-D124

PDF page: 173; original JSON pointer: `/1938`

Setup Specifications

## UG10-CH10-D125

PDF page: 173; original JSON pointer: `/1939`

Perform Heat Balance

## UG10-CH10-D126

PDF page: 173; original JSON pointer: `/1940`

Setup Simulation Options

## UG10-CH10-D127

PDF page: 173; original JSON pointer: `/1941`

Use Results from Previous

## UG10-CH10-D128

PDF page: 173; original JSON pointer: `/1942`

Valid Phases Setup Specifications Global Input Specifications

## UG10-CH10-D129

PDF page: 173; original JSON pointer: `/1943`

替换全局物性规定的一个示例

## UG10-CH10-D130

PDF page: 173; original JSON pointer: `/1944`

在 Properties Specifications Global 全局物性规定 页中规定的 Base Method 基本方

## UG10-CH10-D131

PDF page: 173; original JSON pointer: `/1945`

法 和 Henry’s Components 亨利组分 项中 用 NRTL Method NRTL 方法 和

## UG10-CH10-D132

PDF page: 173; original JSON pointer: `/1946`

Henry1(Henry ’sComponents) 亨利组分 来替换全局值

## UG10-CH10-D133

PDF page: 174; original JSON pointer: `/1948`

要求加热 /冷却曲 线计算

## UG10-CH10-D134

PDF page: 174; original JSON pointer: `/1949`

很多单元操作模块都能生成加热/冷却曲线

## UG10-CH10-D135

PDF page: 174; original JSON pointer: `/1950`

1. 打开该模块的 Data Browser(数据浏览 树 选择 Hcurves 热曲线 文件夹

## UG10-CH10-D136

PDF page: 174; original JSON pointer: `/1951`

2. 在 Hcurves Object Manager 热曲线对象管理器 中 单击 New 新的

## UG10-CH10-D137

PDF page: 174; original JSON pointer: `/1952`

3. 在 Create New ID 创建新 ID 对话框中 输入一个 ID 值或接受缺省的 ID 值 ID 值必须是一个整数

## UG10-CH10-D138

PDF page: 174; original JSON pointer: `/1953`

所选的变量是变化的 以生成中间点

## UG10-CH10-D139

PDF page: 174; original JSON pointer: `/1954`

5. 要定义中间点 需规定下列之一 规定 … 在… 点数 Number of DataPoints (数据点数 点与点之间的增量值 Increment Size 间隔尺寸 独立变量的值列表 List of Values 值列表

## UG10-CH10-D140

PDF page: 175; original JSON pointer: `/1956`

如果你规定了 Number of Data Points (数据点数 中间点就会被平均地放在入口和出口 点之间

## UG10-CH10-D141

PDF page: 175; original JSON pointer: `/1957`

正文待来源表达/OCR边界复核；原文本 SHA256: `d47c47ad03455395611870138408b0427bae53b6c705758d79dc1ac756825443`。

## UG10-CH10-D142

PDF page: 175; original JSON pointer: `/1958`

你也可以要求一些要在 Additional Properties 其它物性 页上计算的其它的物性

## UG10-CH10-D143

PDF page: 175; original JSON pointer: `/1959`

Properties PropSets 物性集 文件夹中的许多 Properties Sets 物性集 都是有效的

## UG10-CH10-D144

PDF page: 175; original JSON pointer: `/1960`

7. 选择一个 Property 物性 集 单击左箭头可以在 Available Property Sets 有效的 物性集 列表和 Sele cted Property Sets 已选的物性集 列表之间移动 Property Set 物性集 要同时把所有的物性集从一个表移动到另一个表中 单击相应的双箭 头 如果你要用这种热 /冷曲线来进行换热器的设计 选择内部物性集 HXDESIGN HXDESIGN 能够用来自于 HTRI HTFS 和 B-JAC 的设计程序计算所需要的全部物性

## UG10-CH10-D145

PDF page: 175; original JSON pointer: `/1961`

ASPEN PLUS 还包括一个接口程序 HTXINT 用于把热/冷曲线结果传递到这些程序中

## UG10-CH10-D146

PDF page: 175; original JSON pointer: `/1962`

生成一个包括换热器设计物性的热曲线 每十度生成一个点

## UG10-CH10-D147

PDF page: 176; original JSON pointer: `/1964`

模拟运行后 生成了一个数据表

## UG10-CH10-D148

PDF page: 177; original JSON pointer: `/1966`

由计算结果可以生成一个曲线图

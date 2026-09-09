# UG10-CH36 Detail Operation Index - 第36章 物流汇总格式

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH36-D001

PDF page: 510; original JSON pointer: `/6154`

在 ASPEN PLUS 中 用表格格式文件 TFFs 可以定制物流报告和表格 使用 TFF 语

## UG10-CH36-D002

PDF page: 510; original JSON pointer: `/6155`

l 为方便分析模拟结果 可以定制适合你自己格式的 Result Summary Streams(结果

## UG10-CH36-D003

PDF page: 510; original JSON pointer: `/6156`

物流汇总表)和 Block StreamResult(模块物流结果)表

## UG10-CH36-D004

PDF page: 510; original JSON pointer: `/6157`

表格式文件含有你能够使用的易懂的语言

## UG10-CH36-D005

PDF page: 510; original JSON pointer: `/6158`

l 按规定顺序显示一个物流性质选定的列表

## UG10-CH36-D006

PDF page: 510; original JSON pointer: `/6159`

l 添加或改变物流性质标签

## UG10-CH36-D007

PDF page: 510; original JSON pointer: `/6160`

本章说明了如何创建和使用 TFFs 提供了 TFFs 示例 如果你想在工艺流程图 PFD

## UG10-CH36-D008

PDF page: 510; original JSON pointer: `/6161`

关于 ASPEN PLUS 表格格式文件

## UG10-CH36-D009

PDF page: 510; original JSON pointer: `/6162`

ASPEN PLUS 在系统路径下提供一些表格格式文件 如果在缺省路径下安装 ASPEN

## UG10-CH36-D010

PDF page: 510; original JSON pointer: `/6163`

PLUS 则系统路径是 ProgramFile\AP10UI\xeq.

## UG10-CH36-D011

PDF page: 510; original JSON pointer: `/6164`

在缺省情况下 ASPEN PLUS 显示物流汇总和物流表 物流汇总和物流表是建立在你

## UG10-CH36-D012

PDF page: 510; original JSON pointer: `/6165`

创建模拟时选择的 Application Type(应用类型)内置的 TFF 基础上的

## UG10-CH36-D013

PDF page: 510; original JSON pointer: `/6166`

选择一个物流格式显示系统报告 从

## UG10-CH36-D014

PDF page: 510; original JSON pointer: `/6167`

l 在 Setup Specifications Stream Report 安装规定物流报告 上的物流格式区域

## UG10-CH36-D015

PDF page: 510; original JSON pointer: `/6168`

l 在 ResultsSummary Streams Material 结果汇总物料 页上的或模块 StreamResults

## UG10-CH36-D016

PDF page: 510; original JSON pointer: `/6169`

Material 物流结果原料 页上的格式区域

## UG10-CH36-D017

PDF page: 510; original JSON pointer: `/6170`

所有的 TFF 文件不是位于系统路径下就是在列表中显示的工作路径下 你可以修改任

## UG10-CH36-D018

PDF page: 510; original JSON pointer: `/6171`

何 ASPEN PLUS TFF 或创建你自己的 TFF TFF 文件应该或者位于你的工作路径下或者位

## UG10-CH36-D019

PDF page: 510; original JSON pointer: `/6172`

ASPEN PLUS 使用显示的 Results Summary Stream 物流结果汇总 页上的区域中选择

## UG10-CH36-D020

PDF page: 510; original JSON pointer: `/6173`

的 TFF 直到你又选择另一个 TFF

## UG10-CH36-D021

PDF page: 510; original JSON pointer: `/6174`

1. 转到 Setup Specifications Stream Report 页 或 ResultsSummary Streams Material 页 或模块 StreamResults Material 页上的 Stream Format(物流格式)区域上

## UG10-CH36-D022

PDF page: 510; original JSON pointer: `/6175`

2. 单击列表和滚动条浏览选项 浏览每个 TFF 说明

## UG10-CH36-D023

PDF page: 510; original JSON pointer: `/6176`

3. 选择一个 TFF 如果你用内置的 TFFs 建议你在其中选择一个与你 Application Type 应用类型 相对应的 TFF 例如 如果你用 Petroleum Application Types 石油应 用类型 中的一种 要选择一个以 Petro 开头的 TFF 要用另一个格式浏览结果 不必重新运行模拟模型 创建一个 TFF 你能够

## UG10-CH36-D024

PDF page: 510; original JSON pointer: `/6177`

l 编辑由 ASPEN PLUS 提供的 TFFs 定制你的物流汇总和物流表格 如果你用缺省

## UG10-CH36-D025

PDF page: 510; original JSON pointer: `/6178`

的路径安装 ASPEN PLUS 这些文件位于 ProgramFile\AP10UI\xeq 路径下

## UG10-CH36-D026

PDF page: 510; original JSON pointer: `/6179`

l 用 TFF 语言创建你自己的 TFF

## UG10-CH36-D027

PDF page: 511; original JSON pointer: `/6181`

下述各节描述了怎样编辑和创建一个新的 TFF你也可以参考本章结尾包括 TFF的示例

## UG10-CH36-D028

PDF page: 511; original JSON pointer: `/6182`

STREAMS=value

## UG10-CH36-D029

PDF page: 511; original JSON pointer: `/6183`

DISPLAY qualifier optional qualifier=value option=value

## UG10-CH36-D030

PDF page: 511; original JSON pointer: `/6184`

SUBSTREAM COMPS PHASE BASIS TEMP PRES LVPCT COMP-ATTR

## UG10-CH36-D031

PDF page: 511; original JSON pointer: `/6185`

FORMAT PPM PPB TRACE TRACE-LABEL ZERO-LABEL MISSING-LABEL

## UG10-CH36-D032

PDF page: 511; original JSON pointer: `/6186`

PROP-HEADER COMPS-HEADER SUBSTREAM-HEADER PB-HEADER

## UG10-CH36-D033

PDF page: 511; original JSON pointer: `/6187`

TEMP-HEADER PRES-HEADER LVPCT-HEADER COMP-ATTR-HEADER

## UG10-CH36-D034

PDF page: 511; original JSON pointer: `/6188`

SUBS-ATTR-HEADER COMP-ATTR-ELEM SUBS-ATTR-ELEM

## UG10-CH36-D035

PDF page: 511; original JSON pointer: `/6189`

SUBSTREAM COMPS PHASE BASIS TEMP PRES LVPCT

## UG10-CH36-D036

PDF page: 511; original JSON pointer: `/6190`

COMP-ATTR SUBS-ATTR

## UG10-CH36-D037

PDF page: 511; original JSON pointer: `/6191`

FORMAT PROP-LABEL UNITS UNITS-LABEL NORMALIZE SCALE

## UG10-CH36-D038

PDF page: 511; original JSON pointer: `/6192`

MISSING-LABEL MW BP MW-BP-FORMAT HEADER PROP-HEADER

## UG10-CH36-D039

PDF page: 511; original JSON pointer: `/6193`

COMPS-HEADER SUBSTREAM-HEADER PB-HEADER TEMP-HEADER

## UG10-CH36-D040

PDF page: 511; original JSON pointer: `/6194`

PRES-HEADER LVPCT-HEADER COMP-ATTR-HEADER

## UG10-CH36-D041

PDF page: 511; original JSON pointer: `/6195`

COMP-ATTR-ELEM SUBS-ATTR-ELEM

## UG10-CH36-D042

PDF page: 511; original JSON pointer: `/6196`

TITLE 物流表标题 在 TFF 中 TITLE 必须是第一个非注释行 如果你隐藏

## UG10-CH36-D043

PDF page: 511; original JSON pointer: `/6197`

一个物流表 TITLE 不重复 TITLE 在 Results Summary Streams 表中不

## UG10-CH36-D044

PDF page: 511; original JSON pointer: `/6198`

TITLE=YES....................... 使用在 Setup Specifications 窗口中规

## UG10-CH36-D045

PDF page: 512; original JSON pointer: `/6200`

定的标题 如果在 Setup pecifications

## UG10-CH36-D046

PDF page: 512; original JSON pointer: `/6201`

窗口中没规定标题 就使用 Heat and

## UG10-CH36-D047

PDF page: 512; original JSON pointer: `/6202`

TITLE=NO......................... 不显示标题 缺省

## UG10-CH36-D048

PDF page: 512; original JSON pointer: `/6203`

STREAMS 用来定义 Results Summary Streams 窗口和物流表中的一组物流和物流

## UG10-CH36-D049

PDF page: 512; original JSON pointer: `/6204`

STREAMS=sid-list........... 物流标识列表 如果在 TFF 中没有

## UG10-CH36-D050

PDF page: 512; original JSON pointer: `/6205`

STREAMS 语句 所有物流将按字母

## UG10-CH36-D051

PDF page: 512; original JSON pointer: `/6206`

数字顺序显示 缺省 你能在 Results

## UG10-CH36-D052

PDF page: 512; original JSON pointer: `/6207`

Summary Streams 窗口中交互选择物

## UG10-CH36-D053

PDF page: 512; original JSON pointer: `/6208`

STREAM-ID-LABEL=NO.. 不显示 Stream ID 行 缺省

## UG10-CH36-D054

PDF page: 512; original JSON pointer: `/6209`

SOURCE-LABEL=NO...... 不显示源模块行 缺省

## UG10-CH36-D055

PDF page: 512; original JSON pointer: `/6210`

DEST-LABEL=NO............ 不显示终模块行 缺省

## UG10-CH36-D056

PDF page: 512; original JSON pointer: `/6211`

PHASE-LABEL=NO......... 不显示相态行 缺省

## UG10-CH36-D057

PDF page: 512; original JSON pointer: `/6212`

可选语句 当有两个或更多 物流 时你可以控制性质显示 你可以把

## UG10-CH36-D058

PDF page: 512; original JSON pointer: `/6213`

起来 定义 DISPLAY 语句组 APSEN PLUS 一次显示 DISPLAY 语句

## UG10-CH36-D059

PDF page: 512; original JSON pointer: `/6214`

规定的一个子物流的性质 在所有必须的子物流之间循环

## UG10-CH36-D060

PDF page: 513; original JSON pointer: `/6216`

DISPLAY 用来控制物流性质显示 DISPLAY 通常用于连接一个或多个 PROP 语

## UG10-CH36-D061

PDF page: 513; original JSON pointer: `/6217`

句 PROP 语句能控制各物性的显示和顺序 在一个 TFF 中可以有任何

## UG10-CH36-D062

PDF page: 513; original JSON pointer: `/6218`

数量的 DISPLAY 语句

## UG10-CH36-D063

PDF page: 513; original JSON pointer: `/6219`

DISPLAY ALL .................. 显示所有由规定的限定语句标识的

## UG10-CH36-D064

PDF page: 513; original JSON pointer: `/6220`

物流 性质 见本章 DISPLAY 和

## UG10-CH36-D065

PDF page: 513; original JSON pointer: `/6221`

说明的格式 见本章 DISPLAY 和

## UG10-CH36-D066

PDF page: 513; original JSON pointer: `/6222`

DISPLAY ONLY ............... 只显示在 DISPLAY ONLY 语句后的

## UG10-CH36-D067

PDF page: 513; original JSON pointer: `/6223`

PROP 语句规定的物流性质 使用由

## UG10-CH36-D068

PDF page: 513; original JSON pointer: `/6224`

限定语句和选项规定的 PROP 语句顺

## UG10-CH36-D069

PDF page: 513; original JSON pointer: `/6225`

DISPLAY REMAIN........... 显示其它物流性质 那些 DISPLAY

## UG10-CH36-D070

PDF page: 513; original JSON pointer: `/6226`

或 PROP 语句没规定的物流性质

## UG10-CH36-D071

PDF page: 513; original JSON pointer: `/6227`

根据选项说明的格式 由规定的限定

## UG10-CH36-D072

PDF page: 513; original JSON pointer: `/6228`

PROP 用来控制各性质的显示 和 DISPLAY ONLY 连接使用 PROP 语句规

## UG10-CH36-D073

PDF page: 513; original JSON pointer: `/6229`

定物性的显示顺序 参见本章 DISPLAY 和 PROP 的限定语句说明

## UG10-CH36-D074

PDF page: 513; original JSON pointer: `/6230`

和 DISPLAY 和 PROP 的选项说明

## UG10-CH36-D075

PDF page: 513; original JSON pointer: `/6231`

Prop-Set 名 例如 MOLEFLMX 是

## UG10-CH36-D076

PDF page: 513; original JSON pointer: `/6232`

Prop-Sets 窗口的 Property 区域中 在

## UG10-CH36-D077

PDF page: 513; original JSON pointer: `/6233`

须是 基本物流结果性质 中的一个

## UG10-CH36-D078

PDF page: 513; original JSON pointer: `/6234`

性质 或者该性质必须是包括在

## UG10-CH36-D079

PDF page: 513; original JSON pointer: `/6235`

Setup Specification Stream Report 窗

## UG10-CH36-D080

PDF page: 513; original JSON pointer: `/6236`

识中 所有这样的性质都按你运行的

## UG10-CH36-D081

PDF page: 513; original JSON pointer: `/6237`

如果你的 TFF 要求的物流性质没在 该表中或没包括在物性集标识中 ASPEN PLUS 不显示该性质 当 ASPEN PLUS 显示性质时 用 PROP 语句规定的选项和 DISPLAY 选 项结合在一起 如果 PROP 和前面的 DISPLAY 语句规定了同一个选项 使用 PROP 的规定 TEXT 在你的物流表副标签内可以插入一行文本 用双引号把文本行引起来 要插入空行 在双引号之间用空格

## UG10-CH36-D082

PDF page: 514; original JSON pointer: `/6239`

下表列出了基本物流结果性质

## UG10-CH36-D083

PDF page: 514; original JSON pointer: `/6240`

MOLEFLOW* 组分摩尔流量

## UG10-CH36-D084

PDF page: 514; original JSON pointer: `/6241`

MOLEFRAC * 组分摩尔分率

## UG10-CH36-D085

PDF page: 514; original JSON pointer: `/6242`

MOLEFLMX 总摩尔流量

## UG10-CH36-D086

PDF page: 514; original JSON pointer: `/6243`

HMX 焓 ( 按摩尔 质量 和流量基准)

## UG10-CH36-D087

PDF page: 514; original JSON pointer: `/6244`

SMX 熵 ( 按摩尔和质量基准)

## UG10-CH36-D088

PDF page: 514; original JSON pointer: `/6245`

RHOMX 密度(按摩尔和质量基准)

## UG10-CH36-D089

PDF page: 514; original JSON pointer: `/6246`

COMP-ATTR 组分属性

## UG10-CH36-D090

PDF page: 514; original JSON pointer: `/6247`

CMOLE_TIME** 实际操作期间组分摩尔流率

## UG10-CH36-D091

PDF page: 514; original JSON pointer: `/6248`

CMOLE_CYCLE** 每个周期的组分摩尔数

## UG10-CH36-D092

PDF page: 514; original JSON pointer: `/6249`

MOLE_TIME ** 实际操作期间总摩尔流率

## UG10-CH36-D093

PDF page: 514; original JSON pointer: `/6250`

MOLE_CYCLE** 每个周期的总摩尔数

## UG10-CH36-D094

PDF page: 514; original JSON pointer: `/6251`

* 只有在 Setup.Main 表中选中相应选项 性质才是可用的

## UG10-CH36-D095

PDF page: 514; original JSON pointer: `/6252`

** 批物流性质. 只有用 Report.Batch-Operation表时才显示

## UG10-CH36-D096

PDF page: 514; original JSON pointer: `/6253`

DISPLAY 和 PROP 限定语句说明

## UG10-CH36-D097

PDF page: 514; original JSON pointer: `/6254`

本节说明在 DISPLAY 和 PROP 语句都能用到的限定语句 你可以认为把 DISPLAY 和

## UG10-CH36-D098

PDF page: 514; original JSON pointer: `/6255`

PROP 限定语句结合起来作为一个性质过滤器 在通过过滤器的物流报告中的性质都能显示

## UG10-CH36-D099

PDF page: 515; original JSON pointer: `/6257`

出来 所列出的限定语句除 UNITS 外都能对 Prop-Set 性质进行规定 见本章的 DISPLAY

## UG10-CH36-D100

PDF page: 515; original JSON pointer: `/6258`

或 PROP 选项说明 能用到基本物流报告性质的限定语句只有 SUBSTREAM 和 COMPS

## UG10-CH36-D101

PDF page: 515; original JSON pointer: `/6259`

如果 PHASE 或 BASIS 限定语句没设成缺省 ALL 而是其它任何值时 基本物流结果性质 都不显示 SUBSTREAM .................. . 要显示性质的子物流 SUBSTREAM=ssid-list .... 子物流标识列表 SUBSTREAM=ALL.......... 所有子物流 缺省 COMPS............................. 要显示性质的组分 COMPS=cid-list................ 组分标识列表

## UG10-CH36-D102

PDF page: 515; original JSON pointer: `/6260`

COMPS=ALL .................... 所有组分 缺省

## UG10-CH36-D103

PDF page: 515; original JSON pointer: `/6261`

PHASE ............................. 要显示性质的相态

## UG10-CH36-D104

PDF page: 515; original JSON pointer: `/6262`

PHASE=ALL .................. 在物流报告中的所有性

## UG10-CH36-D105

PDF page: 515; original JSON pointer: `/6263`

BASIS............................... 要显示性质的基准

## UG10-CH36-D106

PDF page: 515; original JSON pointer: `/6264`

TEMP................................ 要显示性质的温度

## UG10-CH36-D107

PDF page: 515; original JSON pointer: `/6265`

TEMP=ALL..................... 物流报告中所有性质的

## UG10-CH36-D108

PDF page: 515; original JSON pointer: `/6266`

PRES................................ 要显示性质的压力

## UG10-CH36-D109

PDF page: 515; original JSON pointer: `/6267`

PRES=ALL.................... 物流报告中所有性质的

## UG10-CH36-D110

PDF page: 515; original JSON pointer: `/6268`

LVPCT............................. 要显示性质的液体体积百分数

## UG10-CH36-D111

PDF page: 515; original JSON pointer: `/6269`

LVPCT=ALL.................. 物流报告中所有液体性

## UG10-CH36-D112

PDF page: 515; original JSON pointer: `/6270`

COMP-ATTR ................... 要显示的组分属性

## UG10-CH36-D113

PDF page: 515; original JSON pointer: `/6271`

COMP-ATTR=cattr-list .. 组分属性列表

## UG10-CH36-D114

PDF page: 515; original JSON pointer: `/6272`

COMP-ATTR=ALL ......... 所有组分属性 缺省

## UG10-CH36-D115

PDF page: 515; original JSON pointer: `/6273`

SUBS-ATTR..............…... 要显示的子物流属性

## UG10-CH36-D116

PDF page: 515; original JSON pointer: `/6274`

SUBS-ATTR=ALL .......... 所有子物流属性 缺省

## UG10-CH36-D117

PDF page: 515; original JSON pointer: `/6275`

DISPLAY 和 PROP 选项说明

## UG10-CH36-D118

PDF page: 515; original JSON pointer: `/6276`

该节说明 DISPLAY和 PROP语句选项 这些选项控制显示 副标签和物性值的单位

## UG10-CH36-D119

PDF page: 515; original JSON pointer: `/6277`

FORMAT....................... 物流性质数值的显示格式字符串 用双引号引起 缺省=显

## UG10-CH36-D120

PDF page: 515; original JSON pointer: `/6278`

示最大精度 G 格式 见本章 数字格式 DISPLAY 和 PROP

## UG10-CH36-D121

PDF page: 516; original JSON pointer: `/6280`

Viscosity 标签替换 ASPEN PLUS 性质名 MUMX 只适用于

## UG10-CH36-D122

PDF page: 516; original JSON pointer: `/6281`

PROP 语句 在物流汇总中可能被截短了 但在物流表中显示

## UG10-CH36-D123

PDF page: 516; original JSON pointer: `/6282`

UNITS ............................ 物流性质数据度量单位 Setup.Units-Set1 Setup.Units-Set2 和

## UG10-CH36-D124

PDF page: 516; original JSON pointer: `/6283`

Setup.Units-Set3 表 用双引号括起 性质数据可转换成你所

## UG10-CH36-D125

PDF page: 516; original JSON pointer: `/6284`

规定的 一股物流可以有一种或多种度量单位类型 例如 一

## UG10-CH36-D126

PDF page: 516; original JSON pointer: `/6285`

股物流的焓可以是摩尔焓 质量焓和流量焓 这样所规定的单

## UG10-CH36-D127

PDF page: 516; original JSON pointer: `/6286`

位既规定了单位也规定了单位类型 如果不规定单位 物性的

## UG10-CH36-D128

PDF page: 516; original JSON pointer: `/6287`

单位将是可得到的单位类型 如果你在 Results Summary

## UG10-CH36-D129

PDF page: 516; original JSON pointer: `/6288`

Streams 表上选择一个单位集 单位规定将被替代 但仍支持

## UG10-CH36-D130

PDF page: 516; original JSON pointer: `/6289`

选择单位类型 只适用于 PROP 缺省=基本物流结果性质是全

## UG10-CH36-D131

PDF page: 516; original JSON pointer: `/6290`

ASPEN PLUS Units 标签 例如 可以用小写字母打印单位标

## UG10-CH36-D132

PDF page: 516; original JSON pointer: `/6291`

签 只适用于 PROP 语句 并且只有规定 UNITS 限定语句时才

## UG10-CH36-D133

PDF page: 516; original JSON pointer: `/6292`

NORMALIZE=NO ......... 数值不圆整 缺省

## UG10-CH36-D134

PDF page: 516; original JSON pointer: `/6293`

适用于 DISPLAY 和 PROP 语句

## UG10-CH36-D135

PDF page: 516; original JSON pointer: `/6294`

SCALE.......................... 比例系数 物性数据在显示前被该系数除 减少打印值的大小

## UG10-CH36-D136

PDF page: 516; original JSON pointer: `/6295`

你也必须要规定 SCALE-LABEL 只适用于 PROP 语句

## UG10-CH36-D137

PDF page: 516; original JSON pointer: `/6296`

UNITS-LABEL之前 只适用于 PROP 语句

## UG10-CH36-D138

PDF page: 516; original JSON pointer: `/6297`

PPM............................... 每百万切换值 物性值低于规定值时用 PPM 显示 例如 如

## UG10-CH36-D139

PDF page: 516; original JSON pointer: `/6298`

果你规定 PPM=1E-3小于 0.001的物性值按 1 PPM 到 999PPM

## UG10-CH36-D140

PDF page: 516; original JSON pointer: `/6299`

显示 只适用于组分的流量和分率 参见本章 NORMALIZE

## UG10-CH36-D141

PDF page: 516; original JSON pointer: `/6300`

选项 和 PPM PPB 和 TRACE 选项 适用于 DISPLAY 和

## UG10-CH36-D142

PDF page: 516; original JSON pointer: `/6301`

PPB.............................… 每十亿切换值 物性值低于规定值时用 PPB 显示 例如 如果

## UG10-CH36-D143

PDF page: 516; original JSON pointer: `/6302`

你规定 PPB=1E-6小于 0.000001的物性值按 1 PPB 到 999PPB

## UG10-CH36-D144

PDF page: 516; original JSON pointer: `/6303`

TRACE ........................ 跟踪切换值 小于规定切换值的物性值不显示 而显示由

## UG10-CH36-D145

PDF page: 516; original JSON pointer: `/6304`

TRACE-LABEL 规定的字符串 适用于 DISPLAY 和 PROP 语

## UG10-CH36-D146

PDF page: 516; original JSON pointer: `/6305`

TRACE-LABEL ......... 跟踪符号 显示跟踪值 由双引号引起 缺省=空 适用于

## UG10-CH36-D147

PDF page: 516; original JSON pointer: `/6306`

DISPLAY 和 PROP 语句

## UG10-CH36-D148

PDF page: 516; original JSON pointer: `/6307`

ZERO-LABEL............. 零值标签 由双引号引起 缺省=0.0 适用于 DISPLAY 和

## UG10-CH36-D149

PDF page: 516; original JSON pointer: `/6308`

MISSING-LABEL ...... 不计算物性值标签 由双引号引起 缺省=空 适用于 DISPLAY

## UG10-CH36-D150

PDF page: 516; original JSON pointer: `/6309`

MW............................... 分子量显示 只适用于相关组分物性 在物流汇总或物流表中

## UG10-CH36-D151

PDF page: 516; original JSON pointer: `/6310`

MW=YES ..................... 组分标识下一个显示分

## UG10-CH36-D152

PDF page: 516; original JSON pointer: `/6311`

MW=NO........................ 不显示分子量 缺省

## UG10-CH36-D153

PDF page: 516; original JSON pointer: `/6312`

只适用于 PROP 语句

## UG10-CH36-D154

PDF page: 517; original JSON pointer: `/6314`

BP................................. 沸点显示 只适用于相关组分物性 在物流汇总或物流表中单

## UG10-CH36-D155

PDF page: 517; original JSON pointer: `/6315`

BP=YES......................... 组分标识下一个显示沸

## UG10-CH36-D156

PDF page: 517; original JSON pointer: `/6316`

BP=NO .......................... 不显示沸点 缺省

## UG10-CH36-D157

PDF page: 517; original JSON pointer: `/6317`

只适用于 PROP 语句

## UG10-CH36-D158

PDF page: 517; original JSON pointer: `/6318`

MW-BP-FORMAT....... 分子量或沸点格式串 由双引号引起 缺省=%.0f 参见本

## UG10-CH36-D159

PDF page: 517; original JSON pointer: `/6319`

PROP-HEADER=YES .. 显示物性标签 缺省

## UG10-CH36-D160

PDF page: 517; original JSON pointer: `/6320`

PROP-HEADER=NO.. 不显示物性标签

## UG10-CH36-D161

PDF page: 517; original JSON pointer: `/6321`

PROP-LABEL 的规定

## UG10-CH36-D162

PDF page: 517; original JSON pointer: `/6322`

适用于 DISPLAY 和 PROP 语句

## UG10-CH36-D163

PDF page: 517; original JSON pointer: `/6323`

COMPS-HEADER....... 组分标题 只用于组分相关性质

## UG10-CH36-D164

PDF page: 517; original JSON pointer: `/6324`

COMPS-HEADER=YES 使用组分标题 包含一

## UG10-CH36-D165

PDF page: 517; original JSON pointer: `/6325`

CO MPS-HEADER=NO 不显示组分 ID

## UG10-CH36-D166

PDF page: 517; original JSON pointer: `/6326`

COMPS-HEADER="

## UG10-CH36-D167

PDF page: 517; original JSON pointer: `/6327`

@COMPS (组分 ID)

## UG10-CH36-D168

PDF page: 518; original JSON pointer: `/6329`

适用于 DISPLAY 和 PROP 语句

## UG10-CH36-D169

PDF page: 518; original JSON pointer: `/6330`

PB-HEADER=NO ....... 不显示相基准表头

## UG10-CH36-D170

PDF page: 518; original JSON pointer: `/6331`

TEMP-HEADER ......... 温度表头 当在规定温度下计算物性时使用

## UG10-CH36-D171

PDF page: 518; original JSON pointer: `/6332`

TEMP-HEADER=NO . 不显示温度表头

## UG10-CH36-D172

PDF page: 518; original JSON pointer: `/6333`

PRES-HEADER........... 压力表头 当在规定压力下计算物性时使用

## UG10-CH36-D173

PDF page: 518; original JSON pointer: `/6334`

PRES-HEADER=NO .. 不显示压力表头

## UG10-CH36-D174

PDF page: 518; original JSON pointer: `/6335`

LVPCT-HEADER....... 液体体积百分数表头 只用于液体体积百分数相关性质

## UG10-CH36-D175

PDF page: 519; original JSON pointer: `/6337`

LVPCT-HEADER=NO 不显示液体体积百分

## UG10-CH36-D176

PDF page: 519; original JSON pointer: `/6338`

多用 20 个字符规定 字

## UG10-CH36-D177

PDF page: 519; original JSON pointer: `/6339`

适用于 DISPLAY 和 PROP 语句

## UG10-CH36-D178

PDF page: 519; original JSON pointer: `/6340`

COMP-ATTR-HEADE

## UG10-CH36-D179

PDF page: 519; original JSON pointer: `/6341`

COMP-ATTR-HEADER=YES……

## UG10-CH36-D180

PDF page: 519; original JSON pointer: `/6342`

COMP-ATTR-HEADER=NO……

## UG10-CH36-D181

PDF page: 519; original JSON pointer: `/6343`

COMP-ATTR-HEADER="string"

## UG10-CH36-D182

PDF page: 519; original JSON pointer: `/6344`

20 个字符规定 字符串 内可以使用 TFF 变量 @COMPS ( 组分 ) 和 @COMP-ATTR ( 组分 属性) 适用于 DISPLAY 和 PROP 语句 SUBS-ATTR-HEADER .. 子物流属性表头 SUBS-ATTR-HEADER=YES……… … 使用表 ssid sattr -id 子物流属性表头 缺 省 SUBS-ATTR-HEADER=NO……… ….. 不显示子物流属性表 头 SUBS-ATTR-HEADER="string"… …. 子物流属性表头最多用

## UG10-CH36-D183

PDF page: 519; original JSON pointer: `/6345`

20 个字符规定 字符串 内可以使用 TFF 变量 @SUBS-ATTR ( 子物流 属性) 适用于 DISPLAY 和 PROP 语句 COMP-ATTR-ELEM ... . 显示组分属性元素 例如 组分属性 SULFANAL 有三个元素 PYRITIC, SULFATE, 和 ORGANIC COMP-ATTR-ELEM=cattr-elem-lis t… 组分属性元素列表 COMP-ATTR-ELEM=ALL……… …… 所有元素 缺省

## UG10-CH36-D184

PDF page: 520; original JSON pointer: `/6347`

物流表上显示一个表头 你必须规定YES或提供自己的标签

## UG10-CH36-D185

PDF page: 520; original JSON pointer: `/6348`

规定20个字符 你规定的标签不显示在物流汇总表上

## UG10-CH36-D186

PDF page: 520; original JSON pointer: `/6349`

% 百分号 格式规定头一个字符

## UG10-CH36-D187

PDF page: 520; original JSON pointer: `/6350`

xx 规定转换数字最小长度的数字串 打印时该数字至少占有这些空

## UG10-CH36-D188

PDF page: 520; original JSON pointer: `/6351`

yy 规定精度的数字串 也就是 小数点右侧要打印的数字

## UG10-CH36-D189

PDF page: 520; original JSON pointer: `/6352`

e 数字转换成表[-]a.bbbbbbbe[+]cc b的长度由yy规定 缺省是六位

## UG10-CH36-D190

PDF page: 520; original JSON pointer: `/6353`

在打印数字中的大写E的在规定格式中用大写E

## UG10-CH36-D191

PDF page: 520; original JSON pointer: `/6354`

f 数字转换成表[-]aaa.bbbbbb b的长度由yy规定 缺省是六位

## UG10-CH36-D192

PDF page: 520; original JSON pointer: `/6355`

g 使用较短的%e或%f 在打印数字中的大写G的在规定格式中用大

## UG10-CH36-D193

PDF page: 520; original JSON pointer: `/6356`

建议使用 %10.2f 格式 如果有空位 打印值有两位小数点 如果数字比 9,999,999

## UG10-CH36-D194

PDF page: 520; original JSON pointer: `/6357`

数没被删除 小数点要对齐

## UG10-CH36-D195

PDF page: 520; original JSON pointer: `/6358`

%10.nE 用指数法表示的数字 有n+1个有效数字

## UG10-CH36-D196

PDF page: 520; original JSON pointer: `/6359`

代替 BTU/HR 改选项减少了打印数字的大小 因此它能添到用 f 格式规定的表中

## UG10-CH36-D197

PDF page: 520; original JSON pointer: `/6360`

一些数被强制用 f 格式规定的零值显示成 <数字 在 数字 处是能用格式显示的

## UG10-CH36-D198

PDF page: 520; original JSON pointer: `/6361`

最小数字 例如 数字 0.002 在%10.2f 格式下被显示成<0.01

## UG10-CH36-D199

PDF page: 520; original JSON pointer: `/6362`

NORMALIZE选项用于组分流率或分率 如下表显示

## UG10-CH36-D200

PDF page: 520; original JSON pointer: `/6363`

摩尔流量 MOLEFLOW 相同子物流的总摩尔流量 MOLEFLMX

## UG10-CH36-D201

PDF page: 521; original JSON pointer: `/6365`

摩尔分率 MOLEFRAC 1

## UG10-CH36-D202

PDF page: 521; original JSON pointer: `/6366`

显示组分性质被强制加到圆整值 例如 假设用两位数显示质量分率 如%10.2f 并且

## UG10-CH36-D203

PDF page: 521; original JSON pointer: `/6367`

当你在流量或分率物性上规定格式时 选项 FORMAT, PPM, PPB, 和 TRACE 是相关

## UG10-CH36-D204

PDF page: 521; original JSON pointer: `/6368`

的 例如 假如你有如下规定

## UG10-CH36-D205

PDF page: 521; original JSON pointer: `/6369`

PROP MOLEFLOW FORMAT="%10.3f" PPM=1e-3 PPB=1e-6 TRACE=1e-9

## UG10-CH36-D206

PDF page: 521; original JSON pointer: `/6370`

MOLEFLOW 值被显示成

## UG10-CH36-D207

PDF page: 521; original JSON pointer: `/6371`

不被计算 空或用MISSING-LABEL规定字符串

## UG10-CH36-D208

PDF page: 521; original JSON pointer: `/6372`

0 0.0或用ZERO-LABEL规定字符串 <10-9 空或用TRACE-LABEL规定字符串 10-9≤MOLEFLOW<10-6 1-999PPB 10-6≤MOLEFLOW<10-6 1-999PPM <10-3 <0.001 ≥10-3 用%10.3格式转换的数字 你应该始终保持如下关系 TRACE < PPB < PPM < 格式精度 完整的 TFF示例 下文是系统缺省的 TFF 该 TFF 的意图尽可能模仿 ASPEN PLUS 物流报告

## UG10-CH36-D209

PDF page: 521; original JSON pointer: `/6373`

; This TFF mimics the ASPEN PLUS stream report and reports all

## UG10-CH36-D210

PDF page: 521; original JSON pointer: `/6374`

; calculated properties.

## UG10-CH36-D211

PDF page: 522; original JSON pointer: `/6376`

prop moleflow prop-label="Mole Flow"

## UG10-CH36-D212

PDF page: 522; original JSON pointer: `/6377`

prop molefrac prop-label="Mole Frac"

## UG10-CH36-D213

PDF page: 522; original JSON pointer: `/6378`

prop moleflmx prop-label="Total Flow"

## UG10-CH36-D214

PDF page: 522; original JSON pointer: `/6379`

; batch properties follow

## UG10-CH36-D215

PDF page: 522; original JSON pointer: `/6380`

; first, component -dependent properties

## UG10-CH36-D216

PDF page: 522; original JSON pointer: `/6381`

prop cmole_time prop-label = "Mole Flow"

## UG10-CH36-D217

PDF page: 522; original JSON pointer: `/6382`

prop cmole_cycle prop-label = "Mole/Cycle"

## UG10-CH36-D218

PDF page: 522; original JSON pointer: `/6383`

; overall stre am properties

## UG10-CH36-D219

PDF page: 522; original JSON pointer: `/6384`

prop mole_time prop-label = "Mole Flow"

## UG10-CH36-D220

PDF page: 522; original JSON pointer: `/6385`

prop mole_cycle prop-label = "Mole/Cycle"

## UG10-CH36-D221

PDF page: 522; original JSON pointer: `/6386`

包含了 DISPLAY ALL 关键字 它指令 ASPEN PLUS 在所有子物流间循环 并且显示每个

## UG10-CH36-D222

PDF page: 522; original JSON pointer: `/6387`

PHASE-LABEL)被规定使用缺省值 标题语句的顺序指明了它们在物流表中是如何打印的

## UG10-CH36-D223

PDF page: 522; original JSON pointer: `/6388`

由于这些语句是在所有DISPLAY语句前规定的 在物流表的物流值上面显示表头信息

## UG10-CH36-D224

PDF page: 522; original JSON pointer: `/6389`

无论何时ASPEN PLUS都显示系统缺省的TFF中的性质 可使用相应的性质标签 例如

## UG10-CH36-D225

PDF page: 522; original JSON pointer: `/6390`

当ASPEN PLUS显示密度时 使用 Density 标签 如果没有规定标签 就使用缺省标签

## UG10-CH36-D226

PDF page: 522; original JSON pointer: `/6391`

例如 如果没规定PROP-LABEL="Density" 就使用RHOMX标签

## UG10-CH36-D227

PDF page: 523; original JSON pointer: `/6393`

规定了组分的流量和分率的所有六种组合以预测你的规定 如果ASPEN PLUS没找到你

## UG10-CH36-D228

PDF page: 523; original JSON pointer: `/6394`

规定的性质 将什么都不显示

## UG10-CH36-D229

PDF page: 523; original JSON pointer: `/6395`

为生成的物流表定制一个 TFF的示例

## UG10-CH36-D230

PDF page: 523; original JSON pointer: `/6396`

定制物流表要创建如下TFF文件

## UG10-CH36-D231

PDF page: 523; original JSON pointer: `/6397`

stream -id-label="Streams"

## UG10-CH36-D232

PDF page: 523; original JSON pointer: `/6398`

display only format="%10.2f" substream -header=no

## UG10-CH36-D233

PDF page: 523; original JSON pointer: `/6399`

prop molefrac prop-header="Comp mole fraction" &

## UG10-CH36-D234

PDF page: 523; original JSON pointer: `/6400`

comps-header=" @comps" mw=yes mw -bp-format="%6.1f"

## UG10-CH36-D235

PDF page: 523; original JSON pointer: `/6401`

prop moleflmx prop-label="Total Mole Flow" &

## UG10-CH36-D236

PDF page: 523; original JSON pointer: `/6402`

l 物流 ID 标签是定制的 不打印源和终点标签

## UG10-CH36-D237

PDF page: 523; original JSON pointer: `/6403`

l DISPLAY ONLY 语句限制显示如下性质 组分摩尔分率 总摩尔流量 总质量流

## UG10-CH36-D238

PDF page: 523; original JSON pointer: `/6404`

l 对于摩尔分率 由两个位置标识组分 IDs 分子量在组分 Ids 后面显示 带一位小

## UG10-CH36-D239

PDF page: 523; original JSON pointer: `/6405`

l 摩尔分率可以按 FORMAT TRACE PPM 和 TRACE-LABEL 规定显示 如下表

## UG10-CH36-D240

PDF page: 523; original JSON pointer: `/6406`

MOLEFRAC 值显示成

## UG10-CH36-D241

PDF page: 523; original JSON pointer: `/6407`

0 0.0 <10-7 10-7≤MOLEFRAC 10-6 <1PPM 10-6≤MOLEFRAC 10-3 1-999PPM 10-3≤MOLEFRAC 10-2 <0.01 ≥10-2 转换成 10.2f 格式数字

## UG10-CH36-D242

PDF page: 523; original JSON pointer: `/6408`

l 总摩尔流量要求用单位 LBMOL/DAY 总质量流量要求用 LB/DAY 单位

## UG10-CH36-D243

PDF page: 523; original JSON pointer: `/6409`

l 插入两空行使其好看些

## UG10-CH36-D244

PDF page: 523; original JSON pointer: `/6410`

l 要求三个性质 温度 压力和密度 要定制这些性质的性质标签

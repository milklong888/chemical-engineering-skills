# UG10-CH13 Detail Operation Index - 第13章 操作曲线图

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH13-D001

PDF page: 195; original JSON pointer: `/2250`

本章介绍从任意具有表列数据的输入页或结果页生成曲线图 定制曲线图以及打印曲线

## UG10-CH13-D002

PDF page: 195; original JSON pointer: `/2251`

ASPEN PLUS 曲线图是查看运行数据的非常有效的一个方式 用曲线图可以显示出下

## UG10-CH13-D003

PDF page: 195; original JSON pointer: `/2252`

l 单元操作模块的输入和结果分布

## UG10-CH13-D004

PDF page: 195; original JSON pointer: `/2253`

l 流程建立选项和模型分析工具如 Sensitivity 灵敏度 Optimization 优化 及

## UG10-CH13-D005

PDF page: 195; original JSON pointer: `/2254`

Pres-Relief 卸压 的结果

## UG10-CH13-D006

PDF page: 195; original JSON pointer: `/2255`

与生成曲线图有关的步骤有下列三个

## UG10-CH13-D007

PDF page: 195; original JSON pointer: `/2256`

1. 显示含有绘制曲线图所需数据的页 该页可能含有输入数据 或者含有结果数据

## UG10-CH13-D008

PDF page: 195; original JSON pointer: `/2257`

2. 用下列方法生成曲线图

## UG10-CH13-D009

PDF page: 195; original JSON pointer: `/2258`

l 使用 Plot Wizard 曲线图向导 或者

## UG10-CH13-D010

PDF page: 195; original JSON pointer: `/2259`

l 选择因变量 自变量和参数变量

## UG10-CH13-D011

PDF page: 195; original JSON pointer: `/2260`

3. 定制曲线图外观 第一步 显示数据 要显示数据 可按下列步骤进行

## UG10-CH13-D012

PDF page: 195; original JSON pointer: `/2261`

1. 在 Data 菜单上 单击 Data Browser.

## UG10-CH13-D013

PDF page: 195; original JSON pointer: `/2262`

2. 在左窗格中 单击含有绘制曲线图所需数据的表

## UG10-CH13-D014

PDF page: 195; original JSON pointer: `/2263`

3. 在该表上 单击页显示出数据 该页即可以是输入页 也可以是结果页 但它更常用于绘制结果曲线

## UG10-CH13-D015

PDF page: 195; original JSON pointer: `/2264`

4. 要绘制结果曲线 要保证模拟运行有可用的结果 如果结果是可用的 那么主窗口上的状态消息应为 Results Available 结果可用 Results Available with Warnings 结果可用 但有警告消息 Results Available with Errors 结果可用 但有错误消息 或者 Input Changed 输入已改变 关于给出 结果时的状态消息的详细信息 参见第十二章 如果没有可用的结果 则运行模拟程序

## UG10-CH13-D016

PDF page: 195; original JSON pointer: `/2265`

你可以用下列方法中的任一个生成曲线图

## UG10-CH13-D017

PDF page: 195; original JSON pointer: `/2266`

l 使用 Plot Wizard 曲线图向导

## UG10-CH13-D018

PDF page: 196; original JSON pointer: `/2268`

使用 Plot Wizard

## UG10-CH13-D019

PDF page: 196; original JSON pointer: `/2269`

使用 Plot Wizard 曲线图向导 可通过从预定义的曲线图列表中选择曲线来快速生成一

## UG10-CH13-D020

PDF page: 196; original JSON pointer: `/2270`

个曲线图 对于大部分模块和有结果表格的其它对象 Plot Wizard 曲线图向导 都可用

## UG10-CH13-D021

PDF page: 196; original JSON pointer: `/2271`

在你显示出数据之后 进行下列步骤

## UG10-CH13-D022

PDF page: 196; original JSON pointer: `/2272`

1. 在 Plot 菜单上 单击 Plot Wizard 注释 Plot 菜单只有在当前窗口中有 Data Browser 数据浏览器 时才可看到

## UG10-CH13-D023

PDF page: 196; original JSON pointer: `/2273`

3. 从可用的曲线图列表中选择曲线图类型 然后单击 Next.

## UG10-CH13-D024

PDF page: 196; original JSON pointer: `/2274`

4. 为你已选定的曲线图类型选择选项 可用的选项取决于所选的曲线图类型

## UG10-CH13-D025

PDF page: 196; original JSON pointer: `/2275`

6. 为你已选定的曲线图类型选择通用选项 Plot Wizard 曲线图向导 会指导你完成选项的选择 其中包括

## UG10-CH13-D026

PDF page: 196; original JSON pointer: `/2276`

l 改变 Plot 曲线图 类型

## UG10-CH13-D027

PDF page: 196; original JSON pointer: `/2277`

l 改变 Plot 曲线图 和 Axis 轴线 的标题

## UG10-CH13-D028

PDF page: 196; original JSON pointer: `/2278`

l 选择在获得新结果时是否更新曲线图

## UG10-CH13-D029

PDF page: 196; original JSON pointer: `/2279`

l 选择是否要显示曲线图的图例

## UG10-CH13-D030

PDF page: 196; original JSON pointer: `/2280`

7. 要结束 Plot Wizard 曲线图向导 并生成曲线图 则单击 Finish 有关退出向导后 改变曲线图属性的信息 参见本章的第三步 定制曲线图的外观部分 下面是绘 制 RadFrac塔流量曲线的例子

## UG10-CH13-D031

PDF page: 198; original JSON pointer: `/2283`

通常来说 Plot Wizard 曲线图向导 是生成曲线图最快的途径 但是 如果你所关心的

## UG10-CH13-D032

PDF page: 199; original JSON pointer: `/2285`

曲线图在 Plot Wizard 曲线图向导 中没有 那么你可以通过选择自变量 因变量和参数变

## UG10-CH13-D033

PDF page: 199; original JSON pointer: `/2286`

要选择变量 可按下列步骤进行

## UG10-CH13-D034

PDF page: 199; original JSON pointer: `/2287`

1. 单击要标绘在 X-Axis X 轴 上的数据的列标题

## UG10-CH13-D035

PDF page: 199; original JSON pointer: `/2288`

2. 在 Plot 菜单上 单击 X-Axis Variable X 轴变量

## UG10-CH13-D036

PDF page: 199; original JSON pointer: `/2289`

l 按住 Ctrl 键 并单击要标绘在 Y-Axis Y 轴 上的各个数据列的标题

## UG10-CH13-D037

PDF page: 199; original JSON pointer: `/2290`

l 在菜单上 单击 Y-Axis Variable Y 轴变量

## UG10-CH13-D038

PDF page: 199; original JSON pointer: `/2291`

4. 如果要标绘参数变量则

## UG10-CH13-D039

PDF page: 199; original JSON pointer: `/2292`

l 单击要作为参数变量标绘的数据列的标题

## UG10-CH13-D040

PDF page: 199; original JSON pointer: `/2293`

5. 在 Plot 菜单上 单击 Parametric Variable 参数变量 下表列出了一个曲线图可用的变量类型 变量名 变量类型 可进行的操作 Y-Axis 变量 因变量 你想给一个曲线图选择多少个 Y-Axis 因变量就 可以选择多少个 但是至少必须选择一个 Y-Axis 因变量 X-Axis 变量 自变量 只能选择一个 X 轴自变量 或者接受缺省的自变 量 通常为第一列数据 Parametric 变量 第三个变量 用这个变量可绘制其为不同值时因变量对自变量

## UG10-CH13-D041

PDF page: 199; original JSON pointer: `/2294`

的关系曲线 例如 你可以用灵敏度模块来生成

## UG10-CH13-D042

PDF page: 199; original JSON pointer: `/2295`

添加文本给曲线图加注释 该文本可以与图连接和与之分开开

## UG10-CH13-D043

PDF page: 199; original JSON pointer: `/2296`

把文本与曲线上的一个点相连接 在你缩放曲线图和在曲线图工作空间中滚动光

## UG10-CH13-D044

PDF page: 199; original JSON pointer: `/2297`

标时 该文本一直停在窗口内的同一位置上

## UG10-CH13-D045

PDF page: 199; original JSON pointer: `/2298`

要为一个曲线图添加文本 可按下列步骤进行

## UG10-CH13-D046

PDF page: 199; original JSON pointer: `/2299`

1. 显示出你要为之添加文本的曲线图

## UG10-CH13-D047

PDF page: 200; original JSON pointer: `/2301`

2. 在一条曲线上单击鼠标右键 在出现的弹出菜单上 将光标定位到 Modify 上 然后 单击 Add Text

## UG10-CH13-D048

PDF page: 200; original JSON pointer: `/2302`

3. 用 Plot Text Setting 曲线图文本设置 对话框添加或改变文本 使用的文本页 实现的功能 Text 文本 输入注释文本并规定颜色和定向 Attribute 属性 把文本与数据点连接 你可以不用箭头或用小箭 头 中箭头或大箭头来连接它 缺省情况下是用一个中箭头来连接 可以让文本与谁都不连接 你可规定让它左对齐 右对齐或者居中对齐 缺省情况下是左对齐文本 Font 字体 为文本选择字体 字形和字号

## UG10-CH13-D049

PDF page: 200; original JSON pointer: `/2303`

5. 单击曲线图上想要放置该文本的位置

## UG10-CH13-D050

PDF page: 200; original JSON pointer: `/2304`

6. 如果该文本被连接到一个数据点上 那么 ASPEN PLUS 会自动画一条到最近曲线的 直线 如果这个位置不是你所期望的位置 你可以选择该连接点 并把它拖到曲线 图中任意曲线上的任意点 要修改曲线图上的文本 可按下列步骤进行

## UG10-CH13-D051

PDF page: 200; original JSON pointer: `/2305`

1. 选择你要修改的文本 一旦被选定它即变为高亮度显示

## UG10-CH13-D052

PDF page: 200; original JSON pointer: `/2306`

2. 单击鼠标右键 然后单击 Edit

## UG10-CH13-D053

PDF page: 200; original JSON pointer: `/2307`

3. 用 Plot Text Settings 曲线图文本设置 对话框改变文本内容

## UG10-CH13-D054

PDF page: 200; original JSON pointer: `/2308`

4. 单击 OK 你还可以改变曲线图上的缺省文本字体 有关改变曲线图缺省设置的详细信息 参见本 章的改变曲线图缺省设置部分 改变曲线 图的特性 曲线图的大部分组成要素都可以用 Plot Control Properties 曲线图控制特性 对话框来 修改 要进入这个对话框 方法如下

## UG10-CH13-D055

PDF page: 200; original JSON pointer: `/2309`

Ø 在曲线图上单击鼠标右键 然后在出现的菜单上单击 Properties

## UG10-CH13-D056

PDF page: 200; original JSON pointer: `/2310`

下面各节介绍了可对曲线图进行的改变

## UG10-CH13-D057

PDF page: 200; original JSON pointer: `/2311`

你可以改变一个曲线图上数据线的外观 每个变量的数据线的颜色 线型和点标识符类

## UG10-CH13-D058

PDF page: 200; original JSON pointer: `/2312`

要改变曲线图上数据线的属性 可按下列步骤进行

## UG10-CH13-D059

PDF page: 200; original JSON pointer: `/2313`

2. 在该曲线图上单击鼠标右键 并在出现的菜单上单击 Properties

## UG10-CH13-D060

PDF page: 200; original JSON pointer: `/2314`

3. 单击 Attribute 标签

## UG10-CH13-D061

PDF page: 200; original JSON pointer: `/2315`

5. 为该变量选择 Color 颜色 Marker 标记 Line type 线型

## UG10-CH13-D062

PDF page: 201; original JSON pointer: `/2317`

要在一个曲线图上显示图例 方法如下

## UG10-CH13-D063

PDF page: 201; original JSON pointer: `/2318`

2. 在该曲线图上单击鼠标右键 在弹出的菜单上 将光标定位到 Modify 然后单击 Show Legend 显示图例 修改曲线图的图例 你可以修改图例的正文和字体 步骤如下

## UG10-CH13-D064

PDF page: 201; original JSON pointer: `/2319`

2. 双击图例 或者 在光标指到图例上时 单击鼠标右键 然后再单击 Edit

## UG10-CH13-D065

PDF page: 201; original JSON pointer: `/2320`

3. 在 Plot Legend 曲线图图例 对话框上 单击要改变图例的线 这时它出现在 Legend Text 图例正文 框中

## UG10-CH13-D066

PDF page: 201; original JSON pointer: `/2321`

4. 在 Legend Text 图例正文 框中 改变图例

## UG10-CH13-D067

PDF page: 201; original JSON pointer: `/2322`

5. 单击 Replace

## UG10-CH13-D068

PDF page: 201; original JSON pointer: `/2323`

6. 对于要改变图例的每条线重复第 3 4 步

## UG10-CH13-D069

PDF page: 201; original JSON pointer: `/2324`

7. 在 Font 标签上 可以修改整个图例的字体 图例可以被隐藏 然后还可被显示出来 对图例所做的所有改变都会被保存起来 你还可以改变缺省情况下你的曲线图上是否显示图例 有关改变曲线图缺省设置的详细 信息 参见本章的改变曲线图的缺省设置部分 改变坐标轴的绘制 如果一个曲线图有不止一个因变量 缺省情况下 ASPEN PLUS 对每个因变量使用单独 的纵坐标刻度来显示曲线图 你可以把所有变量都绘制到一个单一的坐标轴中 或者把一组 变量绘制到指定的坐标轴中

## UG10-CH13-D070

PDF page: 201; original JSON pointer: `/2325`

例如 假定你要绘制塔的五个组分的摩尔分率分布图 那么你可以把所有组分按一个单

## UG10-CH13-D071

PDF page: 202; original JSON pointer: `/2327`

要规定坐标轴的绘制 可按下列步骤进行

## UG10-CH13-D072

PDF page: 202; original JSON pointer: `/2328`

2. 在曲线图上单击鼠标右键 然后在弹出的菜单上单击 Properties

## UG10-CH13-D073

PDF page: 202; original JSON pointer: `/2329`

3. 单击 AxisMap 标签

## UG10-CH13-D074

PDF page: 202; original JSON pointer: `/2330`

5. 下表列出了你可进行的操作 使用 完成 上箭头和下箭头 改变要绘制的坐标轴个数 如果把坐标轴的个数降为零 则不显示该变量的曲线图 All in One按钮 把所有因变量绘制到一个单一的坐标轴上 One for Each 按钮 把每个因变量绘制到单独的坐标轴上

## UG10-CH13-D075

PDF page: 202; original JSON pointer: `/2331`

6. 单击 OK 改变曲线图的标题 通过定制文本的字体 字形和字号可以随时改变曲线图标题的文本 要改变一个指定曲线图的曲线图标题 可按下列步骤进行

## UG10-CH13-D076

PDF page: 202; original JSON pointer: `/2332`

1. 显示出要改变的曲线图

## UG10-CH13-D077

PDF page: 202; original JSON pointer: `/2333`

3. 在 Text 标签上 输入标题的文本

## UG10-CH13-D078

PDF page: 202; original JSON pointer: `/2334`

4. 在 Font 标签上 选择文本的字体 字型和字号 你还可以改变曲线图标题的缺省文本字体 有关改变曲线图缺省设置的详细信息 参见 本章的改变曲线图的缺省设置部分 改变曲线图坐标轴的标签 曲线图坐标轴标签上的文本随时都可以被修改 还可以为每个标签定制字体 字型和字 号 要改变一个指定曲线图的曲线图坐标轴标签 可按下列步骤进行

## UG10-CH13-D079

PDF page: 202; original JSON pointer: `/2335`

2. 双击要改变的坐标轴标签

## UG10-CH13-D080

PDF page: 202; original JSON pointer: `/2336`

3. 在 Text 标签上 输入坐标轴标签的文本

## UG10-CH13-D081

PDF page: 202; original JSON pointer: `/2337`

4. 在 Font 标签上 选择文本的字体 字型和字号

## UG10-CH13-D082

PDF page: 202; original JSON pointer: `/2338`

5. 对你想要修改的其它坐标轴重复第 2 4 步 你还可以改变所有曲线图坐标轴标签的缺省字体 有关改变曲线图缺省设置的详细信 息 参见本章的改变曲线图的缺省设置部分 改变曲线图的坐标轴 为了能看到指定区域中的曲线图 可以改变横坐标和纵坐标的刻度选项 如果一个曲线 图有不止一个纵坐标 可分别改变每个纵坐标的刻度 要改变横坐标和纵坐标的刻度选项 可按下列步骤进行

## UG10-CH13-D083

PDF page: 202; original JSON pointer: `/2339`

2. 双击要改变的坐标值

## UG10-CH13-D084

PDF page: 202; original JSON pointer: `/2340`

3. 选择是用线性标尺 对数标尺还是倒数标尺

## UG10-CH13-D085

PDF page: 203; original JSON pointer: `/2342`

4. 改变 Grid 间隔 或者 要返回到由 ASPEN PLUS 确定的自动的网格间隔 则关闭 Lock grid 锁定网格 选 项

## UG10-CH13-D086

PDF page: 203; original JSON pointer: `/2343`

5. 利用 Axis Range settings 坐标轴范围设置 可只标绘数据的一个子集 或者规定坐 标轴刻度的终点 要返回到由 ASPEN PLUS 确定的自动范围 则从 Range text 范 围文本 框中删除所有输入项 Value Range 数值范围 框 显示在 Axis Range 坐标轴范围 框下面 指示了数 据范围

## UG10-CH13-D087

PDF page: 203; original JSON pointer: `/2344`

6. 如果想把坐标轴反转成显示从原点递减的变量值 则选定 Variable Descends 变量递 减 框

## UG10-CH13-D088

PDF page: 203; original JSON pointer: `/2345`

7. 在 Font 标签上 选择文本的字体 字型和字号 改变曲线图的网格显示 要改变一个指定曲线图的网格和线的显示选项 可按下列步骤进行

## UG10-CH13-D089

PDF page: 203; original JSON pointer: `/2346`

3. 单击 Grid 标签

## UG10-CH13-D090

PDF page: 203; original JSON pointer: `/2347`

4. 改变所要改变的选项 下表列出了你可以改变的显示设置 所选的 曲线图选项 功能 Grid 定义曲线图的网格类型 可选择下列类型

## UG10-CH13-D091

PDF page: 203; original JSON pointer: `/2348`

Line 为数据曲线选择线形 可选择下列类型

## UG10-CH13-D092

PDF page: 204; original JSON pointer: `/2350`

Square plot 正方形曲线图 把横坐标和纵坐标的范围设成一样的

## UG10-CH13-D093

PDF page: 204; original JSON pointer: `/2351`

Marker size 标记大小 修改在曲线图上显示的标记的大小

## UG10-CH13-D094

PDF page: 204; original JSON pointer: `/2352`

你还可以改变曲线图的缺省显示选项 有关改变曲线图缺省设置的详细信息 参见本章

## UG10-CH13-D095

PDF page: 204; original JSON pointer: `/2353`

的改变曲线图的缺省设置部分

## UG10-CH13-D096

PDF page: 204; original JSON pointer: `/2354`

可以把一个时间标记添加到曲线图上 它标记着该曲线图的创建日期和时间 时间标记

## UG10-CH13-D097

PDF page: 204; original JSON pointer: `/2355`

l RunID 运行标识符

## UG10-CH13-D098

PDF page: 204; original JSON pointer: `/2356`

2. 在 Edit 菜单上 单击 Insert Time Stamp 插入时间标记 时间标记是简单的文本 可用修改文本的方法修改时间标记 你还可以改变曲线图的缺省时间标记 有关改变曲线图缺省设置的详细信息 参见本章 的改变曲线图的缺省设置部分 操作曲线图 本节介绍曲线图的操作 其中包括

## UG10-CH13-D099

PDF page: 204; original JSON pointer: `/2357`

l 在结果改变后更新曲线图

## UG10-CH13-D100

PDF page: 204; original JSON pointer: `/2358`

l 利用曲线图比较运行结果

## UG10-CH13-D101

PDF page: 204; original JSON pointer: `/2359`

l 改变曲线图的缺省设置

## UG10-CH13-D102

PDF page: 204; original JSON pointer: `/2360`

如果在重新运行模拟程序时 Plot 曲线图 窗口一直打开着 那么缺省情况下 ASPEN PLUS 会用来自新运行的数据重新绘制曲线图 要在结果改变后更新曲线图 方法如下

## UG10-CH13-D103

PDF page: 204; original JSON pointer: `/2361`

1. 显示出你想要修改的曲线图

## UG10-CH13-D104

PDF page: 204; original JSON pointer: `/2362`

2. 在 Plot 菜单上 单击 Animate Plot 激活曲线图 也可以在 Plot Wizard 曲线图向导 中选择这个选项

## UG10-CH13-D105

PDF page: 205; original JSON pointer: `/2364`

1. 显示出含有要添加到已有曲线图中的数据的页

## UG10-CH13-D106

PDF page: 205; original JSON pointer: `/2365`

2. 选择因变量和自变量 所选的数据必须与已有的曲线图具有一样的 X 轴变量 例如 现有曲线图是温度相 对理论板数的曲线 那么所选数据必须是相对理论板数的数据

## UG10-CH13-D107

PDF page: 205; original JSON pointer: `/2366`

3. 在 Plot 菜单上 单击 Add New Curve 添加新曲线

## UG10-CH13-D108

PDF page: 205; original JSON pointer: `/2367`

4. 在 Plot Window List 曲线图窗口列表 对话框中 单击要向其添加新数据的那个曲 线图

## UG10-CH13-D109

PDF page: 205; original JSON pointer: `/2368`

5. 单击 OK 新曲线即被添加到该曲线图中 利用曲线图比较运行结果 可以使用 Add New Curve 添加新曲线 功能在一个单一曲线图中比较不同运行的结果

## UG10-CH13-D110

PDF page: 205; original JSON pointer: `/2369`

1. 在运行完第一个模拟后 创建一个曲线图

## UG10-CH13-D111

PDF page: 205; original JSON pointer: `/2370`

2. 在 Plot 菜单上 确保 Animate Plot 激活曲线图 选项没被选中

## UG10-CH13-D112

PDF page: 205; original JSON pointer: `/2371`

3. 改变输入规定并重新运行模拟

## UG10-CH13-D113

PDF page: 205; original JSON pointer: `/2372`

4. 显示出含有要与第一次运行比较的数据的结果页 选择与第一个曲线图中一样的自 变量和因变量

## UG10-CH13-D114

PDF page: 205; original JSON pointer: `/2373`

5. 在 Plot 菜单上 单击 Add New Curve 添加新曲线

## UG10-CH13-D115

PDF page: 205; original JSON pointer: `/2374`

6. 在 Plot Window List 曲线图窗口列表 对话框中 单击要向其添加新数据的那个曲 线图

## UG10-CH13-D116

PDF page: 205; original JSON pointer: `/2375`

7. 单击 OK 新曲线将被添加到该曲线图中 从曲线图中删除数据点和曲线 从已有的曲线图中 你可以删除

## UG10-CH13-D117

PDF page: 205; original JSON pointer: `/2376`

你从曲线图中删除数据点后 ASPEN PLUS 会自动重新绘制曲线

## UG10-CH13-D118

PDF page: 205; original JSON pointer: `/2377`

注释 你无法恢复已删除的数据点 要想再看到它们 必须重新生成该曲线图

## UG10-CH13-D119

PDF page: 205; original JSON pointer: `/2378`

要从一个曲线图中删除所选的数据点

## UG10-CH13-D120

PDF page: 205; original JSON pointer: `/2379`

2. 按住鼠标左键并拖动光标把要删除的数据点框在一个矩形框内

## UG10-CH13-D121

PDF page: 205; original JSON pointer: `/2380`

4. 在出现的菜单中 单击 Delete Points 删除点 注释 你无法恢复已删除的数据点 要删除整个曲线 步骤如下

## UG10-CH13-D122

PDF page: 206; original JSON pointer: `/2382`

3. 在弹出的菜单上 将光标定位到 Modify 修改 然后单击 Hide Variable 隐藏变 量

## UG10-CH13-D123

PDF page: 206; original JSON pointer: `/2383`

4. 选择一个变量 并用 Hide 隐藏 和 Show 显示 箭头按钮把所要删除的变量从 Shown Variables 被显示的变量 列表中移到 Hidden Variables 被隐藏的变量 列 表中 被隐藏的曲线以后可以用上述步骤再显示出来 在曲线图上显示不同范围的数据 利用 zoom 缩放 命令可以在曲线图上显示出不同范围的数据 缩放选项 缩放 Zoom Auto 按一个自动设定量缩小 Zoom Out 按一个自动设定量放大 Zoom Full 放大到整个曲线图

## UG10-CH13-D124

PDF page: 206; original JSON pointer: `/2384`

例如 要缩小到指定数据范围内 可按下列步骤进行

## UG10-CH13-D125

PDF page: 206; original JSON pointer: `/2385`

2. 在曲线图上选择要查看的区域 方法是按住鼠标左键并拖动光标构成一个矩形轮 廓

## UG10-CH13-D126

PDF page: 206; original JSON pointer: `/2386`

3. 在这个区域中单击鼠标右键 并在出现的菜单中 单击 Zoom In 缩小 来显示出 你所选的区域

## UG10-CH13-D127

PDF page: 206; original JSON pointer: `/2387`

4. 要再次显示出整个曲线图 可在曲线图中单击鼠标右键 并在弹出的菜单中 单击 Zoom Full 完全放大 改变曲线图的缺省设置 要改变用来生成曲线图的缺省设置 步骤如下

## UG10-CH13-D128

PDF page: 206; original JSON pointer: `/2388`

1. 在 Tools 菜单上 单击 Options

## UG10-CH13-D129

PDF page: 206; original JSON pointer: `/2389`

2. 在 Plots 标签上 单击你要改变的缺省项

## UG10-CH13-D130

PDF page: 206; original JSON pointer: `/2390`

3. 单击 Title 标题 Axis label 坐标轴标签 Axis scale 坐标轴刻度 或者 Annotation 注释 按钮 修改曲线图上不同类型文本的缺省字体

## UG10-CH13-D131

PDF page: 206; original JSON pointer: `/2391`

4. 使用列表选择新曲线图所用的 Grid Style 网格类型 和 Line Style 线形

## UG10-CH13-D132

PDF page: 206; original JSON pointer: `/2392`

5. 用 Marker Size 标记大小 框规定曲线图中数据标记的大小

## UG10-CH13-D133

PDF page: 206; original JSON pointer: `/2393`

6. 选定 Show legend 显示图例 和/或 Show Time Stamp 显示时间标记 框 以便 缺省情况下在新的曲线图上可显示出这些组成元素 时间标记的组成部分也可以用 这种方法来选择

## UG10-CH13-D134

PDF page: 207; original JSON pointer: `/2395`

你可以打印一个选定的曲线图 方法如下

## UG10-CH13-D135

PDF page: 207; original JSON pointer: `/2396`

1. 显示出你要打印的曲线图

## UG10-CH13-D136

PDF page: 207; original JSON pointer: `/2397`

2. 在 File 菜单上 单击 Print 有关打印的详细信息 参见第十四章

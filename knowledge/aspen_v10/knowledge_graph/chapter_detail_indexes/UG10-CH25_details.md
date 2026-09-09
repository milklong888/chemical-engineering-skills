# UG10-CH25 Detail Operation Index - 第25章 平衡模块

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH25-D001

PDF page: 364; original JSON pointer: `/4355`

用计算的结果更新进入或离开封闭区的物流变量 比如 平衡模块可以计算

## UG10-CH25-D002

PDF page: 364; original JSON pointer: `/4356`

l 循环计算中补充物流的流率 这将删除 Fortran 模块

## UG10-CH25-D003

PDF page: 364; original JSON pointer: `/4357`

l 进料物流流率和基于其它物流和模块信息的条件 这将删除设计规定和收敛回路

## UG10-CH25-D004

PDF page: 364; original JSON pointer: `/4358`

l 规定平衡计算模块和物流

## UG10-CH25-D005

PDF page: 364; original JSON pointer: `/4359`

定义一个平衡模块按下述步骤

## UG10-CH25-D006

PDF page: 364; original JSON pointer: `/4360`

2. 规定平衡计算的模块和物流

## UG10-CH25-D007

PDF page: 364; original JSON pointer: `/4361`

3. 规定和更新物流变量

## UG10-CH25-D008

PDF page: 364; original JSON pointer: `/4362`

5. 可选择地规定闪蒸条件 创建一个平衡模块 创建一个平衡模块

## UG10-CH25-D009

PDF page: 364; original JSON pointer: `/4363`

1. 从 Data 菜单 选择 Flowsheeting Options 然后 Balance

## UG10-CH25-D010

PDF page: 364; original JSON pointer: `/4364`

2. 在 Balance Object Manager, 单击 New 按钮

## UG10-CH25-D011

PDF page: 364; original JSON pointer: `/4365`

3. 在 Create New ID 对话框 输入一个 ID 或接受缺省的 ID 且单击 OK

## UG10-CH25-D012

PDF page: 364; original JSON pointer: `/4366`

4. 从数据浏览器的左屏选择你要输入数据的平衡表 见本章的后续部分有关内容 表 页 规定的是什么 Setup Mass Balance 包括在每个物料平衡封闭区内的模块或物 流 Energy Balance 包括在每个能量平衡封闭区内的模块或物 流 Equations 物料和能量平衡关系以及 在 Mass Balance 和 Energy Balance 页上所做的规定 Calculate 在物料和能量平衡计算后物流变量要计算 且更新 Scale 物流比例缩放因子

## UG10-CH25-D013

PDF page: 364; original JSON pointer: `/4367`

Advanced Parameters 可选择的收敛参数 包括平衡方程的相对残

## UG10-CH25-D014

PDF page: 365; original JSON pointer: `/4369`

Sequence 平衡模块可选择的运行顺序

## UG10-CH25-D015

PDF page: 365; original JSON pointer: `/4370`

Stream Flash 规定物流的可选的闪蒸规定

## UG10-CH25-D016

PDF page: 365; original JSON pointer: `/4371`

规定平衡模块的模 块和物流

## UG10-CH25-D017

PDF page: 365; original JSON pointer: `/4372`

使用 Mass Balance 和 Energy Balance 页规定一个质量和能量平衡封闭区的模块或物流

## UG10-CH25-D018

PDF page: 365; original JSON pointer: `/4373`

l Overrall 不规定 Component(组分) Component Groups( 组分组)或 Substream(子物

## UG10-CH25-D019

PDF page: 365; original JSON pointer: `/4374`

l Substream 不规定 Component(组分)或 Component Groups(组分组)

## UG10-CH25-D020

PDF page: 365; original JSON pointer: `/4375`

l Component Balance

## UG10-CH25-D021

PDF page: 365; original JSON pointer: `/4376`

规定质量平衡计算的模块和物流

## UG10-CH25-D022

PDF page: 365; original JSON pointer: `/4377`

1. 选择 Mass Balance 表

## UG10-CH25-D023

PDF page: 365; original JSON pointer: `/4378`

2. 在 Mass Balance Number 区域 单击向下箭头并选择<new>

## UG10-CH25-D024

PDF page: 365; original JSON pointer: `/4379`

3. 在 New Item 对话框 规定一个 ID 或接受缺省 ID ID 必须是一个整数

## UG10-CH25-D025

PDF page: 365; original JSON pointer: `/4380`

4. 规定包括物料平衡封闭区内的模块和物流 入口和出口

## UG10-CH25-D026

PDF page: 365; original JSON pointer: `/4381`

5. 规定基于物料平衡类型的组分 组分组或子物流

## UG10-CH25-D027

PDF page: 365; original JSON pointer: `/4382`

6. 如果你想要输入多于一个的物料平衡 重复步骤 2 到 5 规定能量平衡计算的模块和物流

## UG10-CH25-D028

PDF page: 365; original JSON pointer: `/4383`

1. 选择 Energy Balance 表

## UG10-CH25-D029

PDF page: 365; original JSON pointer: `/4384`

2. 在 Energy Balance Number 区域 单击向下箭头并选择<new>

## UG10-CH25-D030

PDF page: 365; original JSON pointer: `/4385`

4. 规定包括能量平衡封闭区内的模块和物流 入口和出口

## UG10-CH25-D031

PDF page: 365; original JSON pointer: `/4386`

5. 如果你想要输入多于一个的物料平衡 重复步骤 2 到 4 提示 如果你想要删除一个质量平衡或能量平衡 在 Mass Balance Number 区域或 Energy Balance Number 区域单击鼠标右键 从弹出菜单中选择 Delete 使用方程页创建在一个或多个物流间的全流率或组分流率的一般的摩尔 /质量关系 你 也可规定右手边的摩尔和质量关系 见本章的物料和能量平衡方程中关于方程的内容 规定和更新物流变量 使用 Calculate 页规定通过求解质量和能量平衡关系计算哪个物流变量 你可以规定在

## UG10-CH25-D032

PDF page: 365; original JSON pointer: `/4387`

计算后更新这些变量 为了求解平衡方程 在该表中规定的变量总数必须等于在 Mass

## UG10-CH25-D033

PDF page: 365; original JSON pointer: `/4388`

Balance 和 Energy Balance 表中规定的方程数

## UG10-CH25-D034

PDF page: 366; original JSON pointer: `/4390`

如果当你规定组分流率时你不能规定子物流 ASPEN PLUS 将计算缺省子物流的组分 流率 一个规定组分的缺省子物流是包含那个组分的第一个物流 收敛参数 使用 Advanced Parameters 页

## UG10-CH25-D035

PDF page: 366; original JSON pointer: `/4391`

l 规定平衡模块收敛参数

## UG10-CH25-D036

PDF page: 366; original JSON pointer: `/4392`

平衡或质量/摩尔关系 附加质量平衡方程在缺省情况下被核对 并且如果它们不平衡 计

## UG10-CH25-D037

PDF page: 366; original JSON pointer: `/4393`

算变量不被更新 即使方程不平衡更新计算变量也是可能的 你可以选择不核对附加的质量

## UG10-CH25-D038

PDF page: 366; original JSON pointer: `/4394`

使用 Advanced Sequence 页规定什么时候运行平衡模块

## UG10-CH25-D039

PDF page: 366; original JSON pointer: `/4395`

平衡模块可以自动或手动排序 自动排序时 平衡模块在带有该平衡模块更新的进料物

## UG10-CH25-D040

PDF page: 366; original JSON pointer: `/4396`

流的任何单元操作模块前运行

## UG10-CH25-D041

PDF page: 366; original JSON pointer: `/4397`

有些情况下 ASPEN PLUS 将平衡模块放置在收敛回路内 你可控制模块是否只运行一

## UG10-CH25-D042

PDF page: 366; original JSON pointer: `/4398`

次 比如 初始化一个撕裂流 或总是运行 比如 补充的计算

## UG10-CH25-D043

PDF page: 366; original JSON pointer: `/4399`

使用 Stream Flash 页规定热力学条件或禁止由平衡模块计算更新物流的自动闪蒸计算

## UG10-CH25-D044

PDF page: 366; original JSON pointer: `/4400`

除非只有全流率是更新的变量否则 ASPEN PLUS 自动闪蒸一个更新的物流

## UG10-CH25-D045

PDF page: 366; original JSON pointer: `/4401`

当变量数超出方程数时 你必须输入在 Calculate 表中计算未知变量 因为方程的形式是

## UG10-CH25-D046

PDF page: 366; original JSON pointer: `/4402`

线形的 ASPEN PLUS 会直接求解未知的变量 你可以规定相应的物流变量被更新

## UG10-CH25-D047

PDF page: 367; original JSON pointer: `/4404`

正文待来源表达/OCR边界复核；原文本 SHA256: `99eb50f474d11d563b2deb89ba5c881e20b251223d823d66ac000f8c9fa7cb91`。

## UG10-CH25-D048

PDF page: 367; original JSON pointer: `/4405`

在 Equations 页 你可规定附加的物料关系 其中包括物流中的组分 对于反映系统是

## UG10-CH25-D049

PDF page: 367; original JSON pointer: `/4406`

有用的 当你规定附加的关系时 ASPEN PLUS 使用下述的摩尔/质量平衡方程

## UG10-CH25-D050

PDF page: 367; original JSON pointer: `/4407`

该示例说明怎样对一个 HeatX 模块只做质量计算 目的是演示平衡模块做反推计算的

## UG10-CH25-D051

PDF page: 367; original JSON pointer: `/4408`

HeatX 的两个出口物流已给出 需要计算两个入口物流的流率 出口和入口物流都规定

## UG10-CH25-D052

PDF page: 369; original JSON pointer: `/4411`

在结果表上 列出了计算变量和平衡方程的最后值

## UG10-CH25-D053

PDF page: 369; original JSON pointer: `/4412`

在 Equations 页可找到平衡方程的最终值 问题中的方程已显示 这里右两个质量平衡

## UG10-CH25-D054

PDF page: 370; original JSON pointer: `/4414`

使用平衡模块计算冷却水的流率 它使甲醇温度从 150F 冷却至 100F 平衡模块将删除

## UG10-CH25-D055

PDF page: 370; original JSON pointer: `/4415`

100 F 14.7PSI 水入口

## UG10-CH25-D056

PDF page: 370; original JSON pointer: `/4416`

50 F 14.7PSI 甲醇入口

## UG10-CH25-D057

PDF page: 370; original JSON pointer: `/4417`

150 F 14.7PSI 水出口 Spec80 F 热侧 冷侧

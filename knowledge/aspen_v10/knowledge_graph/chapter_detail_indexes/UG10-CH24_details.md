# UG10-CH24 Detail Operation Index - 第24章 在物流或模块间传递信息

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH24-D001

PDF page: 359; original JSON pointer: `/4311`

l 运行一个传递模块时的规定

## UG10-CH24-D002

PDF page: 359; original JSON pointer: `/4312`

l 给目标物流输入闪蒸规定

## UG10-CH24-D003

PDF page: 359; original JSON pointer: `/4313`

2. 拷贝一个物流 物流流率 一个子物流或一个模块或物流变量

## UG10-CH24-D004

PDF page: 359; original JSON pointer: `/4314`

3. 可选择地输入目标物流的闪蒸规定 缺省情况下 ASPEN PLUS 自动闪蒸修正的物流 它使用在物流中的数值和在工 艺进料物流表或其它物流的源模块中的闪蒸选项

## UG10-CH24-D005

PDF page: 359; original JSON pointer: `/4315`

4. 当传递模块运行时可选择地规定 缺省情况下 ASPEN PLUS 将自动地将模块排序 本章的后续部分将描述这些步骤 创建一个传递模块 创建一个传递模块

## UG10-CH24-D006

PDF page: 359; original JSON pointer: `/4316`

1. 从 Data 菜单指向 Flowsheeting Options 然后单击 Transfer

## UG10-CH24-D007

PDF page: 359; original JSON pointer: `/4317`

2. 在 Transfer Object Manager, 单击 New

## UG10-CH24-D008

PDF page: 359; original JSON pointer: `/4318`

3. 在 Create New ID 对话框中 输入一个 ID 或接受缺省 单击 OK 拷贝流程图变量 From 和 To 页用于规定什么流程图变量要从一个地方拷贝到另一个地方

## UG10-CH24-D009

PDF page: 360; original JSON pointer: `/4320`

在 Form 页中如果你选择 ASPEN PLUS 拷贝

## UG10-CH24-D010

PDF page: 360; original JSON pointer: `/4321`

Stream flow 只有组分流率和一个物流的全流率

## UG10-CH24-D011

PDF page: 360; original JSON pointer: `/4322`

量类型不必相同 但每个变量类型必须有相

## UG10-CH24-D012

PDF page: 360; original JSON pointer: `/4323`

1. 在 Transfer 表上单击 From 标签

## UG10-CH24-D013

PDF page: 360; original JSON pointer: `/4324`

2. 单击 Entire Stream 选项并且在 Stream Name 区域规定物流 一个完整物流信息包括 子物流将被拷贝

## UG10-CH24-D014

PDF page: 360; original JSON pointer: `/4325`

4. 在 Stream 区域中规定目标物流的物流号 拷贝物流流率 拷贝一个物流的组分流率

## UG10-CH24-D015

PDF page: 360; original JSON pointer: `/4326`

2. 单击 Stream Flow 选项且在 Stream Name 区域规定物流 一个物流的组成和全部流 率将被拷贝 但没有条件 温度 压力 气相分率和其它重要变量

## UG10-CH24-D016

PDF page: 360; original JSON pointer: `/4327`

4. 在 Stream 区域中规定目标物流的物流号 拷贝子物流 拷贝一个子物流

## UG10-CH24-D017

PDF page: 360; original JSON pointer: `/4328`

2. 单击 Substream 选项且在 Stream Name 和子物流区域规定物流和子物流 一个物流 的子物流的信息将被拷贝

## UG10-CH24-D018

PDF page: 360; original JSON pointer: `/4329`

4. 在 Stream 和 Substream 区域中规定目标物流的物流号 拷贝模块和或物流变量 拷贝一个模块 物流或其它流程变量

## UG10-CH24-D019

PDF page: 360; original JSON pointer: `/4330`

1 在 Transfer 表上单击 From 标签

## UG10-CH24-D020

PDF page: 360; original JSON pointer: `/4331`

2 选择 Block 或 Stream Variable 选项

## UG10-CH24-D021

PDF page: 360; original JSON pointer: `/4332`

3 在 Type 区域选择你想要拷贝的变量类型

## UG10-CH24-D022

PDF page: 360; original JSON pointer: `/4333`

4 ASPEN PLUS 让你保留必需的区域以完全标识变量 见第十八章访问变量的内容

## UG10-CH24-D023

PDF page: 361; original JSON pointer: `/4335`

6 在 Variable Number区域 单击向下箭头且选择<new>

## UG10-CH24-D024

PDF page: 361; original JSON pointer: `/4336`

7 在 Type 区域 选择拷贝目标的变量类型

## UG10-CH24-D025

PDF page: 361; original JSON pointer: `/4337`

8 ASPEN PLUS 让你保留必需的区域以完全标识变量 重复步骤 6 到 8 可使 From 变量被拷贝到所有的变量中 定义一个传递模块的运行 使用 Transfer Sequence 页做传递模块运行时的规定 你可做下述之一

## UG10-CH24-D026

PDF page: 361; original JSON pointer: `/4338`

l 使用缺省 Automatically Sequence让 ASPEN PLUS 自动定义模块顺序

## UG10-CH24-D027

PDF page: 361; original JSON pointer: `/4339`

l 做当传递模块运行时的规定 在一个模块之前或之后 或在模拟的第一个或最后一

## UG10-CH24-D028

PDF page: 361; original JSON pointer: `/4340`

1. 在 Transfer 表上 单击 Sequence 标签

## UG10-CH24-D029

PDF page: 361; original JSON pointer: `/4341`

2. 该表显示怎样做传递模块的运行规定 在 Execute 区域规定 To Automatically sequenced 自动传递模块的顺序 First 在模拟开始运行传递模块 Before 传递模块在规定的模块 收敛 Fortran 传 递 平衡或泄压之前运行 必须规定模块类型和模块名字 After 传递模块在规定的模块 收敛 Fortran 传 递 平衡或泄压之后运行 必须规定模块类型和模块名字 Last 在模拟最后运行传递模块

## UG10-CH24-D030

PDF page: 361; original JSON pointer: `/4342`

3. 如果你输入 Before 或 After,选择单元操作模块 收敛模块 Fortran 模块 传递模块 平衡模块或泄压模块在传递模块之前或之后运行

## UG10-CH24-D031

PDF page: 361; original JSON pointer: `/4343`

4. 使用本页的 Diagnostic 按钮设定图形输出的水平 输入目标物流的闪蒸规定 当你拷贝生成一个物流时 ASPEN PLUS 使用出现在物流中的数值以及在工艺进料的 Stream 表或其它物流的源模块中的闪蒸选项来闪蒸目标物流以计算一个新系列的物流性质 你能使用可选择的 Stream Flash 页规定热力学条件和修正物流的闪蒸选项 比如 当你 拷贝物流流率并且需要规定目标物流温度和压力时可使用它 闪蒸类型必须规定 可能的闪蒸类型有

## UG10-CH24-D032

PDF page: 362; original JSON pointer: `/4345`

如果希望温度或压力的估计值可以输入 也可以规定闪蒸计算的相态并且选择地输入闪蒸最大循环次数以及容差 输入一个物流的闪蒸规定

## UG10-CH24-D033

PDF page: 362; original JSON pointer: `/4346`

1. 在 Transfer 表上单击 Stream Flash 标签

## UG10-CH24-D034

PDF page: 362; original JSON pointer: `/4347`

2. 在物流区域规定物流名字

## UG10-CH24-D035

PDF page: 362; original JSON pointer: `/4348`

3. 规定 Flash Type.

## UG10-CH24-D036

PDF page: 362; original JSON pointer: `/4349`

4. 做闪蒸规定 规定估计值和/或收敛参数 一个物流拷贝成两个物流的示例 传递模块用于拷贝物流 F-STOIC 为物流 F-CSTR F-PLUG 和 F-GIBBS 一个物流的条件拷贝到一个模块的示例

## UG10-CH24-D037

PDF page: 363; original JSON pointer: `/4351`

物性方法之间使用 Heater 模块并加入温度和压力规定 Heater 模块应该使用入口物流的温

## UG10-CH24-D038

PDF page: 363; original JSON pointer: `/4352`

度 压力和 Heater 出口连接的新的段或模块的物性方法 Transfer 模块用于将入口物流的温

## UG10-CH24-D039

PDF page: 363; original JSON pointer: `/4353`

在这个流程上 因为所有压力都是环境压力 所以只有温度被传递 类似的模块可用

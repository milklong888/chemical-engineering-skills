# UG10-CH21 Detail Operation Index - 第21章 设计规定：反馈控制

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH21-D001

PDF page: 309; original JSON pointer: `/3777`

第 21 章 设计规定 反馈控制

## UG10-CH21-D002

PDF page: 309; original JSON pointer: `/3778`

第21章 设计规定 反馈控制

## UG10-CH21-D003

PDF page: 309; original JSON pointer: `/3779`

在你的模拟中 可使用设计规定作为反馈控制器 本章介绍

## UG10-CH21-D004

PDF page: 309; original JSON pointer: `/3780`

l 可选的 Fortran 语句

## UG10-CH21-D005

PDF page: 309; original JSON pointer: `/3781`

设计规定设定一个变量的值 否则 ASPEN PLUS 将计算该值 例如 你可能想要规

## UG10-CH21-D006

PDF page: 309; original JSON pointer: `/3782`

定一个产品的纯度或规定一个循环物流中允许的杂质的量 对于每个设计规定 你指定要操

## UG10-CH21-D007

PDF page: 309; original JSON pointer: `/3783`

纵 调整 的一个模块输入变量 过程进料物流变量或其它模拟输入变量来满足规定 例如

## UG10-CH21-D008

PDF page: 309; original JSON pointer: `/3784`

你可能调整放空的流率来控制循环物流中的杂质量 设计规定可以用来模拟一个反馈控制器

## UG10-CH21-D009

PDF page: 309; original JSON pointer: `/3785`

当你使用设计规定时 你为一个流程变量或一些流程变量的函数指定一个你所希望的

## UG10-CH21-D010

PDF page: 309; original JSON pointer: `/3786`

值 在设计规定中所用的流程变量称作被采集变量 对于每个设计规定 你还必须选择调整

## UG10-CH21-D011

PDF page: 309; original JSON pointer: `/3787`

一个模块输入变量或过程进料变量以便满足设计规定 该变量称为被操纵变量

## UG10-CH21-D012

PDF page: 309; original JSON pointer: `/3788`

设计规定通过调整一个由用户指定的输入变量来达到它的目标 模拟中计算出的量不能

## UG10-CH21-D013

PDF page: 309; original JSON pointer: `/3789`

直接改变 例如 不能改变一个循环物流的流率 但是 可以改变一个 Fsplit 模块的分流分

## UG10-CH21-D014

PDF page: 309; original JSON pointer: `/3790`

率 而该循环物流是其一个出口物流 设计规定只能调整一个输入变量的值

## UG10-CH21-D015

PDF page: 309; original JSON pointer: `/3791`

设计规定产生必须迭代求解的回路 缺省情况下 ASPEN PLUS 为每个设计规定生成

## UG10-CH21-D016

PDF page: 309; original JSON pointer: `/3792`

一个收敛模块并排序 你可以通过输入你自己的收敛规定来取代缺省设置 关于设计规定的

## UG10-CH21-D017

PDF page: 309; original JSON pointer: `/3793`

在物流或模块输入中提供的被操纵变量的值被用作初始估值 为被操纵变量提供一个好

## UG10-CH21-D018

PDF page: 309; original JSON pointer: `/3794`

的估值将有助于设计规定在较少的迭代次数内收敛 这一点对于具有几个相互有关的设计规

## UG10-CH21-D019

PDF page: 309; original JSON pointer: `/3795`

规定的目标是目标值等于计算出的值 规定的值-计算出的值=0 规定可以是任意涉及

## UG10-CH21-D020

PDF page: 309; original JSON pointer: `/3796`

一个或多个流程量的合法 Fortran 表达式 规定还必须有一个允差 必须在该允差范围内满

## UG10-CH21-D021

PDF page: 309; original JSON pointer: `/3797`

足目标函数关系 因此 实际上必须满足的方程是

## UG10-CH21-D022

PDF page: 309; original JSON pointer: `/3798`

|规定值-计算值|<允差

## UG10-CH21-D023

PDF page: 309; original JSON pointer: `/3799`

除了是否满足目标函数方程外, 设计规定无任何直接结果 被操纵的和/或被采集的变量

## UG10-CH21-D024

PDF page: 309; original JSON pointer: `/3800`

的最终值可在相应物流或模块结果页面上直接查看 通过选择相应 Convergence 收敛 模

## UG10-CH21-D025

PDF page: 309; original JSON pointer: `/3801`

块的 Results 结果 页面 可以查看收敛模块的摘要和收敛历史

## UG10-CH21-D026

PDF page: 309; original JSON pointer: `/3802`

定义一个设计规定有下列五个步骤

## UG10-CH21-D027

PDF page: 309; original JSON pointer: `/3803`

l 标识设计规定中所用的被采集流程变量

## UG10-CH21-D028

PDF page: 310; original JSON pointer: `/3805`

第 21 章 设计规定 反馈控制

## UG10-CH21-D029

PDF page: 310; original JSON pointer: `/3806`

l 为一个被采集变量或一些被采集变量函数指定目标值并指定一个允差

## UG10-CH21-D030

PDF page: 310; original JSON pointer: `/3807`

l 标识一个为达到目标值而被调整的模拟输入变量 并指定调整该变量的上下限

## UG10-CH21-D031

PDF page: 310; original JSON pointer: `/3808`

l 输入可选的 Fortran 语句

## UG10-CH21-D032

PDF page: 310; original JSON pointer: `/3809`

1. 从 Data 菜单 将鼠标指向 Flowsheeting Options 建立流程选项 然后 指向 Design Specs 设计规定 在 Design Specification Object Manager 设计规定对象 管理器 中 单击 N ew 新建

## UG10-CH21-D033

PDF page: 310; original JSON pointer: `/3810`

2. 在 Create New ID 建立新的标识符 对话框中 输入一个标识符或接受缺省值 然后单击 OK 下面几节如何完成所需的页面 标识被采集流程变量 使用 Flowsheeting Option Design Spec Define 建立流程 选项 设计规定 定义 页面来 表示设计规定中所用的流程变量 并赋给它们变量名 变量名标识了在其它设计规定页面上 的变量 用 Define 定义 页面标识一个流程变量并赋给它一个变量名 当完成一个 Define 定

## UG10-CH21-D034

PDF page: 310; original JSON pointer: `/3811`

义 页面时 在 Variable Definition 变量定义 对话框中指定变量 Define 定义 页面显

## UG10-CH21-D035

PDF page: 310; original JSON pointer: `/3812`

示所有被访问变量的简单一览 但是 你不能修改 Define 定义 页面上的变量

## UG10-CH21-D036

PDF page: 310; original JSON pointer: `/3813`

在 Define 定义 页面上 你可以做下列工作

## UG10-CH21-D037

PDF page: 310; original JSON pointer: `/3814`

1. 若创建一个新变量 单击 New 新建 按扭 或者 若编辑一个现有变量 选择 一个变量并单击 Edit 编辑 按扭

## UG10-CH21-D038

PDF page: 310; original JSON pointer: `/3815`

2. 在 Variable Name 变量名 字段中 输入变量名 如果你正编辑一个现有变量并 要改变它的名字 则在 Variable Name 变量名 字段上单击鼠标右键 在弹出的 菜单上 单击 Rename 重命名 变量名必须符合下列条件

## UG10-CH21-D039

PDF page: 310; original JSON pointer: `/3816`

l 不能以 IZ 或 ZZ 开头

## UG10-CH21-D040

PDF page: 310; original JSON pointer: `/3817`

3. 在 Category 类别 框中 使用 Option 选项 按扭选择变量类别

## UG10-CH21-D041

PDF page: 310; original JSON pointer: `/3818`

4. 在 Reference 引用 框中 从 Type 类型 字段中的列表内选择变量类型 ASEPN PLUS 显示完成变量定义所需的其它字段

## UG10-CH21-D042

PDF page: 310; original JSON pointer: `/3819`

5. 单击 Close 关闭 返回 Define 定义 页面 关于访问变量的更详细信息 参见第十八章 访问流程变量 提示 用 Delete 删除 按扭能快速删除一个变量及定义它所用的所有字段 提示 用 Edit 编辑 按扭可以修改对 Variable Definition 变量定义 中某个变量的定 义

## UG10-CH21-D043

PDF page: 311; original JSON pointer: `/3821`

第 21 章 设计规定 反馈控制

## UG10-CH21-D044

PDF page: 311; original JSON pointer: `/3822`

1. 在 Design Spec 设计规定 表上 单击 Spec 规定 页面

## UG10-CH21-D045

PDF page: 311; original JSON pointer: `/3823`

2. 在 Spec 规定 字段中 输入目标变量或 Fortran 表达式

## UG10-CH21-D046

PDF page: 311; original JSON pointer: `/3824`

3. 在 Target 目标 字段中 按一个常数或一个 Fortran 表达式来指定目标值

## UG10-CH21-D047

PDF page: 311; original JSON pointer: `/3825`

4. 在 Tolerance 允差 字段中 按一个常数或一个 Fortran 表达式来输入规定允差 设计规定是 规定表达式=目标表达式 当下列条件成立时 设计规定收敛 -允差<规定表达式-目标表达式<允差 如果你需要输入一个用一单个表达式不能处理的复杂 Fortran 表达式 你可以输入附加 的 Fortran 语句 参见本章 输入可选 Fortran 语句 提示 为了确保你输入了正确的变量名 在 Spec 规定 Target 目标 Tolerance 允

## UG10-CH21-D048

PDF page: 311; original JSON pointer: `/3826`

差 字段内 单击鼠标右键 在弹出菜单中 单击 Variable List 变量列表 出现 Defined

## UG10-CH21-D049

PDF page: 311; original JSON pointer: `/3827`

Variable List 已定义变量的列表 窗口 你可以将变量从 Defined Variable List 已定义变量

## UG10-CH21-D050

PDF page: 311; original JSON pointer: `/3828`

的列表 中拖放到 Spec 规定 页面中

## UG10-CH21-D051

PDF page: 311; original JSON pointer: `/3829`

用 Vary 改变 页面来标识被操纵变量并指定它的上下限 被操纵变量的上下限可以

## UG10-CH21-D052

PDF page: 311; original JSON pointer: `/3830`

若标识被操纵变量并指定上下限

## UG10-CH21-D053

PDF page: 311; original JSON pointer: `/3831`

1. 在 Design Spec 设计规定 表上 单击 Vary 改变 页面

## UG10-CH21-D054

PDF page: 311; original JSON pointer: `/3832`

2. 在 Type 类型 字段中 选择一个变量类型 ASPEN PLUS 引导你到只有标识流 程变量所需的其余字段

## UG10-CH21-D055

PDF page: 311; original JSON pointer: `/3833`

3. 在 Lower 下限 字段中 输入一个常数或一个 Fortran 表达式作为操作变量的下 限

## UG10-CH21-D056

PDF page: 311; original JSON pointer: `/3834`

4. 在 Upper 上限 字段中 输入一个常数或一个 Fortran 表达式作为操作变量的上 限 你必须已经把被操纵变量作为一个输入规定输入 或者 它必须有一个缺省值 被操纵 变量的初始估值便是该规定或缺省值 你不能调整整型模块变量 例如 某个精馏塔的进料 位置 如果由于设计规定的解超出了限定范围而不能满足设计规定 ASPEN PLUS 选择最 满足规定的那个界限 输入可选的 Fortran 语句 你可以输入计算设计规定项或被操作变量界限所需的任何 Fortran 语句 任何由 Fortran

## UG10-CH21-D057

PDF page: 311; original JSON pointer: `/3835`

语句计算的变量都可用在 Spec 规定 和 Vary 改变 页面上的表达式中 只有当函数太

## UG10-CH21-D058

PDF page: 311; original JSON pointer: `/3836`

复杂而不能在 Spec 规定 和 Vary 改变 页面上输入时才需要使用 Fortran 语句

## UG10-CH21-D059

PDF page: 311; original JSON pointer: `/3837`

你可以按下列方式输入 Fortran 语句

## UG10-CH21-D060

PDF page: 311; original JSON pointer: `/3838`

l 在 Fortran 页面上

## UG10-CH21-D061

PDF page: 312; original JSON pointer: `/3840`

第 21 章 设计规定 反馈控制

## UG10-CH21-D062

PDF page: 312; original JSON pointer: `/3841`

l 在你的文本编辑器中 例如 记事本 然后将它们复制并粘贴到 Fortran 页面上

## UG10-CH21-D063

PDF page: 312; original JSON pointer: `/3842`

按与可执行 Fortran 语句相同的方式输入 Fortran 说明语句 只是用 Declarations 说明

## UG10-CH21-D064

PDF page: 312; original JSON pointer: `/3843`

语句 页面代替 Fortran 页面

## UG10-CH21-D065

PDF page: 312; original JSON pointer: `/3844`

你可以将任何 Fortran 说明语句加到一个 Fortran 模块中 例如

## UG10-CH21-D066

PDF page: 312; original JSON pointer: `/3845`

l DIMENSION 定义

## UG10-CH21-D067

PDF page: 312; original JSON pointer: `/3846`

l 数据类型定义 INTEGER 和 REAL

## UG10-CH21-D068

PDF page: 312; original JSON pointer: `/3847`

如果某个 Fortran 变量符合下列条件 你可以将它放到一个 COMMON 中

## UG10-CH21-D069

PDF page: 312; original JSON pointer: `/3848`

l 在某个 Fortran 的迭代计算过程中该变量的值保持不变

## UG10-CH21-D070

PDF page: 312; original JSON pointer: `/3849`

你在 Specification 规定 页面上定义的 Fortran 变量不能在 Declarations 说明语句

## UG10-CH21-D071

PDF page: 312; original JSON pointer: `/3850`

使用 Fortran 页面

## UG10-CH21-D072

PDF page: 312; original JSON pointer: `/3851`

若在 Fortran 页面上输入可执行语句

## UG10-CH21-D073

PDF page: 312; original JSON pointer: `/3852`

1. 在 Design Spec 设计规定 表上 单击 Fortran 页面

## UG10-CH21-D074

PDF page: 312; original JSON pointer: `/3853`

2. 使用 Help 帮助 来查看关于内嵌 Fortran 的规则和限制

## UG10-CH21-D075

PDF page: 312; original JSON pointer: `/3854`

3. 输入你的 Fortran 语句 为了确保你输入了正确的变量名 单击鼠标右键 在弹出菜单中 单击 Variable List 变 量列表 出现 Defined Variable List 已定义变量的列表 窗口 你可以将变量从 Defined Variable List 已定义变量的列表 中拖放到 Fortran 页面中 解决设计规定的问题 如果没有满足目标函数 可以考虑做以下几个方面工作

## UG10-CH21-D076

PDF page: 312; original JSON pointer: `/3855`

l 检查被操纵变量是否处于上限或下限

## UG10-CH21-D077

PDF page: 312; original JSON pointer: `/3856`

l 验证解是否在为操作变量指定的界限范围内 可能需要通过灵敏度分析来验证

## UG10-CH21-D078

PDF page: 312; original JSON pointer: `/3857`

l 检查确认操作变量确实不影响被采集变量的值 尝试为操作变量提供一个更好的初

## UG10-CH21-D079

PDF page: 312; original JSON pointer: `/3858`

l 尝试改变与设计规定相关的收敛模块的特性 迭代步长 迭代次数等

## UG10-CH21-D080

PDF page: 312; original JSON pointer: `/3859`

调整 RGibbs 模块 REACT 的温度 将组分 ESTER 相对于 ETOH 的选择性控制在

## UG10-CH21-D081

PDF page: 312; original JSON pointer: `/3860`

2.40+/-0.01 该例假定在 RGibbs Setup Specification Rgibbs 设置规定 页面上为模块 REACT

## UG10-CH21-D082

PDF page: 312; original JSON pointer: `/3861`

指定了温度 RGibbs 输入规定变成了设计规定的初始估值

## UG10-CH21-D083

PDF page: 312; original JSON pointer: `/3862`

l 设计规定是 FESTER/FALC=2.50

## UG10-CH21-D084

PDF page: 312; original JSON pointer: `/3863`

l 满足设计规定的条件是|FESTER/FALC-2.50|<0.01

## UG10-CH21-D085

PDF page: 313; original JSON pointer: `/3865`

第 21 章 设计规定 反馈控制

## UG10-CH21-D086

PDF page: 313; original JSON pointer: `/3866`

l Fortran 表达式例如 FESTER/FALC 可以用在设计规定表达式的任何部分 规定

## UG10-CH21-D087

PDF page: 313; original JSON pointer: `/3867`

l 反应器温度是被操纵变量 设计规定模块将找到使 FESTER/FALC=2.50的温度

## UG10-CH21-D088

PDF page: 313; original JSON pointer: `/3868`

l 就象没有设计规定一样 在反应器模块中指定温度 指定的值被设计规定收敛模块

## UG10-CH21-D089

PDF page: 313; original JSON pointer: `/3869`

用作初始估值 设计规定模块将不尝试求解低于 50F 或高于 150F 的温度 即使目

## UG10-CH21-D090

PDF page: 313; original JSON pointer: `/3870`

标函数的解是在该范围之外 如果设计规定未满足 上下限则成为另一种规定 在

## UG10-CH21-D091

PDF page: 313; original JSON pointer: `/3871`

反应器模块中输入的初始估值处于该界限内

## UG10-CH21-D092

PDF page: 313; original JSON pointer: `/3872`

l 你不必为设计规定指定收敛模块 ASPEN PLUS 将自动生成一个收敛模块来收敛

## UG10-CH21-D093

PDF page: 314; original JSON pointer: `/3874`

第 21 章 设计规定 反馈控制

## UG10-CH21-D094

PDF page: 315; original JSON pointer: `/3876`

第 21 章 设计规定 反馈控制

## UG10-CH21-D095

PDF page: 315; original JSON pointer: `/3877`

具有变量允差和上下限的设计规定的示例

## UG10-CH21-D096

PDF page: 315; original JSON pointer: `/3878`

有一个设计规定指定某个 Heater 加热器 模块 HX1 的出入口熵相等 选择 HX1 的温

## UG10-CH21-D097

PDF page: 315; original JSON pointer: `/3879`

度作为被操纵变量 温度限制不能预先设定 但是已知等熵将处于入口温度的上下 75F 范围

## UG10-CH21-D098

PDF page: 315; original JSON pointer: `/3880`

内 设计规定的允差是熵的函数

## UG10-CH21-D099

PDF page: 315; original JSON pointer: `/3881`

l 设计规定设定出口熵 SOUT 等于入口熵 SIN

## UG10-CH21-D100

PDF page: 315; original JSON pointer: `/3882`

l 允差是用变量 TOL 来规定 在 Design Spec 设计规定 Fortran 页面上指定 TOL

## UG10-CH21-D101

PDF page: 315; original JSON pointer: `/3883`

为入口物流 SIN 的熵的 0.0001 倍 满足设计规定的条件是|SOUT-SIN|<TOL

## UG10-CH21-D102

PDF page: 315; original JSON pointer: `/3884`

l 就象没有设计规定一样指定 Heater 模块的温度 所指定的值被设计规定收敛模块

## UG10-CH21-D103

PDF page: 315; original JSON pointer: `/3885`

l 设计规定模块不尝试求解低于入口温度 TIN-75F 或高于 TIN+75F 的温度 即使目

## UG10-CH21-D104

PDF page: 315; original JSON pointer: `/3886`

标函数的解处于该范围之外 如果设计规定未满足 上下限则成为另一种规定 在

## UG10-CH21-D105

PDF page: 315; original JSON pointer: `/3887`

加热器模块中输入的初始估值处于该界限内

## UG10-CH21-D106

PDF page: 315; original JSON pointer: `/3888`

l 你不必为设计规定指定收敛模块 ASPEN PLUS 将自动生成一个收敛模块来收敛

## UG10-CH21-D107

PDF page: 316; original JSON pointer: `/3890`

第 21 章 设计规定 反馈控制

## UG10-CH21-D108

PDF page: 317; original JSON pointer: `/3892`

第 21 章 设计规定 反馈控制

## UG10-CH21-D109

PDF page: 318; original JSON pointer: `/3894`

第 21 章 设计规定 反馈控制

## UG10-CH21-D110

PDF page: 319; original JSON pointer: `/3896`

第 21 章 设计规定 反馈控制

## UG10-CH21-D111

PDF page: 319; original JSON pointer: `/3897`

调整标准生成焓来获得所希望的反应热的示例

## UG10-CH21-D112

PDF page: 319; original JSON pointer: `/3898`

-32570 因为有可能访问物性参数 参见第十九章 访问变量 所以 用一个设计规定来

## UG10-CH21-D113

PDF page: 319; original JSON pointer: `/3899`

调整标准生成焓以便获得所希望的反应热

## UG10-CH21-D114

PDF page: 319; original JSON pointer: `/3900`

在 APSEN PLUS 中 反应热是按纯组分焓差来计算的 由于是使用标准生成焓 纯组

## UG10-CH21-D115

PDF page: 319; original JSON pointer: `/3901`

分参数 DHFORM 来计算汽液相焓 所以调整 DHFORM 也就调整了反应热

## UG10-CH21-D116

PDF page: 320; original JSON pointer: `/3903`

第 21 章 设计规定 反馈控制

## UG10-CH21-D117

PDF page: 321; original JSON pointer: `/3905`

第 21 章 设计规定 反馈控制

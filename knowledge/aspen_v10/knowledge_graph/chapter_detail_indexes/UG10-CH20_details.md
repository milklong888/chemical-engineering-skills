# UG10-CH20 Detail Operation Index - 第20章 灵敏度分析

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH20-D001

PDF page: 301; original JSON pointer: `/3683`

l 定义一个灵敏度分析模块

## UG10-CH20-D002

PDF page: 301; original JSON pointer: `/3684`

l 指定被采集变量和被操纵变量

## UG10-CH20-D003

PDF page: 301; original JSON pointer: `/3685`

l 可选的 Fortran 语句

## UG10-CH20-D004

PDF page: 301; original JSON pointer: `/3686`

可以用它改变一个或多个流程变量并研究该变化对其它流程变量的影响 它是做工况研究的

## UG10-CH20-D005

PDF page: 301; original JSON pointer: `/3687`

一个最有用的工具 被变化的流程变量必须是流程的输入参数 在模拟中计算出的变量不能

## UG10-CH20-D006

PDF page: 301; original JSON pointer: `/3688`

被改变 你可以用灵敏度分析来验证一个设计规定的解是否在操作变量的变化范围内 你还

## UG10-CH20-D007

PDF page: 301; original JSON pointer: `/3689`

可以用它做简单的过程优化 你可以用灵敏度分析模块生成随进料物流 模块输入参数或其

## UG10-CH20-D008

PDF page: 301; original JSON pointer: `/3690`

它输入变量变化的模拟结果的表和/或图 灵敏度分析结果在 Sensitivity Results Summary 灵

## UG10-CH20-D009

PDF page: 301; original JSON pointer: `/3691`

敏度分析结果摘要 页面上按一个表的形式输出 表的前 n 列是被改变的变量的值 其中

## UG10-CH20-D010

PDF page: 301; original JSON pointer: `/3692`

n 是在 Sensitivity Input Vary 灵敏度分析输入变化 页面上输入的被改变的流程变量个数

## UG10-CH20-D011

PDF page: 301; original JSON pointer: `/3693`

表中其余的列含有在 Tabulate 制表 页面上你用来制表的变量的值 制表的结果可以是任

## UG10-CH20-D012

PDF page: 301; original JSON pointer: `/3694`

意流程变量 或者是随流程变量变化的任意合法 Fortran 表达式 流程变量是输入参数或是

## UG10-CH20-D013

PDF page: 301; original JSON pointer: `/3695`

你可以用 Plot 曲线图 菜单上的 Plot Wizard 绘图专家 将结果绘成曲线 以便很容

## UG10-CH20-D014

PDF page: 301; original JSON pointer: `/3696`

易地观察不同变量间的关系 关于 Plot Wizard 绘图专家 的更详细信息 请参见第十三章

## UG10-CH20-D015

PDF page: 301; original JSON pointer: `/3697`

灵敏度分析模块提供了基本工况结果的附加信息 但对基本工况模拟没有影响 模拟独

## UG10-CH20-D016

PDF page: 301; original JSON pointer: `/3698`

在灵敏度表中 具有一个以上变化变量的灵敏度模块为每个值的组合形式都生成一行数

## UG10-CH20-D017

PDF page: 301; original JSON pointer: `/3699`

灵敏度分析模块产生回路 对于灵敏度分析表的每一行都必须求解一次这些回路

## UG10-CH20-D018

PDF page: 301; original JSON pointer: `/3700`

ASPEN PLUS 自动排序灵敏度分析模块 你可以用 Convergence Sequence Specification 收

## UG10-CH20-D019

PDF page: 301; original JSON pointer: `/3701`

敛顺序规定 页面排序一个灵敏度分析模块 被访问的标量型流程变量的单位采用的是为灵

## UG10-CH20-D020

PDF page: 301; original JSON pointer: `/3702`

Data Browser 数据浏览器 工具栏上 改变灵敏度分析模块的单位集 或者 在制表页面

## UG10-CH20-D021

PDF page: 301; original JSON pointer: `/3703`

上输入一个表达式来转换变量 被访问的矢量型变量总是按 SI 单位

## UG10-CH20-D022

PDF page: 301; original JSON pointer: `/3704`

按下列步骤定义一个灵敏度分析块

## UG10-CH20-D023

PDF page: 301; original JSON pointer: `/3705`

l 建立一个灵敏度分析块

## UG10-CH20-D024

PDF page: 301; original JSON pointer: `/3706`

l 标识要操纵的输入变量来生成一个表

## UG10-CH20-D025

PDF page: 301; original JSON pointer: `/3707`

l 定义你要 ASPEN PLUS 将什么制表

## UG10-CH20-D026

PDF page: 302; original JSON pointer: `/3709`

l 输入可选的 Fortran 语句

## UG10-CH20-D027

PDF page: 302; original JSON pointer: `/3710`

建立一个灵敏度分析模 块

## UG10-CH20-D028

PDF page: 302; original JSON pointer: `/3711`

若建立一个灵敏度分析模块

## UG10-CH20-D029

PDF page: 302; original JSON pointer: `/3712`

1. 从 Data 数据 菜单上 单击 Model Analysis Tool 模型分析工具 然后再单击 Sensitivity 灵敏度分析

## UG10-CH20-D030

PDF page: 302; original JSON pointer: `/3713`

2. 在 Sensitivity Object Manager 灵敏度分析对象管理器 上 单击 New 新建

## UG10-CH20-D031

PDF page: 302; original JSON pointer: `/3714`

3. 在 Create New ID 建立新的标识符 对话框中 输入一个标识符或接受缺省值 然后 单击 OK 标识被采集流程变量 对于每个灵敏度分析模块 你必须标识流程变量并赋给它们变量名 你可以将这些变量 制表或将它们用到 Fortran 表达式中来计算制表的结果 变量名标识其它灵敏度分析页面上 的流程变量 用 Define 定义 页面来标识一个流程变量 并赋给它一个变量名 当填充一个 Define 定义 页面时 在 Variable Definition 变量定义 对话框中指定变量 Define 定义 页

## UG10-CH20-D032

PDF page: 302; original JSON pointer: `/3715`

面显示一个所有访问变量的简单一览 但你不能在 Define 定义 页面上修改变量

## UG10-CH20-D033

PDF page: 302; original JSON pointer: `/3716`

在 Define 定义 页面上

## UG10-CH20-D034

PDF page: 302; original JSON pointer: `/3717`

1. 若建立一个新变量 则单击 New 新建 按扭 或者 编辑一个现有变量 选择 一个变量并单击 Edit 编辑 按扭

## UG10-CH20-D035

PDF page: 302; original JSON pointer: `/3718`

2. 在 Variable Name 变量名 字段中 输入变量名 如果你编辑一个变量并且要改变变量名 则在 Variable Name 变量名 字段中单 击鼠标右键 在弹出菜单上单击 Rename 重命名 变量名必须是

## UG10-CH20-D036

PDF page: 302; original JSON pointer: `/3719`

l 不要以 IZ 或 ZZ 开头

## UG10-CH20-D037

PDF page: 302; original JSON pointer: `/3720`

3. 在 Category 类别 框中 用选项按扭选择变量类别

## UG10-CH20-D038

PDF page: 302; original JSON pointer: `/3721`

4. 在 Reference 引用 框中 从 Type 类型 字段中的列表选择变量类型 ASPEN PLUS 还显示为完成变量定义所需的其它字段

## UG10-CH20-D039

PDF page: 302; original JSON pointer: `/3722`

5. 单击 Close 关闭 返回 Define 定义 页面 关于访问变量的更详细信息 参见第十八章 提示 用 Delete 删除 按扭可以快速删除一个变量及定义它所用的所有字段 使 用 Edit 编辑 按扭可以修改在 Variable Definition 变量定义 对话中对一个变量 的定义 关于访问流程变量的更详细信息 参见第十八章 关于用 Define 定义 页面来标识流 程变量的更详细信息 参见第十九章

## UG10-CH20-D040

PDF page: 303; original JSON pointer: `/3724`

用 Vary 改变 页面来标识在生成一个表时变化的流程变量 你只能改变模块输入变

## UG10-CH20-D041

PDF page: 303; original JSON pointer: `/3725`

量 过程进料物流变量及其它输入变量 你必须为变化的变量指定值或一个值范围

## UG10-CH20-D042

PDF page: 303; original JSON pointer: `/3726`

你可改变整型变量 例如 一个精馏塔的进料位置 你最多可以指定 5 个操纵变量

## UG10-CH20-D043

PDF page: 303; original JSON pointer: `/3727`

1. 在 Sensitivity Input 灵敏度分析输入 表上 单击 Vary 改变 页面

## UG10-CH20-D044

PDF page: 303; original JSON pointer: `/3728`

2. 在 Variable Type 变量类型 字段内 选择一个变量类型 ASPEN PLUS 将引导你到只有标识流程变量所需的其余字段

## UG10-CH20-D045

PDF page: 303; original JSON pointer: `/3729`

3. 为操纵变量指定一个值列表或指定一个值范围 你可以输入下列内容之一

## UG10-CH20-D046

PDF page: 303; original JSON pointer: `/3730`

你可以输入一个常数或一个 Fortran 表达式

## UG10-CH20-D047

PDF page: 303; original JSON pointer: `/3731`

4. 你也可以标注变化的变量以便在报告或 Results Summary 结果一览 页面上显示 它们 用 Line1 至 Line4 字段来定义这些标注

## UG10-CH20-D048

PDF page: 303; original JSON pointer: `/3732`

5. 若标识附加的变量 从 Variable Number 变量号 字段中的列表内选择 New 新 建 重复步骤 2 至 5 ASPEN PLUS 为变化变量值的每个组合都生成一行表内容 组合数有可能很大 以至 需要大量计算时间和存储空间 例如 最大 5 个变量 每个变量有 10 个点 这将导致做 100000 个灵敏度分析模块的回路计算 每个操纵变量必须已经作为一个输入规定而输入 或者 它 必须有一个缺省值 定义制表变量 用 Tabulate 制表 页面来定义你要 ASPEN PLUS 制表的结果 并提供列标题

## UG10-CH20-D049

PDF page: 303; original JSON pointer: `/3733`

1. 在 Sensitivity Input 灵敏度分析输入 表上 单击 Tabulate 制表 页面

## UG10-CH20-D050

PDF page: 303; original JSON pointer: `/3734`

2. 在 Column Number 列号 字段中 输入一个列号

## UG10-CH20-D051

PDF page: 303; original JSON pointer: `/3735`

3. 在 Tabulated Variable or Expression 制表的变量及表达式 字段中 输入一个变 量名或一个 Fortran 表达式 对于操纵变量的每个组合 ASPEN PLUS 都将值或表达式结果制表 为了确保你输入了正确的变量名 单击鼠标右键 在弹出菜单中 单击 Variable List 变量列表 出现 Defined Variable List 已定义的变量列表 窗口 你可以从 Defined Variable List 已定义的变量列表 中将变量拖放到 Fortran 页面

## UG10-CH20-D052

PDF page: 303; original JSON pointer: `/3736`

4. 若输入可选的标注 单击 Table Format 表格式 按扭 在前四行中 为任意或所 有制表结果的列提供列标注

## UG10-CH20-D053

PDF page: 303; original JSON pointer: `/3737`

5. 用两个 Unit Labels 单位标注 行来为制表结果输入单位标注 如果在 Specification 规定 页面上将制表结果表达式按一单个变量名来输入 ASPEN PLUS 自动生成单位标注

## UG10-CH20-D054

PDF page: 303; original JSON pointer: `/3738`

6. 单击 Close 关闭 来关闭 Table Format 表格式 对话框

## UG10-CH20-D055

PDF page: 303; original JSON pointer: `/3739`

7. 重复步骤 2-6 直到你定义完你要制表的所有结果 没有任何限制

## UG10-CH20-D056

PDF page: 304; original JSON pointer: `/3741`

缺省情况下 ASPEN PLUS 用上一行的结果来开始计算新的一行结果 对于某些行

## UG10-CH20-D057

PDF page: 304; original JSON pointer: `/3742`

如果模块或循环回路不能收敛 你可以指定每行重新初始化计算 重新初始化模块 若重新初始化模块

## UG10-CH20-D058

PDF page: 304; original JSON pointer: `/3743`

1. 在 Sensitivity Input 灵敏度分析输入 表上 选择 Optional 可选项 标签

## UG10-CH20-D059

PDF page: 304; original JSON pointer: `/3744`

2. 在 Block To Be Reinitialized 要重新初始化的模块 字段中选择 Include Specified Blocks 包括指定的模块 或 Reinitialize All Blocks 重新初始化所有模块

## UG10-CH20-D060

PDF page: 304; original JSON pointer: `/3745`

3. 如果你选择了 Include Specified Blocks 包括指定的模块 则选择要重新初始化的 单元操作模块和/或收敛模块 重新初始化物流 若重新初始化物流

## UG10-CH20-D061

PDF page: 304; original JSON pointer: `/3746`

2. 在 Stream To Be Reinitialized 要重新初始化的物流 字段中选择 Include Specified Streams 包括指定的物流 或 Reinitialize All Streams 重新初始化所有物流

## UG10-CH20-D062

PDF page: 304; original JSON pointer: `/3747`

3. 如果你选择了 Include Specified Streams 包括指定的物流 则选择要重新初始化 的物流 输入可选的 Fortran 语句 你可以输入 Fortran 语句来计算制表结果及变化变量的范围 任何有 Fortran 语句计算的 变量都可以用在 Tabulate 制表 和 Vary 改变 页面上的表达式中 只有当函数太复杂而 不能在这些页面上输入时才需要用 Fortran 语句 你可以通过下列方式输入 Fortran 语句

## UG10-CH20-D063

PDF page: 304; original JSON pointer: `/3748`

l 在 Fortran 页面上

## UG10-CH20-D064

PDF page: 304; original JSON pointer: `/3749`

l 在你的文本编辑器中 例如 记事本 然后将它们复制并粘贴到 Fortran 页面上

## UG10-CH20-D065

PDF page: 304; original JSON pointer: `/3750`

使用灵敏度分析输入的 Fortran 页面

## UG10-CH20-D066

PDF page: 304; original JSON pointer: `/3751`

若在 Fortran 页面上输入可执行 Fortran 语句

## UG10-CH20-D067

PDF page: 304; original JSON pointer: `/3752`

l 在 Sensitivity Input 灵敏度分析输入 表中 单击 Fortran 页面

## UG10-CH20-D068

PDF page: 304; original JSON pointer: `/3753`

l 查看内嵌 Fortran 的规则和限制 关于更详细信息 参见第十九章

## UG10-CH20-D069

PDF page: 304; original JSON pointer: `/3754`

l 输入你的 Fortran 语句

## UG10-CH20-D070

PDF page: 304; original JSON pointer: `/3755`

为了确保你输入正确的变量名 单击鼠标右键 在弹出菜单中 单击 Variable List

## UG10-CH20-D071

PDF page: 304; original JSON pointer: `/3756`

变量列表 出现 Defined Variable List 已定义变量的列表 窗口 你可以将变

## UG10-CH20-D072

PDF page: 304; original JSON pointer: `/3757`

量从 Defined Variable List 已定义变量的列表 中拖放到 Fortran 页面中

## UG10-CH20-D073

PDF page: 304; original JSON pointer: `/3758`

Fortran 说明语句

## UG10-CH20-D074

PDF page: 304; original JSON pointer: `/3759`

按输入可执行 Fortran 语句的同样方式来输入 Fortran 说明语句 只是用 Declarations 说

## UG10-CH20-D075

PDF page: 305; original JSON pointer: `/3761`

明语句 页面替代 Fortran 页面

## UG10-CH20-D076

PDF page: 305; original JSON pointer: `/3762`

你可以将任意 Fortran 说明语句加到一个灵敏度分析模块中 它们包括

## UG10-CH20-D077

PDF page: 305; original JSON pointer: `/3763`

l DIMENSION 定义

## UG10-CH20-D078

PDF page: 305; original JSON pointer: `/3764`

l 数据类型定义 INTEGER 和 REAL

## UG10-CH20-D079

PDF page: 305; original JSON pointer: `/3765`

如果某个 Fortran 变量满足下列条件之一 则你应将它放到一个 COMMON 中

## UG10-CH20-D080

PDF page: 305; original JSON pointer: `/3766`

你在 Define 定义 页面上定义的 Fortran 变量不应在 Declarations 说明语句 页面上

## UG10-CH20-D081

PDF page: 305; original JSON pointer: `/3767`

将反应选择性相对于反应器温度制表的示例

## UG10-CH20-D082

PDF page: 305; original JSON pointer: `/3768`

把 RGibbs 模块 REACT 的温度对反应器出口中组分 ESTER 相对 ETOH的选择性的影响

## UG10-CH20-D083

PDF page: 305; original JSON pointer: `/3769`

制成表 假定在 RGibbs Setup Specifications RGibbs 设置规定 页面上已经输入了模块

## UG10-CH20-D084

PDF page: 305; original JSON pointer: `/3770`

REACT 温度的初始规定值

## UG10-CH20-D085

PDF page: 308; original JSON pointer: `/3774`

选择性 即 FESTER 与 FALC 的比是在 Tabulate 制表 页面上按 Fortran 表达式

## UG10-CH20-D086

PDF page: 308; original JSON pointer: `/3775`

FESTER/FALC输入的

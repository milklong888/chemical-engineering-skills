# UG10-CH19 Detail Operation Index - 第19章 FORTRAN块及内嵌FORTRAN

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH19-D001

PDF page: 284; original JSON pointer: `/3501`

第 19 章 FO RTRAN 块及内嵌 FORTRAN

## UG10-CH19-D002

PDF page: 284; original JSON pointer: `/3502`

第19章 FORTRAN 块及内嵌 FORTRAN

## UG10-CH19-D003

PDF page: 284; original JSON pointer: `/3503`

ASPEN PLUS 让你能够把你自己的 FORTRAN语句插入到流程计算中 本章将介绍

## UG10-CH19-D004

PDF page: 284; original JSON pointer: `/3504`

l 在 ASPEN PLUS 中使用 Fortran

## UG10-CH19-D005

PDF page: 284; original JSON pointer: `/3505`

l 建立一个 Fortran 块

## UG10-CH19-D006

PDF page: 284; original JSON pointer: `/3506`

l 输入 Fortran 语句

## UG10-CH19-D007

PDF page: 284; original JSON pointer: `/3507`

l 指定何时执行一个 Fortran 块

## UG10-CH19-D008

PDF page: 284; original JSON pointer: `/3508`

l 书写 Fortran 语句的规则

## UG10-CH19-D009

PDF page: 284; original JSON pointer: `/3509`

在 ASPEN PLUS中使用 Fortran

## UG10-CH19-D010

PDF page: 284; original JSON pointer: `/3510`

你可以在 ASPEN PLUS 中使用 Fortran 来执行任何可写成合法 Fortran 表达式的任务

## UG10-CH19-D011

PDF page: 284; original JSON pointer: `/3511`

你可以在 ASPEN PLUS 中按下列几种途径输入 Fortran 表达式

## UG10-CH19-D012

PDF page: 284; original JSON pointer: `/3512`

l 在 Fortran 块中

## UG10-CH19-D013

PDF page: 284; original JSON pointer: `/3513`

l 在其它模块的 Fortran 页中 例如设计规定 灵敏度分析或优化模块

## UG10-CH19-D014

PDF page: 284; original JSON pointer: `/3514`

l 在外部 Fortran 子程序中

## UG10-CH19-D015

PDF page: 284; original JSON pointer: `/3515`

l 含有用于执行用户定义的任务的 Fortran 表达式

## UG10-CH19-D016

PDF page: 284; original JSON pointer: `/3516`

在你输入 Fortran 代码时 ASPEN PLUS 将交互式地检查代码以便在运行之前能检测出

## UG10-CH19-D017

PDF page: 284; original JSON pointer: `/3517`

多数错误 如果在某个 Fortran 页上的状态指示器是

## UG10-CH19-D018

PDF page: 284; original JSON pointer: `/3518`

请使用 Next(下一步)找出未完成的

## UG10-CH19-D019

PDF page: 284; original JSON pointer: `/3519`

当由 ASPEN PLUS 提供的模型不能满足你的需要时 你可以编写外部用户 Fortran 子程

## UG10-CH19-D020

PDF page: 284; original JSON pointer: `/3520`

序 在你编译这些子程序后 在模拟运行时会动态地链接它们 通过使用这些外部用户子程

## UG10-CH19-D021

PDF page: 284; original JSON pointer: `/3521`

ASPEN PLUS 可以解释多数内嵌 Fortran 不能解释的 Fortran 被编译并且动态地链接到

## UG10-CH19-D022

PDF page: 284; original JSON pointer: `/3522`

ASPEN PLUS 模型上 因为采用了动态链接 所以编译内嵌 Fortran 所用的时间很少

## UG10-CH19-D023

PDF page: 284; original JSON pointer: `/3523`

注释 如果 Fortran 不能被解释 则需要一个 FORTRAN 编译器 关于对某给定平台所 推荐的编译器 请参见 ASPEN PLUS 安装指南 关于 FORTRAN 模块 通过用 Fortran 模块 你可以把 Fortran 语句插入到流程计算中 以便执行用户定义的任 务 例如

## UG10-CH19-D024

PDF page: 284; original JSON pointer: `/3524`

l 在使用输入变量前计算和设定它们 前馈控制

## UG10-CH19-D025

PDF page: 284; original JSON pointer: `/3525`

l 把信息写到控制面板上

## UG10-CH19-D026

PDF page: 284; original JSON pointer: `/3526`

l 从一个文件中读取输入数据

## UG10-CH19-D027

PDF page: 285; original JSON pointer: `/3528`

第 19 章 FORTRAN 块及内嵌 FORTRAN

## UG10-CH19-D028

PDF page: 285; original JSON pointer: `/3529`

l 把结果写到 ASPEN PLUS 报告或写到任意外部文件

## UG10-CH19-D029

PDF page: 285; original JSON pointer: `/3530`

由于 ASPEN PLUS 是一个每次执行一个单元操作的序贯模块化模拟器 所以你必须指

## UG10-CH19-D030

PDF page: 285; original JSON pointer: `/3531`

定在单元操作顺序中的何处执行每个 Fortran 模块 你可以通过做下列规定之一来完成上述

## UG10-CH19-D031

PDF page: 285; original JSON pointer: `/3532`

l 那些变量是从 Fortran 模块读取 或向 Fortran 模块写入

## UG10-CH19-D032

PDF page: 285; original JSON pointer: `/3533`

l 在单元操作模块列表中 Fortran 模块的位置

## UG10-CH19-D033

PDF page: 285; original JSON pointer: `/3534`

这样 ASPEN PLUS 就可以确定应当何时执行 Fortran 模块 建议你让 ASPEN PLUS 来

## UG10-CH19-D034

PDF page: 285; original JSON pointer: `/3535`

确定某个 Fortran 模块的执行顺序

## UG10-CH19-D035

PDF page: 285; original JSON pointer: `/3536`

通过下列步骤来定义一个 Fortran 模块

## UG10-CH19-D036

PDF page: 285; original JSON pointer: `/3537`

1. 建立一个 Fortran 模块

## UG10-CH19-D037

PDF page: 285; original JSON pointer: `/3538`

2. 标识模块被采集的或被操纵的流程变量

## UG10-CH19-D038

PDF page: 285; original JSON pointer: `/3539`

3. 输入 Fortran 语句

## UG10-CH19-D039

PDF page: 285; original JSON pointer: `/3540`

4. 指定何时执行 Fortran 模块 建立一个 Fortran 模块 若建立一个 Fortran 模块

## UG10-CH19-D040

PDF page: 285; original JSON pointer: `/3541`

1. 从 Data(数据)菜单中将鼠标指向 Flowsheeting Option( 建立流程选项 ) 然后指向 Fortran

## UG10-CH19-D041

PDF page: 285; original JSON pointer: `/3542`

2. 在 Fortran Object Manager(Fortran 对象管理器)中 单击 New(新建)

## UG10-CH19-D042

PDF page: 285; original JSON pointer: `/3543`

3. 在 Create New ID(建立新标识符)对话框中 输入一个标识符或接受缺省值 并单击 OK 下列章节介绍如何填写必需的页面 标识流程变量 你必须标识出一个 Fortran 模块中所用的流程变量 并且赋给它们变量名 一个变量名 标识出了在其它 Fortran 模块页面上的一个流程变量 使用 Define(定义 )页面来标识流程变量 使用 Define(定义)页面来标识一个流程变量并赋给它一个变量名 当填完一个 Define 页 面时 在 Variable Definition( 变量定义)对话框中指定变量 Define 定义 页面显示一个关

## UG10-CH19-D043

PDF page: 285; original JSON pointer: `/3544`

于所有存取变量的摘要 但是 你不能在 Define 定义 页面上修改变量

## UG10-CH19-D044

PDF page: 285; original JSON pointer: `/3545`

在 Define 定义 页面上

## UG10-CH19-D045

PDF page: 285; original JSON pointer: `/3546`

1. 若建立一个新变量 单击 New 新建 按扭 或者 若编辑一个现有变量 则选 择一个变量并单击 Edit 编辑 按扭

## UG10-CH19-D046

PDF page: 285; original JSON pointer: `/3547`

2. 在 Variable Name(变量名)字段中输入变量名 变量名必须符合下列规则

## UG10-CH19-D047

PDF page: 285; original JSON pointer: `/3548`

l 对于一个标变量 必须为 6 个或 6 个以下字符

## UG10-CH19-D048

PDF page: 285; original JSON pointer: `/3549`

l 对于一个矢变量 必须为 5 个或 5 个以下字符

## UG10-CH19-D049

PDF page: 286; original JSON pointer: `/3551`

第 19 章 FO RTRAN 块及内嵌 FORTRAN

## UG10-CH19-D050

PDF page: 286; original JSON pointer: `/3552`

3. 在 Category 类别 框内 使用选项按扭来选择变量类别

## UG10-CH19-D051

PDF page: 286; original JSON pointer: `/3553`

4. 在 Reference 引用 框内 从 Type 类型 字段内的列表中选变量类型 ASEPN PLUS 还显示完成变量定义所需的其它字段

## UG10-CH19-D052

PDF page: 286; original JSON pointer: `/3554`

5. 单击 Close 关闭 返回 Define 定义 页面 关于存取变量的更详细信息 参见第十八章 提示 使用 Delete 删除 按扭能够快速删除一个变量及用于定义该变量的所有字段 使用 Edit 编辑 按扭能够修改 Variable Definition 变量定义 对话框中的对某个变量的定 义 输入 Fortran 语句及说明语句 你可以按以下方式输入 Fortran 语句

## UG10-CH19-D053

PDF page: 286; original JSON pointer: `/3555`

l 在 Fortran 页面上

## UG10-CH19-D054

PDF page: 286; original JSON pointer: `/3556`

l 在你的文本编辑器中 例如 记事本 然后将它们复制并粘贴到 Fortran 页面上

## UG10-CH19-D055

PDF page: 286; original JSON pointer: `/3557`

按与可执行 Fortran 语句相同的方式输入 Fortran 说明语句 但应当用 Declarations 页面

## UG10-CH19-D056

PDF page: 286; original JSON pointer: `/3558`

取代 Fortran 页面

## UG10-CH19-D057

PDF page: 286; original JSON pointer: `/3559`

你可以将任意 Fortran 说明语句加到一个 Fortran 模块中 例如

## UG10-CH19-D058

PDF page: 286; original JSON pointer: `/3560`

l DIMENSION 定义

## UG10-CH19-D059

PDF page: 286; original JSON pointer: `/3561`

l 数据类型定义 INTEGER 和 REAL

## UG10-CH19-D060

PDF page: 286; original JSON pointer: `/3562`

如果某个 Fortran 变量符合下列条件之一 你应当将它放到一个 COMMON 定义中

## UG10-CH19-D061

PDF page: 286; original JSON pointer: `/3563`

l 在一个 Fortran 模块迭代计算过程中 它的值必须保持不变

## UG10-CH19-D062

PDF page: 286; original JSON pointer: `/3564`

你在 Define 页面上定义的 Fortran 变量不应在 Declarations 页面上说明

## UG10-CH19-D063

PDF page: 286; original JSON pointer: `/3565`

使用 Fortran 页面

## UG10-CH19-D064

PDF page: 286; original JSON pointer: `/3566`

若在 Fortran 页面上输入可执行 Fortran 语句

## UG10-CH19-D065

PDF page: 286; original JSON pointer: `/3567`

1. 在 Fortran 表上单击 Fortran 标签 若了解关于内嵌 Fortran 的规则及限制 参见本章 内嵌 Fortran 语句的规则

## UG10-CH19-D066

PDF page: 286; original JSON pointer: `/3568`

2. 输入你的 Fortran 语句

## UG10-CH19-D067

PDF page: 286; original JSON pointer: `/3569`

3. 为了确保你输入了正确的变量名 单击鼠标右键 在弹出菜单中 单击 Variable List 变量列表 出现 Defined Variable List 已定义变量的列表 窗口 你可以将变 量从 Defined Variable List 已定义变量的列表 中拖放到 Fortran 页面中 指定何时执行 Fortran 语句 你必须指定在计算过程中何时执行某个 Fortran 模块 若完成此工作 在 Fortran 表上 单击 Sequence 页面

## UG10-CH19-D068

PDF page: 286; original JSON pointer: `/3570`

1. 在 Read Variables 读变量 字段中 指定被使用但不改变的变量

## UG10-CH19-D069

PDF page: 286; original JSON pointer: `/3571`

2. 在 Write Variables 写变量 字段中 指定被改变的变量

## UG10-CH19-D070

PDF page: 287; original JSON pointer: `/3573`

第 19 章 FORTRAN 块及内嵌 FORTRAN

## UG10-CH19-D071

PDF page: 287; original JSON pointer: `/3574`

在 Sequence 页面的 Execute 字段中 指定何时执行该模块

## UG10-CH19-D072

PDF page: 287; original JSON pointer: `/3575`

Before 在某个模块之前 指定该模块的类型和名称

## UG10-CH19-D073

PDF page: 287; original JSON pointer: `/3576`

After 在某个模块之后 指定该模块的类型和名称

## UG10-CH19-D074

PDF page: 287; original JSON pointer: `/3577`

Report 在生成报告时

## UG10-CH19-D075

PDF page: 287; original JSON pointer: `/3578`

按在 Convergence Sequence Specification 收敛顺序规定 页

## UG10-CH19-D076

PDF page: 287; original JSON pointer: `/3579`

使用读/写变量 ASPEN PLUS 使用读写变量自动排序 Fortran 模块

## UG10-CH19-D077

PDF page: 287; original JSON pointer: `/3580`

Read Variables 读变量 和 Write Variables 写变量 是用于确定在 Define 定义 页

## UG10-CH19-D078

PDF page: 287; original JSON pointer: `/3581`

面上出现的变量中那些只是被采集变量 那些是由 Fortran 模块改变的变量

## UG10-CH19-D079

PDF page: 287; original JSON pointer: `/3582`

Read Variables 读变量 建立了从含有一个被采集 只读 变量的模块或流股到 Fortran

## UG10-CH19-D080

PDF page: 287; original JSON pointer: `/3583`

Write Variables 写变量 建立了从 Fortran 模块到被改变 读写或只写 变量的信息流

## UG10-CH19-D081

PDF page: 287; original JSON pointer: `/3584`

如果采用 Read Variables 读变量 和 Write Variables 写变量 的自动排序逻辑不能正 确排序 则使用 Execute 执行 语句来明确指定何时执行模块 由 Fortran 模块引起的收敛回路 一个 Fortran 模块可能引起必须迭代求解的回路 例如 一个 Fortran 模块可以根据某个 下游变量改变一个上游变量 如果 Fortran 模块是用来根据产品流率设定一个补充物流 则 会出现这种情况 如果你使用了产生回路的 Fortran 模块 那么 你必须指定 Read Variables 读变量 和

## UG10-CH19-D082

PDF page: 287; original JSON pointer: `/3585`

Write Variables 写变量 以便 ASPEN PLUS 检测回路并且生成正确的模拟结果

## UG10-CH19-D083

PDF page: 287; original JSON pointer: `/3586`

如果你完成了以下工作 ASPEN PLUS 自动求解由 Fortran 模块引起的任何回路

## UG10-CH19-D084

PDF page: 287; original JSON pointer: `/3587`

l 在 Convergence Conv-Options Defaults Sequencing 页面上 选择 Tear Fortran Write

## UG10-CH19-D085

PDF page: 287; original JSON pointer: `/3588`

Variable 撕裂 Fortran 写变量 复选框

## UG10-CH19-D086

PDF page: 287; original JSON pointer: `/3589`

l 在 Fortran block Sequence Fortran 模块顺序 页面上 指定 Read Variables 读变

## UG10-CH19-D087

PDF page: 287; original JSON pointer: `/3590`

当一个 Fortran 模块产生一个回路时 作为 Write Variables 写变量 输入的变量可以按

## UG10-CH19-D088

PDF page: 287; original JSON pointer: `/3591`

与撕裂循环流股同样的方法来撕裂以便收敛 APSEN PLUS 能够自动完成此工作 你也可

## UG10-CH19-D089

PDF page: 287; original JSON pointer: `/3592`

若把一个 Fortran Write Variables 写变量 指定为一个撕裂变量 则

## UG10-CH19-D090

PDF page: 287; original JSON pointer: `/3593`

l 在 Fortran 表上 单击 Tears 撕裂 标签

## UG10-CH19-D091

PDF page: 287; original JSON pointer: `/3594`

l 在 Tear Variable Name 撕裂变量名 字段中 选择你已在 S equence 顺序 页面

## UG10-CH19-D092

PDF page: 287; original JSON pointer: `/3595`

上的 Write Variables 写变量 字段中所输入的一个变量

## UG10-CH19-D093

PDF page: 287; original JSON pointer: `/3596`

l 在 Lower Bound 低限 和 Upper Bound 高限 字段内 输入撕裂变量的低限和

## UG10-CH19-D094

PDF page: 288; original JSON pointer: `/3598`

第 19 章 FO RTRAN 块及内嵌 FORTRAN

## UG10-CH19-D095

PDF page: 288; original JSON pointer: `/3599`

Definition 变量定义 对话框来选择的 为了使模拟能正确地收敛 需要在 Convergence

## UG10-CH19-D096

PDF page: 288; original JSON pointer: `/3600`

Conv-Options Defaults Sequencing 页面上选择 Tear Fortran Write Variable 撕裂 Fortran 写变

## UG10-CH19-D097

PDF page: 289; original JSON pointer: `/3602`

第 19 章 FORTRAN 块及内嵌 FORTRAN

## UG10-CH19-D098

PDF page: 290; original JSON pointer: `/3604`

第 19 章 FO RTRAN 块及内嵌 FORTRAN

## UG10-CH19-D099

PDF page: 291; original JSON pointer: `/3606`

第 19 章 FORTRAN 块及内嵌 FORTRAN

## UG10-CH19-D100

PDF page: 292; original JSON pointer: `/3608`

第 19 章 FO RTRAN 块及内嵌 FORTRAN

## UG10-CH19-D101

PDF page: 292; original JSON pointer: `/3609`

在 Convergence Conv -Options Defaults Sequencing 页面上 选择 Tear Fortran Write

## UG10-CH19-D102

PDF page: 292; original JSON pointer: `/3610`

Variable 撕裂 Fortran 写变量

## UG10-CH19-D103

PDF page: 292; original JSON pointer: `/3611`

有一个 Fortran 模块是用来使物流 HX2 的流率等于物流 HX1 的 75%

## UG10-CH19-D104

PDF page: 293; original JSON pointer: `/3613`

第 19 章 FORTRAN 块及内嵌 FORTRAN

## UG10-CH19-D105

PDF page: 294; original JSON pointer: `/3615`

第 19 章 FO RTRAN 块及内嵌 FORTRAN

## UG10-CH19-D106

PDF page: 295; original JSON pointer: `/3617`

第 19 章 FORTRAN 块及内嵌 FORTRAN

## UG10-CH19-D107

PDF page: 295; original JSON pointer: `/3618`

内嵌 Fortran 语句的规则

## UG10-CH19-D108

PDF page: 295; original JSON pointer: `/3619`

为了成功地编译你的 Fortran 语句 请遵循下列规则

## UG10-CH19-D109

PDF page: 295; original JSON pointer: `/3620`

l 缺省情况下 以 A-H 或 O-Z 为首字母的变量是双精度实型变量 以 I-N 为首字母

## UG10-CH19-D110

PDF page: 295; original JSON pointer: `/3621`

的变量是整型变量 并且缺省情况下使用双精度函数 例如 DSQRT 及双精度

## UG10-CH19-D111

PDF page: 295; original JSON pointer: `/3622`

l 不要使用以 IZ 或 ZZ 为首的变量名

## UG10-CH19-D112

PDF page: 295; original JSON pointer: `/3623`

l 因为 Fortran 是受列制约的语言 下表介绍如何作一些事情

## UG10-CH19-D113

PDF page: 295; original JSON pointer: `/3624`

输入语句标号 只是第三 四 五列

## UG10-CH19-D114

PDF page: 295; original JSON pointer: `/3625`

l 你可以调用你自己的子程序或函数 你可以用有标记的或空的 无标记 的

## UG10-CH19-D115

PDF page: 295; original JSON pointer: `/3626`

l 你在 Specification 页面上定义的 Fortran 变量不能放在 COMMON 中

## UG10-CH19-D116

PDF page: 295; original JSON pointer: `/3627`

l 不要使用 IMPLICIT SUBROUTINE ENTRY RETURN END 语句 也不要使

## UG10-CH19-D117

PDF page: 295; original JSON pointer: `/3628`

缺省情况下 ASPEN PLUS 交互式地检查你的 Fortran 语句 你可以关闭交互式语法检

## UG10-CH19-D118

PDF page: 295; original JSON pointer: `/3629`

查 有时你可能需要这样做 例如 当你使用一个接受非标准 Fortran 扩充的编译器的时候

## UG10-CH19-D119

PDF page: 295; original JSON pointer: `/3630`

或当语法检查程序不正确地把正确的 Fortran 标志为未完成的时候

## UG10-CH19-D120

PDF page: 295; original JSON pointer: `/3631`

若关闭 Fortran 语法检查

## UG10-CH19-D121

PDF page: 295; original JSON pointer: `/3632`

l 从 Tools 工具 菜单上 单击 Options 选项)

## UG10-CH19-D122

PDF page: 295; original JSON pointer: `/3633`

l 确保清除 Check Inline Fortran for Syntax Errors| 检查内置 Fortran 的语法错误 复

## UG10-CH19-D123

PDF page: 296; original JSON pointer: `/3635`

第 19 章 FO RTRAN 块及内嵌 FORTRAN

## UG10-CH19-D124

PDF page: 296; original JSON pointer: `/3636`

输出到屏幕和 ASPEN PLUS 文件

## UG10-CH19-D125

PDF page: 296; original JSON pointer: `/3637`

在 Fortran 的 WRITE 语句中 你可以使用下列预定义的变量来表示单元通道号

## UG10-CH19-D126

PDF page: 296; original JSON pointer: `/3638`

NTREM 控制面板 如果通过用户界面运行

## UG10-CH19-D127

PDF page: 296; original JSON pointer: `/3639`

终端 如果在用户界面之外交互式运行 或者 日志文件 如果批处理运行 NRPT ASPEN PLUS 报告 NHSTRY 模拟历史 示例: 若写到控制面板上 则 WRITE(NTERM,*)A B C X 若写到报告文件中 则 WRITE(NRPT *)A B C X 如果从一个 Fortran 模块向 ASPEN PLUS 报告中写入信息 则在 Sequence 顺序 页面 上的 Execute 执行 字段中选择 Report 报告 写到报告文件的输出信息将在 Fortran 模

## UG10-CH19-D128

PDF page: 296; original JSON pointer: `/3640`

块报告的 Flowsheet 流程 部分中显示

## UG10-CH19-D129

PDF page: 296; original JSON pointer: `/3641`

当向一个用户定义文件写入时 则使用一个 50 至 100 之间的单元通道号

## UG10-CH19-D130

PDF page: 296; original JSON pointer: `/3642`

在 Fortran 的 READ 语句中 你可以使用预定义的变量 NTERM 来表示交互式输入的单

## UG10-CH19-D131

PDF page: 296; original JSON pointer: `/3643`

下表显示了预定义变量实现的功能

## UG10-CH19-D132

PDF page: 296; original JSON pointer: `/3644`

交互式运行的形式 READ NTERM*

## UG10-CH19-D133

PDF page: 296; original JSON pointer: `/3645`

通过用户界面 显示一个接受一行输入信息的对话框

## UG10-CH19-D134

PDF page: 296; original JSON pointer: `/3646`

在用户界面之外运行 暂停 等待由终端输入

## UG10-CH19-D135

PDF page: 296; original JSON pointer: `/3647`

*当批处理方式运行 则不从 NTERM 读取

## UG10-CH19-D136

PDF page: 296; original JSON pointer: `/3648`

从一个 Fortran 模块交互式 READ 的示例

## UG10-CH19-D137

PDF page: 296; original JSON pointer: `/3649`

一个 Fortran 模块暂停运行 以便用户在运行模块 HX1 之前输入该模块的温度

## UG10-CH19-D138

PDF page: 296; original JSON pointer: `/3650`

下列表格定义变量 HX1TEM 用于指定模块 HX1 的输入温度

## UG10-CH19-D139

PDF page: 297; original JSON pointer: `/3652`

第 19 章 FORTRAN 块及内嵌 FORTRAN

## UG10-CH19-D140

PDF page: 297; original JSON pointer: `/3653`

Fortran 语句从交互式屏幕输入中读取 HX1TEM 并把值返回到控制面板

## UG10-CH19-D141

PDF page: 298; original JSON pointer: `/3655`

第 19 章 FO RTRAN 块及内嵌 FORTRAN

## UG10-CH19-D142

PDF page: 298; original JSON pointer: `/3656`

Sequence 顺序 页面指定 HX1TEM 是一个写变量 所以 ASPEN PLUS 可以排序 Fortran

## UG10-CH19-D143

PDF page: 298; original JSON pointer: `/3657`

如果你要实现下列功能 则把一个 Fortran 变量放到一个 在 Declareations 说明 页 面中的 COMMON 块中

## UG10-CH19-D144

PDF page: 298; original JSON pointer: `/3658`

COMMON 语句必须出现在每个使用所涉及变量的模块中

## UG10-CH19-D145

PDF page: 299; original JSON pointer: `/3660`

第 19 章 FORTRAN 块及内嵌 FORTRAN

## UG10-CH19-D146

PDF page: 299; original JSON pointer: `/3661`

缺省情况下 如果可能的话 ASPEN PLUS 将解释内嵌 Fortran 不能解释的 Fortran 将

## UG10-CH19-D147

PDF page: 299; original JSON pointer: `/3662`

被编译并链接到一个共享库或动态链接库 DLL 若编译代码 需要有一个 Fortran 编译器

## UG10-CH19-D148

PDF page: 299; original JSON pointer: `/3663`

关于对于给定平台推荐的编译器 参见有关安装指南 通过在 Setup Simulation Options

## UG10-CH19-D149

PDF page: 299; original JSON pointer: `/3664`

System 设置模拟选项系统 页面中将 Write Inline Fortran to a Subroutine 把内嵌 Fortran

## UG10-CH19-D150

PDF page: 299; original JSON pointer: `/3665`

写到一个子程序 选择为 Compiled and Dynamically Linked 编译并动态链接 可以编译所

## UG10-CH19-D151

PDF page: 299; original JSON pointer: `/3666`

下列 Fortran 可以被解释

## UG10-CH19-D152

PDF page: 299; original JSON pointer: `/3667`

l 调用下列内置 Fortran 函数

## UG10-CH19-D153

PDF page: 299; original JSON pointer: `/3668`

DATAN DGAMMA DSINH MOD

## UG10-CH19-D154

PDF page: 299; original JSON pointer: `/3669`

DATAN2 DLGAMA DSQRT

## UG10-CH19-D155

PDF page: 299; original JSON pointer: `/3670`

如果你使用下列语句 那么 你必须在 Declaration 说明 页面上输入它们

## UG10-CH19-D156

PDF page: 299; original JSON pointer: `/3671`

COMPLEX PRINT

## UG10-CH19-D157

PDF page: 299; original JSON pointer: `/3672`

关于外部 Fortran 子程序

## UG10-CH19-D158

PDF page: 299; original JSON pointer: `/3673`

外部用户 Fortran 是 ASPEN PLUS 的一个开放式并且能做大量定制工作的功能 一个

## UG10-CH19-D159

PDF page: 299; original JSON pointer: `/3674`

ASPEN PLUS 用户模型是由一个或多个 Fortran 子程序组成 这些子程序是在 ASPEN PLUS

## UG10-CH19-D160

PDF page: 299; original JSON pointer: `/3675`

提供的模型不能满足你的需要时你自己编写的 为了将你的模型能够与 ASPEN PLUS 接口

## UG10-CH19-D161

PDF page: 300; original JSON pointer: `/3677`

第 19 章 FO RTRAN 块及内嵌 FORTRAN

## UG10-CH19-D162

PDF page: 300; original JSON pointer: `/3678`

外部 Fortran 应用类型 用途

## UG10-CH19-D163

PDF page: 300; original JSON pointer: `/3679`

物性模型 纯组分和混合物 活度模型 KLL 用户状态方程

## UG10-CH19-D164

PDF page: 300; original JSON pointer: `/3680`

定制报告 用户定义的物流报告 用户模块报告 基于 Summary File

## UG10-CH19-D165

PDF page: 300; original JSON pointer: `/3681`

Toolkit 摘要文件工具箱 的应用

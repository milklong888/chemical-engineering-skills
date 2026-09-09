# UG10-CH22 Detail Operation Index - 第22章 优化

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH22-D001

PDF page: 322; original JSON pointer: `/3907`

l 输入可选的 Fortran 语句

## UG10-CH22-D002

PDF page: 322; original JSON pointer: `/3908`

l Fortran 说明语句

## UG10-CH22-D003

PDF page: 322; original JSON pointer: `/3909`

采用优化模块 通过调整决策变量 进料物流 模块输入或其它输入变量 来使一个用

## UG10-CH22-D004

PDF page: 322; original JSON pointer: `/3910`

户指定的目标函数最大化或最小化

## UG10-CH22-D005

PDF page: 322; original JSON pointer: `/3911`

目标函数可以是任意含有一个或多个流程量的合法 Fortran 表达式 目标函数的允差是

## UG10-CH22-D006

PDF page: 322; original JSON pointer: `/3912`

束与设计规定类似 约束可以是任意用 Fortran 表达式或内嵌 Fortran 语句计算的流程变量的

## UG10-CH22-D007

PDF page: 322; original JSON pointer: `/3913`

函数 你必须指定约束的误差 撕裂流和优化问题可以同时收敛或单独收敛

## UG10-CH22-D008

PDF page: 322; original JSON pointer: `/3914`

ASPEN PLUS 迭代求解优化问题 缺省情况下 ASPEN PLUS 为优化问题生成一个收

## UG10-CH22-D009

PDF page: 322; original JSON pointer: `/3915`

敛模块并进行排序 你可以通过在 Convergence 收敛 表上输入收敛规定来取代收敛的缺

## UG10-CH22-D010

PDF page: 322; original JSON pointer: `/3916`

省设置 用 SQP 和 Complex 方法收敛优化问题 关于优化收敛的完整介绍 参见第十七章

## UG10-CH22-D011

PDF page: 322; original JSON pointer: `/3917`

在物流或模块输入中所提供的被操纵变量的值被用作初始估值 为被操纵变量提供一个

## UG10-CH22-D012

PDF page: 322; original JSON pointer: `/3918`

除了目标函数和约束的收敛状况外 优化问题不直接与任何结果有关 你可以直接在相

## UG10-CH22-D013

PDF page: 322; original JSON pointer: `/3919`

应的物流或模块页面上查看被操纵变量和 /或被采集变量的最终值 或者在收敛模块的

## UG10-CH22-D014

PDF page: 322; original JSON pointer: `/3920`

Results Manipulated Variables 结果 被操纵变量 页面上查看摘要结果 若查找收敛模块的

## UG10-CH22-D015

PDF page: 322; original JSON pointer: `/3921`

摘要和迭代历史 请选择相应 Convergence 收敛 模块的 Results 结果 表页

## UG10-CH22-D016

PDF page: 322; original JSON pointer: `/3922`

优化问题很难公式化并不易收敛 在增加优化的复杂性之前很好地理解模拟问题十分重

## UG10-CH22-D017

PDF page: 322; original JSON pointer: `/3923`

要 我们推荐的建立一个优化问题的过程是

## UG10-CH22-D018

PDF page: 322; original JSON pointer: `/3924`

1. 从一个模拟开始 而不是从一个优化开始 使用该方法有下列原因

## UG10-CH22-D019

PDF page: 322; original JSON pointer: `/3925`

l 较容易检测到模拟中的流程错误

## UG10-CH22-D020

PDF page: 323; original JSON pointer: `/3927`

l 你可以确定合理的规定

## UG10-CH22-D021

PDF page: 323; original JSON pointer: `/3928`

2. 在优化之前做灵敏度分析 以便找出合适的决策变量和它们的范围

## UG10-CH22-D022

PDF page: 323; original JSON pointer: `/3929`

3. 用灵敏度分析来估算问题的解以便确定最优值是宽还是窄 定义一个优化问题 按下列步骤定义优化问题

## UG10-CH22-D023

PDF page: 323; original JSON pointer: `/3930`

2. 标识目标函数中所用的被采集变量

## UG10-CH22-D024

PDF page: 323; original JSON pointer: `/3931`

3. 为一个被采集变量或一些被采集变量的函数指定目标函数 并标识出与问题有关的 约束

## UG10-CH22-D025

PDF page: 323; original JSON pointer: `/3932`

4. 标识出为使目标函数最大或最小而被调整的模拟输入变量 并指定它们可被调整的 上下限

## UG10-CH22-D026

PDF page: 323; original JSON pointer: `/3933`

5. 输入可选的 Fortran 语句

## UG10-CH22-D027

PDF page: 323; original JSON pointer: `/3934`

6. 定义优化问题的约束条件 建立一个优化问题 若建立一个优化问题

## UG10-CH22-D028

PDF page: 323; original JSON pointer: `/3935`

1. 从 Data 菜单中 将鼠标移至 Model Analysis Tools ( 模型分析工具) 然后 指向 Optimization 优化

## UG10-CH22-D029

PDF page: 323; original JSON pointer: `/3936`

2. 在 Optimization Object Manager 优化目标管理器 中 单击 New (新建)

## UG10-CH22-D030

PDF page: 323; original JSON pointer: `/3937`

3. 在 Create New ID 建立新的标识符 对话框中 输入一个标识符 或接受一个缺 省的标识符 并单击 OK 标识被采集的流程变量 使用 Model Analysis Optimization Define 模型分析 优化 定义 页面来标识在设置优 化问题中所用的流程变量 并赋给它们变量名 变量名标识出你在定义目标函数 为操纵变 量指定范围或编写 Fortran 语句时可以使用的流程变量 使用 Define 定义 页面来标识一个流程变量并赋给它一个变量名 当完成一个 Define

## UG10-CH22-D031

PDF page: 323; original JSON pointer: `/3938`

定义 页面时 在 Variable Definition 变量定义 对话框中指定变量 Define 定义 页

## UG10-CH22-D032

PDF page: 323; original JSON pointer: `/3939`

面显示一个所有被访问变量的简单一览 但是 你不能修改 Define 定义 页面上的变量

## UG10-CH22-D033

PDF page: 323; original JSON pointer: `/3940`

在 Define 定义)页面上

## UG10-CH22-D034

PDF page: 323; original JSON pointer: `/3941`

1. 若建立一个新变量 单击 New 新建 按扭 或者 若编辑一个现有变量 选择 一个变量并单击 Edit 编辑 按扭

## UG10-CH22-D035

PDF page: 323; original JSON pointer: `/3942`

2. 在 Variable Name 变量名 字段中 输入变量名 如果你编辑一个变量并且要改 变变量名 则在 Variable Name 变量名 字段中单击鼠标右键 在弹出菜单上单 击 Rename 重命名 变量名必须是

## UG10-CH22-D036

PDF page: 324; original JSON pointer: `/3944`

l 不要以 IZ 或 ZZ 开头

## UG10-CH22-D037

PDF page: 324; original JSON pointer: `/3945`

3. 在 Category 类别 框中 用选项按扭选择变量类别

## UG10-CH22-D038

PDF page: 324; original JSON pointer: `/3946`

4. 在 Reference 引用 框中 从 Type 类型 字段中的列表选择变量类型 ASPEN PLUS 还显示为完成变量定义所需的其它字段

## UG10-CH22-D039

PDF page: 324; original JSON pointer: `/3947`

5. 单击 Close 关闭 返回 Define 定义 页面 关于访问变量的更详细信息 参见第十八章 访问流程变量 提示 用 Delete 删除 按扭能快速删除一个变量及定义它所用的所有字段 提示 用 Edit 编辑 按扭可以修改对 Variable Definition 变量定义 中某个变量的定 义 输入目标函数 如果优化有约束条件 则在你指定目标函数之前定义它们 更详细信息 参见本章 定 义约束条件 若为优化问题输入目标函数并标识约束条件

## UG10-CH22-D040

PDF page: 324; original JSON pointer: `/3948`

1. 在 Optimization 优化 表页上 单击 Objective & Constraints 目标和约束条件 标签

## UG10-CH22-D041

PDF page: 324; original JSON pointer: `/3949`

2. 选择 Maximize 最大化 或 Minimize 最小化 在 Objective Function 目标函数 字段中 输入目标变量或 Fortran 表达式

## UG10-CH22-D042

PDF page: 324; original JSON pointer: `/3950`

3. 为了确保你输入了正确的变量名 单击鼠标右键 在弹出菜单中 单击 Variable List 变量列表 出现 Defined Variable List 已定义变量的列表 窗口 你可以将变 量从 Defined Variable List 已定义变量的列表 中拖放到 Objective Function 目标 函数 页面中

## UG10-CH22-D043

PDF page: 324; original JSON pointer: `/3951`

4. 选择优化的约束条件 方法是用箭头按扭将它们从 Available Constraints 可用的约 束条件 列表中移到 Selected Constraints 已选的约束条件 列表中 如果你需要输入一个用一单个表达式不能处理的复杂 Fortran 表达式 你可以输入附加 的 Fortran 语句 更详细信息参见本章 输入可选 Fortran 语句 标识被操纵变量 用 Vary 改变 页面来标识被操纵变量并指定它的上下限 被操纵变量的上下限可以 是常数或是流程变量的函数

## UG10-CH22-D044

PDF page: 324; original JSON pointer: `/3952`

若标识被操纵变量并指定上下限

## UG10-CH22-D045

PDF page: 324; original JSON pointer: `/3953`

1. 在 Optimization 优化 表页上 单击 Vary 改变 标签

## UG10-CH22-D046

PDF page: 324; original JSON pointer: `/3954`

2. 在 Variable Number 变量号 字段中 单击下箭头并选择<new>

## UG10-CH22-D047

PDF page: 324; original JSON pointer: `/3955`

3. 在 Type 类型 字段中 选择一个变量类型 ASPEN PLUS 引导你到只有标识流 程变量所需的其余字段 关于访问变量的更详细信息 参见第十八章

## UG10-CH22-D048

PDF page: 324; original JSON pointer: `/3956`

4. 在 Lower 下限 字段中 输入一个常数或一个 Fortran 表达式作为被操纵变量的 下限

## UG10-CH22-D049

PDF page: 324; original JSON pointer: `/3957`

5. 在 Upper 上限 字段中 输入一个常数或一个 Fortran 表达式作为被操纵变量的 上限

## UG10-CH22-D050

PDF page: 325; original JSON pointer: `/3959`

6. 你可以标注决策变量以便其用于报告或 Results 结果 表页中 用 Line1 至 Line4 字段来定义这些标注

## UG10-CH22-D051

PDF page: 325; original JSON pointer: `/3960`

7. 重复步骤 2 至 6 直到指定完所有被操纵变量 你必须已经把被操纵变量作为一个输入规定输入 或者 它必须有一个缺省值 被操纵 变量的初始估值便是该规定或缺省值 你不能调整整型模块变量 例如 某个精馏塔的进料 位置 关于约束条件 你可以为优化问题指定等式和不等式约束条件 等式约束条件和非优化问题中的设计规 定一样 为你定义的每个约束条件提供一个标识符 约束条件标识符标识了 Optimization 优 化 页面上的约束条件 定义约束条件

## UG10-CH22-D052

PDF page: 325; original JSON pointer: `/3961`

按下列方法定义一个约束条件

## UG10-CH22-D053

PDF page: 325; original JSON pointer: `/3962`

2. 标识约束条件中所用的被采集变量

## UG10-CH22-D054

PDF page: 325; original JSON pointer: `/3963`

3. 指定约束条件表达式

## UG10-CH22-D055

PDF page: 325; original JSON pointer: `/3964`

4. 确认在 Optimization Objective & Constraints 优化目标和约束条件 页面选择了约 束条件 建立约束条件 若建立一个约束条件问题

## UG10-CH22-D056

PDF page: 325; original JSON pointer: `/3965`

1. 从 Data 数据 菜单 将鼠标指向 Model Analysis Tools 模型分析工具 然后指 向 C onstraints 约束条件

## UG10-CH22-D057

PDF page: 325; original JSON pointer: `/3966`

2. 在 Constraints Object Manager 约束条件对象管理器 中 单击 N ew 新建

## UG10-CH22-D058

PDF page: 325; original JSON pointer: `/3967`

3. 在 Create New ID 建立新标识符 对话框中 输入一个标识符 或接受缺省的标 识符 并单击 OK 标识用于约束条件的被采集流程变量 用 Model Analysis Constraints Define 模型分析 约束条件 定义 页面确定优化问题中 所用的流程变量并赋给它们变量名 变量名标识了你可在 Spec 规定 和 Fortran 页面中使 用的流程变量 使用 Define(定义)页面来标识一个流程变量并赋给它一个变量名 当填完一个 Define 页

## UG10-CH22-D059

PDF page: 325; original JSON pointer: `/3968`

面时 在 Variable Definition( 变量定义)对话框中指定变量 Define 定义 页面显示一个关

## UG10-CH22-D060

PDF page: 325; original JSON pointer: `/3969`

于所有存取变量的摘要 但是 你不能在 Define 定义 页面上修改变量

## UG10-CH22-D061

PDF page: 325; original JSON pointer: `/3970`

在 Define 定义 页面上

## UG10-CH22-D062

PDF page: 325; original JSON pointer: `/3971`

1. 若建立一个新变量 单击 New 新建 按扭 或者 若编辑一个现有变量 则选 择一个变量并单击 Edit 编辑 按扭

## UG10-CH22-D063

PDF page: 326; original JSON pointer: `/3973`

2. 在 Variable Name(变量名)字段中输入变量名 如果你编辑一个变量并且要改变变量 名 则在 Variable Name 变量名 字段中单击鼠标右键 在弹出菜单上单击 Rename 重命名 变量名必须是 变量名必须符合下列规则

## UG10-CH22-D064

PDF page: 326; original JSON pointer: `/3974`

l 对于一个标变量 必须为 6 个或 6 个以下字符

## UG10-CH22-D065

PDF page: 326; original JSON pointer: `/3975`

l 对于一个矢变量 必须为 5 个或 5 个以下字符

## UG10-CH22-D066

PDF page: 326; original JSON pointer: `/3976`

3. 在 Category 类别 框内 使用选项按扭来选择变量类别

## UG10-CH22-D067

PDF page: 326; original JSON pointer: `/3977`

4. 在 Reference 引用 框内 从 Type 类型 字段内的列表中选变量类型 ASEPN PLUS 还显示完成变量定义所需的其它字段

## UG10-CH22-D068

PDF page: 326; original JSON pointer: `/3978`

5. 单击 Close 关闭 返回 Define 定义 页面 关于存取变量的更详细信息 参见第十八章 访问流程变量 提示 使用 Delete 删除 按扭能够快速删除一个变量及用于定义该变量的所有字段 提示 使用 Edit 编辑 按扭能够修改 Variable Definition 变量定义 对话框中的对某 个变量的定义 指定约束条件 表达式 你需要把约束条件指定为被采集变量的函数并为约束条件提供允差 约束条件函数定义如下

## UG10-CH22-D069

PDF page: 326; original JSON pointer: `/3979`

1. 在 Constraints 约束条件 表页上 单击 Spec 规定 标签

## UG10-CH22-D070

PDF page: 326; original JSON pointer: `/3980`

2. 在两个 Constraints expression specification (约束条件表达式规定)字段中 按常数或 Fortran 表达式来输入表达式 1 和表达式 2 为了确保你输入了正确的变量名 单击鼠标右键 在弹出菜单中 单击 Variable List 变量列表 出现 Defined Variable List 已定义变量的列表 窗口 你可以将变 量从 Defined Variable List 已定义变量的列表 中拖放到 Spec 表的字段中

## UG10-CH22-D071

PDF page: 326; original JSON pointer: `/3981`

3. 为规定选择 Equal to 等于 Less than or equal to 小于或等于 或 Greater than or equal to 大于或等于

## UG10-CH22-D072

PDF page: 326; original JSON pointer: `/3982`

4. 在 Tolerance 允差 字段中 按一个常数或一个 Fortran 表达式输入约束条件的允 差

## UG10-CH22-D073

PDF page: 326; original JSON pointer: `/3983`

5. 如果约束条件使一个矢量 选择 This is a Vector Constraint 这是一个矢量约束条件 复选框 并指定应使用的矢量元素 如果你需要输入不能用一单行表达式处理的较复杂 Fortran 你可以在 Constraints Fortran 约束条件 Fortran 页面上输入附加的语句 参见本章 可选的 Fortran 语句

## UG10-CH22-D074

PDF page: 327; original JSON pointer: `/3985`

输入可选的 Fortran 语句

## UG10-CH22-D075

PDF page: 327; original JSON pointer: `/3986`

你可以输入计算优化目标函数项或被操纵变量限制所需的任何 Fortran 语句 任何由

## UG10-CH22-D076

PDF page: 327; original JSON pointer: `/3987`

Fortran 语句计算的变量都可以用在下列页面上的表达式中

## UG10-CH22-D077

PDF page: 327; original JSON pointer: `/3988`

l Optimization Objective & Constraints 优化目标及约束条件

## UG10-CH22-D078

PDF page: 327; original JSON pointer: `/3989`

l Optimization Vary 优化 改变

## UG10-CH22-D079

PDF page: 327; original JSON pointer: `/3990`

l Constraints Spec 约束条件 规定

## UG10-CH22-D080

PDF page: 327; original JSON pointer: `/3991`

只有函数太复杂而不能在这些页面上输入时才需要 Fortran 语句

## UG10-CH22-D081

PDF page: 327; original JSON pointer: `/3992`

你可以按下列方式输入 Fortran 语句

## UG10-CH22-D082

PDF page: 327; original JSON pointer: `/3993`

l 在 Fortran 页面上

## UG10-CH22-D083

PDF page: 327; original JSON pointer: `/3994`

l 在你的文本编辑器中 例如 记事本 然后将它们复制并粘贴到 Fortran 页面上

## UG10-CH22-D084

PDF page: 327; original JSON pointer: `/3995`

使用 Fortran 页面

## UG10-CH22-D085

PDF page: 327; original JSON pointer: `/3996`

若在 Fortran 页面上输入可执行语句

## UG10-CH22-D086

PDF page: 327; original JSON pointer: `/3997`

1. 在 Optimization 优化 或 Constraints 约束条件 表页上 单击 Fortran 标签

## UG10-CH22-D087

PDF page: 327; original JSON pointer: `/3998`

2. 查看关于内嵌 Fortran 的规则和限制 更详细信息参见第十九章

## UG10-CH22-D088

PDF page: 327; original JSON pointer: `/3999`

3. 输入 Fortran 语句 为了确保你输入了正确的变量名 单击鼠标右键 在弹出菜单中 单击 Variable List 变 量列表 出现 Defined Variable List 已定义变量的列表 窗口 你可以将变量从 Defined Variable List 已定义变量的列表 中拖放到 Fortran 页面中 Fortran 说明语句 按输入可执行 Fortran 语句的同样方式来输入 Fortran 说明语句 只是用 Declarations 说

## UG10-CH22-D089

PDF page: 327; original JSON pointer: `/4000`

明语句 页面替代 Fortran 页面

## UG10-CH22-D090

PDF page: 327; original JSON pointer: `/4001`

你可以将任意 Fortran 说明语句加到一个优化问题中 它们包括

## UG10-CH22-D091

PDF page: 327; original JSON pointer: `/4002`

l DIMENSION 定义

## UG10-CH22-D092

PDF page: 327; original JSON pointer: `/4003`

l 数据类型定义 INTEGER 和 REAL

## UG10-CH22-D093

PDF page: 327; original JSON pointer: `/4004`

如果某个 Fortran 变量满足下列条件之一 则你应将它放到一个 COMMON 中

## UG10-CH22-D094

PDF page: 327; original JSON pointer: `/4005`

你在 Define 定义 页面上定义的 Fortran 变量不应在 Declarations 说明语句 页面上

## UG10-CH22-D095

PDF page: 328; original JSON pointer: `/4007`

可行 如果有撕裂流和等式约束条件 设计规定 的话 则要求在每次优化 迭代都收敛它们 非可行 可以将撕裂流 等式约束条件和非等式约束条件同时与优化问题一起 收敛/ 在 ASPEN LUS中可用下列优化算法

## UG10-CH22-D096

PDF page: 328; original JSON pointer: `/4008`

l COMPLEX 方法

## UG10-CH22-D097

PDF page: 328; original JSON pointer: `/4009`

COMPLEX 方法采用的是大家熟知的复合型算法 这是一个可行路径 黑箱 式搜索法

## UG10-CH22-D098

PDF page: 328; original JSON pointer: `/4010`

该方法能处理不等式约束条件和决策变量的边界 等式约束条件必须按设计规定处理 你必

## UG10-CH22-D099

PDF page: 328; original JSON pointer: `/4011`

须用单独的收敛模块来收敛任意撕裂流和设计规定 COMPLEX 方法经常需要进行多次迭代

## UG10-CH22-D100

PDF page: 328; original JSON pointer: `/4012`

优化收敛提供了一个稳定和可靠的选择

## UG10-CH22-D101

PDF page: 328; original JSON pointer: `/4013`

非等式约束与优化问题同时收敛 SQP 方法通常只在较少的迭代次数内收敛 但是 需要

## UG10-CH22-D102

PDF page: 328; original JSON pointer: `/4014`

用户可以指定执行 Wegstein 计算的次数 选择一个大的值能够有效地使 SQP 成为一个

## UG10-CH22-D103

PDF page: 328; original JSON pointer: `/4015`

可行路径 但不是黑箱 方法 APSEN PLUS 缺省情况下是进行三次 Wegstein 计算

## UG10-CH22-D104

PDF page: 328; original JSON pointer: `/4016`

通过将撕裂流和设计规定作为优化问题的一个内回路 使用单独的收敛模块 你可以

## UG10-CH22-D105

PDF page: 328; original JSON pointer: `/4017`

在 ASPEN PLUS 中缺省的优化收敛方法是用 SQP 方法同时收敛撕裂流和优化问题

## UG10-CH22-D106

PDF page: 328; original JSON pointer: `/4018`

优化问题的收敛可能对被操纵变量的初值敏感 优化算法只找到目标函数中局域最大值

## UG10-CH22-D107

PDF page: 328; original JSON pointer: `/4019`

1. 确认在一个被操纵变量变化范围内目标函数曲线没有一个单调区间 避免使用含有 不连续点的目标函数和约束条件

## UG10-CH22-D108

PDF page: 328; original JSON pointer: `/4020`

2. 尽可能将约束条件线性化

## UG10-CH22-D109

PDF page: 328; original JSON pointer: `/4021`

3. 如果开始误差有改善 但接着又变化不大 则计算的微分对步长敏感 需要尝试做

## UG10-CH22-D110

PDF page: 329; original JSON pointer: `/4023`

l 检查被操作变量是否处于它的上限或下限

## UG10-CH22-D111

PDF page: 329; original JSON pointer: `/4024`

模拟选项 页面上 关闭 Use Results from Previous Convergence Pass 使用上

## UG10-CH22-D112

PDF page: 329; original JSON pointer: `/4025`

4. 检查确认被操纵变量是否影响目标函数和/或约束条件的值 或许 需要通过执行 一个灵敏度分析来实现

## UG10-CH22-D113

PDF page: 329; original JSON pointer: `/4026`

5. 为被操纵变量提供一个更好的初始估值

## UG10-CH22-D114

PDF page: 329; original JSON pointer: `/4027`

6. 缩窄被操纵变量的上下限或放宽目标函数的允差可能有助于收敛

## UG10-CH22-D115

PDF page: 329; original JSON pointer: `/4028`

7. 修改与优化相关的收敛模块的参数 步长 迭代次数等 最大化产品价值的示例 某个反应器产品物流的价值是所希望产品 P 的流率和不希望的副产品 G 流率的函数 价值=P-30*G 采用优化来找到使产品价值最大的反应温度

## UG10-CH22-D116

PDF page: 329; original JSON pointer: `/4029`

l 你可以在优化问题的任何部分使用 Fortran 表达式 例如 P-30*G

## UG10-CH22-D117

PDF page: 329; original JSON pointer: `/4030`

器温度 就象没有优化模块一样 在反应器模块内指定被操纵变量 所指定的值被

## UG10-CH22-D118

PDF page: 329; original JSON pointer: `/4031`

l 你不必指定优化的收敛模块 ASPEN PLUS 自动生成一个收敛模块来收敛优化问

## UG10-CH22-D119

PDF page: 332; original JSON pointer: `/4035`

的蒸汽的成本来计算的 使用 Fortran 页面来计算价值函数

## UG10-CH22-D120

PDF page: 333; original JSON pointer: `/4037`

l 用 Fortran 页面计算价值函数 CFUNC

## UG10-CH22-D121

PDF page: 333; original JSON pointer: `/4038`

l 就象没有优化模块一样 在模块内指定被操纵变量 所指定的值被优化收敛模块用

## UG10-CH22-D122

PDF page: 333; original JSON pointer: `/4039`

l 你不必指定优化的收敛模块 ASPEN PLUS 自动生成一个收敛模块来收敛优化问

## UG10-CH22-D123

PDF page: 333; original JSON pointer: `/4040`

在 Optimization 优化 页面上

## UG10-CH22-D124

PDF page: 337; original JSON pointer: `/4045`

在 DUTY 约束条件页面上

## UG10-CH22-D125

PDF page: 338; original JSON pointer: `/4047`

在 PURITY 约束条件页面上

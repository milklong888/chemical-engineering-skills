# UG10-CH18 Detail Operation Index - 第18章 访问流程变量

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH18-D001

PDF page: 261; original JSON pointer: `/3311`

l Fortran 模块

## UG10-CH18-D002

PDF page: 261; original JSON pointer: `/3312`

l Data-Fit(数据拟合)题目

## UG10-CH18-D003

PDF page: 261; original JSON pointer: `/3313`

l 选择输入变量和参数变量

## UG10-CH18-D004

PDF page: 261; original JSON pointer: `/3314`

l 被访问的变量在 Fortran 语句中使用示例

## UG10-CH18-D005

PDF page: 261; original JSON pointer: `/3315`

当你在 ASPEN PLUS 中运行一个模拟时 你经常需要记录或修改模拟中的量值 例如

## UG10-CH18-D006

PDF page: 261; original JSON pointer: `/3316`

的特性要求你访问变量 例如设计规定 Fortran 模块 优化题目 Data-Fit(数据拟合)题目

## UG10-CH18-D007

PDF page: 261; original JSON pointer: `/3317`

被访问得最多的变量有一个用户规定的相关名字 例如 你可能将名称 PRES 和代

## UG10-CH18-D008

PDF page: 261; original JSON pointer: `/3318`

表一个 Flash2 模块中的压力的一个变量联系起来 然而 要由设计规定 灵敏度模块或优

## UG10-CH18-D009

PDF page: 261; original JSON pointer: `/3319`

化改变的变量没有一个相关的名称

## UG10-CH18-D010

PDF page: 261; original JSON pointer: `/3320`

用户输入的变量 用户可以直接操作任何用户输入的变量 这些变量可以或者

## UG10-CH18-D011

PDF page: 261; original JSON pointer: `/3321`

这些变量不应被重写或者被直接改变 因为这会导致不一致

## UG10-CH18-D012

PDF page: 261; original JSON pointer: `/3322`

的结果 这些变量仅应该被读

## UG10-CH18-D013

PDF page: 261; original JSON pointer: `/3323`

确信访问了正确的变量是很重要的 当你从一个下拉列表中选择了一个变量时 看一看

## UG10-CH18-D014

PDF page: 261; original JSON pointer: `/3324`

例如 当你为一个 Flash2 或一个叫 PDROP 的加热器选择模块变量时 提示会告诉你这

## UG10-CH18-D015

PDF page: 261; original JSON pointer: `/3325`

是加热或冷却曲线的压降(不是模块的压降) 当你选择了变量 PRES 提示会告诉你这个变

## UG10-CH18-D016

PDF page: 261; original JSON pointer: `/3326`

量是对模块的压力规定 如果输入了压降 那么它的值将是负的

## UG10-CH18-D017

PDF page: 261; original JSON pointer: `/3327`

被访问的标量变量的值采用在 Units(单位)域(在 Data Browser 工具栏上)中规定的单位

## UG10-CH18-D018

PDF page: 261; original JSON pointer: `/3328`

例如 你或许在 Design Spec Define (设计规定定义)页上定义了一个变量作为流股温度 如

## UG10-CH18-D019

PDF page: 262; original JSON pointer: `/3330`

位是 SI 单位 而不管规定的单位是什么 对于一个对象仅有一个单位集 一个对象的所有

## UG10-CH18-D020

PDF page: 262; original JSON pointer: `/3331`

访问变量(既包括定义的也包括改变的)的单位在一个相同的单位集中

## UG10-CH18-D021

PDF page: 262; original JSON pointer: `/3332`

Mole-Flow 流股中的组分摩尔流量

## UG10-CH18-D022

PDF page: 262; original JSON pointer: `/3333`

Mole-Frac** 流股中的组分摩尔分率

## UG10-CH18-D023

PDF page: 262; original JSON pointer: `/3334`

Stream-Prop** 由性质集定义的流股性质

## UG10-CH18-D024

PDF page: 262; original JSON pointer: `/3335`

Compattr-Var 组分属性元素

## UG10-CH18-D025

PDF page: 262; original JSON pointer: `/3336`

Compattr-Vec 组分属性矢量

## UG10-CH18-D026

PDF page: 262; original JSON pointer: `/3337`

* 这些流股仅被作为结果访问 你不能改变它们或设置它们

## UG10-CH18-D027

PDF page: 262; original JSON pointer: `/3338`

MOLE -ENTHALPY MASS-ENTHALPY MOLE-ENTROPY MASS-ENTROPY

## UG10-CH18-D028

PDF page: 262; original JSON pointer: `/3339`

MOLE-DENSITY MASS-DENSITY LFRAC

## UG10-CH18-D029

PDF page: 262; original JSON pointer: `/3340`

** 此种类型的变量仅被作为结果访问 你不能改变或设置它们

## UG10-CH18-D030

PDF page: 262; original JSON pointer: `/3341`

Parameter 用户定义的参数 参见本章的使用参数变量部分

## UG10-CH18-D031

PDF page: 263; original JSON pointer: `/3343`

当正在完成一个 Define 页 例如在一个 Fortran Design specification (设计规定 )或

## UG10-CH18-D032

PDF page: 263; original JSON pointer: `/3344`

Sensitivity(灵敏度)表格上时 在 Variable Definition(变量定义)对话框上规定变量 Define(定

## UG10-CH18-D033

PDF page: 263; original JSON pointer: `/3345`

义)页显示了所有被访问的变量的简要叙述 但你不能在 Define(定义)页上修改这些变量

## UG10-CH18-D034

PDF page: 263; original JSON pointer: `/3346`

当在任意 Define(定义)页上时

## UG10-CH18-D035

PDF page: 263; original JSON pointer: `/3347`

1. 要创建一个新变量 就单击 New(新建)按钮 或 要编辑一个已有的变量 选择一个变量并单击 Edit(编辑)按钮

## UG10-CH18-D036

PDF page: 263; original JSON pointer: `/3348`

2. 在 Variable Name(变量名)域中 输入变量名

## UG10-CH18-D037

PDF page: 263; original JSON pointer: `/3349`

3. 在 Category(类别)窗口中 使用选项按钮来选择变量类别

## UG10-CH18-D038

PDF page: 263; original JSON pointer: `/3350`

4. 在 Reference(参考)窗口中 从在 Type(类型)域中的列表上选择变量类型 ASPEN PLUS 显示要完成变量定义必需的其它域

## UG10-CH18-D039

PDF page: 263; original JSON pointer: `/3351`

5. 单击 Close(关闭)返回 Define(定义)页 计算补充流率示例 一个补充流股 (MAKE-UP)质量流率是通过使用一个 FORTRAN 模块 由循环流股 (RECYCLE)质量流率减去 120 lb/hr 来确定的 ASPEN PLUS 将补充流率写入 Control Panel(控制面板) 在 Fortran Define(Fortran 定义)页上 定义了两个 Fortran 变量 FMAKE 和 FRECYC 代表 两个流股质量流率 Variable Definition(变量定义)对话框被用来定义这些变量

## UG10-CH18-D040

PDF page: 265; original JSON pointer: `/3354`

在 Fortran Fortran 页上 加入下列这些 Fortran 语句

## UG10-CH18-D041

PDF page: 265; original JSON pointer: `/3355`

C If no makeup is required set

## UG10-CH18-D042

PDF page: 265; original JSON pointer: `/3356`

C stream composition

## UG10-CH18-D043

PDF page: 265; original JSON pointer: `/3357`

10 FORMAT(1X.’MAKEUP FLOW RATE=’ F10.2) 选择输入或结果变量 有时当访问下列变量时区别输入和结果是很重要的

## UG10-CH18-D044

PDF page: 265; original JSON pointer: `/3358`

例如 假定你正在给模拟规定了温度和气体分率的一个加热器模块计算的负荷 你必须

## UG10-CH18-D045

PDF page: 265; original JSON pointer: `/3359`

访问结果变量 QCALC 不是输入变量 DUTY DUTY 将不会有值

## UG10-CH18-D046

PDF page: 265; original JSON pointer: `/3360`

要确定一个变量是输入变量还是结果变量

## UG10-CH18-D047

PDF page: 265; original JSON pointer: `/3361`

1. 在其中你正在访问变量的 Variable Definition(变量定义)对话框中 在 Variable(变量) 域上单击箭头 并从列表中选择变量

## UG10-CH18-D048

PDF page: 265; original JSON pointer: `/3362`

2. 检查提示 如果提示以 Calculated(计算的)开头 则该变量是结果变量 否则它是 一个输入变量 选择输入或结果变量的指导原则 选择输入或结果变量要遵循下列这些原则

## UG10-CH18-D049

PDF page: 265; original JSON pointer: `/3363`

l 当设置和操作输入规定时选择输入变量

## UG10-CH18-D050

PDF page: 265; original JSON pointer: `/3364`

l 选择要用于设计规定表达式 优化目标函数 约束条件表达式和灵敏度表的结果变

## UG10-CH18-D051

PDF page: 265; original JSON pointer: `/3365`

l 要知在 Data-Fit(数据拟合)模块中访问变量时的特殊方法 参见第十九章

## UG10-CH18-D052

PDF page: 265; original JSON pointer: `/3366`

l 如果在一个模块的输出流股中 结果是有效的 就访问流股变量 例如 要访问一 加热器模块计算的温度 就访问输出流股的温度

## UG10-CH18-D053

PDF page: 265; original JSON pointer: `/3367`

l 如果在一模块的输出流股中不能获得结果 那么就选择带有以 Calculated 开头的提 示符的模块变量 例如 变量 QCALC(由一加热器模块计算的负荷 )的提示是 Calculated heat duty(计算的热负荷)

## UG10-CH18-D054

PDF page: 265; original JSON pointer: `/3368`

l MASS-FRAC MOLE-FRAC 和 STDVOL-FRAC 是结果变量 并且不能被改变

## UG10-CH18-D055

PDF page: 265; original JSON pointer: `/3369`

参数变量是用户定义的全局变量 用于临时存储未在 ASPEN PLUS 中定义的量 例如

## UG10-CH18-D056

PDF page: 265; original JSON pointer: `/3370`

一个设计规定操作一个用户定义的变量(Parameter 1 参数 1) 它代表了两个加热器之

## UG10-CH18-D057

PDF page: 265; original JSON pointer: `/3371`

间的温差 一个 Fortran 模块检索参数(DELT)和第一加热器的温度(T1) 并且使用这些变量

## UG10-CH18-D058

PDF page: 265; original JSON pointer: `/3372`

来设置第二加热器的温度(T2) 在 Fortran Define(Fortran 定义)页上 Fortran Definition(定义)

## UG10-CH18-D059

PDF page: 265; original JSON pointer: `/3373`

对话框被用来定义这些变量 在 Design Spec(设计规定)窗口中

## UG10-CH18-D060

PDF page: 266; original JSON pointer: `/3375`

在 Fortran 窗口中

## UG10-CH18-D061

PDF page: 269; original JSON pointer: `/3379`

ASPEN PLUS 将你分配给矢量的 Fortran 变量解释为一个数组变量 你不必为它选定维数

## UG10-CH18-D062

PDF page: 269; original JSON pointer: `/3380`

Compattr-Vec 组分属性矢量 ( 参见本章的组分属性和PSD部分)

## UG10-CH18-D063

PDF page: 269; original JSON pointer: `/3381`

ASPEN PLUS 通过在你分配给矢量的Fortran变量名的开头加一个字母L来生成变量 该

## UG10-CH18-D064

PDF page: 269; original JSON pointer: `/3382`

变量的值即矢量的长度 你可以在Fortran语句中使用该变量 但你不能改变它的值

## UG10-CH18-D065

PDF page: 269; original JSON pointer: `/3383`

流股或子流股 ASPEN PLUS 将你分配给流股的 Fortran 变量解释为一数组变量 你不必计

## UG10-CH18-D066

PDF page: 269; original JSON pointer: `/3384`

一个流股矢量包含用于那个流股类的所有子流股矢量 子流股的顺序在 Define Stream

## UG10-CH18-D067

PDF page: 269; original JSON pointer: `/3385`

Class 对话框上被定义(在 Setup StreamClass Flowsheet (设置流股类流程)页上 单击 Define

## UG10-CH18-D068

PDF page: 269; original JSON pointer: `/3386`

Stream Class(定义流股类流程)按钮)

## UG10-CH18-D069

PDF page: 269; original JSON pointer: `/3387`

下表列出了当访问缺省流股类 CONVEN 时 用于子流股 MIXED 和 Stream-Vec(流股矢

## UG10-CH18-D070

PDF page: 269; original JSON pointer: `/3388`

1, . . . , NCC 组分摩尔流量(kg-moles/sec)

## UG10-CH18-D071

PDF page: 269; original JSON pointer: `/3389`

NCC + 1 总摩尔流量(kg-moles/sec)

## UG10-CH18-D072

PDF page: 269; original JSON pointer: `/3390`

NCC + 9 分子量(kg/kg-mole)

## UG10-CH18-D073

PDF page: 269; original JSON pointer: `/3391`

NCC 是在 Components Specifications Selection (组分规定选择)页上规定的常规组分数

## UG10-CH18-D074

PDF page: 270; original JSON pointer: `/3393`

Define(定义)页上的 Unit specification(单位规定)是什么

## UG10-CH18-D075

PDF page: 270; original JSON pointer: `/3394`

ASPEN PLUS 通过在你分配给子流股或流股矢量的 Fortran 变量名的开头加一个字母 L

## UG10-CH18-D076

PDF page: 270; original JSON pointer: `/3395`

来生成一个变量 该变量的值就是矢量的长度(NCC+9) 你可以在 Fortran 语句中使用变量

## UG10-CH18-D077

PDF page: 270; original JSON pointer: `/3396`

一 Fortran 模块用来将流股 HX1-OUT 的摩尔分率写到终端 在 Fortran 模块的 Define(定

## UG10-CH18-D078

PDF page: 270; original JSON pointer: `/3397`

义)页上 定义了 Stram-Vec(流股矢量)类型的 Fortran 变量 SOUT

## UG10-CH18-D079

PDF page: 270; original JSON pointer: `/3398`

在 Fortran Fortran 页上 加入了这些 Fortran 语句

## UG10-CH18-D080

PDF page: 270; original JSON pointer: `/3399`

NCOMP=LSOUT-9

## UG10-CH18-D081

PDF page: 270; original JSON pointer: `/3400`

DO 10 I=1, NCOMP

## UG10-CH18-D082

PDF page: 270; original JSON pointer: `/3401`

X(I)=SOUT(I)/SOUT(NCOMP+1)

## UG10-CH18-D083

PDF page: 270; original JSON pointer: `/3402`

20 FORMAT (10X, I3, 2X, F10.4)

## UG10-CH18-D084

PDF page: 270; original JSON pointer: `/3403`

30 FORMAT (‘STREAM HX1-OUT MOLE FRACTIONS’)

## UG10-CH18-D085

PDF page: 271; original JSON pointer: `/3405`

在 Fortran Declarations(Fortran 说明)页上 下列语句最多容许 20 个组分

## UG10-CH18-D086

PDF page: 271; original JSON pointer: `/3406`

CISOLID 子流股的子流股矢量形式与子流股 MIXED 的矢量形式相同 只有一个例外

## UG10-CH18-D087

PDF page: 271; original JSON pointer: `/3407`

是常规组分数 在 MIXED 和 CISOLID 子流股中都保存了用于所有常规组分的空间 组分

## UG10-CH18-D088

PDF page: 271; original JSON pointer: `/3408`

顺序与在 Component Specifications Selection(组分规定选择)页上的顺序相同 所有值都采用

## UG10-CH18-D089

PDF page: 271; original JSON pointer: `/3409`

SI 单位制 而不管在 Units speciifications(单位规定)上规定的是什么单位

## UG10-CH18-D090

PDF page: 271; original JSON pointer: `/3410`

1, . . . , NCC 常规组分摩尔流量(kg-moles/sec)

## UG10-CH18-D091

PDF page: 271; original JSON pointer: `/3411`

NCC + 1 总摩尔流量(kg-moles/sec)

## UG10-CH18-D092

PDF page: 271; original JSON pointer: `/3412`

NCC + 9 分子量(kg/kg-mole)

## UG10-CH18-D093

PDF page: 271; original JSON pointer: `/3413`

PSD 值(如果为该子流股定义了一个PSD属性 )

## UG10-CH18-D094

PDF page: 271; original JSON pointer: `/3414`

ASPEN PLUS通过在你分配给子流股或流股矢量的Fortran变量名的开头增加了一个字母

## UG10-CH18-D095

PDF page: 271; original JSON pointer: `/3415`

L来生成一个变量 该变量的值等于矢量(NCC+9+n)的长度 你可以在Fortran语句中使用该

## UG10-CH18-D096

PDF page: 271; original JSON pointer: `/3416`

变量 但你不能改变它的值

## UG10-CH18-D097

PDF page: 271; original JSON pointer: `/3417`

用于 …的组分顺序 与在 …上规定的组分顺序相同

## UG10-CH18-D098

PDF page: 271; original JSON pointer: `/3418`

组分流量 Components Specifications Selection(组分规定选择)页

## UG10-CH18-D099

PDF page: 271; original JSON pointer: `/3419`

组分属性 Properties Advanced NC -Props Property Methods (性质高级

## UG10-CH18-D100

PDF page: 271; original JSON pointer: `/3420`

每个组分的属性按照在 Properties Advanced NC -Props Property Methods (性质高级

## UG10-CH18-D101

PDF page: 271; original JSON pointer: `/3421`

NC-Props 性质方法)页上为那个组分规定的顺序出现 所有值都采用 SI 单位制 而不管单位

## UG10-CH18-D102

PDF page: 272; original JSON pointer: `/3423`

PSD值(如果给子流股定义了一个PSD属性)

## UG10-CH18-D103

PDF page: 272; original JSON pointer: `/3424`

你可以使用 Compattr-Vec 和 PSD-Vec 变量类型来访问组分属性矢量和 PSD 流股矢量

## UG10-CH18-D104

PDF page: 272; original JSON pointer: `/3425`

可以从 Components Attr -Comps Selection (组分属性 -组分选择 )页和 Properties Advanced

## UG10-CH18-D105

PDF page: 273; original JSON pointer: `/3427`

你还可以使用 Block-Vec 访问下列模块结果分布数据

## UG10-CH18-D106

PDF page: 273; original JSON pointer: `/3428`

ASPEN PLUS 自动地

## UG10-CH18-D107

PDF page: 273; original JSON pointer: `/3429`

l 将你分配给分布数据的 Fortran 变量解释为一个数组变量

## UG10-CH18-D108

PDF page: 273; original JSON pointer: `/3430`

ASPEN PLUS 通过在你分配给模块矢量的 Fortran 变量名的开头加字母 L 来生成变量

## UG10-CH18-D109

PDF page: 273; original JSON pointer: `/3431`

该变量的长度就是数组的长度 你可以在 Fortran 语句中使用变量 但你不能改变它的值

## UG10-CH18-D110

PDF page: 273; original JSON pointer: `/3432`

在 Fortran 数组中的值的顺序依赖于你选择哪个变量 该章以后的章节描述了变量的顺

## UG10-CH18-D111

PDF page: 273; original JSON pointer: `/3433`

序 所有的值都采用 SI 单位制 而不管你在 Define(定义)页上的 Unitsspecifications(单位规

## UG10-CH18-D112

PDF page: 273; original JSON pointer: `/3434`

2 级或区段 2 . . N 最后级或区段 N 代表塔中的级或区段的数目 与级数相关的变量的示例是 RadFrac MultiFrac Extract PetroFrac 或 BatchFrac 中的 温度和流量分布数据 与段数相关的矢量变量的示例就是用于 RateFrac 的温度和流量分布 数据 访问一温度分布数据示例 通过使用一个 Fortran 模块 一个 RadFrac 模块的温度分布数据被写到 Control Panel(控 制面板)

## UG10-CH18-D113

PDF page: 273; original JSON pointer: `/3435`

在 Fortran 模块的 Define(定义)页上 通过使用 Variable Definition(变量定义)对话框定义

## UG10-CH18-D114

PDF page: 273; original JSON pointer: `/3436`

了 Block-Vec 类型的 Fortran 变量 TPROF

## UG10-CH18-D115

PDF page: 274; original JSON pointer: `/3438`

在 Fortran Fortran 页上 加入了下列这些 Fortran 语句

## UG10-CH18-D116

PDF page: 274; original JSON pointer: `/3439`

20 FORMAT (‘*** TEMPERATURE PROFILE ***’

## UG10-CH18-D117

PDF page: 274; original JSON pointer: `/3440`

30 FORMAT (10X, I3, 2X, F10.2) 与段数相关的变量 与段数的相关矢量变量的示例是用于 Scfrac 的分级索引和负荷结果 用于塔板和填料的 设计/核算结果 矢量的各分量布局如下 其中 Nsec 指塔中的段数

## UG10-CH18-D118

PDF page: 275; original JSON pointer: `/3442`

2 段 2 . . Nsec 最后段 与操作步数相关的变量 与操作步数相关的矢量变量的示例是用于 BatchFrac 的蒸馏塔和回流比结果 矢量的各 分量布局如下 其中 Nopstep 指操作步数 数组索引 用于 …的值

## UG10-CH18-D119

PDF page: 275; original JSON pointer: `/3443`

2 操作步 2 . . Nopstep 最后的操作步 与组分号相关的变量 与组分号相关的矢量变量的示例是 RadFrac 热虹吸管再沸器组成 矢量的各分量布局如 下 其中 NCC 是指在 Components Specifications Selection (组分规定选择)页上输入的组分 的数目 组分的顺序与在那个页上的顺序相同 数组索引 用于 …的值

## UG10-CH18-D120

PDF page: 275; original JSON pointer: `/3444`

2 组分 2 . . NCC 最后一个组分 与组分号和级或段数相关的变量 与组分号和级数相关的矢量变量的示例是 RadVrac MultiFrac Extract PetroFrac 或 BatchFrac 中的液相和气相组成分布数据 与组分号和段数相关的矢量变量的示例是用于 RateFrac 的液相和气相组成分布数据 这些值被存储为一维数组 级或区段 1 的所有组分值 在开头 接下来是级或区段 2 的所有组分值 等等 组分数和组分顺序与在 Components

## UG10-CH18-D121

PDF page: 275; original JSON pointer: `/3445`

Specifications Selection(组分规定选择)页上的相同

## UG10-CH18-D122

PDF page: 275; original JSON pointer: `/3446`

对于有三个组分和五个级的塔 液相组成分布数据被按下列方式存储

## UG10-CH18-D123

PDF page: 275; original JSON pointer: `/3447`

1 组分 1 级或段 1

## UG10-CH18-D124

PDF page: 275; original JSON pointer: `/3448`

2 组分 2 级或段 1

## UG10-CH18-D125

PDF page: 275; original JSON pointer: `/3449`

3 组分 3 级或段 1

## UG10-CH18-D126

PDF page: 276; original JSON pointer: `/3451`

4 组分 1 级或段 2 . . .

## UG10-CH18-D127

PDF page: 276; original JSON pointer: `/3452`

15 组分 3 级或段 5 访问摩尔分率分布数据示例 访问有三个组分的 RadFrac 塔的整个液相摩尔分率分布数据 通过一 Fortran 模块 将 第五个级上的第二个组分的值写到 Control Panel(控制面板)中 通过使用 Variable Definition(变量定义)对话框 在 Fortran 模块的 Define(定义)页上 定 义 Block-Vec 类型的 Fortran 变量 XPROF

## UG10-CH18-D128

PDF page: 277; original JSON pointer: `/3454`

在 Fortran 页上 加入下列这些 Fortran 语句

## UG10-CH18-D129

PDF page: 277; original JSON pointer: `/3455`

C* TOTAL NUMBER OF COMPONENTS IS 3 *

## UG10-CH18-D130

PDF page: 277; original JSON pointer: `/3456`

C* COMPONENT TO BE ACCESSED IS 2 *

## UG10-CH18-D131

PDF page: 277; original JSON pointer: `/3457`

II = NCOMP*(ISTAGE-1) + ICOMP

## UG10-CH18-D132

PDF page: 277; original JSON pointer: `/3458`

10 FORMAT(‘* MOLE FRACTION OF 2ND COMPONENT ON 5TH STAGE*’)

## UG10-CH18-D133

PDF page: 277; original JSON pointer: `/3459`

20 FORMAT(10X,F10.2) 与级数和段数相关的变量 与级数和段数相关的矢量变量的示例是塔板核算计算的分布数据结果 它们的值被存储 为一维数组 段 1 的各级的值在开头 接下来是段 2 的所有级的值 等等 组分数和组分的 顺序与在 Components Specifications Selection(组分规定选择)页上的组分数和顺序相同 对于 一个有五个级和三个段的一个塔 液泛近似分布数据被按如下方式存储 数组索引 用于 …的值

## UG10-CH18-D134

PDF page: 277; original JSON pointer: `/3460`

6 级 1 段 2 . . .

## UG10-CH18-D135

PDF page: 277; original JSON pointer: `/3461`

15 级 5 段 3 与级 数和操作步数相关的变量 与级数和操作步数相关的矢量变量的示例是用于 BatchFrac 的温度和流量分布数据 它 们的值被存储为一维数组 操作步 1 的所有级值在开头 接下来是操作步 2 的所有级的值 等等 对于一个有四个级和三个操作步的 BatchFrac 模块 温度分布数据被按如下方式存储 数组索引 用于 …的值

## UG10-CH18-D136

PDF page: 277; original JSON pointer: `/3462`

5 级 1 操作步 2 . . .

## UG10-CH18-D137

PDF page: 277; original JSON pointer: `/3463`

12 级 4 操作步 3

## UG10-CH18-D138

PDF page: 278; original JSON pointer: `/3465`

数据 它们的值被存储为一维数组 汽提塔 1 的级 1 的所有组分值在开头 接下来是汽提塔

## UG10-CH18-D139

PDF page: 278; original JSON pointer: `/3466`

1 的级 2 的所有组分值 等等 当到达汽提塔 1 的 Nstot 后 汽提塔 2 的组分和级值开始 等等 Nstot 是指那个汽提塔的级总数 对于一个有三个组分 六个汽提塔级 和三个汽提塔的 PetroFrac 模块 液相组成分布 数据被按如下方式存储 数组索引 用于 …的值

## UG10-CH18-D140

PDF page: 278; original JSON pointer: `/3467`

1 组分 1 级 1 汽提塔 1

## UG10-CH18-D141

PDF page: 278; original JSON pointer: `/3468`

2 组分 2 级 1 汽提塔 1

## UG10-CH18-D142

PDF page: 278; original JSON pointer: `/3469`

3 组分 3 级 1 汽提塔 1

## UG10-CH18-D143

PDF page: 278; original JSON pointer: `/3470`

4 组分 1 级 2 汽提塔 1 . .

## UG10-CH18-D144

PDF page: 278; original JSON pointer: `/3471`

18 组分 3 级 1 汽提塔 1

## UG10-CH18-D145

PDF page: 278; original JSON pointer: `/3472`

19 组分 1 级 1 汽提塔 2 . .

## UG10-CH18-D146

PDF page: 278; original JSON pointer: `/3473`

54 组分 3 Nstot 汽提塔 3 与组分号 级数和操作步数相关的变量 与组分号 级数和操作步数(opstep)相关的矢量变量的示例是 BatchFrac 的组成分布数 据 它们的值被存储为一维数组 操作步 1 的级 1 的所有组分值在开头 接下来是操作步 1 的级 2 的所有组分值 等等 当 opstep1 到达 Nstage 后 opstep2 的组分和级值开始 等等 Nstage 指塔中的级数 对于一个有两个组分 三个级 和四个操作步的 BatchFrac 模块 液相组成分布数据被

## UG10-CH18-D147

PDF page: 278; original JSON pointer: `/3474`

1 组分 1 级 1 操作步 1

## UG10-CH18-D148

PDF page: 278; original JSON pointer: `/3475`

2 组分 1 级 2 操作步 1

## UG10-CH18-D149

PDF page: 278; original JSON pointer: `/3476`

3 组分 1 级 1 操作步 1 . .

## UG10-CH18-D150

PDF page: 278; original JSON pointer: `/3477`

1 组分 2 Nstage 操作步 1

## UG10-CH18-D151

PDF page: 278; original JSON pointer: `/3478`

1 组分 1 级 1 操作步 2 . .

## UG10-CH18-D152

PDF page: 278; original JSON pointer: `/3479`

24 组分 2 Nstage 操作步 3 与组分号 累加器号和操作步数相关的变量 在 BatchFrac 中的累加器组成分布数据是唯一的与组分号 累加器号和操作步数(opstep) 相关的矢量变量 它们的值被存储为一维数组 操作步 1 的累加器 1 的所有组分值在开头 接下来是操作步 1 的累加器 2 的所有组分值 等等 Naccum 是指塔中的累加器的总数 当

## UG10-CH18-D153

PDF page: 279; original JSON pointer: `/3481`

1 组分 1 累加器 1 操作步 1

## UG10-CH18-D154

PDF page: 279; original JSON pointer: `/3482`

2 组分 2 累加器 1 操作步 1

## UG10-CH18-D155

PDF page: 279; original JSON pointer: `/3483`

3 组分 1 累加器 2 操作步 1 . .

## UG10-CH18-D156

PDF page: 279; original JSON pointer: `/3484`

6 组分 2 Naccum 操作步 1

## UG10-CH18-D157

PDF page: 279; original JSON pointer: `/3485`

7 组分 1 累加器 1 操作步 2 . .

## UG10-CH18-D158

PDF page: 279; original JSON pointer: `/3486`

24 组分 2 Naccum 操作步 1 MheatX 分布数据 你可以使用 Block-Vec 变量类型来访问 MheatX 模块的热侧和冷侧之间的温差 变量 描述 DT 温度接近分布数据 包括增加的用于相态变化点的点和用于流股输 入和离开交换器的点 DTBASE 仅用于基点的温度接近分布数据 矢量的长度等于 Zone 数+1 Zone 数在 MheatX input ZoneAnalysis页上规定 反应器分布数据 你可以使用 Block-Vec 变量类型访问用于象计算的温度和压力那样的变量的 Rbatch 时

## UG10-CH18-D159

PDF page: 279; original JSON pointer: `/3487`

间分布数据和 Rplug 长度分布数据 在每个输出点都存储了变量值 矢量的长度等于输出点

## UG10-CH18-D160

PDF page: 279; original JSON pointer: `/3488`

例如 一个运行了 10 小时 且每小时都有点输出的 Rbatch 反应器的温度分布数据将会

## UG10-CH18-D161

PDF page: 279; original JSON pointer: `/3489`

3 2 小时 . . .

## UG10-CH18-D162

PDF page: 279; original JSON pointer: `/3490`

11 10 小时 输出间隔被确定如下 模型 输出间隔 Rplug 沿反应器长度的分布数据点数 在 Rplug Report rofiles(Rplug 报告分 布数据)页上规定 Rbatch 分布数据点间的时间间隔 在 Rbatch Setup Opertion Times(Rbatch 设 置操作时间段)页上规定

## UG10-CH18-D163

PDF page: 280; original JSON pointer: `/3492`

ASPEN PLUS 自动

## UG10-CH18-D164

PDF page: 280; original JSON pointer: `/3493`

l 将你分配给分布数据的 Fortran 变量解释为一个数组变量

## UG10-CH18-D165

PDF page: 280; original JSON pointer: `/3494`

ASPEN PLUS 通过在你分配给矢量的 Fortran 变量名的开头加一个字母 L 来生成一个变

## UG10-CH18-D166

PDF page: 280; original JSON pointer: `/3495`

和模型 你还可以通过在 Properties PureComponent (纯组分性质) and Perperties Parameters

## UG10-CH18-D167

PDF page: 280; original JSON pointer: `/3496`

在下面的 Define(定义)页上 所有的参考数据都是数据集 1

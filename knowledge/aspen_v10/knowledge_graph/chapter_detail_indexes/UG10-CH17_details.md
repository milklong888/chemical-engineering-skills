# UG10-CH17 Detail Operation Index - 第17章 收敛

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH17-D001

PDF page: 239; original JSON pointer: `/2942`

l 流程再循环和设计规定

## UG10-CH17-D002

PDF page: 239; original JSON pointer: `/2943`

ASPEN PLUS 使用序贯模块法进行流程计算 每个单元操作模块按顺序执行 每个模

## UG10-CH17-D003

PDF page: 239; original JSON pointer: `/2944`

带有再循环回路 设计规定 或优化题目的流程计算必须循环求解 流程的执行要求

## UG10-CH17-D004

PDF page: 239; original JSON pointer: `/2945`

l 选择撕裂流股 一股撕裂流股就是具有所有由循环确定的组分流 总摩尔流 压力

## UG10-CH17-D005

PDF page: 239; original JSON pointer: `/2946`

l 定义收敛模块使撕裂流股 设计规定 或优化题目收敛 收敛模块决定对一撕裂流

## UG10-CH17-D006

PDF page: 239; original JSON pointer: `/2947`

股或设计规定控制的变量的估测如何在循环过程中更新

## UG10-CH17-D007

PDF page: 239; original JSON pointer: `/2948`

如果你不规定撕裂流股 收敛模块 或次序 ASPEN PLUS 会自动确定它们 每个设 计规定和撕裂流股都有一个相关的收敛模块 由 ASPEN PLUS 生成的收敛模块的名字以字 符 $ 开始 而由用户定义的收敛模块不应以字符 $ 开始 ASPEN PLUS 会自动确定执行流程所需要的任何附加的规定 根据缺省 ASPEN PLUS 还会核查由用户规定的确保所有回路均被撕裂的次序 你可以作的收敛规定为 如果你想规定 使用该收敛形 式 要知更详细的情况参见本 章的相关部分 收敛参数和 /或用于收敛模块的 方法 Conv Options 收敛选项

## UG10-CH17-D008

PDF page: 239; original JSON pointer: `/2949`

所需的用于系统生成的收敛模块

## UG10-CH17-D009

PDF page: 239; original JSON pointer: `/2950`

所需的一些或全部收敛模块 Convergence 规定用户定义的收敛模块

## UG10-CH17-D010

PDF page: 239; original JSON pointer: `/2951`

用于一些或全部用户定义的收敛

## UG10-CH17-D011

PDF page: 239; original JSON pointer: `/2952`

Conv Order 规定收敛顺序

## UG10-CH17-D012

PDF page: 239; original JSON pointer: `/2953`

用于流程的全部或一部分的次序 Sequence 规定计算次序

## UG10-CH17-D013

PDF page: 240; original JSON pointer: `/2955`

使用 Convergence ConvOptions(收敛收敛选项)页来规定用于收敛模块的下列参数

## UG10-CH17-D014

PDF page: 240; original JSON pointer: `/2956`

l 用于由 ASPEN PLUS 生成的收敛模块中使用的撕裂流股 设计规定和优化题目

## UG10-CH17-D015

PDF page: 240; original JSON pointer: `/2957`

l 每种方法收敛参数 规定的参数被用作定义的和由 ASPEN PLUS 生成的收敛模

## UG10-CH17-D016

PDF page: 240; original JSON pointer: `/2958`

对于流股 缺省的收敛变量是总摩尔流 全部组分摩尔流 压力 和焓 当 Trace

## UG10-CH17-D017

PDF page: 240; original JSON pointer: `/2959`

Option(跟踪选项)是 Cutoff(在 Convergence ConvOptions DefaultsTearConvergence 页上规定)

## UG10-CH17-D018

PDF page: 240; original JSON pointer: `/2960`

了一个 100*跟踪阈值 该设置逐渐放松了对跟踪组分的收敛试验

## UG10-CH17-D019

PDF page: 240; original JSON pointer: `/2961`

要规定用于收敛模块的撕裂收敛参数

## UG10-CH17-D020

PDF page: 240; original JSON pointer: `/2962`

1. 在 Data(数据)菜单中 单击 Convergence(收敛) 然后选择 Conv Options( 收敛选 项)

## UG10-CH17-D021

PDF page: 240; original JSON pointer: `/2963`

2. 单击 TearConvergence(撕裂收敛)页

## UG10-CH17-D022

PDF page: 240; original JSON pointer: `/2964`

3. 规定撕裂容差和其它收敛参数 例如 Trace Threshold( 跟踪阈值 )和 Trace Option(跟踪选项) 在撕裂收敛页上可获得下列参数 域 缺省值 为了 Tolerance 0.001 规定撕裂收敛容差 当下面的关系式对于所有的流股变量都是真值时 撕裂 流股收敛 tolX XXtol assumed assumedcalculated ≤−≤− Trace Threshold Tolerance/ 规定跟踪组分阈值 ASPEN PLUS 忽略了对小于跟踪阈 值的摩尔分率的组分的收敛测试 Trace Option

## UG10-CH17-D023

PDF page: 240; original JSON pointer: `/2965`

Cutoff 选择用于跟踪组分的收敛测试选项 Trace option =

## UG10-CH17-D024

PDF page: 240; original JSON pointer: `/2966`

Gradual 相当于在分母上加上 100*跟踪阈值 该设置会

## UG10-CH17-D025

PDF page: 240; original JSON pointer: `/2967`

组分组在Comp Comp -Group窗口定义 参见第六章

## UG10-CH17-D026

PDF page: 240; original JSON pointer: `/2968`

题 组分组规定主要和矩阵收敛方法 (Broyden,Newton,

## UG10-CH17-D027

PDF page: 240; original JSON pointer: `/2969`

选择要收敛的状态变量 当知道压力是恒定的或未计算

## UG10-CH17-D028

PDF page: 241; original JSON pointer: `/2971`

Enthalpy 焓值(只进行质量平衡模拟)时 你可以选择一个不同于缺

## UG10-CH17-D029

PDF page: 241; original JSON pointer: `/2972`

省值的状态选项 状态规定主要用来和矩阵收敛方法

## UG10-CH17-D030

PDF page: 241; original JSON pointer: `/2973`

checked 当有收敛错误时 将撕裂恢复为最后一次估测的值

## UG10-CH17-D031

PDF page: 241; original JSON pointer: `/2974`

如果你通过内嵌FORTRAN程序获得了撕裂流股的温度 密度或熵 或者如果你需要看到或使用中间的或部分的 收敛结果 那么就复选闪蒸撕裂流股 如果你想节省计 算时间或如果你不需要中间收敛结果 就不要复选闪蒸 撕裂流股 闪蒸撕裂流股独立于收敛方法 只有一个例 外 如果物质的组成和化学性质与撕裂流股有关 那么 不管你复不复选 缺省情况都不是要闪蒸撕裂流股 Diagnostics Display Maximum Error / Tolerance 规定是应生成包含全部变量的表还是应生成只带有最大 错的变量

## UG10-CH17-D032

PDF page: 241; original JSON pointer: `/2975`

你可以规定要被系统生成的收敛模块使用的数值方法 要得到关于数值方法的更详细

## UG10-CH17-D033

PDF page: 241; original JSON pointer: `/2976`

要规定被系统生成的收敛模块使用的数值方法

## UG10-CH17-D034

PDF page: 241; original JSON pointer: `/2977`

1. 在Data(数据)菜单中 单击Convergence(收敛),然后单击Conv Options

## UG10-CH17-D035

PDF page: 241; original JSON pointer: `/2978`

正文待来源表达/OCR边界复核；原文本 SHA256: `066da25939dc1b3db61e2892c26f2179e46a6de6cc3cf1f6b1436a99d4bfc0ed`。

## UG10-CH17-D036

PDF page: 241; original JSON pointer: `/2979`

Optimization SQP 优化收敛模块

## UG10-CH17-D037

PDF page: 241; original JSON pointer: `/2980`

你可以规定控制撕裂流股选择和自动排序的参数

## UG10-CH17-D038

PDF page: 241; original JSON pointer: `/2981`

1. 在Data(数据)菜单中 单击Convergence(收敛) 然后单击Conv Options(收敛选项)

## UG10-CH17-D039

PDF page: 241; original JSON pointer: `/2982`

2. 选择Squencing(排序)页

## UG10-CH17-D040

PDF page: 241; original JSON pointer: `/2983`

3. 你可以规定撕裂和排序参数

## UG10-CH17-D041

PDF page: 242; original JSON pointer: `/2985`

Design Spec Nesting Inside 设计规定是否应嵌入在撕裂流股回路内部 撕裂流股回

## UG10-CH17-D042

PDF page: 242; original JSON pointer: `/2986`

路外部 或与撕裂流股同时收敛 Design spec(设计规定)

## UG10-CH17-D043

PDF page: 242; original JSON pointer: `/2987`

嵌套不用于按收敛顺序形式规定的收敛模块 当一外部

## UG10-CH17-D044

PDF page: 242; original JSON pointer: `/2988`

回路的撕裂流股被在一内部回路中重新计算时 生成的

## UG10-CH17-D045

PDF page: 242; original JSON pointer: `/2989`

实际次序可以不严格遵循在Design spec (设计规定)嵌套

## UG10-CH17-D046

PDF page: 242; original JSON pointer: `/2990`

和用户嵌套域中规定的回路顺序优先权

## UG10-CH17-D047

PDF page: 242; original JSON pointer: `/2991`

User Nesting Outside 用户嵌套让你规定一优先权 用于按Conv Order(收敛顺

## UG10-CH17-D048

PDF page: 242; original JSON pointer: `/2992`

序)形式规定的收敛模块是应嵌套在其它收敛模块(用户

## UG10-CH17-D049

PDF page: 242; original JSON pointer: `/2993`

定义的或系统生成的 )的内部还是外部 用户嵌套域优

## UG10-CH17-D050

PDF page: 242; original JSON pointer: `/2994`

先于Design Spec(设计规定)嵌套域

## UG10-CH17-D051

PDF page: 242; original JSON pointer: `/2995`

时 生成的实际次序可以不严格遵循在Design spec(设计

## UG10-CH17-D052

PDF page: 242; original JSON pointer: `/2996`

规定)嵌套和用户嵌套域中规定回路顺序优先权

## UG10-CH17-D053

PDF page: 242; original JSON pointer: `/2997`

Tear Fortran Write

## UG10-CH17-D054

PDF page: 242; original JSON pointer: `/2998`

当Fortran模块出现在返回回路中时 Fortran模块变量是

## UG10-CH17-D055

PDF page: 242; original JSON pointer: `/2999`

章Fortran 由Fortran变量引入的收敛回路部分

## UG10-CH17-D056

PDF page: 242; original JSON pointer: `/3000`

Check Sequence checked ASPEN PLUS 是否检查用户规定的次序来确保撕裂所

## UG10-CH17-D057

PDF page: 242; original JSON pointer: `/3001`

你可以为每个数值方法都规定附加参数 为收敛方法选择适当的标签 要得到关于数

## UG10-CH17-D058

PDF page: 242; original JSON pointer: `/3002`

1. 在Data(数据)菜单中 单击Convergence(收敛) 然后单击Conv Options(收敛选项)

## UG10-CH17-D059

PDF page: 242; original JSON pointer: `/3003`

2. 在Data Brower(数据浏览器)窗口的左部 选择Methods(方法)表格

## UG10-CH17-D060

PDF page: 242; original JSON pointer: `/3004`

3. 选择合适的收敛方法页

## UG10-CH17-D061

PDF page: 242; original JSON pointer: `/3005`

4. 规定那种方法的参数 规定撕裂流股 使用Tear Spec ifications(撕裂规定)页来辨别由系统生成的收敛模块收敛的撕裂流股 如果你给你的流程规定了一个不完整的撕裂集 ASPEN PLUS就会自动选择流股的剩下的 撕裂集 如果你规定了冗余的撕裂集(撕裂流股太多) ASPEN PLUS可以忽略一些撕裂流 股或找到一个无效的次序 要规定一个撕裂流股

## UG10-CH17-D062

PDF page: 242; original JSON pointer: `/3006`

1. 在Data(数据)菜单中 单击Convergence(收敛) 然后单击Tear(撕裂)

## UG10-CH17-D063

PDF page: 242; original JSON pointer: `/3007`

2. 在流股域中 使用列表并选择一个流股标号

## UG10-CH17-D064

PDF page: 242; original JSON pointer: `/3008`

3. 此流股必须在模拟流程的一个循环回路中 注 当一Fortran模块位于一循环回路中时 你可以撕裂在Fortran Sequence( 次序)页上

## UG10-CH17-D065

PDF page: 243; original JSON pointer: `/3010`

4. 规定你选择的余下的任一可选域 在撕裂规定页上可获得下列参数 区域 缺省值 用途 Tolerance 0.001 规定撕裂收敛容差 当对于所有流股变量下列关系运算式是真值时 撕裂流股 收敛 tolX XXtol assumed assumedcalculated ≤−≤− Trace Tolerance/100 规定跟踪组分阈值 对于小于Trace Threshhold(跟踪阈值)的摩尔分率的组分 ASPEN PLUS 忽略此项收敛测试

## UG10-CH17-D066

PDF page: 243; original JSON pointer: `/3011`

All components 辨认将在撕裂流股中收敛的组分的 Component group

## UG10-CH17-D067

PDF page: 243; original JSON pointer: `/3012`

ID(组分组标识符) 组分组在Components Comp-Group表

## UG10-CH17-D068

PDF page: 243; original JSON pointer: `/3013`

中定义(参见第六章) 当你知道一些组分有零或恒定流率

## UG10-CH17-D069

PDF page: 243; original JSON pointer: `/3014`

时 使用组分组 如果未收敛组分有有效的流量时 组分

## UG10-CH17-D070

PDF page: 243; original JSON pointer: `/3015`

组分组规定主要用于矩阵收敛方法 (Broyden,Newton, 和

## UG10-CH17-D071

PDF page: 243; original JSON pointer: `/3016`

当压力已知为常数或焓值未被计算出来 (只进行质量平衡

## UG10-CH17-D072

PDF page: 243; original JSON pointer: `/3017`

模拟)时 你可以选择一个不同于缺省值(压力和焓)的状态

## UG10-CH17-D073

PDF page: 243; original JSON pointer: `/3018`

状态规定主要用于与矩阵收敛方法 (Broyden,Newton, 和

## UG10-CH17-D074

PDF page: 243; original JSON pointer: `/3019`

收敛 并且有时是必需的 尤其对涉及蒸馏模块的循环回路而言 要得到关于规定流股的

## UG10-CH17-D075

PDF page: 243; original JSON pointer: `/3020`

使用Convergence页为用户定义的收敛模块规定收敛方法 容差和收敛变量 由ASPEN

## UG10-CH17-D076

PDF page: 243; original JSON pointer: `/3021`

PLUS系统生成的收敛模块不使用这些规定

## UG10-CH17-D077

PDF page: 243; original JSON pointer: `/3022`

1. 在Data(数据)菜单 选Convergence(收敛) 然后选Convergence(收敛)

## UG10-CH17-D078

PDF page: 243; original JSON pointer: `/3023`

2. 在Convergence Object Manager (收敛对象管理器)中单击New(新建)

## UG10-CH17-D079

PDF page: 243; original JSON pointer: `/3024`

3. 在Create New ID(创建新标识符)对话框中 输入一个ID(标识符)或接受缺省名

## UG10-CH17-D080

PDF page: 243; original JSON pointer: `/3025`

4. 在Create New ID(创建新标识符)对话框中 选择你想创建的收敛模块类型 使用该方法 进行收敛 BROYDEN or NEWTON 撕裂流股 两个或两个以上的设计规定 或撕裂流股和设计规定同 时进行 当循环回路和/或设计规定高度相关时使用该方法 当使用

## UG10-CH17-D081

PDF page: 244; original JSON pointer: `/3027`

Broyden方法不能收敛时 使用New(牛顿法)

## UG10-CH17-D082

PDF page: 244; original JSON pointer: `/3028`

COMPLEX 带有不平衡约束的优化

## UG10-CH17-D083

PDF page: 244; original JSON pointer: `/3029`

SECANT 单个设计规定 推荐用于设计规定收敛模块

## UG10-CH17-D084

PDF page: 244; original JSON pointer: `/3030`

5. 单击Tear Streams(撕裂流股) Design Spections(设计规定) Fortran Tears(Fortran 撕裂) 或Optimization(优化)标签来选择你想要收敛模块求解的元素

## UG10-CH17-D085

PDF page: 244; original JSON pointer: `/3031`

6. 要规定可选的参数 单击Parameters(参数)页 收敛方法 该部分描述了在ASPEN PLUS中可用的收敛方法 用于每种方法的参数可在Convergence ConvOptions Methods (收敛收敛选项方法)表中 和用于Convergence(收敛)模块的表中找到 WEGSTEIN 方法 传统的有限Wegstein方法通常是用于撕裂流股收敛的最快和最可靠的方法 是一种直 接迭代循环的外推 变量间的相互作用被忽略 因此 当变量之间的联系特别强时 该方

## UG10-CH17-D086

PDF page: 244; original JSON pointer: `/3032`

Wegstein方法可以仅用于撕裂流股 是用于ASPEN PLUS收敛的缺省方法 可同时把

## UG10-CH17-D087

PDF page: 244; original JSON pointer: `/3033`

你可以通过规定下列各项控制Wegstein方法

## UG10-CH17-D088

PDF page: 244; original JSON pointer: `/3034`

Maximum Flowsheet

## UG10-CH17-D089

PDF page: 244; original JSON pointer: `/3035`

30 流程估算的最大数 Wait 1 在第一次加速替换循环之前直接迭代循环数 Consecutive Direct Substitution Steps

## UG10-CH17-D090

PDF page: 244; original JSON pointer: `/3036`

0 在加速循环之间的直接迭代循环数 Consecutive Acceleration Steps

## UG10-CH17-D091

PDF page: 244; original JSON pointer: `/3037`

1 连续加速循环数 Lower Bound -5 用于Wegstein加速参数的最小值(q) Upper Bound 0 用于Wegstein加速参数的最大值(q) WEGSTEIN加速度参数 你可以通过给下列各项规定上下限来控制Wegstein方法

## UG10-CH17-D092

PDF page: 244; original JSON pointer: `/3038`

在有界的Wegstein方法中 每股撕裂流股的加速参数 q 按如下所述公式计算

## UG10-CH17-D093

PDF page: 245; original JSON pointer: `/3040`

下列表格显示了q 对收敛的作用

## UG10-CH17-D094

PDF page: 245; original JSON pointer: `/3041`

0 < q < 1 阻尼 因为如果 q 无界的话 会出现震荡和发散 所以要对q 加以限制 q的缺省下限和上 限分别是-5和0 对于大多数流程 这些限制很有效并且不必改变 正常情况下 你应该使用Wegstein 0 加速参数为上限 如果循环使变量缓慢趋向收敛 那么较小的Wegstein加速参数下限值 (可能-25或-50)可能会给出更好的结果 如果直接迭 代出现了震荡 0和1之间的上下限值可能会有所帮助 DIRECT 方法 对于直接迭代 撕裂流股变量的新值是由以前的流程计算循环公式导出来的值 ( )kk XGX =+1 其中 =X 撕裂流股变量的估值

## UG10-CH17-D095

PDF page: 245; original JSON pointer: `/3042`

( ) =XG 计算出来的变量结果值

## UG10-CH17-D096

PDF page: 245; original JSON pointer: `/3043`

情况是有效的 直接迭代还可以使辨别收敛题目(例如系统内含的组分)更容易 直接迭代

## UG10-CH17-D097

PDF page: 245; original JSON pointer: `/3044`

正割是切割线性近似方法 有较高级增益 你可以选择一个定界 /二等分间隔选项

## UG10-CH17-D098

PDF page: 245; original JSON pointer: `/3045`

无论函数何时不连续 非单调或在一区域内很平缓 就选择该选项 如果可能 划定界限

## UG10-CH17-D099

PDF page: 245; original JSON pointer: `/3046`

会删去平缓区域并切换回正割法

## UG10-CH17-D100

PDF page: 245; original JSON pointer: `/3047`

你可以将正割法用于单个设计规定 正割是用于设计规定收敛的缺省方法 并且被推

## UG10-CH17-D101

PDF page: 245; original JSON pointer: `/3048`

荐用于用户生成的收敛模块 你可以通过规定下列各项控制正割法

## UG10-CH17-D102

PDF page: 245; original JSON pointer: `/3049`

Maximum Flowsheet

## UG10-CH17-D103

PDF page: 245; original JSON pointer: `/3050`

30 流程估算的最大数 Step Size 0.01 初始步长是范围的几分之一 用于设计规定操作的变量 Maximum Step Size 1 最大步长是范围的几分之一 用于设计规定操作的变量

## UG10-CH17-D104

PDF page: 246; original JSON pointer: `/3052`

X Tolerance 1e-8 操作变量的另一种容差

## UG10-CH17-D105

PDF page: 246; original JSON pointer: `/3053`

循环比例操作变量改变值小于X Tolerance时停止

## UG10-CH17-D106

PDF page: 246; original JSON pointer: `/3054`

X Final on Error Last

## UG10-CH17-D107

PDF page: 246; original JSON pointer: `/3055`

当收敛模块遇到错误时要用哪个操作变量值作为最终

## UG10-CH17-D108

PDF page: 246; original JSON pointer: `/3056`

Bracket No 如果正割算法应该切换到定界算法

## UG10-CH17-D109

PDF page: 246; original JSON pointer: `/3057`

计规定函数改变了符号 使间隔二等分

## UG10-CH17-D110

PDF page: 246; original JSON pointer: `/3058`

当Bracket被规定为No时 那么就不能使用Bracketing

## UG10-CH17-D111

PDF page: 246; original JSON pointer: `/3059`

时可能会增加特殊的循环 所以你可能会将 Bracket规

## UG10-CH17-D112

PDF page: 246; original JSON pointer: `/3060`

定为No 当Bracketing被规定为 Yes时 如果函数不变

## UG10-CH17-D113

PDF page: 246; original JSON pointer: `/3061`

当Bracket被规定为Check Bounds(检查边界)时 如果函

## UG10-CH17-D114

PDF page: 246; original JSON pointer: `/3062`

使用Broyden收敛撕裂流股 两个或两个以上的设计规定 或同时收敛撕裂流股和设

## UG10-CH17-D115

PDF page: 246; original JSON pointer: `/3063`

计规定 Broyden用于多重撕裂流股和/或设计规定 相互高度相关的撕裂变量 或者用于

## UG10-CH17-D116

PDF page: 246; original JSON pointer: `/3064`

彼此间相互关联以致不能实现嵌套的循环回路和设计规定 当撕裂流股和设计规定都收敛

## UG10-CH17-D117

PDF page: 246; original JSON pointer: `/3065`

时 你可以规定撕裂流股被收敛或先部分收敛 然后接下来就是撕裂流股和设计规定同时

## UG10-CH17-D118

PDF page: 246; original JSON pointer: `/3066`

你可以通过规定下面各项控制Broyden方法

## UG10-CH17-D119

PDF page: 246; original JSON pointer: `/3067`

Maximum Flowsheet Evaluations 30 流程估值的最大数

## UG10-CH17-D120

PDF page: 246; original JSON pointer: `/3068`

X Tolerance 0.001 关于操作变量的另一种容差 当在比例操作变

## UG10-CH17-D121

PDF page: 246; original JSON pointer: `/3069`

量上的改变量小于X Torlerance时 循环停止

## UG10-CH17-D122

PDF page: 246; original JSON pointer: `/3070`

Tear Tolerance (on Advanced

## UG10-CH17-D123

PDF page: 246; original JSON pointer: `/3071`

Parameters dialog box)

## UG10-CH17-D124

PDF page: 246; original JSON pointer: `/3072`

撕裂容差 使用条件是通过在包括设计规定前

## UG10-CH17-D125

PDF page: 246; original JSON pointer: `/3073`

收敛撕裂流股(到规定的容差)来初始化撕裂流

## UG10-CH17-D126

PDF page: 246; original JSON pointer: `/3074`

TearTolerance Ratio (on

## UG10-CH17-D127

PDF page: 246; original JSON pointer: `/3075`

Advanced Parameters dialog

## UG10-CH17-D128

PDF page: 246; original JSON pointer: `/3076`

撕裂容差比 使用条件是通过包括在设计规定

## UG10-CH17-D129

PDF page: 246; original JSON pointer: `/3077`

要在包括设计规定前求解撕裂流股的最大流程

## UG10-CH17-D130

PDF page: 247; original JSON pointer: `/3079`

Parameters dialog box)

## UG10-CH17-D131

PDF page: 247; original JSON pointer: `/3080`

0 用于Wegstein加速参数(q)的最大值 NEWTON 方法 NEWTON是对用于联立非线性方程的修正牛顿法的补充 导数仅在收敛速率不令人 满意时计算 该NEWTON方法补充允许变量边界值 并且包括改善的稳定性直线搜索 NEWTON在循环回路和/或设计规定高度相关时有用 但使用Broyden时不能实现收敛 数 值导数被频繁计算 仅在组分数很小或不能通过其它方法实现收敛时对撕裂流股使用 NEWTON 当正在收敛撕裂流股和设计规定时 可以规定撕裂流股首先收敛或首先部分

## UG10-CH17-D132

PDF page: 247; original JSON pointer: `/3081`

收敛 然后是撕裂流股和设计规定同时收敛

## UG10-CH17-D133

PDF page: 247; original JSON pointer: `/3082`

当你使用Newton或Broyden方法收敛设计规定 并且一个或更多的操作变量已经达到

## UG10-CH17-D134

PDF page: 247; original JSON pointer: `/3083`

了它们的下限或上限时 就会找到一个使设计规定和撕裂流股误差的平方和除以它们的容

## UG10-CH17-D135

PDF page: 247; original JSON pointer: `/3084`

差后的值的最小解 循环在成比例的操作变量的改变量的均方根小于 X 容差时停止

## UG10-CH17-D136

PDF page: 247; original JSON pointer: `/3085`

你可以通过规定下列各项来控制Newton方法

## UG10-CH17-D137

PDF page: 247; original JSON pointer: `/3086`

Maximum Flowsheet

## UG10-CH17-D138

PDF page: 247; original JSON pointer: `/3087`

9999 流程估值的最大数 Wait 2 在第一次加速循环前的直接迭代循环数 X Tolerance 0.0001 关于操作变量的另一种容差 循环在比例操作变量的改变量小于 X Tolerance(X 容差)时停止 Reduction Factor 0.2 减小因子 确定用于在计算一新的 Jacobian(导数)矩阵前使用的Newton循环数 使用该选项 只要Jacobian能继续通过减小 因子减少每次循环的误差就会被重复使用 Iterations to Reuse Jacobian 重新使用Jacobian(导数)矩阵的循环数 该选项使Jacobian被重新使用一定的次数

## UG10-CH17-D139

PDF page: 247; original JSON pointer: `/3088`

缺省情况为将Jacobian的重新使用建立在减

## UG10-CH17-D140

PDF page: 247; original JSON pointer: `/3089`

Tear Tolerance (on

## UG10-CH17-D141

PDF page: 247; original JSON pointer: `/3090`

撕裂容差 使用条件是通过设计规定被包括

## UG10-CH17-D142

PDF page: 247; original JSON pointer: `/3091`

之前收敛撕裂流股(到规定的容差)来初始化

## UG10-CH17-D143

PDF page: 247; original JSON pointer: `/3092`

Tear Tolerance Ratio (on

## UG10-CH17-D144

PDF page: 247; original JSON pointer: `/3093`

收敛容差比 使用容差是通过设计规定被包

## UG10-CH17-D145

PDF page: 247; original JSON pointer: `/3094`

要在包括设计规定前求解撕裂流股的最大

## UG10-CH17-D146

PDF page: 247; original JSON pointer: `/3095`

0 用于Wegstein加速参数的最大值(q)

## UG10-CH17-D147

PDF page: 248; original JSON pointer: `/3097`

你可以使用 Complex 方法来收敛带有操作变量界限和不平衡约束的优化题目

## UG10-CH17-D148

PDF page: 248; original JSON pointer: `/3098`

COMPLEX 是一个直接搜索方法 它不需要数值导数 它可用于没有循环回路或平衡约束

## UG10-CH17-D149

PDF page: 248; original JSON pointer: `/3099`

成的优化收敛模块 对于用户生成的收敛模块 推荐使用 SQP

## UG10-CH17-D150

PDF page: 248; original JSON pointer: `/3100`

你可以通过规定下列各项控制 SQP 方法

## UG10-CH17-D151

PDF page: 248; original JSON pointer: `/3101`

Maximum Optimization

## UG10-CH17-D152

PDF page: 248; original JSON pointer: `/3102`

30 SQP优化循环的最大数 Maximum Flowsheet Evaluations

## UG10-CH17-D153

PDF page: 248; original JSON pointer: `/3103`

9999 流程估值的最大数 对数值导数的每步扰动都被算作一次估算 Additional Iterations when Constraints are not Satisfied

## UG10-CH17-D154

PDF page: 248; original JSON pointer: `/3104`

2 当约束条件在收敛测试被满足之后还没满足时的 附加循环数 Iterations to Converge Tears for Each Optimization Iteration

## UG10-CH17-D155

PDF page: 248; original JSON pointer: `/3105`

3 为了在优化的每次循环时都有助于收敛撕裂流股 所采用的循环数 Iterations to Enforce Maximum Step Size

## UG10-CH17-D156

PDF page: 248; original JSON pointer: `/3106`

3 对操作变量强制使用最大步长的循环数 Tolerance 0.001 优化收敛容差 Wait 1 在第一次加速循环前的直接迭代循环数 Lower Bound -5 用于Wegstein加速参数(q)的最小值 Upper Bound 0 用于Wegstein加速参数(q)的最大值 SQP Wegstein 加速度参数 当 SQP 方法被用于同时收敛撕裂流股和优化题目时 算法是一不可行路径法(其中撕 裂流股不是在每次循环时都收敛但却在最佳值处收敛 )和一可行路径法 (其中撕裂流股在

## UG10-CH17-D157

PDF page: 248; original JSON pointer: `/3107`

优化的每次循环处都收敛 ) 的混合 你可以通过规定要采用的 有助于收敛撕裂流股

## UG10-CH17-D158

PDF page: 248; original JSON pointer: `/3108`

(Iterations To Converge Tears Each Optimization Iteration( 在每次优化循环时用来收敛撕裂

## UG10-CH17-D159

PDF page: 248; original JSON pointer: `/3109`

如果你使用了多于一个用户定义的收敛模块 那么你可以规定你定义的收敛模块的计 算次序 在 ConvOrder Specification( 收敛次序规定)或 Sequenc e Specifications( 次序规定)

## UG10-CH17-D160

PDF page: 249; original JSON pointer: `/3111`

1. 在 Data(数据)菜单中 单击 Convergence(收敛) 然后单击 Conv Order(收敛次序)

## UG10-CH17-D161

PDF page: 249; original JSON pointer: `/3112`

2. 在 Available Blocks(可用的模块)列表中选择一个模块 使用箭头键将你想首先收 敛的模块移动到 Convergence Order(收敛次序)列表的顶部

## UG10-CH17-D162

PDF page: 249; original JSON pointer: `/3113`

3. 按次序选择你想要的其它任何模块 并把它们移动到 Convergence Order( 收敛次 序)列表中 你可以用向上和向下箭头键重新在列表中排列模块的顺序 第一模 块首先被收敛并且被嵌套在最里层 规定计算顺序 你可以为全部或部分流程定义计算顺序 你需为每个次序提供 ID 要定义顺序

## UG10-CH17-D163

PDF page: 249; original JSON pointer: `/3114`

1. 在 Data(数据)菜单中 单击 Convergence(收敛) 然后单击 Sequence(顺序)

## UG10-CH17-D164

PDF page: 249; original JSON pointer: `/3115`

2. 在 Object Manager(对象管理器)中 单击 New(新建)按钮

## UG10-CH17-D165

PDF page: 249; original JSON pointer: `/3116`

3. 在 Create New ID (创建新 ID)对话框中 输入一个 ID 或接受缺省的 ID 并单击 OK(确定)

## UG10-CH17-D166

PDF page: 249; original JSON pointer: `/3117`

4. 在规定页上规定计算顺序 在页的每行 你可以输入下列各项之一

## UG10-CH17-D167

PDF page: 249; original JSON pointer: `/3118`

对于一个循环的开头和末尾 在 Loop-Return 域中规定 Begin(开始)或 Return To(返回

## UG10-CH17-D168

PDF page: 249; original JSON pointer: `/3119`

到) 在 Block Type(模块类型)域中规定模块类型 下列模块开始循环

## UG10-CH17-D169

PDF page: 249; original JSON pointer: `/3120`

l Sensitivity(灵敏度)

## UG10-CH17-D170

PDF page: 249; original JSON pointer: `/3121`

l Data Fit(数据拟合)

## UG10-CH17-D171

PDF page: 249; original JSON pointer: `/3122`

Fortran 模块可以仅为循环控制 Fortran 模块的特殊情况引进循环

## UG10-CH17-D172

PDF page: 249; original JSON pointer: `/3123`

为下列模块类型规定模块类型和模块 ID

## UG10-CH17-D173

PDF page: 249; original JSON pointer: `/3124`

为进行经济的计算 为模块类型规定 Economic(经济) 对于经济计算来说 没有模块

## UG10-CH17-D174

PDF page: 249; original JSON pointer: `/3125`

在一个次序中 你可以插入已经有一个 ID 和一个定义的次序的流程的一个子集 对

## UG10-CH17-D175

PDF page: 249; original JSON pointer: `/3126`

于流程按这种方式建立次序规定是有用的 在 Block Type(模块次序)域中规定 Sequence(顺

## UG10-CH17-D176

PDF page: 249; original JSON pointer: `/3127`

序) 在 Block ID(模块 ID)域中为该子集规定次序 ID

## UG10-CH17-D177

PDF page: 249; original JSON pointer: `/3128`

ASPEN PLUS 精确地按照你输入的次序执行这些模块 但下列情况除外

## UG10-CH17-D178

PDF page: 249; original JSON pointer: `/3129`

Sequencing(收敛选项缺省排序)页上

## UG10-CH17-D179

PDF page: 249; original JSON pointer: `/3130`

复选 Check Sequence(检查次序)域

## UG10-CH17-D180

PDF page: 249; original JSON pointer: `/3131`

果一个回路未被撕裂 ASPEN PLUS 会显示一

## UG10-CH17-D181

PDF page: 249; original JSON pointer: `/3132`

在一个 Fortran 模块中规定 execute

## UG10-CH17-D182

PDF page: 249; original JSON pointer: `/3133`

在你定义的顺序中插入 Fortran 模块

## UG10-CH17-D183

PDF page: 249; original JSON pointer: `/3134`

规定一个 Design-Spec (设计规定) 自动生成设计规定的收敛模块并把它们插入到

## UG10-CH17-D184

PDF page: 250; original JSON pointer: `/3136`

计算序在 Control Panel(控制面板)左屏中显示 如果 Control Panel 的左屏是空的 就

## UG10-CH17-D185

PDF page: 250; original JSON pointer: `/3137`

在 RUN(运行)菜单中选择 Step(单步运行)

## UG10-CH17-D186

PDF page: 250; original JSON pointer: `/3138`

在 Streams Specifications(流股规定)页上输入撕裂流股的初始组成和流率 并运行该模

## UG10-CH17-D187

PDF page: 250; original JSON pointer: `/3139`

拟 或者使用 Tear(撕裂)页选择你自己的撕裂流股 并且为它们提供初始估计

## UG10-CH17-D188

PDF page: 250; original JSON pointer: `/3140`

一个流程的撕裂和排序是复杂的且可以要求用户输入 下列关于和 ASPEN PLUS 排

## UG10-CH17-D189

PDF page: 250; original JSON pointer: `/3141`

序算法相互作用的信息是提供给高级用户的 推荐其它用户接受缺省排序

## UG10-CH17-D190

PDF page: 250; original JSON pointer: `/3142`

ASPEN PLUS 最初按下列次序撕裂和给流程排序

## UG10-CH17-D191

PDF page: 250; original JSON pointer: `/3143`

1. 收集单元操作模块 Fortran 模块 设计规定 约束 优化以及成本模块的信息 流(关联矩阵)

## UG10-CH17-D192

PDF page: 250; original JSON pointer: `/3144`

2. 由于可能丢失撕裂流股 所以检查你定义的次序 且用你定义的次序生成一个简 化的关联矩阵 在简化的关联矩阵中 你所规定的子次序失效且被作为一个单个 模块

## UG10-CH17-D193

PDF page: 250; original JSON pointer: `/3145`

3. 简化的关联矩阵被分成可被连续求解的独立子系统

## UG10-CH17-D194

PDF page: 250; original JSON pointer: `/3146`

4. 考虑到用户规定的 Tear(撕裂) Tear Variable (撕裂变量) 和 Convergence(收敛) 规定 所以要为每个子系统确定撕裂流股或 Fortran 模块撕裂变量 ASPEN PLUS 中的自动排序算法通过最小化下列各项数目的加权组合来选择撕裂流股

## UG10-CH17-D195

PDF page: 250; original JSON pointer: `/3147`

5. 确定一初始次序作为撕裂的一部分 对于每个子系统为不被用户规定的收敛模块 收敛的设计规定 撕裂流股和撕裂变量创建 Conergence( 收敛 ) 模块 在 Convergence ConvOptions Defaults Sequencing( 收敛收敛选项缺省排序)页上规定 Design Spec Nesting (设计规定嵌套)为 Inside(在里面) 会为所有的撕裂流股和撕 裂变量生成一个撕裂收敛模块 并为每个设计规定都生成一个单个的设计规定收

## UG10-CH17-D196

PDF page: 250; original JSON pointer: `/3148`

敛模块 要知更详细的情况 参见本章的规定排序参数部分

## UG10-CH17-D197

PDF page: 250; original JSON pointer: `/3149`

你可以通过下列措施影响自动排序算法

## UG10-CH17-D198

PDF page: 250; original JSON pointer: `/3150`

l 调节 Convergence ConvOptions Defaults Sequencing( 收敛收敛选项缺省排序)页上

## UG10-CH17-D199

PDF page: 250; original JSON pointer: `/3151`

l 为 Streams 表中的每个可能的撕裂流股规定初始估计 如果可能 那么对非进料

## UG10-CH17-D200

PDF page: 250; original JSON pointer: `/3152`

流股的规定会被用作初始估测 带有数据的流股在排序算法中被加权 所以它们

## UG10-CH17-D201

PDF page: 250; original JSON pointer: `/3153`

l 使用 Tear Specification( 撕裂规定)页 直接规定撕裂流股 你应该注意不要规定

## UG10-CH17-D202

PDF page: 250; original JSON pointer: `/3154`

比收敛要求的撕裂流股更多的撕裂流股 你可以不规定撕裂流股的数目 而

## UG10-CH17-D203

PDF page: 251; original JSON pointer: `/3156`

1. 对所有的收敛模块 象它们在 ConvOrder Speccification(收敛顺序规定)表和用户 嵌套在 ConvOptions Defaults Squencing( 收敛选项缺省排序)页上的当前设置上出 现的那样被排列 要根据 ConvOptions Defaults Squencing( 收敛选项缺省排序)页 上的 Design Spec Nesting( 设计规定嵌套)设置和收敛模块在初始次序中的间距排 列在 ConvOrder Specification(收敛顺序规定)表上未提到的模块

## UG10-CH17-D204

PDF page: 251; original JSON pointer: `/3157`

2. ASPEN PLUS 通过重复从最外面的收敛模块中删除撕裂流股和/或设计规定和通 过划分简化的流程来获得最后的收敛次序

## UG10-CH17-D205

PDF page: 251; original JSON pointer: `/3158`

3. 对于嵌套于 Convergence ConvOptions Defaults Sequencing( 收敛收敛选项缺省排 序)页上作为 Inside(在里面)或 Inside simultaneous(在里面同时)的设计规定 你可 以为设计规定定义用户指定的收敛模块 且它们将会被自动插入到次序中 为次序增加特殊的选项 在最终的收敛次序的末尾 增加特殊的选项

## UG10-CH17-D206

PDF page: 251; original JSON pointer: `/3159`

1. 将带有 Execute(执行)选项的模块插入到收敛次序中

## UG10-CH17-D207

PDF page: 251; original JSON pointer: `/3160`

2. 插入还没在次序中的 Sensitivity(灵敏度) Balance(平衡) 和 Data Fit( 数据拟合) 模块 因为一个设计规定循环通常有一个小跨距 所以排序算法不会把它们嵌套进去(例如 一个外面的撕裂流股和里面的许多独立设计规定循环) 既然算法不考虑数字值 因此它 有时将设计规定放置在撕裂循环里面 这时它们可能会比在外面实现得更好 在 Convergence ConvOptions Defaults Sequencing( 收敛收敛选项缺省排序)页上将 Design Spec

## UG10-CH17-D208

PDF page: 251; original JSON pointer: `/3161`

Nesting(设计规定嵌套)规定为 Outside(在外面)会改变次序 但这经常导致大流程的深度嵌

## UG10-CH17-D209

PDF page: 251; original JSON pointer: `/3162`

要浏览次序以及由 ASPEN PLUS 决定的撕裂流股和收敛模块

## UG10-CH17-D210

PDF page: 251; original JSON pointer: `/3163`

Ø 在 View 菜单中 单击 Control Panel(控制面板)

## UG10-CH17-D211

PDF page: 251; original JSON pointer: `/3164`

该次序显示在 Control Panel(控制面板)的左屏中 如果 Control Panel(控制面板)的左屏

## UG10-CH17-D212

PDF page: 251; original JSON pointer: `/3165`

为空 那么选择 Run(运行)菜单中的 Step(单步运行)

## UG10-CH17-D213

PDF page: 251; original JSON pointer: `/3166`

该示例描述了要收敛一个使用自动排序不能正确收敛的简单流程的步骤 它说明了

## UG10-CH17-D214

PDF page: 251; original JSON pointer: `/3167`

l 改变带有 Design spec(设计规定)嵌套的计算次序

## UG10-CH17-D215

PDF page: 251; original JSON pointer: `/3168`

l 改变带有 Conv Order(收敛顺序)的计算次序

## UG10-CH17-D216

PDF page: 251; original JSON pointer: `/3169`

COOLER 产品冷却器

## UG10-CH17-D217

PDF page: 252; original JSON pointer: `/3171`

PROD中的组分 THF 的纯度规定 在设计规定 THF 中 PROD 是一个从 BOTCOL/COOLER

## UG10-CH17-D218

PDF page: 252; original JSON pointer: `/3172`

流出的产品流股 PSPEC 是定义的用来收敛 THF 的收敛模块

## UG10-CH17-D219

PDF page: 252; original JSON pointer: `/3173`

当蒸馏塔出现在一个循环回路中时 必须经常给出撕裂流股的初始估计 ASPEN

## UG10-CH17-D220

PDF page: 252; original JSON pointer: `/3174`

PLUS 使这种估计更加容易 就象你会给一个进料流股提供数据一样 在 Streams(流股)

## UG10-CH17-D221

PDF page: 252; original JSON pointer: `/3175`

表中简单地给一个塔进料或循环中的其它流股提供数据 并且 ASPEN PLUS 会优先选择

## UG10-CH17-D222

PDF page: 252; original JSON pointer: `/3176`

该流股作为一个撕裂流股(如果根据撕裂判据另一个流股是更好的选择的话 那么你选择

## UG10-CH17-D223

PDF page: 252; original JSON pointer: `/3177`

| PSPEC BOTCOL COOLER

## UG10-CH17-D224

PDF page: 252; original JSON pointer: `/3178`

$OLVER01 是被定义用来收敛带有提供的初始数据的流股 REFLUX(中间的连接流股)

## UG10-CH17-D225

PDF page: 252; original JSON pointer: `/3179`

的 然而由于使用了这种次序 PSPEC 和$OLVER01 不会收敛 因为设计规定被嵌套在

## UG10-CH17-D226

PDF page: 252; original JSON pointer: `/3180`

塔循环回路的里面 设计规定 THF 不收敛 因为纯度规定主要是根据两个塔 (不是

## UG10-CH17-D227

PDF page: 252; original JSON pointer: `/3181`

设计规定估算之前 设计规定应该被嵌套在塔循环回路的外面 你可以根据下列两种措施

## UG10-CH17-D228

PDF page: 252; original JSON pointer: `/3182`

之一来改变收敛回路的嵌套顺序

## UG10-CH17-D229

PDF page: 252; original JSON pointer: `/3183`

l 在 Convergence ConvOptions Defaults Sequencing( 收敛收敛选项缺省排序)页上规

## UG10-CH17-D230

PDF page: 252; original JSON pointer: `/3184`

定 Design Spec Nesting(设计规定嵌套)为 Outside(在外面) 或

## UG10-CH17-D231

PDF page: 252; original JSON pointer: `/3185`

l 在 ConvOrder Specification(收敛顺序规定)页上规定 PSPEC

## UG10-CH17-D232

PDF page: 252; original JSON pointer: `/3186`

两种规定中任何一种都会使排序算法确定下面的计算次序 该次序收敛

## UG10-CH17-D233

PDF page: 252; original JSON pointer: `/3187`

| (R ETURN $OLEVER01)

## UG10-CH17-D234

PDF page: 252; original JSON pointer: `/3188`

对于这个简单题目来说 这两种规定嵌套顺序的方法都是等效的 但是当处理大流程

## UG10-CH17-D235

PDF page: 253; original JSON pointer: `/3190`

时 使用 ConvOptions Defaults Sequencing(收敛选项缺省排序)表允许你有选择地改变计算

## UG10-CH17-D236

PDF page: 253; original JSON pointer: `/3191`

$OLVER01 COOLER 中间(较高)

## UG10-CH17-D237

PDF page: 253; original JSON pointer: `/3192`

如果用于 PSPEC 的 Error(误差)/Tolerance(容差)似乎会迅速下降到 10 并停在那 那么 你应该缩紧用于 PSPEC 回路内的所有模块的容差或放松用于 PSPEC 的容差 如果你注意 到了在$OLVER01中有相似的问题 那么你就应缩紧 TOPCOL 和 BOTCOL 容差 尤其重要的是确保嵌套的设计规定有足够紧的容差 因为这些容差是由用户规定的 如果出现问题 或如果设计规定被嵌套得非常深 一个更紧些的容差可能是必要的

## UG10-CH17-D238

PDF page: 253; original JSON pointer: `/3193`

在你的模拟完成之后或在它处于暂停时 你能浏览收敛模块的结果来检查收敛题目的

## UG10-CH17-D239

PDF page: 253; original JSON pointer: `/3194`

1. 如果你的模拟被暂停 那么就在 Run(运行)菜单中 单击 Load Results(加载结果)

## UG10-CH17-D240

PDF page: 253; original JSON pointer: `/3195`

2. 在 Data(数据)菜单中 单击 Convergence(收敛) 然后单击 Convergence(收敛)

## UG10-CH17-D241

PDF page: 253; original JSON pointer: `/3196`

3. 在 Convergence Object Manager(收敛对象管理器)中 选择收敛模块并单击 Edit(编 辑) 对于系统生成的收敛模块 (名字以$OLVER01 开头)显示结果页 对于用 户定义的收敛模块 选择在 Data Browser( 数据浏览器)窗口中的左边窗格上的 Results(结果)

## UG10-CH17-D242

PDF page: 253; original JSON pointer: `/3197`

正文待来源表达/OCR边界复核；原文本 SHA256: `d6fa8e0fd1bc42d56960629e31142287f2fcc76fff8be0487e6e0119497c4550`。

## UG10-CH17-D243

PDF page: 253; original JSON pointer: `/3198`

设计规定收敛)数据表 来帮助你诊断和校正撕裂流股和设计规定收敛题目 它有助于生

## UG10-CH17-D244

PDF page: 253; original JSON pointer: `/3199`

Control Panel 显示每个收敛模块的收敛诊断 每次收敛模块在一循环收敛回路中执行

## UG10-CH17-D245

PDF page: 253; original JSON pointer: `/3200`

时 信息都会按下列格式出现

## UG10-CH17-D246

PDF page: 253; original JSON pointer: `/3201`

Converging tear streams 3

## UG10-CH17-D247

PDF page: 254; original JSON pointer: `/3203`

4 vars not converged Max Err/Tol 0.18603E+02 每次用于设计规定的收敛模块在一收敛回路中执行时 信息会按下列格式出现 >> Loop CV Method SECANT Iteration 2 Converging specs: H2RATE

## UG10-CH17-D248

PDF page: 254; original JSON pointer: `/3204`

1 vars not converged Max Err/Tol 0.36525E+03 其中 CV = 收敛模块 ID Max Err/Tol =用于未收敛变量的最大误差/容差 > =指示收敛回路嵌套级别的符号 > 外面的循环回路 >> 嵌套的一级循环回路 >>> 嵌套的二级循环回路 等等 当 Max Err/Tol 值变得小于 1.0 时实现收敛 收敛诊断 你可以在 Setup Specifications Diagnostics (设置规定诊断)页上从总体上修改收敛的诊

## UG10-CH17-D249

PDF page: 254; original JSON pointer: `/3205`

断级 要知关于如何改变诊断级的细节 参见第五章

## UG10-CH17-D250

PDF page: 254; original JSON pointer: `/3206`

在控制面板和历史记录文件中使用 Convergence( 收敛)游标为收敛模块信息修改诊断

## UG10-CH17-D251

PDF page: 254; original JSON pointer: `/3207`

级 你还可以在任何一个收敛模块的 Input Parameters(输入参数)页上使用 Diagnostics(诊断)

## UG10-CH17-D252

PDF page: 254; original JSON pointer: `/3208`

按钮为一个单一的收敛模块规定诊断级

## UG10-CH17-D253

PDF page: 254; original JSON pointer: `/3209`

在 ASPEN PLUS 内缺省的诊断级是 4 在值为 4 的 Convergence Diagnostics Level(收

## UG10-CH17-D254

PDF page: 254; original JSON pointer: `/3210`

敛诊断级别)上 每次收敛模块执行时 都会在 Conrtrol Panel(控制面板)中创建一个信息

## UG10-CH17-D255

PDF page: 254; original JSON pointer: `/3211`

在历史记录文件中的信息是相似的 但却不是完全相同的

## UG10-CH17-D256

PDF page: 254; original JSON pointer: `/3212`

收敛模块在 CONTROL PANEL(控制面板)中创建一个收敛信息表

## UG10-CH17-D257

PDF page: 254; original JSON pointer: `/3213`

Converging tear streams: 4

## UG10-CH17-D258

PDF page: 254; original JSON pointer: `/3214`

TOTAL MOLEFLOW (1) 0.135448E-01 0.135448E-01 0.000000E+00 10000.0

## UG10-CH17-D259

PDF page: 254; original JSON pointer: `/3215`

N2 MOLEFLOW (2) 0.188997E-03 0.188997E-03 0.000000E+00 10000.0

## UG10-CH17-D260

PDF page: 254; original JSON pointer: `/3216`

C1 MOLEFLOW (2) 0.755987E-03 0.755987E-03 0.000000E+00 10000.0

## UG10-CH17-D261

PDF page: 254; original JSON pointer: `/3217`

BZ MOLEFLOW (2) 0.314995E-03 0.314995E-03 0.000000E+00 10000.0

## UG10-CH17-D262

PDF page: 254; original JSON pointer: `/3218`

CH MOLEFLOW (2) 0.122848E-01 0.122848E-01 0.000000E+00 10000.0

## UG10-CH17-D263

PDF page: 254; original JSON pointer: `/3219`

TOTAL MOLEFL (3) 0.377994E-01 0.000000E+00 0.377994E-01 -375.000

## UG10-CH17-D264

PDF page: 254; original JSON pointer: `/3220`

8 vars not converged, Max Err/Tol 0.17679E+05

## UG10-CH17-D265

PDF page: 255; original JSON pointer: `/3222`

1 未被收敛算法更新的撕裂流股变量

## UG10-CH17-D266

PDF page: 255; original JSON pointer: `/3223`

2 被收敛方法更新的撕裂流股变量

## UG10-CH17-D267

PDF page: 255; original JSON pointer: `/3224`

3 设计规定操作变量 由算法更新

## UG10-CH17-D268

PDF page: 255; original JSON pointer: `/3225`

4 Fortran 撕裂变量 由算法更新 新 X 是用于下一个循环的变量的值 X 是用于以前循环的变量值 G(X)是前面的循 环结束时变量的计算值 当变量收敛时 X 和 G(X)的差应小于容差 所有值的单位都是 SI 单位 将 Convergence Diagnostics level (收敛诊断级别 )设置为 6 或更高的级别不改变在 Control Panel (控制面板)中报告的信息量 然而 根据正使用的收敛方法 它会影响在历 史记录文件报告的信息量 流程收敛的策略

## UG10-CH17-D269

PDF page: 255; original JSON pointer: `/3226`

一个流程经常可以不必改变任何收敛参数就被收敛

## UG10-CH17-D270

PDF page: 255; original JSON pointer: `/3227`

它们会象期望的那样运行 在一定的条件下 一敏感模块可用于确定其它模块的

## UG10-CH17-D271

PDF page: 255; original JSON pointer: `/3228`

l 尽可能从最简单的模块开始 例如 在将它切换至一严格 HeatX 之前用一简单

## UG10-CH17-D272

PDF page: 255; original JSON pointer: `/3229`

流股一个零缺省值 这可能引起问题 如果可能的话 选择一个保持相对恒定的

## UG10-CH17-D273

PDF page: 255; original JSON pointer: `/3230`

l 检查物理性质 确保这些性质在模拟的整个操作范围内被正确计算

## UG10-CH17-D274

PDF page: 255; original JSON pointer: `/3231`

l 知道你的流程如何响应 使用敏感度分析检查模块和设计规定的运行状态 寻找

## UG10-CH17-D275

PDF page: 255; original JSON pointer: `/3232`

l 检查变量访问 拼写 和单元规定的正确性 当访问实变量时 确保你的变量名

## UG10-CH17-D276

PDF page: 255; original JSON pointer: `/3233`

该表显示了出现撕裂流股收敛问题的可能原因和解决这些问题的办法

## UG10-CH17-D277

PDF page: 255; original JSON pointer: `/3234`

检查来自循环回路的出口流股以证实所有的组分都有

## UG10-CH17-D278

PDF page: 256; original JSON pointer: `/3236`

Wegstein Input Parameters (收敛模块 Wegstein 输入参

## UG10-CH17-D279

PDF page: 256; original JSON pointer: `/3237`

数)页上 设置 Wegstein 加速参数的下限 = -20 如果

## UG10-CH17-D280

PDF page: 256; original JSON pointer: `/3238`

震荡收敛 对于 Wegstein 设置上限为 0.5 来减弱震荡

## UG10-CH17-D281

PDF page: 256; original JSON pointer: `/3239`

l 使用这些模块的 Tolerance(容差)域为模块和内部

## UG10-CH17-D282

PDF page: 256; original JSON pointer: `/3240`

循环的收敛模块设置一个较紧的容差 模块容差

## UG10-CH17-D283

PDF page: 256; original JSON pointer: `/3241`

可以在 Setup SimulationOptions Flash

## UG10-CH17-D284

PDF page: 256; original JSON pointer: `/3242`

Convergence(设置模拟选项闪蒸收敛 )页进行全局

## UG10-CH17-D285

PDF page: 256; original JSON pointer: `/3243`

改变或在收敛模块的 Parameter(参数)页上进行部

## UG10-CH17-D286

PDF page: 256; original JSON pointer: `/3244`

敛选项缺省排序)页上的 Design Spec Nesting(设计

## UG10-CH17-D287

PDF page: 256; original JSON pointer: `/3245`

如果撕裂流股和设计规定都在收敛模块中被规定的 话 那么仅通过规定 Tear Tolerance (撕裂容差)或 Tear Tolerance Ratio (撕裂容差比)首先求解撕裂流股 单击 在收敛模块的 Parameter( 参数 ) 页上的 Advansed Parameters(高级参数)按钮 切换至 Wegstein 方法 一些其它的用于撕裂流股收敛的策略是

## UG10-CH17-D288

PDF page: 256; original JSON pointer: `/3246`

详细的关于规定流股的信息 参见第九章

## UG10-CH17-D289

PDF page: 256; original JSON pointer: `/3247`

l 选择一个不会变化很大的 Tear stream(撕裂流股) 例如 一般来说 选择一个

## UG10-CH17-D290

PDF page: 256; original JSON pointer: `/3248`

Heater(加热器)模块的出口流股作为撕裂流股要比选择来自 Reactor(反应器)的出

## UG10-CH17-D291

PDF page: 256; original JSON pointer: `/3249`

l 断开循环流股 取得一个好的初始估计值和检查灵敏度

## UG10-CH17-D292

PDF page: 256; original JSON pointer: `/3250`

l 增加一个 Mixer(混合器)模块来减少撕裂流股数

## UG10-CH17-D293

PDF page: 256; original JSON pointer: `/3251`

l 定义和使用一个 Component Group(组分组)来减少变量数

## UG10-CH17-D294

PDF page: 256; original JSON pointer: `/3252`

l 选择一个现有较少组分的撕裂流股

## UG10-CH17-D295

PDF page: 256; original JSON pointer: `/3253`

l 从一个设定出口温度的模块中选择一个撕裂流股

## UG10-CH17-D296

PDF page: 256; original JSON pointer: `/3254`

l 重新初始化模拟 尽量使用等于 0 的 Wegstein 加速参数(设置上限和下限为 0)来

## UG10-CH17-D297

PDF page: 256; original JSON pointer: `/3255`

收敛模拟 这等于直接迭代 随着循环的进行 查看一个或一个以上组分的不断

## UG10-CH17-D298

PDF page: 256; original JSON pointer: `/3256`

l 试不同的收敛方法例如 Broyden 或 Newton 方法而不是缺省的 Wegstein 方法

## UG10-CH17-D299

PDF page: 256; original JSON pointer: `/3257`

l 核实模拟次序(ASPEN PLUS 或用户定义的)的合理性 参见本章的规定计算次序

## UG10-CH17-D300

PDF page: 256; original JSON pointer: `/3258`

该表显示了引起设计规定(Design Specification)收敛问题的可能原因和解决办法

## UG10-CH17-D301

PDF page: 257; original JSON pointer: `/3260`

Err/Tol 不变 规定函数对操作变

## UG10-CH17-D302

PDF page: 257; original JSON pointer: `/3261`

1. 检查规定函数的表示是否正确

## UG10-CH17-D303

PDF page: 257; original JSON pointer: `/3262`

2. 检查是否正在使用正确的操作变量

## UG10-CH17-D304

PDF page: 257; original JSON pointer: `/3263`

3. 使用 Sensitivity 分析来确定操作变量对规定 函数的影响 对于正割法 在 Conv Options ( 收敛选项 ) 或 Convergence block ( 收敛模块 ) 页上选择 Bracket=Yes 来使用二分法 Err/Tol 下降为一 阈值级别 但不再 进一步下降 嵌套的循环 和内 部循环的收敛容差 太松 采取下列措施之一

## UG10-CH17-D305

PDF page: 257; original JSON pointer: `/3264`

l 为模块和内部循环的收敛模块设置一个较紧

## UG10-CH17-D306

PDF page: 257; original JSON pointer: `/3265`

的容差 使用这些模块 Tolerance(容差)域

## UG10-CH17-D307

PDF page: 257; original JSON pointer: `/3266`

缺省排序)页上的 Design Spec Nesting (设计

## UG10-CH17-D308

PDF page: 257; original JSON pointer: `/3267`

非单调规定函数 1. 对于正割法 在 Conv Options (收敛选项)或

## UG10-CH17-D309

PDF page: 257; original JSON pointer: `/3268`

数)页上的选择 Bracket=Check bounds 来使

## UG10-CH17-D310

PDF page: 257; original JSON pointer: `/3269`

2. 使用 Sensitivity(灵敏度 )分析来确定操作变 量对规定函数的影响 调节操作变量的边界 或选择一个更好的初始估测 其它的一些用于设计规定收敛的一般策略为

## UG10-CH17-D311

PDF page: 257; original JSON pointer: `/3270`

l 使规定合理化以避免不连续

## UG10-CH17-D312

PDF page: 257; original JSON pointer: `/3271`

l 使规定合理以减少设计变量的非线性程度 例如 当浓度接近零时 在它的记录上设

## UG10-CH17-D313

PDF page: 257; original JSON pointer: `/3272`

l 通过用一个 Sensitivity(灵敏度)模块替换设计规定来证实存在一种解法

## UG10-CH17-D314

PDF page: 257; original JSON pointer: `/3273`

l 确保容差是合理的 尤其是当和在设计规定收敛模块内部的模块容差相比时

## UG10-CH17-D315

PDF page: 257; original JSON pointer: `/3274`

要知关于设计规定的更详细的信息 参见第二十一章

## UG10-CH17-D316

PDF page: 257; original JSON pointer: `/3275`

Fortran 模块的收敛建议

## UG10-CH17-D317

PDF page: 257; original JSON pointer: `/3276`

用于 Fortran 模块收敛的其它的策略是

## UG10-CH17-D318

PDF page: 257; original JSON pointer: `/3277`

l 避免引起隐含的质量平衡问题的循环 如果 Fortran 模块被用 Read(读)和 White(写)

## UG10-CH17-D319

PDF page: 257; original JSON pointer: `/3278`

变量排序并且如果在 ConvOptions Defaults Sequencing (收敛选项缺省排序)页上

## UG10-CH17-D320

PDF page: 257; original JSON pointer: `/3279`

复选 Tear Fortran WriteVariables(撕裂 Fortran 写变量)的话 那么排序算法可以检

## UG10-CH17-D321

PDF page: 257; original JSON pointer: `/3280`

测到和收敛 Fortran 撕裂变量 然后 Fortran 撕裂变量就会和撕裂流股一起被求解

## UG10-CH17-D322

PDF page: 257; original JSON pointer: `/3281`

l 检查在 Fortran 模块中的 Fortran 语句的正确性

## UG10-CH17-D323

PDF page: 258; original JSON pointer: `/3283`

l 增强诊断来检查在计算中使用的变量值 单击 Fortran Sequencing (Fortran 排序)

## UG10-CH17-D324

PDF page: 258; original JSON pointer: `/3284`

页上的 Diagnostics(诊断)按钮 在 Diagnostics(诊断)对话框中 将 Fortran Defined

## UG10-CH17-D325

PDF page: 258; original JSON pointer: `/3285`

Variables(Fortran 定义的变量)提高到 5 或 6 这会打印出所访问的变量值

## UG10-CH17-D326

PDF page: 258; original JSON pointer: `/3286`

l 向你的 Fortran 模块中加入写语句以便打印出中间变量的值

## UG10-CH17-D327

PDF page: 258; original JSON pointer: `/3287`

要知关于 Fortran Block(Fortran 模块)的更多的信息 参见第十九章

## UG10-CH17-D328

PDF page: 258; original JSON pointer: `/3288`

1. 使用由 ASPEN PLUS 生成的缺省次序运行模拟

## UG10-CH17-D329

PDF page: 258; original JSON pointer: `/3289`

2. 检查模拟结果 寻找跳过的和未收敛的单元操作模块 检查 Control Panel (控制 面板)和没有正常完成 有错误或有意想不到可能会影响循环的结果的模块结果 页 要了解更详细的情况 参见本章的检查收敛结果部分 出现这些问题的一些常见原因是 问题 操作 不正确的模块规定 改正这些规定 进料条件差得太远 给撕裂流股和或设计变量提供更好的估计 收敛规定 试一下不同的规定 不同的算法选项 或增大循环数 算法选项 改变选项 没有足够的循环 增大循环数 如果你作了一些改正的话 就转到步骤 9

## UG10-CH17-D330

PDF page: 258; original JSON pointer: `/3290`

3. 检查容差是否需要调节 如果收敛模块的最大 Err/Tol 迅速减少到 10 附近 但那 以后又不断起伏 那么容差调节可能是必须的 要知更详细的情况 参见 Seqquencing Example(排序示例) 改正容差问题的另一个办法是用一个 Broyden 或 Newton 收敛模块去收敛多重设 计规定

## UG10-CH17-D331

PDF page: 258; original JSON pointer: `/3291`

4. 如果 Wegstein 收敛模块收敛得很慢 就试一试 Wegstein 参数 例如 Wait=4 Consecutive Direct Substitution Steps=4 Lower Bound=-50 给撕裂流股提供更好 的估值也会有所帮助

## UG10-CH17-D332

PDF page: 258; original JSON pointer: `/3292`

5. 如果撕裂流股收敛模块发生震荡 就给收敛试一试 Direct 方法 如果问题继续存 在 那么就检查流程来确定每个组分是否都有一个出口 一个撕裂流股循环回路 的震荡还可能是由在撕裂流股循环回路里面的设计规定循环回路的不收敛引起 如果震荡继续存在的话 接下来就检查一下是不是这个原因 如果震荡停止了 就试一试在步骤 4 中描述的加速技巧

## UG10-CH17-D333

PDF page: 258; original JSON pointer: `/3293`

6. 检查 Spec Summary(规定一览)和检查一下未收敛的设计规定 设计规定不收敛的 一些原因是 设计规定问题 操作 不能到达变量的边界之内 接受所得的解或放松边界 对操作变量不敏感 选择一个不同的操作变量来满足设计规定或删除设计 规定 在某一范围内对操作变量不 敏感 提供一个更好的初始估测 改善边界 和/或使 Secant 收敛方法的 Bracket 选项有效 对操作变量不敏感 因为未 确嵌套设计规定循环回路 参见本章的排序示例部分 如果改变计算次序是必要 的 那么参见步骤 7

## UG10-CH17-D334

PDF page: 259; original JSON pointer: `/3295`

7. 如果必要的话 使用下列选项之一 改变计算次序 (这个步骤要求你对正在模 拟的工艺有一个好的了解 且它仅用于高级用户) 如果你想要 规定 使一个或更多的设计规定循环 回路作最外面的循环回路 在 ConvOrder Specifications (收敛顺序规定 )页上规 定这些循环回路(参见本章的规定收敛顺序部分) 改变流程的一小部分的嵌套 在 Sequence Specfications (次序规定)页上规定一部 分次序(参见本章的规定计算次序部分)

## UG10-CH17-D335

PDF page: 259; original JSON pointer: `/3296`

使用特殊的撕裂流股 在 Tear Specifications (撕裂规定)页上规定这些流股

## UG10-CH17-D336

PDF page: 259; original JSON pointer: `/3297`

(参见本章的规定撕裂流股部分)

## UG10-CH17-D337

PDF page: 259; original JSON pointer: `/3298`

在 ConvOptions Defaults Sequencing (收敛选项缺省排序)页上还有其它选项也影响计

## UG10-CH17-D338

PDF page: 259; original JSON pointer: `/3299`

8. 如果所有的收敛模块都收敛但总的质量平衡却未处于平衡状态 那么就检查一下 Fortran 模块找一找可能的原因 推荐你使用 Read 和 Write 变量来给常规 Fortran 模块排序 并使用 Execute(执行)来给初始化 Fortran 模块排序

## UG10-CH17-D339

PDF page: 259; original JSON pointer: `/3300`

9. 如果修改了流程 那么就重新运行模拟并回到步骤 2 Err/Tol正下降为一个阈值的示例 在进行了大约 8 个循环收敛循环之后 Err/Tol 值下降到一个阈值 但不进一步降低 该循环被嵌套在一个内部设计循环回路的外面 给内部循环回路设置一个较紧的容差 向一个边界移动的操纵变量的示例 该设计规定函数不是单调函数 根据操作变量的初值 即使在边界内存在一个解 收敛 算法也可能将操作变量移动到上边界 在 Convergence ConvOptions Methods Secant (收敛收

## UG10-CH17-D340

PDF page: 259; original JSON pointer: `/3301`

敛选项方法正割)页或 Secant Input Parameters (正割输入参数)页上的 Bracket 域中规定 Check

## UG10-CH17-D341

PDF page: 259; original JSON pointer: `/3302`

Bounds(检查边界) 确保正割算法两个边界都检查 以便尽量将解包含在内

## UG10-CH17-D342

PDF page: 260; original JSON pointer: `/3304`

对于一个设计规定来说 Err/Tol 的值不变化 其中反应器的温度正被操作来控制该反应

## UG10-CH17-D343

PDF page: 260; original JSON pointer: `/3305`

器中的转化率 灵敏度分析表明规定函数 (转化)在操作变量的一些范围内是平缓的 在

## UG10-CH17-D344

PDF page: 260; original JSON pointer: `/3306`

Parameters(正割输入参数)页上的 Bracket 域为该设计规定题目规定 Yes 项

## UG10-CH17-D345

PDF page: 260; original JSON pointer: `/3307`

Biegler L.T. 和 J.E.Cuthrell Impoverd Infeasible Path Optimization for Sequ ential

## UG10-CH17-D346

PDF page: 260; original JSON pointer: `/3308`

Modular Smulators Part The Optimization Algorithm Computers & Chemical Engineering

## UG10-CH17-D347

PDF page: 260; original JSON pointer: `/3309`

9 3 p.257(1985) Lang Y-D 和 L.T.Biegler A Unified Algorithm for Flowsheet Optimization Computers and Chemical Engeering 11 2 p.143(1987)

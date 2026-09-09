# UG10-CH31 Detail Operation Index - 第31章 物性数据回归

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH31-D001

PDF page: 444; original JSON pointer: `/5298`

你可以输入任何实验物性数据 如

## UG10-CH31-D002

PDF page: 444; original JSON pointer: `/5299`

l 输入纯组分数据 相平衡数据和混合数据

## UG10-CH31-D003

PDF page: 444; original JSON pointer: `/5300`

l 检查并将回归结果绘制成曲线图

## UG10-CH31-D004

PDF page: 444; original JSON pointer: `/5301`

l 比较几个工况的回归结果

## UG10-CH31-D005

PDF page: 444; original JSON pointer: `/5302`

1. 启动 ASPEN PLUS 并从第二章所述模板中创建一个新的运行程序

## UG10-CH31-D006

PDF page: 444; original JSON pointer: `/5303`

2. 在 New 对话框上 在 Run Type 运行类别 列表框中选择 Data Regression 数据 回归 或 在 Data 数据 菜单中 单击 Setup 设定 然后在 Setup Specifications Global 全 局设定规定 页的 Run Type 运行类别 列表框中选择 Data Regression 数据回归

## UG10-CH31-D007

PDF page: 444; original JSON pointer: `/5304`

3. 用 Components Specifications Selection 组分规定选择 页定义组分 参见第六章

## UG10-CH31-D008

PDF page: 444; original JSON pointer: `/5305`

4. 用 Properties Specifications Global 全局物性规定 页选择物性方法 参见第七章

## UG10-CH31-D009

PDF page: 444; original JSON pointer: `/5306`

5. 在 Properties Parameters 物性参数 及 Properties Estimation 物性估算 窗口上 输入或估计任何附加的物性参数 参见第九章和第三十章

## UG10-CH31-D010

PDF page: 444; original JSON pointer: `/5307`

6. 在 Properties Data 物性数据 窗口上输入实验数据 详细说明参见本章的后面

## UG10-CH31-D011

PDF page: 444; original JSON pointer: `/5308`

7. 在 Properties Regression 物性回归 表上规定回归工况 参见本章的 用方程表示 回归工况 下面的应用将由这些步骤来指导

## UG10-CH31-D012

PDF page: 445; original JSON pointer: `/5310`

你必须选择使用某物性模型的物性方法 用它来确定你想要的参数

## UG10-CH31-D013

PDF page: 445; original JSON pointer: `/5311`

例如 为拟合 UNIQUAC二元参数 可选择下列物性方法之一

## UG10-CH31-D014

PDF page: 445; original JSON pointer: `/5312`

对于使用拟合参数的模拟运算 应选择相同的物性方法 例如 如果你想用 UNIQ-HOC

## UG10-CH31-D015

PDF page: 445; original JSON pointer: `/5313`

气相活度物性方法进行模拟计算 则在数据回归计算中也必须使用 UNIQ-HOC 物性方法

## UG10-CH31-D016

PDF page: 445; original JSON pointer: `/5314`

有一个很重要的情况例外 即不能将结尾为-2 的物性方法用 Data Regression 数据回归

## UG10-CH31-D017

PDF page: 445; original JSON pointer: `/5315`

所确定的二元参数在 Properties Parameters Binary Interaction 物性二元交互作用参数 表中是

## UG10-CH31-D018

PDF page: 445; original JSON pointer: `/5316`

l 在 Properties Parameters 物性参数 表中输入所需参数

## UG10-CH31-D019

PDF page: 445; original JSON pointer: `/5317`

l 用 P roperties Estimation 物性估算 表输入这些参数的估计值

## UG10-CH31-D020

PDF page: 445; original JSON pointer: `/5318`

则必须输入下列参数的估计值 MW TC PC ZC DHVLWT PLXANT 及 CPIG

## UG10-CH31-D021

PDF page: 445; original JSON pointer: `/5319`

你也可以输入将于 Properties Parameters 物性参数 窗口中确定的参数值 Data Regression

## UG10-CH31-D022

PDF page: 445; original JSON pointer: `/5320`

1. 用 Properties Data PURE-COMP 纯组分物性数据 窗口输入实验数据作为温度的 函数

## UG10-CH31-D023

PDF page: 445; original JSON pointer: `/5321`

2. 在 Properties Regression Input 物性回归输入 窗口规定物性方法 实验数据及被 回归的参数 输入纯组分数据 用 Properties Data PURE-COMP 纯组分物性数据 窗口可以输入纯组分物性的实验数据 作为温度的函数 例如 可以输入蒸汽压作为温度的函数 输入纯组分数据有以下几个步骤

## UG10-CH31-D024

PDF page: 445; original JSON pointer: `/5322`

1. 在 Data 数据 菜单上 单击 Properties 物性

## UG10-CH31-D025

PDF page: 445; original JSON pointer: `/5323`

2. 在 Data Browser 数据浏览器 左屏中 单击 Data 数据 文件夹

## UG10-CH31-D026

PDF page: 446; original JSON pointer: `/5325`

3. 单击 Data Object Manager 数据对象管理 上的 New 可创建一个新的 Data ID 数 据标识

## UG10-CH31-D027

PDF page: 446; original JSON pointer: `/5326`

4. 在 Create New ID 创建新标识 对话框中 输入一个标识或接受缺省标识 在 Select Type 选择类别 列表中 选择 PURE-COMP 纯组分 并单击 OK

## UG10-CH31-D028

PDF page: 446; original JSON pointer: `/5327`

5. 为编辑一个现有的 ID 标识 在 Object Manger 对象管理 选择该数据标识并 单击 Edit 编辑

## UG10-CH31-D029

PDF page: 446; original JSON pointer: `/5328`

6. 在 Setup 设置 页上 于 Property 物性 列表框中选择物性数据类型 并对每 个物性做提示性描述 你可以利用 Property 物性 列表 通过在 Category 类 别 列表中选择物性类别 来限制物性数据的类型 缺省的类别是 ALL

## UG10-CH31-D030

PDF page: 446; original JSON pointer: `/5329`

7. 在 Component list 组分列表 框中,为你现有的试验数据定义组分

## UG10-CH31-D031

PDF page: 446; original JSON pointer: `/5330`

8. 在 Temperature 温度 和 Pressure 压力 区 如果是激活的 规定常温和常压 在这些区中输入的值应用于所有的数据点 并简化所输入的恒温恒压数据

## UG10-CH31-D032

PDF page: 446; original JSON pointer: `/5331`

9. 单击 Data 数据 页

## UG10-CH31-D033

PDF page: 446; original JSON pointer: `/5332`

10. 在 Data 数据 页的适当列中输入试验数据

## UG10-CH31-D034

PDF page: 446; original JSON pointer: `/5333`

11. 输入物性数据的标准偏差值或接受系统缺省值 参见本章 测量值标准偏差的输入 如果你想让 ASPEN PLUS 忽略一些数据或已输入的标准偏差 请到 Usage 应用 区 单击该行 并选择 Ignore 忽略 ASPEN PLUS 在后面的任何回归计算中都不使用这些数 据 拟合相平衡数据和混合数据 为拟合相平衡数据和混合数据 如汽 液平衡数据和密度数据 需进行如下操作

## UG10-CH31-D035

PDF page: 446; original JSON pointer: `/5334`

1. 用 Properties Data MIXTURE 混合物性数据 窗口输入试验数据 见下一节

## UG10-CH31-D036

PDF page: 446; original JSON pointer: `/5335`

2. 用 Properties Regression Input 物性回归输入 定义物性方法 试验数据及被回归 的二元或双参数 参见本章 用方程表示回归工况 输入相平衡数据和混合数据 用 Properties Data MIXTURE 混合物性数据 窗口输入相平衡和混合物性的试验数据 作为温度 压力 和组分的函数 例如 你可以输入两个组分的 Txy 汽 液平衡数据 输入相平衡数据和混合数据有以下几个步骤

## UG10-CH31-D037

PDF page: 446; original JSON pointer: `/5336`

1. 在 Data 数据 菜单上,单击 Properties 物性

## UG10-CH31-D038

PDF page: 446; original JSON pointer: `/5337`

2. 在 Data Browser 数据 左屏中,单击 Data 数 文件夹

## UG10-CH31-D039

PDF page: 446; original JSON pointer: `/5338`

3. 在 Data Object Manager 数据对象管理 上,单击 New ,创建一个新的 Data ID 数 据标识 在 Create New ID 创建新标识 对话框中 输入一个标识或接受缺省标 识 在 Select Type 选择类别 列表中 选择 MIXTURE 混合 并单击 OK

## UG10-CH31-D040

PDF page: 446; original JSON pointer: `/5339`

4. 为编辑一个现有的标识 在 Object Manger 对象管理 选择该数据标识 并单击 Edit 编辑

## UG10-CH31-D041

PDF page: 446; original JSON pointer: `/5340`

5. 在 Setup 设置 页 于 Data Type 数据类别 列表框中选择物性数据类型 选项 列于表 31.1 和 31.2 中 你可以利用 Property 物性 列表 通过在 Category 类 别 列表框中选择物性类别 来限制物性数据的类型 缺省的类别是 ALL

## UG10-CH31-D042

PDF page: 446; original JSON pointer: `/5341`

6. 从 Available Components 有效组分 列表中选择组分 并用右箭头键将他们移至 Selected Components 选定的组分 列表中

## UG10-CH31-D043

PDF page: 447; original JSON pointer: `/5343`

7. 在 Temperature 温度 和 Pressure 压力 区 如果是激活的 规定常温和常压 在这些区中输入的值应用于所有的数据点

## UG10-CH31-D044

PDF page: 447; original JSON pointer: `/5344`

8. 在 Composition Basis 组分基准 列表框中 定义组分数据基准 你可以输入摩 尔分率 质量分率 摩尔百分率或质量百分率作为组分基准 摩尔分率是缺省基准

## UG10-CH31-D045

PDF page: 447; original JSON pointer: `/5345`

9. 单击 Data 页

## UG10-CH31-D046

PDF page: 447; original JSON pointer: `/5346`

10. 在 Data 页的适当列中输入试验数据

## UG10-CH31-D047

PDF page: 447; original JSON pointer: `/5347`

正文待来源表达/OCR边界复核；原文本 SHA256: `c0ddd4308727408d77b28fc76f368401b8288208fe1b40ee5ced2d876a2c2e39`。

## UG10-CH31-D048

PDF page: 447; original JSON pointer: `/5348`

RKSWS, RKSMHV2,和 PSRK 状态方程物性方法

## UG10-CH31-D049

PDF page: 448; original JSON pointer: `/5350`

USER-X 用户定义物性对 X 的函数

## UG10-CH31-D050

PDF page: 448; original JSON pointer: `/5351`

USER-Y 用户定义物性对 Y 的函数

## UG10-CH31-D051

PDF page: 448; original JSON pointer: `/5352`

USERI-X 用户定义部分物性对 X 的函数

## UG10-CH31-D052

PDF page: 448; original JSON pointer: `/5353`

USERI-Y 用户定义部分物性对 Y 的函数

## UG10-CH31-D053

PDF page: 448; original JSON pointer: `/5354`

定义电解质活度系数模型的参数

## UG10-CH31-D054

PDF page: 448; original JSON pointer: `/5355`

HLMX 液相摩尔焓 定义活度系数模型的与温度有关的二元或双参

## UG10-CH31-D055

PDF page: 448; original JSON pointer: `/5356`

OSMOT 渗透系数 定义电解质活度系数模型的参数

## UG10-CH31-D056

PDF page: 448; original JSON pointer: `/5357`

PH pH 定义化学平衡常数 仅用于表观组分近似值

## UG10-CH31-D057

PDF page: 448; original JSON pointer: `/5358`

VLMX 液相摩尔体积 定义 Clake(克拉克)密度模型的参数

## UG10-CH31-D058

PDF page: 448; original JSON pointer: `/5359`

* 可以只输入单个电解质系统的克分子浓度平均离子活度系数数据

## UG10-CH31-D059

PDF page: 448; original JSON pointer: `/5360`

** 在几个温度状态下适用该数据以确保精确地代表混合热

## UG10-CH31-D060

PDF page: 448; original JSON pointer: `/5361`

*** 对于单电解质或电解质混合溶液 在饱和状态时输入该数据 且必须在 Reactions Chemistry 表上

## UG10-CH31-D061

PDF page: 448; original JSON pointer: `/5362`

生成二 元 VLE 和 LLE 数据

## UG10-CH31-D062

PDF page: 448; original JSON pointer: `/5363`

对于有两个组分的系统 可以用指定的物性方法产生 VLE 和 LLE 数据 ASPEN PLUS

## UG10-CH31-D063

PDF page: 448; original JSON pointer: `/5364`

可以用生成的数据回归另一物性方法的参数 据此特性 你可以在两个不同的物性方法之间

## UG10-CH31-D064

PDF page: 449; original JSON pointer: `/5366`

例如 你可以用 UNIFAC 表述物性方法 产生 VLE 数据和 LLE 数据 然后用生成的数

## UG10-CH31-D065

PDF page: 449; original JSON pointer: `/5367`

生成二元 VLE 和 LLE 数据有以下几个步骤

## UG10-CH31-D066

PDF page: 449; original JSON pointer: `/5368`

1. 在 Data 数据 菜单上,单击 Properties 物性

## UG10-CH31-D067

PDF page: 449; original JSON pointer: `/5369`

2. 在 Data Browser 数据浏览器 左屏中,单击 Data 数据 文件夹

## UG10-CH31-D068

PDF page: 449; original JSON pointer: `/5370`

3. 在 Data Object Manager 数据对象管理 上,单击 New ,创建一个新的 Data ID 数 据标识

## UG10-CH31-D069

PDF page: 449; original JSON pointer: `/5371`

4. 在 Create New ID 创建新标识 对话框中 输入一个标识或接受缺省标识 在 Select Type 选择类别 列表框中 选择 MIXTURE 混合 并单击 OK

## UG10-CH31-D070

PDF page: 449; original JSON pointer: `/5372`

5. 为编辑一个现有的标识 在 Object Manger 对象管理 选择该数据标识 并单击 Edit

## UG10-CH31-D071

PDF page: 449; original JSON pointer: `/5373`

6. 在 Setup 设置 页上 于 Data Type 数据类别 列表框中选择物性数据类型 选项 生成的数据 TXY, PXY, 或 TPXY VLE TXX 或 TPXX LLE 不要选择 GEN-TPXY 或 GEN_TPXX 数据类型

## UG10-CH31-D072

PDF page: 449; original JSON pointer: `/5374`

7. 从 Available Components 有效组分 列表中选择组分 并用右箭头键将他们移至 Selected Components 选定的组分 列表中

## UG10-CH31-D073

PDF page: 449; original JSON pointer: `/5375`

8. 在 Temperature 温度 和 Pressure 压力 区 如果是激活的 规定常温和常压 在这种状态下 将生成数据

## UG10-CH31-D074

PDF page: 449; original JSON pointer: `/5376`

9. 单击 Data 表

## UG10-CH31-D075

PDF page: 449; original JSON pointer: `/5377`

10. 在 Data 数据 页上 单击 Generate Data 创建数据 键

## UG10-CH31-D076

PDF page: 449; original JSON pointer: `/5378`

11. Generate Binary VLE or LLE Data 生成二元 VLE 或 LLE Data 数据 对话框中,选 择合适的物性方法 亨利组分标识和化学标识

## UG10-CH31-D077

PDF page: 449; original JSON pointer: `/5379`

12. 单击 Generate 生成 键生成数据 Data 页会显示液相组分 并将生成的该组分数据用于回归计算 输入测量的标准偏差 测量变量的标准偏差是随机误差的数量级估计值 数据回归系统会基于你所选择的物性 或数据类型 指定一个合理的标准偏差的缺省值 如果你知道数据的标准偏差 可用 Properties Data Data 物性数据值 页输入 数据回归系统指定的缺省标准偏差值如下 参数 标准偏差值 温度 0.1 度* 压力 0.1% 液相组成 0.1% 气相组成 1.0% 参数 1.0%

## UG10-CH31-D078

PDF page: 449; original JSON pointer: `/5380`

* 对于 Txx 或 TPxx 数据 缺省值是 0.01

## UG10-CH31-D079

PDF page: 450; original JSON pointer: `/5382`

你可以为下列情况指定一套标准偏差

## UG10-CH31-D080

PDF page: 450; original JSON pointer: `/5383`

要想在 Properties Data Data 上输入一标准偏差行 请打开 Usage 应用 选择 select

## UG10-CH31-D081

PDF page: 450; original JSON pointer: `/5384`

Std-Dev 选择标准偏差 在遇到另一个 Std-Dev 标准偏差 之前 你所输入的值将适用

## UG10-CH31-D082

PDF page: 450; original JSON pointer: `/5385`

于后面的所有数据点 标准偏差以百分数或绝对值形式输入数据回归系统 数据回归不要求

## UG10-CH31-D083

PDF page: 450; original JSON pointer: `/5386`

标准偏差值很精确 通常只需你确定数量级和比例

## UG10-CH31-D084

PDF page: 450; original JSON pointer: `/5387`

标准偏差是零的变量被认为无错误 只是具有很小或没有随机误差的状态变量可以是

## UG10-CH31-D085

PDF page: 450; original JSON pointer: `/5388`

零 如蒸汽压或密度等物性的标准偏差不能是零 不能将所有的标准偏差都输成零

## UG10-CH31-D086

PDF page: 450; original JSON pointer: `/5389`

对于相平衡数据 如 TPXY 数据 零标准偏差数必须大于或等于相平衡约束因素数 或

## UG10-CH31-D087

PDF page: 450; original JSON pointer: `/5390`

相当于混合物中参与相平衡的组分数 例如 对于两个组分的 TPXY 数据 你只能将两个

## UG10-CH31-D088

PDF page: 450; original JSON pointer: `/5391`

变量的标准偏差指定为零 T 或 P, 及 X(1) 或 Y (1)的标准偏差可以是零 TPX 数据有个例

## UG10-CH31-D089

PDF page: 450; original JSON pointer: `/5392`

你可以在 plot 曲线 菜单上用 Plot Wizard 智能绘图 将你所输入的试验数据用曲线

## UG10-CH31-D090

PDF page: 450; original JSON pointer: `/5393`

依据你所输入的数据类型 Plot Wizard 智能绘图 提供下列类型的曲线图

## UG10-CH31-D091

PDF page: 450; original JSON pointer: `/5394`

用 Properties Regression 物性回归 窗口可以将回归工况方程化

## UG10-CH31-D092

PDF page: 450; original JSON pointer: `/5395`

1. 在 Data 数据 菜单上,单击 Properties 物性

## UG10-CH31-D093

PDF page: 450; original JSON pointer: `/5396`

2. 在 Data Browser 数据浏览器 左屏中, 单击 Regression 回归 文件夹

## UG10-CH31-D094

PDF page: 451; original JSON pointer: `/5398`

3. 在 Data Object Manager 数据对象管理 上, 单击 New , 创建一个新的 Regression ID 回归标识 在 Create New ID 创建新标识 对话框中 输入一个标识或接受缺 省标识 并单击 OK

## UG10-CH31-D095

PDF page: 451; original JSON pointer: `/5399`

4. 为编辑一个现有的标识 在 Object Manger 对象管理 上选择该回归标识 并单 击 Edit

## UG10-CH31-D096

PDF page: 451; original JSON pointer: `/5400`

5. 在 Regression Input Setup 回归输入设顶 的 Property Options 物性选项 框内 定义物性方法 亨利组分标识 化学标识和电解质计算方法 在 Properties Specifications Global 全局物性规定 上输入的全局物性规定是缺省的 你可以选 择已在 Properties Specifications 物性规定 窗口中所输入的任何物性方法

## UG10-CH31-D097

PDF page: 451; original JSON pointer: `/5401`

6. 在 Setup 设定 页的底部 用 Data Set 数据集 框为将被回归的试验数据输入 Data set IDs 数据集标识 数据集标识 在 Weight 加权 区输入一个大于一的数 值 可以设置更大的加权数据

## UG10-CH31-D098

PDF page: 451; original JSON pointer: `/5402`

7. 对于每个 Binary VLE Data 二元 VLE 数据 参考设置 你可以用 Perform Test 执 行测试 复选框来选择你是否执行热力学一致性测试 如果你选择进行一致性测试 则可以用 Test Method 测试方法 列表框选择一致性测试的类型 还要用 Reject 放弃 复选框来选择你是否放弃失败的一致性测试数据 详细信息参见本章 VLE 数据的热力学一致性测试

## UG10-CH31-D099

PDF page: 451; original JSON pointer: `/5403`

8. 单击 Parameters 参数 表

## UG10-CH31-D100

PDF page: 451; original JSON pointer: `/5404`

9. 输入被回归的参数 按照以下各节的程序定义被回归的参数 在多数情况下 ASPEN PLUS 将按照你已定义的物性方法和数据集自动完成 Regression Input 回归输入 窗口 例如 假定你选择 NRTL 物性方法并为二元系统输入了 Txy 数据 ASPEN PLUS 会完成 Regression Input 回归输入 窗口 通过

## UG10-CH31-D101

PDF page: 451; original JSON pointer: `/5405`

l 在 Data ID 数据标识 区填入

## UG10-CH31-D102

PDF page: 451; original JSON pointer: `/5406`

l 定义将回归的 NRTL 二元参数

## UG10-CH31-D103

PDF page: 451; original JSON pointer: `/5407`

在被回归的参数未被定义 或当你想修改缺省参数或增加附加参数的情况下 就可以用

## UG10-CH31-D104

PDF page: 451; original JSON pointer: `/5408`

Regression Input Parameters 回归参数输入 表了

## UG10-CH31-D105

PDF page: 451; original JSON pointer: `/5409`

定义回归参数需以下几个步骤

## UG10-CH31-D106

PDF page: 451; original JSON pointer: `/5410`

1. 在 Regression Input Parameters 回归参数输入 的 Type 类别 区, 选择其一 选项 适用范围 Parameter 纯组分参数 Binary parameter 二元参数 Group parameter UNIFAC 官能团参数 Group binary parameter UNIFAC 官能团二元参数 Pair parameter 电解质 NRTL 模型双参数 Chemistry 电解质化学的相平衡常数

## UG10-CH31-D107

PDF page: 451; original JSON pointer: `/5411`

2. 在 Name/Element 名称/元素 列表框中,选择参数名称,该参数有提示性标志

## UG10-CH31-D108

PDF page: 451; original JSON pointer: `/5412`

3. 在参数名称右边输入参数的元素数量 , 对于 Lyngby-modified UNIFAC 和 Dortmund-modified UNIFAC官能团的交互作用参数, 只回归第一个元素

## UG10-CH31-D109

PDF page: 451; original JSON pointer: `/5413`

4. 在 Component/Group 组分/组 列表框中输入组分标识或 UNIFAC官能团标识

## UG10-CH31-D110

PDF page: 452; original JSON pointer: `/5415`

正文待来源表达/OCR边界复核；原文本 SHA256: `653950414a84facaa51a690f16f9e728d22ecca001fb22f8a4f048408a29e535`。

## UG10-CH31-D111

PDF page: 452; original JSON pointer: `/5416`

工况研究中 观察哪个值给出的结果最好

## UG10-CH31-D112

PDF page: 452; original JSON pointer: `/5417`

6. 你可以输入参数的初值 上限 下限和比例系数 VLE 数据的热力学一致性测试 如果提供下列数据 ASPEN PLUS 将测试你在 Data Mixture 混合数据 中输入的二元 VLE 数据以测试热力学一致性 这些数据是

## UG10-CH31-D113

PDF page: 452; original JSON pointer: `/5418`

l 不算纯组分数据点 x=0.0 和 x=1.0 至少五个数据点

## UG10-CH31-D114

PDF page: 452; original JSON pointer: `/5419`

Onken 的 Vapor-Liquid Equilibrium Data Collection 汽 液平衡数据集 DECHEMA

## UG10-CH31-D115

PDF page: 452; original JSON pointer: `/5420`

Chemistry Data Series DECHEMA 化学数据系 , Vol.I 第一卷 Part 1 第一部分 由

## UG10-CH31-D116

PDF page: 452; original JSON pointer: `/5421`

Chemisches Apparatewesen, 1977)编辑

## UG10-CH31-D117

PDF page: 452; original JSON pointer: `/5422`

缺省时 ASPEN PLUS 执行区域测试 可以用 Regression Input Setup 回归输入设顶

## UG10-CH31-D118

PDF page: 452; original JSON pointer: `/5423`

页选择另一测试方法或改变测试容差 在 Setup 设定 页上 可以规定你舍弃还是使用失

## UG10-CH31-D119

PDF page: 452; original JSON pointer: `/5424`

在 Regression Results 回归结果 的 Consistency Tests 一致性测试 页上标明了你的

## UG10-CH31-D120

PDF page: 452; original JSON pointer: `/5425`

l 数据有错误 不是在原始数据里就是在数据输入过程中

## UG10-CH31-D121

PDF page: 452; original JSON pointer: `/5426`

l 气相状态平衡模型不是恰好引起非理想状态的原因

## UG10-CH31-D122

PDF page: 452; original JSON pointer: `/5427`

l 没有足够的数据点或者数据只替换很小的浓度范围 要获得均衡一致的结果 需输

## UG10-CH31-D123

PDF page: 452; original JSON pointer: `/5428`

如果数据测试失败 检查你在 Data Mixture 混合数据 窗口输入的 Txy, Pxy, 或 TPxy 数值和单位 为获得均衡一致的测试结果 需输入全部组分范围内的数据 如果数据只替换很窄的数 据范围 你可以忽略测试结果

## UG10-CH31-D124

PDF page: 453; original JSON pointer: `/5430`

你可以用 Data Regression 数据回归 估算已知模型参数的精度 将实验数据与你用模

## UG10-CH31-D125

PDF page: 453; original JSON pointer: `/5431`

型得到的计算结果进行比较

## UG10-CH31-D126

PDF page: 453; original JSON pointer: `/5432`

1. 在 Properties Specifications Global 全局物性规定 页中 选择一物性方法 参见 第七章

## UG10-CH31-D127

PDF page: 453; original JSON pointer: `/5433`

2. 在 Properties Data 物性数据 表中 输入实验数据 参见本章 输入纯组分数据 和输入相平衡和混合数据部分

## UG10-CH31-D128

PDF page: 453; original JSON pointer: `/5434`

3. 在 Properties Parameter 物性参数 表上 输入已知的模型参数 参见第八章 要 想估算储存在数据库中的参数 则跳过这一步

## UG10-CH31-D129

PDF page: 453; original JSON pointer: `/5435`

4. 在 Regression Input Setup 回归输入设置 页上 定义在估算中所用的物性方法并 输入实验数据 参见本章 用方程表示回归工况

## UG10-CH31-D130

PDF page: 453; original JSON pointer: `/5436`

5. 在 Regression Input 回归输入 的 Calculation Type 计算类别 框中 选择 Evaluation 估算 运行回归工况 运行回归工况 需在 Run 运行 菜单或 Control Panel 控制面板 中选择 Run 运 行 如果你有多于一个的回归工况 会显示 Data Regression Run Selection 数据回归运 行选择 对话框 所有的工况都列在 Run 运行 区内 Don`t Run 不运行 区是空的 你需进行如下操作

## UG10-CH31-D131

PDF page: 453; original JSON pointer: `/5437`

l 单击 OK 运行所有的工况

## UG10-CH31-D132

PDF page: 453; original JSON pointer: `/5438`

l 改变各工况执行的顺序 用 Up 和 Down 箭头键选择一个工况

## UG10-CH31-D133

PDF page: 453; original JSON pointer: `/5439`

l 从运行工况中除去某些回归工况 选定一个工况 然后用左箭头键将它移至 Don`t

## UG10-CH31-D134

PDF page: 453; original JSON pointer: `/5440`

回归工况的运行顺序是重要的 回归运算所得到的参数被自动用于后面的所有回归工况

## UG10-CH31-D135

PDF page: 453; original JSON pointer: `/5441`

中 ASPEN PLUS 将按照 Run 区所显示的顺序执行回归工况的运算

## UG10-CH31-D136

PDF page: 453; original JSON pointer: `/5442`

本节将讨论回归结果检查 绘制回归曲线及回归结果比较

## UG10-CH31-D137

PDF page: 453; original JSON pointer: `/5443`

检查回归结果有以下几个步骤

## UG10-CH31-D138

PDF page: 453; original JSON pointer: `/5444`

1. 在 Data 数据 菜单上,单击 Properties 物性

## UG10-CH31-D139

PDF page: 453; original JSON pointer: `/5445`

2. 在 Data Browser 数据浏览器 左屏中,双击 Regression 回归 文件夹

## UG10-CH31-D140

PDF page: 453; original JSON pointer: `/5446`

3. 在 Data Browser 数据浏览器 菜单上 双击你感兴趣的 Regression ID 回归标识 并选择 Results 结果 此时回显示 Regression Results 回归结果 窗口 包含下列页

## UG10-CH31-D141

PDF page: 454; original JSON pointer: `/5448`

Consistency Tests 热力学一致性测试结果

## UG10-CH31-D142

PDF page: 454; original JSON pointer: `/5449`

归值之差 实验值和回归值之差的百分数 偏差浏览 包括

## UG10-CH31-D143

PDF page: 454; original JSON pointer: `/5450`

单击 Deviations 偏差 按钮所得到的平均值和最大偏差

## UG10-CH31-D144

PDF page: 454; original JSON pointer: `/5451`

Profiles 所有的实验数据和计算值 这些数据用于所有已预定义的曲

## UG10-CH31-D145

PDF page: 454; original JSON pointer: `/5452`

线上 参见本章的绘制回归结果曲线

## UG10-CH31-D146

PDF page: 454; original JSON pointer: `/5453`

Extra Property 使用 VLE 数据时特殊物性残差 如 Regression Input Report

## UG10-CH31-D147

PDF page: 454; original JSON pointer: `/5454`

回归输入报告 所要求的那样 例如 活度系数和 K 值

## UG10-CH31-D148

PDF page: 454; original JSON pointer: `/5455`

如果数据回归运行收敛失败 则可能是 Properties Data 物性数据 窗口中有数据输入 错误 检查这些数据和单位 或用 Plot 菜单上的 Plot Wizard 智能绘图 将这些数据绘制 成曲线 以检查错误和逸出值 数据可能使用了不和适的标准偏差 关于这方面的指南 参见第本章 输入测量的标准 偏差 如果使用了二元 VLE 数据 则数据可能不具有热力学一致性 要求用 Setup 设置 页 做一致性测试 返回回归工况 用 Regression Results Consistency Tests 回归结果一致性测

## UG10-CH31-D149

PDF page: 454; original JSON pointer: `/5456`

当一套数据拟合不同的模型时 选择能给出最小均方根残差的模型

## UG10-CH31-D150

PDF page: 454; original JSON pointer: `/5457`

在 Regression Results Correlation 回归结果校正 页上 矩阵偏离对角线的元素表明了

## UG10-CH31-D151

PDF page: 454; original JSON pointer: `/5458`

表明关联度高 如果可能的话 选择没有关联的参数 有一个重要的情况例外 活度系数模

## UG10-CH31-D152

PDF page: 454; original JSON pointer: `/5459`

型不对称的二元参数是高度关联的 ij 和 ji 参数都要求有最好的拟合

## UG10-CH31-D153

PDF page: 454; original JSON pointer: `/5460`

如何确认不令人满意的数据回归结果

## UG10-CH31-D154

PDF page: 454; original JSON pointer: `/5461`

有可能你的 Data Regression 数据回归 运行收敛无错误 但是有可能结果不适合用于

## UG10-CH31-D155

PDF page: 454; original JSON pointer: `/5462`

模型运行 用下面的这些 Regression Results 回归结果 页可以确认不好的拟合

## UG10-CH31-D156

PDF page: 454; original JSON pointer: `/5463`

如果存在上述任何一种情况 在 Properties Data 窗口上检查原始数据源 数据及单位的 错误 于 Plot 菜单用 Plot Wizard将数据绘制成曲线 用 Regression Results Residual 页查看 一下每一个数据点是如何拟合的 查找一下范围之外的数据

## UG10-CH31-D157

PDF page: 455; original JSON pointer: `/5465`

在浏览 Regression Results 回归结果 窗口时 你可以用 Plot Wizard 智能绘图 产生

## UG10-CH31-D158

PDF page: 455; original JSON pointer: `/5466`

有用的回归结果曲线 ASPEN PLUS 提供了许多预先确定好了的图表

## UG10-CH31-D159

PDF page: 455; original JSON pointer: `/5467`

在浏览 Regression Results 回归结果 窗口时 于主菜单的 Plot 菜单上选定 Plot Wizard

## UG10-CH31-D160

PDF page: 455; original JSON pointer: `/5468`

可启动 Plot Wizard 根据回归类型 可以得到如下一些曲线

## UG10-CH31-D161

PDF page: 455; original JSON pointer: `/5469`

预定的曲线如 T-xy 或 P-xy 将实验数据显示成符号而将计算数据显示成曲线 这些曲

## UG10-CH31-D162

PDF page: 455; original JSON pointer: `/5470`

线允许评估一定量的拟合数据 也可以通过对比实验数据和计算结果来确认不好的数据点

## UG10-CH31-D163

PDF page: 455; original JSON pointer: `/5471`

T-xy 或 P-xy 图形 以检查回归参数的推论

## UG10-CH31-D164

PDF page: 455; original JSON pointer: `/5472`

你可以将几个回归工况的结果绘制在一条曲线上 这允许你将拟合同一套数据的几个物

## UG10-CH31-D165

PDF page: 455; original JSON pointer: `/5473`

性模型进行比较 要想将几个工况结果绘制成曲线 在 Plot Wizard上选择 Add to Plot 第三

## UG10-CH31-D166

PDF page: 455; original JSON pointer: `/5474`

例如 你可以用两个工况的结果绘制 Txy plot 曲线

## UG10-CH31-D167

PDF page: 455; original JSON pointer: `/5475`

1. 从第一个工况结果窗口的 Plot 菜单 用 Plot Wizard绘制 T-xy 曲线

## UG10-CH31-D168

PDF page: 455; original JSON pointer: `/5476`

2. 选择数据组和组分用以绘图 单击 Next 或 Finish 来显示该曲线

## UG10-CH31-D169

PDF page: 455; original JSON pointer: `/5477`

3. 到 Regression Results 回归结果 窗口 不要关闭曲线

## UG10-CH31-D170

PDF page: 455; original JSON pointer: `/5478`

4. 用 Plot 菜单的 Plot Wizard 选择 T-xy 曲线类型 单击 Next

## UG10-CH31-D171

PDF page: 455; original JSON pointer: `/5479`

5. 选择与第 2 步相同的数据组和组分

## UG10-CH31-D172

PDF page: 455; original JSON pointer: `/5480`

6. 选择 Add to Plot 加入曲线 以选择 Plot Mode 曲线模式 然后从列表框中选择第 一个曲线

## UG10-CH31-D173

PDF page: 455; original JSON pointer: `/5481`

7. 单击 Next of Finish 可显示两个工况的结果曲线 必要的话 你可以用鼠标右键菜单的 Properties 选项改变曲线特性

## UG10-CH31-D174

PDF page: 456; original JSON pointer: `/5483`

在流程运行中应用回归结果

## UG10-CH31-D175

PDF page: 456; original JSON pointer: `/5484`

回归所确定的参数被自动放在 Properties Parameters 物性参数 窗口的合适位置 在一

## UG10-CH31-D176

PDF page: 456; original JSON pointer: `/5485`

1. 从 Data Browser 数据浏览器 窗口选择 Setup Specifications Global 全局设置规 定 页

## UG10-CH31-D177

PDF page: 456; original JSON pointer: `/5486`

2. 在 Run-type 运行类别 区中 选择 Flowsheet 流程 你可以在 Component Data 组分数据 页上将回归结果和估算结果拷贝到参数窗口上

## UG10-CH31-D178

PDF page: 456; original JSON pointer: `/5487`

1. 在 Tools 工具栏 菜单上 选择 Options 选项

## UG10-CH31-D179

PDF page: 456; original JSON pointer: `/5488`

2. 单击 Component Data 组分数据 项

## UG10-CH31-D180

PDF page: 456; original JSON pointer: `/5489`

3. 选择 Copy Regression and Estimation Results Onto Parameters Forms 将回归结果和 估算结果复制到表上 复选框 由 DETHERM 和 the Internet 检索数据 你可以由 DETHERM and the Internet 检索很宽范围的实验数据 DETHERM包含全世界 最全面的热力学物理物性和相平衡数据集 如果你有权使用 DETHERM 请在主应用工具 条上单击 DETHERM 以检查你所需要的实验数据 你所修改的实验数据将显示在 Properties

## UG10-CH31-D181

PDF page: 456; original JSON pointer: `/5490`

Data 窗口上 并可用于数据回归

## UG10-CH31-D182

PDF page: 456; original JSON pointer: `/5491`

正文待来源表达/OCR边界复核；原文本 SHA256: `9807c420411e50e83a82d74c5a087c39115d5db2119d766cb1253e09ecfa00a5`。

## UG10-CH31-D183

PDF page: 456; original JSON pointer: `/5492`

Atmospheric data of Ortega J. and Pena J.A., J. Chem. Eng. Data 31, 339 (1986): T C X ETOAC Y ETOAC T C X ETOAC Y ETOAC

## UG10-CH31-D184

PDF page: 457; original JSON pointer: `/5494`

1. 启动 ASPEN PLUS 创建一个新的运行模型 选择 Data Regression 作为 Run Type

## UG10-CH31-D185

PDF page: 457; original JSON pointer: `/5495`

2. 在 Components Specifications Selection 组分规定选择 页上输入组分 注释 可以在 ASPEN PLUS 的 Online Applications Library 在线应用库 中得到包含本 例结果的一个完整的备份文件 该文件名叫 DRS1 本例中 有三个活度系数模型拟合 VLE 数据 每个活度系数模型都在不同的工况中

## UG10-CH31-D186

PDF page: 458; original JSON pointer: `/5497`

3. 选择物性方法 用 Properties Specifications Global 全局物性方法 页选择物性方法 本例对计算结果 拟合于 Wilson, NRTL, 和 UNIQUAC的物性方法进行了比较 在 Global 全局 页上选择三 者之一 其余两个在 Referenced 参考 页上 本例中 在 Global 页上选择了 Wilson 模型

## UG10-CH31-D187

PDF page: 458; original JSON pointer: `/5498`

4. 输入实验数据 用 Properties Data Mixture 混合物性数据 窗口输入气液平衡数据 要求输入三套数据 下面的 Setup 和 Data 页是为 40°C 时的等温数据集设置的

## UG10-CH31-D188

PDF page: 459; original JSON pointer: `/5500`

正文待来源表达/OCR边界复核；原文本 SHA256: `bf79d3432c37c97a72b20b516ea5e3a0b395e525acb78a5cac31dd6fa73a0f57`。

## UG10-CH31-D189

PDF page: 460; original JSON pointer: `/5502`

6. 规定附加回归工况 用 Regression Object Manager 回归对象管理 可以定义两个附加工况 用相同的实验 数据集 但是用 NRTL 和 UNIQUAC 物性方法 ASPEN PLUS 会再一次填完 Regression Input 窗口 但是 由于 WILSON 方法是全局物性方法 故它是缺省的 在 Setup 页的 Method 列 表框中定义物性方法是 NRTL 则 NRTL 物性方法被用于第二个工况中 如果使用 NRTL 物

## UG10-CH31-D190

PDF page: 460; original JSON pointer: `/5503`

性方法 必需回归 NRTL 二元参数 规定 NRTL 二元参数的元素 1 和元素 2 为回归参数

## UG10-CH31-D191

PDF page: 461; original JSON pointer: `/5505`

7. 运行回归工况 运行这三个工况 则在 Data Regression Run Selection 数据回归运行选择 对话框中单 击 OK 即可 也可以运行你所选的工况 只要用左箭头键将你不想运行的工况移至 Don`t Run 区内即可

## UG10-CH31-D192

PDF page: 461; original JSON pointer: `/5506`

8. 检查在 Regression Results 回归结果 表中的结果 在 Regression Results Parameters 页中可以检查最终参数值

## UG10-CH31-D193

PDF page: 462; original JSON pointer: `/5508`

用 Regression Results Sum of Squares 回归结果平方和 页可以检查质量平方和及均方

## UG10-CH31-D194

PDF page: 462; original JSON pointer: `/5509`

用 Regression Results Consistency Tests 回归结果一致性测试 页可以检验热力学一致

## UG10-CH31-D195

PDF page: 462; original JSON pointer: `/5510`

性测试结果 所有的数据组都通过 Redlich Kister区域测试

## UG10-CH31-D196

PDF page: 462; original JSON pointer: `/5511`

用 Regression Results Residual 回归结果残差 页可以检验温度 压力及组成的拟合残

## UG10-CH31-D197

PDF page: 463; original JSON pointer: `/5513`

用 Plot 菜单的 Plot Wizard可以将工况 VLE 1 的压力残差绘制成曲线

## UG10-CH31-D198

PDF page: 463; original JSON pointer: `/5514`

将实验数据与运算结果进行比较很有用 用 Plot 菜单的 Plot Wizard 可以生成第一组

## UG10-CH31-D199

PDF page: 464; original JSON pointer: `/5516`

将 NRTL 和 UNIQUAC 工况的结果加入 WILSON 物性方法绘制出的图中 见本章

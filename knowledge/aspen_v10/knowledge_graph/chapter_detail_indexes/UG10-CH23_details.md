# UG10-CH23 Detail Operation Index - 第23章 模拟模型的数据拟合

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH23-D001

PDF page: 341; original JSON pointer: `/4051`

你可以用 Data-Fit 数据拟合 功能将 ASPEN PLUS 模拟模型与装置或实验数据拟合

## UG10-CH23-D002

PDF page: 341; original JSON pointer: `/4052`

你为一个模拟模型的输入和结果变量提供一套或多套测量数据 Data-Fit 数据拟合 调整

## UG10-CH23-D003

PDF page: 341; original JSON pointer: `/4053`

或估算 输入参数以便使模型与数据最吻合 如果你要 Data-Fit 数据拟合 整和输入变

## UG10-CH23-D004

PDF page: 341; original JSON pointer: `/4054`

Data-Fit 数据拟合 将测量数据和模型预测数据之差的加权平方和最小化 按统计学

## UG10-CH23-D005

PDF page: 341; original JSON pointer: `/4055`

说法 Data-Fit 数据拟合 进行了普通最小平方或最大值似然 变量误差 估算

## UG10-CH23-D006

PDF page: 341; original JSON pointer: `/4056`

l Data-Fit 数据拟合 应用的类型

## UG10-CH23-D007

PDF page: 341; original JSON pointer: `/4057`

l 定义一个 Data-Fit 数据拟合 问题

## UG10-CH23-D008

PDF page: 341; original JSON pointer: `/4058`

l 建立 Point-Data 点数据 集

## UG10-CH23-D009

PDF page: 341; original JSON pointer: `/4059`

l 建立 Profile-Data 分布数据 数据集

## UG10-CH23-D010

PDF page: 341; original JSON pointer: `/4060`

l 定义 Data-Fit 数据拟合 回归工况

## UG10-CH23-D011

PDF page: 341; original JSON pointer: `/4061`

l 确认定义完备的 Data-Fit 数据拟合 问题

## UG10-CH23-D012

PDF page: 341; original JSON pointer: `/4062`

Data-Fit 数据拟合 应用的类型

## UG10-CH23-D013

PDF page: 341; original JSON pointer: `/4063`

Data-Fit 数据拟合 应用分为两大类

## UG10-CH23-D014

PDF page: 341; original JSON pointer: `/4064`

在第一种类型的应用中 Data-Fit 数据拟合 Data-Fit 数据拟合 根据实验室动力

## UG10-CH23-D015

PDF page: 341; original JSON pointer: `/4065`

多个温度下浓度对应时间的数据 Data-Fit 数据拟合 就能确定幂律动力学模型的系数

## UG10-CH23-D016

PDF page: 341; original JSON pointer: `/4066`

在第二种类型的应用中 Data-Fit 数据拟合 将一个 ASPEN PLUS 模拟结果与装置数

## UG10-CH23-D017

PDF page: 341; original JSON pointer: `/4067`

Data-Fit 数据拟合 找到最吻合测量数据的塔效率 同时 Data-Fit 数据拟合 还能实现

## UG10-CH23-D018

PDF page: 341; original JSON pointer: `/4068`

Data-Fit 数据拟合 是被设计成离线地用于开发一个与可获得数据匹配的 ASPEN PLUS

## UG10-CH23-D019

PDF page: 341; original JSON pointer: `/4069`

模拟模型过程中 Data-Fit 数据拟合 没有被设计成在线装置数据的整和应用

## UG10-CH23-D020

PDF page: 341; original JSON pointer: `/4070`

定义一个 Data-Fit 数据拟合 问题

## UG10-CH23-D021

PDF page: 341; original JSON pointer: `/4071`

1. 建立基本工况 ASPEN PLUS 模型 例如 若要拟合浓度相对时间的动力学数据 则建立一个 Rbatch 模型 你用 Reactions 反应 表页为 Rbatch 模型输入的动力学模型系数便成为 Data-Fit 数据

## UG10-CH23-D022

PDF page: 342; original JSON pointer: `/4073`

2. 建立一个或多个 Data-Fit 数据拟合 数据集 数据集类型 要拟合的数据 POINT-DATA

## UG10-CH23-D023

PDF page: 342; original JSON pointer: `/4074`

PROFILE-DATA l 一个间歇反应器的时间系列数据

## UG10-CH23-D024

PDF page: 342; original JSON pointer: `/4075`

3. 定义回归工况 指定 Data-Fit 数据拟合 工况和所要估算的输入参数 参见本章 定义 Data-Fit 数据拟合 回归工况 建立 Point-Data 点数据 数据集 若建立一个 Point-Data 点数据 数据集

## UG10-CH23-D025

PDF page: 342; original JSON pointer: `/4076`

1. 从 Data 数据 菜单 将鼠标指向 Model Analysis Tools 模型分析工具 然后指 向 Data Fit 数据拟合

## UG10-CH23-D026

PDF page: 342; original JSON pointer: `/4077`

2. 在 Data Browser 数据浏览器 左窗格上 选择 Data-Set 数据集

## UG10-CH23-D027

PDF page: 342; original JSON pointer: `/4078`

3. 在 Data-Set Object Manager 数据集对象管理器 中 单击 New 新建

## UG10-CH23-D028

PDF page: 342; original JSON pointer: `/4079`

4. 在 Create New ID 建立新的标识符 对话框中 输入一个标识符或接受缺省的标 识符

## UG10-CH23-D029

PDF page: 342; original JSON pointer: `/4080`

5. 在 Select Type 选择类型 列表中 选择 Point-Data 点数据 并单击 OK

## UG10-CH23-D030

PDF page: 342; original JSON pointer: `/4081`

6. 在 Define 定义 页面上 标识出你有测量值的流程变量 参见本章 标识流程变 量

## UG10-CH23-D031

PDF page: 342; original JSON pointer: `/4082`

7. 在 Data 数据 页面上 输入测量数据 参见本章输入测量的 Point-Data 点数据 标识流程变量 你必须标识出你拥有其测量值的流程变量 使用 Data-Fit Data-Set Define 数据拟合 数 据集 定义 页面来标识出数据集所用的流程变量 并赋给它们变量名 变量名标识出在其 它数据集页面上的流程变量 使用 Define(定义)页面来标识一个流程变量并赋给它一个变量名 当填完一个 Define 页 面时 在 Variable Definition( 变量定义)对话框中指定变量 Define 定义 页面显示一个关

## UG10-CH23-D032

PDF page: 342; original JSON pointer: `/4083`

于所有存取变量的摘要 但是 你不能在 Define 定义 页面上修改变量

## UG10-CH23-D033

PDF page: 342; original JSON pointer: `/4084`

在 Define 定义 页面上

## UG10-CH23-D034

PDF page: 342; original JSON pointer: `/4085`

1. 若建立一个新变量 单击 New 新建 按扭 或者 若编辑一个现有变量 则选 择一个变量并单击 Edit 编辑 按扭

## UG10-CH23-D035

PDF page: 342; original JSON pointer: `/4086`

2. 在 Variable Name(变量名)字段中输入变量名 如果你编辑一个变量并且要改变变量 名 则在 Variable Name 变量名 字段中单击鼠标右键 在弹出菜单上单击 Rename 重命名 变量名必须符合下列规则

## UG10-CH23-D036

PDF page: 342; original JSON pointer: `/4087`

l 对于一个标变量 必须为 6 个或 6 个以下字符

## UG10-CH23-D037

PDF page: 342; original JSON pointer: `/4088`

l 对于一个矢变量 必须为 5 个或 5 个以下字符

## UG10-CH23-D038

PDF page: 343; original JSON pointer: `/4090`

3. 在 Category 类别 框内 使用选项按扭来选择变量类别

## UG10-CH23-D039

PDF page: 343; original JSON pointer: `/4091`

4. 在 Reference 引用 框内 从 Type 类型 字段内的列表中选变量类型 ASPEN PLUS 还显示完成变量定义所需的其它字段

## UG10-CH23-D040

PDF page: 343; original JSON pointer: `/4092`

5. 单击 Close 关闭 返回 Define 定义 页面 关于存取变量的更详细信息 参见第十八章 访问流程变量 提示 使用 Delete 删除 按扭能够快速删除一个变量及用于定义该变量的所有字段 提示 使用 Edit 编辑 按扭能够修改 Variable Definition 变量定义 对话框中的对某 个变量的定义 流程变量的类型 你必须标识出你拥有其测量值的流程变量 你也可以标识你没有测量数据的结果变量 ASPEN PLUS 将为每个数据点计算结果变量 并将它们制成表

## UG10-CH23-D041

PDF page: 343; original JSON pointer: `/4093`

在 Data-Fit 数据拟合 中你不能访问矢量 你必须按不同的标变量来访问在一个组成

## UG10-CH23-D042

PDF page: 343; original JSON pointer: `/4094`

矢量中的每个物流变量或每个组分 一定要按组分的摩尔 质量或标准体积流量来访问进料

## UG10-CH23-D043

PDF page: 343; original JSON pointer: `/4095`

物流的组成 不要按分率来访问它们 这样避免了由于没归一化分率而引起的任何问题

## UG10-CH23-D044

PDF page: 343; original JSON pointer: `/4096`

对于一些流程变量 你既可访问输入值也可访问结果值 例如 某个 RadFrac 模块的冷

## UG10-CH23-D045

PDF page: 343; original JSON pointer: `/4097`

凝器热负荷既可以作为输入变量 Q1 访问 也可以作为结果变量 COND-DUTY 来访问 其

## UG10-CH23-D046

PDF page: 343; original JSON pointer: `/4098`

再沸器负荷既可以作为输入变量 QN 来访问也可以作为结果变量 REB-DUTY 来访问

## UG10-CH23-D047

PDF page: 343; original JSON pointer: `/4099`

按下列规则来判断选择输入变量还是选择结果变量

## UG10-CH23-D048

PDF page: 343; original JSON pointer: `/4100`

在基本工况中被测量的变量作为一个输入而指定了吗 则选择

## UG10-CH23-D049

PDF page: 343; original JSON pointer: `/4101`

l 你的基本工况模型是由一个 RadFrac 模块组成 在该模块中指定了 Reflux Ratio 回

## UG10-CH23-D050

PDF page: 343; original JSON pointer: `/4102`

对于再沸器负荷 你必须选择结果变量 REB-DUTY 因为在基本工况模型中它没有作

## UG10-CH23-D051

PDF page: 343; original JSON pointer: `/4103`

为一个输入而被指定 对于冷凝器负荷 你必须选择输入变量 Q1 因为在基本工况模型中

## UG10-CH23-D052

PDF page: 343; original JSON pointer: `/4104`

输入测量的 Point-Data 点数据

## UG10-CH23-D053

PDF page: 343; original JSON pointer: `/4105`

使用 Data-Fit Data-Set Data 数据拟合 数据集 数据 页面输入被测量的数据

## UG10-CH23-D054

PDF page: 343; original JSON pointer: `/4106`

1. 在 Data-Fit Data-Set 数据拟合 数据集 表页上 单击 Data 数据 标签

## UG10-CH23-D055

PDF page: 343; original JSON pointer: `/4107`

2. 为 Data-Fit 数据拟合 问题指定变量是一个模拟输入还是模拟结果

## UG10-CH23-D056

PDF page: 344; original JSON pointer: `/4109`

被测量的进料物流 INPUT(输入)

## UG10-CH23-D057

PDF page: 344; original JSON pointer: `/4110`

被测量的产品物流 RESULT 结果

## UG10-CH23-D058

PDF page: 344; original JSON pointer: `/4111`

在 Define 定义 页面上作为输入

## UG10-CH23-D059

PDF page: 344; original JSON pointer: `/4112`

所有其它被测量的变量 RESULT 结果

## UG10-CH23-D060

PDF page: 344; original JSON pointer: `/4113`

注释 中间物流变量通常是结果 但是 当一个 Data-Fit 数据拟合 问题只涉及流程

## UG10-CH23-D061

PDF page: 344; original JSON pointer: `/4114`

的一部分时 你可以将成为 Data-Fit 数据拟合 子问题入口物流的中间物流作为输入

## UG10-CH23-D062

PDF page: 344; original JSON pointer: `/4115`

3. 在数据表的第一行中为测量值指定一个标准偏差

## UG10-CH23-D063

PDF page: 344; original JSON pointer: `/4116`

4. 输入一个或多个数据点 表的行 对于某个 Result 结果 变量 如果你得不到 其测量值 那么将它的 Data 数据 字段为空 Data-Fit 数据拟合 将估算它 对于一个 Input 输入变量 你必须输入一个值 你可以随时引入一个新的标准偏差行 它将用于后面的数据点 标准偏差 标准偏差是测量数据的不可靠程度 你可以按一个绝对偏差或按一个百分数偏差 在值 上加一个%号 输入它 通常很难得到统计确定的标准偏差 你提供一个根据经验或仪器技 术说明估计出的 大致的 期望偏差 便足够了 在平方和函数中的每个剩余 测量值-模

## UG10-CH23-D064

PDF page: 344; original JSON pointer: `/4117`

型预测值 项是通过 1/ 标准偏差 2 加权的 你必须为每个被拟合的结果变量指定一个大

## UG10-CH23-D065

PDF page: 344; original JSON pointer: `/4118`

于零的标准偏差 如果为标准偏差输入了一个零值 则在回归中不包括该结果变量

## UG10-CH23-D066

PDF page: 344; original JSON pointer: `/4119`

对于输入变量 大于零的标准偏差调用了最大似然 变量误差 估算方法

## UG10-CH23-D067

PDF page: 344; original JSON pointer: `/4120`

零 认为测量值准确 并且 Data-Fit 数据拟合 不调整它

## UG10-CH23-D068

PDF page: 344; original JSON pointer: `/4121`

大于零 调整 整合 测量数据及结果测量数据以便匹配被拟合的模型

## UG10-CH23-D069

PDF page: 344; original JSON pointer: `/4122`

注释 整和输入数据可能大大地增加求解时间 因为每个被整

## UG10-CH23-D070

PDF page: 344; original JSON pointer: `/4123`

和的输入数据都由最小平方算法作为一个决策变量处理

## UG10-CH23-D071

PDF page: 344; original JSON pointer: `/4124`

建立 Profile-Data 分布数据 集

## UG10-CH23-D072

PDF page: 344; original JSON pointer: `/4125`

若建立 Profile-Data 分布数据 数据集

## UG10-CH23-D073

PDF page: 344; original JSON pointer: `/4126`

1. 从 Data 数据 菜单 选择 Model Analysis Tools 模型分析工具 然后选择 Data Fit 数据拟合

## UG10-CH23-D074

PDF page: 344; original JSON pointer: `/4127`

2. 在 Data Browser 数据浏览器 左窗格上 选择 Data-Set 数据集

## UG10-CH23-D075

PDF page: 344; original JSON pointer: `/4128`

3. 在 Data-Set Object Manager 数据集对象管理器 中 单击 New 新建

## UG10-CH23-D076

PDF page: 344; original JSON pointer: `/4129`

4. 在 Create New ID 建立新的标识符 对话框中 输入一个标识符或接受缺省的标 识符

## UG10-CH23-D077

PDF page: 344; original JSON pointer: `/4130`

5. 在 Select Type 选择类型 列表中 选择 Profile-Data 分布数据 并单击 OK

## UG10-CH23-D078

PDF page: 344; original JSON pointer: `/4131`

6. 在 Define 定义 页面上 标识出你有测量值的流程变量 参见本章 标识分布数 据变量

## UG10-CH23-D079

PDF page: 344; original JSON pointer: `/4132`

7. 在 Data 数据 页面上 输入测量数据 参见本章 输入测量的 Profile-Data 分

## UG10-CH23-D080

PDF page: 345; original JSON pointer: `/4134`

8. 你可以在 Initial Conditions 初始条件 页面上指定加料 Rbatch 或进料 Rplug 标识分布数据变量 对于 Rbatch 和 Rplug 单元操作模型 可以使用分布数据变量

## UG10-CH23-D081

PDF page: 345; original JSON pointer: `/4135`

1. 在 Data-Set 数据集 表页上 单击 Define 定义 标签

## UG10-CH23-D082

PDF page: 345; original JSON pointer: `/4136`

2. 在 Model and Block Name 模型和模块名 区域内 选择 Rbatch 或 Rplug

## UG10-CH23-D083

PDF page: 345; original JSON pointer: `/4137`

3. 在 Block 模块 字段中 标识出被测量分布数据的模块

## UG10-CH23-D084

PDF page: 345; original JSON pointer: `/4138`

4. 在 Variable Name(变量名)字段中输入一个变量名 变量名必须符合下列规则

## UG10-CH23-D085

PDF page: 345; original JSON pointer: `/4139`

l 对于一个标变量 必须为 6 个或 6 个以下字符

## UG10-CH23-D086

PDF page: 345; original JSON pointer: `/4140`

5. 在 Variable 变量 列表内 选择一个变量 参见关于每个变量描述的提示

## UG10-CH23-D087

PDF page: 345; original JSON pointer: `/4141`

6. 对于浓度或分率分布变量 在 Component 组分 字段中 标识被测量的组分 你必须 按单独的被测量变量标识每个组分的浓度或分率

## UG10-CH23-D088

PDF page: 345; original JSON pointer: `/4142`

7. 对于每个被测量变量重复步骤 4 至 6 你可以标识你没有其测量数据的分布数据变量 Data-Fit 数据拟合 将计算它们并将它们 制表 输入被测量的 Profile-Data 分布数据 使用 Data-Fit Data-Set Data 数据拟合 数据集 数据 页面输入被测量的数据 对于每个被测量的变量

## UG10-CH23-D089

PDF page: 345; original JSON pointer: `/4143`

1. 在 Data-Fit Data-Set 数据拟合 数据集 表页上 单击 Data 数据 标签

## UG10-CH23-D090

PDF page: 345; original JSON pointer: `/4144`

2. 在数据表的第一行中 为每个要被拟合测量值指定一个大于零标准偏差 如果为标 准偏差输入了一个零值 在回归中不包含该结果变量

## UG10-CH23-D091

PDF page: 345; original JSON pointer: `/4145`

3. 为每个数据点输入时间或长度以及测量值 缺少的测量值为空 ASPEN PLUS 将 估算它们 你可以随时引入一个新的标准偏差行 它将用于后面的数据点

## UG10-CH23-D092

PDF page: 345; original JSON pointer: `/4146`

4. 如果你要指定温度和压力值来取代基本工况中的值 在 Initial Conditions 初始条 件 页面中输入这些值 Data-Fit 数据拟合 不整合 调整 这些值 假定它们 是准确的

## UG10-CH23-D093

PDF page: 345; original JSON pointer: `/4147`

5. 如果某个进料或加料的实验数据与基本工况中的数据不同 则在 Profile-Data Initial Condition 分布数据初始条件 页面上指定组分流量 选择基准 Mole/Mass/StdVol 和单位 输入组分流量 ASPEN PLUS 假定你输入的值是准确的 并且不调整它 们 你只能为常规组分指定流量 如果在基本工况模型中指定的进料/加料含有非 常规组分 Data-Fit 数据拟合 将采用下列手段

## UG10-CH23-D094

PDF page: 345; original JSON pointer: `/4148`

l 对于非常规组分 采用基本工况的规定

## UG10-CH23-D095

PDF page: 345; original JSON pointer: `/4149`

l 将本表页上输入的常规组分流量作为反应器的进料/加料

## UG10-CH23-D096

PDF page: 346; original JSON pointer: `/4151`

定义 Data-Fit 数据拟合 回归工况

## UG10-CH23-D097

PDF page: 346; original JSON pointer: `/4152`

你可以在同一个回归工况中拟合 Point-Data 点数据 和 Profile-Data 分布数据 数据

## UG10-CH23-D098

PDF page: 346; original JSON pointer: `/4153`

集 例如 你可能有某个反应器在一个温度下的时间系列数据 Profile-Data 分布数据 并

## UG10-CH23-D099

PDF page: 346; original JSON pointer: `/4154`

有在几个温度下的总转化率数据 Point-Data 点数据

## UG10-CH23-D100

PDF page: 346; original JSON pointer: `/4155`

Data-Fit 数据拟合 回归工况必须至少涉及下列数据之一

## UG10-CH23-D101

PDF page: 346; original JSON pointer: `/4156`

l 一个被整和的输入 具有大于零标准偏差

## UG10-CH23-D102

PDF page: 346; original JSON pointer: `/4157`

当你在 Data-Set Data 数据集 数据 页面上为输入测量值指定非零的标准偏差时

## UG10-CH23-D103

PDF page: 346; original JSON pointer: `/4158`

ASPEN PLUS 调整 整和 被测量的输入变量 对于每个数据点 每个被整和的被测输入

## UG10-CH23-D104

PDF page: 346; original JSON pointer: `/4159`

对于一个被估算参数 你必须已经在模拟工况中作为输入规定为其输入一个值 或者

## UG10-CH23-D105

PDF page: 346; original JSON pointer: `/4160`

它必须有一个缺省值 Data-Fit 数据拟合 使用该规定作为变量的初始估值

## UG10-CH23-D106

PDF page: 346; original JSON pointer: `/4161`

如果基本工况的值处于你在 Regression Vary 回归 改变 页面上为该参数所输入边界 之外 或者处于你为一个被整和的输入参数所输入的边界之外 Data-Fit 数据拟合 采用 最靠近的边界作为初始估值 对于所估算的参数的个数没有限制 对于某个变量 如果其值超出限制将进一步减小平方和函数 Data-Fit 数据拟合 将 让该变量处于其上限或下限 建立 Data-Fit 数据拟合 回归工况 若建立一个 Data-Fit 数据拟合 回归工况

## UG10-CH23-D107

PDF page: 346; original JSON pointer: `/4162`

1. 从 Data 数据 菜单 选择 Model Analysis Tools 模型分析工具 然后选择 Data Fit 数据拟合

## UG10-CH23-D108

PDF page: 346; original JSON pointer: `/4163`

2. 在 Data Browser 数据浏览器 左窗格上 选择 Regression 回归

## UG10-CH23-D109

PDF page: 346; original JSON pointer: `/4164`

3. 在 Regression Object Manager 回归对象管理器 中 单击 New 新建

## UG10-CH23-D110

PDF page: 346; original JSON pointer: `/4165`

4. 在 Create New ID 建立新的标识符 对话框中 输入一个标识符或接受缺省的标 识符

## UG10-CH23-D111

PDF page: 346; original JSON pointer: `/4166`

5. 在 Specifications 规定 页面上 标识出本工况中所要拟合的数据集 参见本章 Point-Data 点数据 数据集和建立 Profile-Data 分布数据 数据集 你还可以提 供用于调整数据集相对加权的加权系数 但是 通常不需要这样做 关于加权系数 的更详细信息 参见数据拟合数值公式

## UG10-CH23-D112

PDF page: 346; original JSON pointer: `/4167`

6. 在 Vary 改变 页面上 标识出你要估算的任何模拟输入参数 Data-Fit 数据拟 合 将调整变量找出与在 Specifications 规定 页面上所列的 Data-Set 数据集 最吻合的参数

## UG10-CH23-D113

PDF page: 346; original JSON pointer: `/4168`

7. 在 Convergence 收敛 页面上 你可以选择在整和输入测量值时所用的 Initialization Method 初始化方法 若初始化被整和输入参数为 采用的初始化方法 基本工况值 Base Case Values 基本工况值 测量值 Measurements 测量值 缺省的基本工况初始化方法是最可靠的方法 但是 如果测量值远离基本工况值 它可能需要更多次迭代

## UG10-CH23-D114

PDF page: 347; original JSON pointer: `/4170`

通常 你不需要改变 Regression Convergence 回归 收敛 页面上的任何其它缺省

## UG10-CH23-D115

PDF page: 347; original JSON pointer: `/4171`

Regression Convergence 回归收敛 页面是用来指定可选的 Data-Fit 数据拟合 收敛

## UG10-CH23-D116

PDF page: 347; original JSON pointer: `/4172`

参数 多数情况下 不需要改变这些参数的缺省值

## UG10-CH23-D117

PDF page: 347; original JSON pointer: `/4173`

在 Convergence 收敛 页面上有下列参数

## UG10-CH23-D118

PDF page: 347; original JSON pointer: `/4174`

50 指定优化器的迭代次数 Maximum Passes Trough Flowsheet 最大流程计 算次数

## UG10-CH23-D119

PDF page: 347; original JSON pointer: `/4175`

1000 设定在一个 Data-Fit 数据拟合 运行中所允许最 大流程计算次数 流程计算次数包括初始基本工 况 计算剩余项所需的次数以及通过扰动计算 Jacobian 矩阵所需的次数 Bound Factor 边界因 子

## UG10-CH23-D120

PDF page: 347; original JSON pointer: `/4176`

10 被整和的输入变量的上下边界是用 Bound Factor 边界因子 乘以该变量的标准偏差来计算的 关于设定 Bound Factor 边界因子 的更详细信息 参见本章 Bound Factor 边界因子 Absolute Function Tolerance 函数绝对允 差 0.01 指定平方和目标函数的绝对允差 如果优化器找到了一个点 在该点处目标函数值小 于 Absolute Function Tolerance 函数绝对允差 则问题收敛 Relative Function

## UG10-CH23-D121

PDF page: 347; original JSON pointer: `/4177`

Tolerance 函数相对允

## UG10-CH23-D122

PDF page: 347; original JSON pointer: `/4178`

0.002 指定函数的相对误差

## UG10-CH23-D123

PDF page: 347; original JSON pointer: `/4179`

X Convergence Tolerance

## UG10-CH23-D124

PDF page: 347; original JSON pointer: `/4180`

0.002 指定 X 收敛允差

## UG10-CH23-D125

PDF page: 347; original JSON pointer: `/4181`

Convergence Tolerance X 收敛允差 并且此步中

## UG10-CH23-D126

PDF page: 347; original JSON pointer: `/4182`

Minimum Step Tolerance

## UG10-CH23-D127

PDF page: 347; original JSON pointer: `/4183`

1e-10 如果在某步中 用最大为 Minimum Step Tolerance

## UG10-CH23-D128

PDF page: 347; original JSON pointer: `/4184`

Data-Fit 数据拟合 则返回次优解

## UG10-CH23-D129

PDF page: 347; original JSON pointer: `/4185`

选取 计算协方差和相关矩阵并将相关矩阵写到报告文

## UG10-CH23-D130

PDF page: 347; original JSON pointer: `/4186`

Regression Advanced 回归 高级 页面是用于指定 Data-Fit 数据拟合 的附加收敛参

## UG10-CH23-D131

PDF page: 347; original JSON pointer: `/4187`

数 多数情况下 不需要改变这些参数的缺省值

## UG10-CH23-D132

PDF page: 348; original JSON pointer: `/4189`

算法给出围绕被改变值矢量当前估值的一个区域的直径的估值 在该区域中算法能预测

## UG10-CH23-D133

PDF page: 348; original JSON pointer: `/4190`

最小平方目标函数的表现性质 该区域即为信任区域 在 Convergence 收敛 页面上可用

## UG10-CH23-D134

PDF page: 348; original JSON pointer: `/4191`

信任区微调参数字段 缺省

## UG10-CH23-D135

PDF page: 348; original JSON pointer: `/4192`

Switching Parameter 切换参数 1.5 Data-Fit 数据拟合 采用了一个信任区策略

## UG10-CH23-D136

PDF page: 348; original JSON pointer: `/4193`

试来确定何时为信任区切换模型

## UG10-CH23-D137

PDF page: 348; original JSON pointer: `/4194`

Reduction Factor 缩减系数 0.5 如果当前的 X 导致函数或 Jacobian 计算错误

## UG10-CH23-D138

PDF page: 348; original JSON pointer: `/4195`

2 用于增加信任区半径的最小系数 Maximum Expansion Factor 最 小膨胀系数

## UG10-CH23-D139

PDF page: 348; original JSON pointer: `/4196`

4 每次可用于增加信任区半径的最大系数 步长及微调参数字段 缺省 值 用途 Initial Step Size 初始步长 1 确定信任区初始步长的系数 对 Initial Step Size 初始步长 的选择能够对 算法性能有很大影响 不同的值有时会导致找 到不同区域的最大值 Initial Step Size 初始步 长 的值太小或太大会使算法在第一次迭代中 花费一些函数计算来增加或减少信任区的大 小 Size Control Parameter 步长控 制参数

## UG10-CH23-D140

PDF page: 348; original JSON pointer: `/4197`

0.0001 对于被接受的步长 实际函数的减少量必须大

## UG10-CH23-D141

PDF page: 348; original JSON pointer: `/4198`

0.005 在变量 X 的 Jacobian 计算过程中 缺省的扰动

## UG10-CH23-D142

PDF page: 348; original JSON pointer: `/4199`

Parameter 假收敛检查参数

## UG10-CH23-D143

PDF page: 348; original JSON pointer: `/4200`

0.1 帮助确定何时检查假收敛并确定何时为当前信

## UG10-CH23-D144

PDF page: 348; original JSON pointer: `/4201`

Data-Fit 数据拟合 数学公式

## UG10-CH23-D145

PDF page: 348; original JSON pointer: `/4202`

Data-Fit 数据拟合 用下列公式求解问题

## UG10-CH23-D146

PDF page: 349; original JSON pointer: `/4204`

Nsets = 在 Regression Specifications 回归规定 页面上指定的数据集个数

## UG10-CH23-D147

PDF page: 349; original JSON pointer: `/4205`

Nri = 被整和的输入变量个数

## UG10-CH23-D148

PDF page: 349; original JSON pointer: `/4206`

Nrr = 测量结果变量个数

## UG10-CH23-D149

PDF page: 349; original JSON pointer: `/4207`

Wi = 在 Regression Specifications 回归规定 页面上指定的数据集 i 的加权系数

## UG10-CH23-D150

PDF page: 349; original JSON pointer: `/4208`

Xp = 矢量或被改变参数

## UG10-CH23-D151

PDF page: 349; original JSON pointer: `/4209`

Xmri = 被整和输入参数的测量值

## UG10-CH23-D152

PDF page: 349; original JSON pointer: `/4210`

Xri = 被整和输入参数的计算值

## UG10-CH23-D153

PDF page: 349; original JSON pointer: `/4211`

Xmrr = 结果变量的测量值

## UG10-CH23-D154

PDF page: 349; original JSON pointer: `/4212`

Xrr = 结果变量的计算值

## UG10-CH23-D155

PDF page: 349; original JSON pointer: `/4213`

Sigma = 为测量变量指定的标准偏差

## UG10-CH23-D156

PDF page: 349; original JSON pointer: `/4214`

数据拟合模块调整被整和的输入变量独立地使每套实验的误差平方和最小

## UG10-CH23-D157

PDF page: 349; original JSON pointer: `/4215`

确认定义完备的 Data-Fit 数据拟合 问题

## UG10-CH23-D158

PDF page: 349; original JSON pointer: `/4216`

本节主要适用于 Point-Data 点数据 数据集

## UG10-CH23-D159

PDF page: 349; original JSON pointer: `/4217`

虽然 Data-Fit 数据拟合 相当灵活 但是你必须确认 Data-Fit 数据拟合 问题是否

## UG10-CH23-D160

PDF page: 349; original JSON pointer: `/4218`

定义完备 Data-Fit 数据拟合 不为你检查这一点 你必须遵循下列两个基本规则

## UG10-CH23-D161

PDF page: 349; original JSON pointer: `/4219`

l 当 Data-Fit 数据拟合 评价一个数据点时 它将被测量输入和被估算参数的当前

## UG10-CH23-D162

PDF page: 349; original JSON pointer: `/4220`

值与基本工况规定值合并 为了避免产生错误结果 对应一个数据集的这套被测量

## UG10-CH23-D163

PDF page: 349; original JSON pointer: `/4221`

输入值必须形成一个完整的输入规定以便唯一地为该数据集计算被测结果

## UG10-CH23-D164

PDF page: 349; original JSON pointer: `/4222`

l 即使测量值没有构成质量平衡和能量平衡 基本工况模拟模型也必须设计成有一个

## UG10-CH23-D165

PDF page: 349; original JSON pointer: `/4223`

一个定义完备的 Data-Fit 数据拟合 问题的示例

## UG10-CH23-D166

PDF page: 349; original JSON pointer: `/4224`

进料数据是由组分摩尔流率和温度构成 产品物流数据只由总流和温度构成

## UG10-CH23-D167

PDF page: 349; original JSON pointer: `/4225`

下表列出了对于该问题的一个完备的 Data-Fit 数据拟合 定义

## UG10-CH23-D168

PDF page: 350; original JSON pointer: `/4227`

基本工况模拟模型 l 一个规定了温度 压力和组分摩尔流量的进料物流

## UG10-CH23-D169

PDF page: 350; original JSON pointer: `/4228`

l 一个规定了摩尔回流比 塔顶馏出物与进料的摩尔比及压力

## UG10-CH23-D170

PDF page: 350; original JSON pointer: `/4229`

操作点的数据集 输入变量

## UG10-CH23-D171

PDF page: 350; original JSON pointer: `/4230`

l 塔顶馏出物与进料的比 它作为 RadFrac 的摩尔 D:F 输入变

## UG10-CH23-D172

PDF page: 350; original JSON pointer: `/4231`

量访问 并在数据集中按一个未测得输入参数而输入

## UG10-CH23-D173

PDF page: 350; original JSON pointer: `/4232`

对于该问题 压力和摩尔回流比是不变的规定 对于每个数据点计算 Data-Fit 数据

## UG10-CH23-D174

PDF page: 350; original JSON pointer: `/4233`

拟合 替代基本工况的进料组分的流率 温度及塔的馏出物与进料比的规定值 如果数据集

## UG10-CH23-D175

PDF page: 350; original JSON pointer: `/4234`

中省略了任何输入 则把基本工况值用于数据点计算 这将产生不正确的结果

## UG10-CH23-D176

PDF page: 350; original JSON pointer: `/4235`

必须使用馏出物与进料的比的规定以便在任何进料下 RadFrac 都能求解 如果用馏出物

## UG10-CH23-D177

PDF page: 350; original JSON pointer: `/4236`

流量规定来代替该规定 那么 与测量的进料量没有很好的质量平衡的馏出物流量测量值将

## UG10-CH23-D178

PDF page: 350; original JSON pointer: `/4237`

导致由不合理的塔规定 致使 RadFrac 不能求解

## UG10-CH23-D179

PDF page: 350; original JSON pointer: `/4238`

当你为被测量的输入变量指定非零的标准偏差时 Data-Fit 数据拟合 将对变量估值

## UG10-CH23-D180

PDF page: 350; original JSON pointer: `/4239`

边界系数的缺省值是 10 你可以在 Regression Convergence 回归收敛 页面上输入一

## UG10-CH23-D181

PDF page: 350; original JSON pointer: `/4240`

ASPEN PLUS 检查流量的下限是否是负值 如果是的话 则给出一个警告并将下限设

## UG10-CH23-D182

PDF page: 350; original JSON pointer: `/4241`

为零 在设置边界系数时要注意以免出现零流率

## UG10-CH23-D183

PDF page: 350; original JSON pointer: `/4242`

记住 将边界设置的太紧或太松都将使 Data-Fit 数据拟合 移到一个不合理的区域

## UG10-CH23-D184

PDF page: 350; original JSON pointer: `/4243`

例如 如果你整和一个塔的回流量并用回流量作为一个被整和的输入变量 并且 你允许回 流量的下限为零 那么 在求解过程中 Data-Fit 数据拟合 可能使得回流量为零 从而 引起 RadFrac 的严重错误 你可以将被整和的输入变量作为固定值 从而不用将它们的边界 设的太紧 估算未测量的变量 Data-Fit 数据拟合 可以估算任何未测量的结果 并将它们制表 在一个数据集中按 一个结果变量来访问被计算变量 输入一个非零标准偏差 并使数据字段为空

## UG10-CH23-D185

PDF page: 350; original JSON pointer: `/4244`

Data-Fit 数据拟合 还可以估算未测量的输入变量 在一个数据集中按一个输入变量

## UG10-CH23-D186

PDF page: 350; original JSON pointer: `/4245`

来访问变量 为该变量输入一个合理的初始估值和一个大的标准偏差 例如 50% 确认

## UG10-CH23-D187

PDF page: 351; original JSON pointer: `/4247`

排列 Data-Fit 数据拟合 计算顺序

## UG10-CH23-D188

PDF page: 351; original JSON pointer: `/4248`

对于 Data-Fit 数据拟合 问题 ASPEN PLUS 将做以下工作

## UG10-CH23-D189

PDF page: 351; original JSON pointer: `/4249`

l 执行 Data-Fit 数据拟合 回路计算直到它收敛或收敛失败

## UG10-CH23-D190

PDF page: 351; original JSON pointer: `/4250`

l 用回归出的值替代基本工况中的被拟合参数的值 并重新运行基本工况模拟

## UG10-CH23-D191

PDF page: 351; original JSON pointer: `/4251`

如果有工况研究或灵敏度分析模块存在 ASPEN PLUS 用被拟合的参数来生成工况研 究和/或灵敏度分析表 每次不重新执行 Data-Fit 数据拟合 问题 ASPEN PLUS 的自动排序算法将 Data-Fit 数据拟合 回路放到任何流程收敛回路之外 多数情况下 用独立运行 Data-Fit 数据拟合 例如 你可能要用 RCSTR 模块估算幂 律表达式的动力学系数 运行具有 RCSTR 的 Data-Fit 数据拟合 然后在一个具有该 RCSTR

## UG10-CH23-D192

PDF page: 351; original JSON pointer: `/4252`

模块的大流程中把回归出的值用作输入值

## UG10-CH23-D193

PDF page: 351; original JSON pointer: `/4253`

你可以在 Convergence Sequence 收敛排序 表页上人工排列执行顺序以便适合你的需

## UG10-CH23-D194

PDF page: 351; original JSON pointer: `/4254`

使用 Data-Fit 数据拟合 结果

## UG10-CH23-D195

PDF page: 351; original JSON pointer: `/4255`

主要的 Data-Fit 数据拟合 结果如下

## UG10-CH23-D196

PDF page: 351; original JSON pointer: `/4256`

结果 所在的 Data-Fit 数据拟合 页面

## UG10-CH23-D197

PDF page: 351; original JSON pointer: `/4257`

拟合的 Chi-平方统计数据 Regression Results Summary 回归结果一览

## UG10-CH23-D198

PDF page: 351; original JSON pointer: `/4258`

被估算参数的最终估值和标准偏差 Regression Results Manipulated Variable 回归结

## UG10-CH23-D199

PDF page: 351; original JSON pointer: `/4259`

Regression Results Fitted -Data 回归结果 拟合

## UG10-CH23-D200

PDF page: 351; original JSON pointer: `/4260`

函数结果 或改变结果及被整和的输入的

## UG10-CH23-D201

PDF page: 351; original JSON pointer: `/4261`

Regression Results Iteration History 回归结果

## UG10-CH23-D202

PDF page: 351; original JSON pointer: `/4262`

大于限阈值的 Chi-平方值表示模型不与数据拟合 这可能是由于测量数据错误 或者

## UG10-CH23-D203

PDF page: 351; original JSON pointer: `/4263`

模型不能很好地模拟这些数据 你可以用 Chi-平方统计数据来选择模型 如果你用相同数据

## UG10-CH23-D204

PDF page: 351; original JSON pointer: `/4264`

查看 Regression Results Fitted -Data 回归结果 拟合的数据 页面上的是否有大的归一

## UG10-CH23-D205

PDF page: 351; original JSON pointer: `/4265`

量输入变量 没有被估算值和残差 Data-Fit 数据拟合 不调整这些测量值

## UG10-CH23-D206

PDF page: 351; original JSON pointer: `/4266`

在 Regression Results Fitted -Data 回归结果 拟合的数据 页面上 你可以将结果绘成

## UG10-CH23-D207

PDF page: 351; original JSON pointer: `/4267`

关于生成曲线的更详细信息 参见第十三章

## UG10-CH23-D208

PDF page: 351; original JSON pointer: `/4268`

如果 Data-Fit 数据拟合 不收敛 则查找下列内容

## UG10-CH23-D209

PDF page: 352; original JSON pointer: `/4270`

l 输入测量值过程中的大错误 例如 数据输入错误或不正确的单位

## UG10-CH23-D210

PDF page: 352; original JSON pointer: `/4271`

在设计问题时可能发生错误 请检查下列内容

## UG10-CH23-D211

PDF page: 352; original JSON pointer: `/4272`

l 被测量的输入完整地确定被测量的结果吗 参见本章 确认定义完备地 Data-Fit 数据

## UG10-CH23-D212

PDF page: 352; original JSON pointer: `/4273`

l 基本工况模拟是否被定义成能够处理没有很好的质量平衡的被测量数据 参见本章 确

## UG10-CH23-D213

PDF page: 352; original JSON pointer: `/4274`

认定义完备地 Data-Fit 数据拟合 问题

## UG10-CH23-D214

PDF page: 352; original JSON pointer: `/4275`

l 在基本工况模拟中所规定的值为被估算参数提供很好的估值了吗

## UG10-CH23-D215

PDF page: 352; original JSON pointer: `/4276`

l 被估算参数在整个指定范围内影响被测变量吗 你可以运行一个灵敏度分析来检查被

## UG10-CH23-D216

PDF page: 352; original JSON pointer: `/4277`

l 所指定的边界允许决策变量把模型带到不合理的区域 导致单元操作模型算法或内部收

## UG10-CH23-D217

PDF page: 352; original JSON pointer: `/4278`

l 被拟合的参数在数量级上有很大差别吗 如果是的话 使用一个 Fortran 模块将有助于

## UG10-CH23-D218

PDF page: 352; original JSON pointer: `/4279`

l 模型能够很好地模拟数据吗 如果不是的话 或是选择另一个模型或是输入一个新的基

## UG10-CH23-D219

PDF page: 352; original JSON pointer: `/4280`

该问题的备份文件在示例库中 名为 datafit1.bkp

## UG10-CH23-D220

PDF page: 352; original JSON pointer: `/4281`

600 秒 0.30149 0.19745

## UG10-CH23-D221

PDF page: 352; original JSON pointer: `/4282`

900 秒 0.25613 未测

## UG10-CH23-D222

PDF page: 352; original JSON pointer: `/4283`

1900 秒 0.14938 0.45820 基本工况模拟用下列规定来定义 进料 流率 ALLYL 0.05 lb/hr ACET 0.07lb/hr Rbatch 规定 值 反应器类型 恒温 温度 30.0°C 反应周期 1900.0 秒 反应的相态 只是液相 幂律动力学规定 值 ALLYL幂指数 1.0 ACET 幂指数 0.5

## UG10-CH23-D223

PDF page: 353; original JSON pointer: `/4285`

在一个 Profile-Data 分布数据 数据集内输入时间系列数据

## UG10-CH23-D224

PDF page: 354; original JSON pointer: `/4287`

因为只有在一个温度下所得到的数据 所以 指前因子与不变的活化能拟合 必须按下

## UG10-CH23-D225

PDF page: 355; original JSON pointer: `/4289`

在运行 Data-Fit 数据拟合 问题之后 指前因子的结果值在 Regression Results

## UG10-CH23-D226

PDF page: 355; original JSON pointer: `/4290`

Manipulated Variable 回归 结果 操作变量 页面上出现

## UG10-CH23-D227

PDF page: 355; original JSON pointer: `/4291`

Regression Results Fitted-Data 回归 结果 拟合数据 页面上显示原测量值以及这些变

## UG10-CH23-D228

PDF page: 356; original JSON pointer: `/4293`

将塔的 Murphree 板效率与操作数据拟合 该问题的备份文件在示例库中 名为 datafit2.bkp

## UG10-CH23-D229

PDF page: 356; original JSON pointer: `/4294`

运行 1 运行 2 运行 3

## UG10-CH23-D230

PDF page: 356; original JSON pointer: `/4295`

基本工况模拟用下列规定定义

## UG10-CH23-D231

PDF page: 356; original JSON pointer: `/4296`

RadFrac 规定 值

## UG10-CH23-D232

PDF page: 357; original JSON pointer: `/4298`

即使测量的进料与塔顶馏出物流量质量不平衡 塔的规定 回流比和塔顶馏出物与进料

## UG10-CH23-D233

PDF page: 357; original JSON pointer: `/4299`

该例中定义了一个 Fortran 模块来设定塔的板效率并且该模块就在 RadFrac 模块之前执

## UG10-CH23-D234

PDF page: 357; original JSON pointer: `/4300`

行 该 Fortran 模块读取一个被 Data-Fit 数据拟合 改变的参数并将该参数传递给塔的第

## UG10-CH23-D235

PDF page: 357; original JSON pointer: `/4301`

一和最后板的效率 RadFrac 自动将该效率用于所有中间板

## UG10-CH23-D236

PDF page: 357; original JSON pointer: `/4302`

Point-Data 点数据 数据集如下

## UG10-CH23-D237

PDF page: 357; original JSON pointer: `/4303`

的标准偏差 该规定告诉 Data-Fit 数据拟合 对于每个数据点根据需要来改变塔顶馏出物

## UG10-CH23-D238

PDF page: 357; original JSON pointer: `/4304`

被估算的未测量的输入变量 塔顶馏出物和塔底馏出物的流率作为测量结果对待 这样确保

## UG10-CH23-D239

PDF page: 358; original JSON pointer: `/4306`

对于每个 Data-Fit 数据拟合 数据点塔都有合理的解

## UG10-CH23-D240

PDF page: 358; original JSON pointer: `/4307`

被测量的塔顶馏出物和塔底馏出物的流率可能已作为一个输入参数 RadFrac 规定 被

## UG10-CH23-D241

PDF page: 358; original JSON pointer: `/4308`

使用 但是 如果流率测量值中有大的误差并且质量不平衡 RadFrac 将不能找到解

## UG10-CH23-D242

PDF page: 358; original JSON pointer: `/4309`

Data-Fit 数据拟合 回归工况定义如下

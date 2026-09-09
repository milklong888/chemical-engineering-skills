# UG10-CH06 Detail Operation Index - 第6章 规定组分

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH06-D001

PDF page: 69; original JSON pointer: `/970`

本章说明在模拟中怎样去定义组分 包括的信息为

## UG10-CH06-D002

PDF page: 69; original JSON pointer: `/971`

l 规定数据库和非数据库组分

## UG10-CH06-D003

PDF page: 69; original JSON pointer: `/972`

l 增加 删除和修改组分

## UG10-CH06-D004

PDF page: 69; original JSON pointer: `/973`

l 生成电解质组分和反应

## UG10-CH06-D005

PDF page: 69; original JSON pointer: `/974`

l 规定超临界(HENRY)组分

## UG10-CH06-D006

PDF page: 69; original JSON pointer: `/975`

l 规定 UNIFAC官能团

## UG10-CH06-D007

PDF page: 69; original JSON pointer: `/976`

使用这些窗口规定组分信息: 窗口 页 规定的是什么 Specifications Selection Petroleum Nonconventional Databanks 在模拟中使用的所有组分 分析 混合和虚拟组分 非常规组分 查找物性参数的纯组分库 Assay/Blend Petro Characterization - 分析和混合 更详细的内容 参见第 三十二章 虚拟组分特性 更详细的内容 参见 第三十二章 Pseudocomponents 虚拟组分数据 更详细的内容 参见 第三十二章

## UG10-CH06-D008

PDF page: 69; original JSON pointer: `/977`

Attr-Comps Selection 给出常规组分的组分属性

## UG10-CH06-D009

PDF page: 69; original JSON pointer: `/978`

Henry components

## UG10-CH06-D010

PDF page: 69; original JSON pointer: `/979`

UNIFAC Groups Selection UNIFAC官能团

## UG10-CH06-D011

PDF page: 69; original JSON pointer: `/980`

Comp-Group - 看作一个单元的撕裂流收敛的组分组

## UG10-CH06-D012

PDF page: 69; original JSON pointer: `/981`

浏览可用的纯组分数据库 浏览或改变一个模拟可以用的数据库

## UG10-CH06-D013

PDF page: 69; original JSON pointer: `/982`

1. 从 Data(数据)菜单中 单击 Components 组分

## UG10-CH06-D014

PDF page: 69; original JSON pointer: `/983`

2. 在 Specifications(规定)窗口中 单击 Databanks 数据库 页 ASPEN PLUS 在这 个页中按 Selected Databanks(选择的数据库)列表的顺序查找数据库 缺省的顺序适 合多数的模拟

## UG10-CH06-D015

PDF page: 69; original JSON pointer: `/984`

3. 在这个模拟中改变数据库的查找顺序 在 Selected Databanks(选择的数据库)列表中 单击数据库 然后单击上和下箭头键在列表中移动数据库的上部分或下部分

## UG10-CH06-D016

PDF page: 70; original JSON pointer: `/986`

4. 你可以从 Available Databanks 可用的数据库 列表中选择另外的数据库 并使用 右键头按钮把它们加到 Selected Databanks(选择的数据库)列表中

## UG10-CH06-D017

PDF page: 70; original JSON pointer: `/987`

正文待来源表达/OCR边界复核；原文本 SHA256: `913bf2c6a630398535008963ba3d055020616334ffb5647c5bcb4a9a411d814c`。

## UG10-CH06-D018

PDF page: 70; original JSON pointer: `/988`

COMBUST 燃烧物的纯组分参数 ,包括自

## UG10-CH06-D019

PDF page: 70; original JSON pointer: `/989`

对于定制数据库缺省顺序的资料 参见第十六章

## UG10-CH06-D020

PDF page: 70; original JSON pointer: `/990`

l 保证你的模拟至少包含一个组分

## UG10-CH06-D021

PDF page: 70; original JSON pointer: `/991`

l 对每个组分标识一个组分 ID 标识符 这个 ID 将与后面的输入报表 结果报表

## UG10-CH06-D022

PDF page: 70; original JSON pointer: `/992`

1. 从 Data(数据)菜单 单击 Components(组分)

## UG10-CH06-D023

PDF page: 70; original JSON pointer: `/993`

2. 在 Selection 页的 Component ID(组分标识符)框中 输入一个你要加的 ID 标识符 每个组分必须有一个 Component ID(组分标识符) 在数据库中发现准确 的匹配了吗 然后 ASPEN PLUS 是的 填上分子式和组分名 省略余下的步骤 如果你选择了不检索数据 用倒格键删除分子式或组分名 否 如果你要从数据库中检索数据 必须输入分子式或组分名 规定分子式或你自己的组分名 执行步骤 3 使用 Find 查找 ,单击 Find 查找 按钮 并执行步骤 4

## UG10-CH06-D024

PDF page: 71; original JSON pointer: `/995`

3 这个表列出了发生的结果 如果你输入一个 并且一个恰当的匹配是 那么 ASPEN PLUS 分子式 Found 填上 Component Name 组分名 如 果你还没有做的话 你必须规定 Component ID(组分标识符) 省略余下 的步骤 分子式 Not found 显示带有部分匹配结果的 Find 查找 对话框 参见步骤 4 使用 Find 查找 对话框 省略余下的步骤 组分名 Found 填上 Formula(分子式) 如果你还没有

## UG10-CH06-D025

PDF page: 71; original JSON pointer: `/996`

做的话 你必须规定 Component ID(组

## UG10-CH06-D026

PDF page: 71; original JSON pointer: `/997`

组分名 Not found 显示部分匹配结果的 Find 查找 对

## UG10-CH06-D027

PDF page: 71; original JSON pointer: `/998`

4. 使用 Find 查找 对话框输入你的组分查找的原则 在 Name 组分名 或 Formula 分子式 页上 你可以查找组分名或分子式中包含的 字符串 使用 Advanced 页 输入下面这些项的任何一组 用于查找组分 如果你输入一个 那么 ASPEN PLUS查找 组分名或分子式 包括组分名或分子式一部分的字符串中任意组分 仅匹配组分开头这个字符 串 包括组分名或分子式开头的字符串的任何组分 组分类型 在组分类别中的组分 分子量 在分子量范围内的组分 沸点 在沸程内的组分 CAS 号 Chemical Abstract Service(化学文摘服务)登记号的组分

## UG10-CH06-D028

PDF page: 71; original JSON pointer: `/999`

5. 单击 Find Now 按钮显示符合你查找原则的所有组分 然后从列表中选择一个组分 并单击 Add 把它加到组分列表中 单击这里去看一个使用 Find 的例子

## UG10-CH06-D029

PDF page: 71; original JSON pointer: `/1000`

6. 当你完成查找组分时 单击 Close(关闭)返回到 Selection 页 建立你的模拟时 你随时都可以返回到 Components Specifications Selection 页 增 加或删除组分 规定组分例子 在这个例子中 组分 CH4 的 Formula 分子式 和 Component Name 组分名 是自动 从数据库检索的 组分 CH4 和 C4H10 的数据是从数据库中检索的 组分 C3 是非数据库组 分

## UG10-CH06-D030

PDF page: 72; original JSON pointer: `/1002`

使用 Find Dialog Box 查找对话框 的例子

## UG10-CH06-D031

PDF page: 72; original JSON pointer: `/1003`

在这个例子中 组分 Find 查找 对话框用于查出在分子式中包括 C3 并且沸点在 200

## UG10-CH06-D032

PDF page: 72; original JSON pointer: `/1004`

1. 在 Components Specifications Selection 页中 选择一个空的组分 ID 字段 然后单击 Find

## UG10-CH06-D033

PDF page: 72; original JSON pointer: `/1005`

2. 在 Component Name 组分名 或 Formula 分子式 框中 输入 C3

## UG10-CH06-D034

PDF page: 72; original JSON pointer: `/1006`

3. 选择 Advanced 页 你可根据化学类型 分子量范围 沸程和 CAS 号查找组分

## UG10-CH06-D035

PDF page: 72; original JSON pointer: `/1007`

4. 在 Boiling Point 沸点 框中 输入沸点为 200 250K

## UG10-CH06-D036

PDF page: 72; original JSON pointer: `/1008`

5. 单击 Find Now ASPEN PLUS 根据组分名或分子式中含有 C3 这个字符和沸点 200 250K 来查找组分 库 然后在窗口的底半部显示结果

## UG10-CH06-D037

PDF page: 72; original JSON pointer: `/1009`

6. 包括你模拟中查找结果的组分 从列表中选择组分名 然后单击 Add 从 Find 查 找 对话框你可以继续选择组分名 单击 Add 按钮从查找结果中选择多个组分并 把它们加到你的模拟中 你也可以修改你的查找标准 单击 Find Now 再去生成新 的查找结果

## UG10-CH06-D038

PDF page: 72; original JSON pointer: `/1010`

7. 当完成后 单击 Close 关闭 返回到 Components Specifications Selection 页

## UG10-CH06-D039

PDF page: 73; original JSON pointer: `/1012`

定义一个不在数据库中的组分

## UG10-CH06-D040

PDF page: 73; original JSON pointer: `/1013`

1. 从 Data 菜单中 单击 Component

## UG10-CH06-D041

PDF page: 73; original JSON pointer: `/1014`

2. 在 Specifications Selection 页上 只输入 Component ID 组分标识符

## UG10-CH06-D042

PDF page: 73; original JSON pointer: `/1015`

3. 如果 ASPEN PLUS在数据库中找到一个与你输入的 ID 相匹配的组分 删除 Formula 或 Component Name 那么 ASPEN PLUS 就会把这个组分作为一个非数据库组分

## UG10-CH06-D043

PDF page: 73; original JSON pointer: `/1016`

4. 你必须提供所有非数据库组分需要的物性参数 你可以使用 Properties Data 物性 数据 和 Parameters 参数 窗口提供你自己的参数 -或- 用下面的一种或两种方法组成用户输入的参数和数据

## UG10-CH06-D044

PDF page: 73; original JSON pointer: `/1017`

l Property Estimation 物性估算 使用 Properties Estimation 窗口估算所需的参

## UG10-CH06-D045

PDF page: 73; original JSON pointer: `/1018`

l Data Regression 数据回归 使用 Properties Regression 窗口回归数据 得到参

## UG10-CH06-D046

PDF page: 74; original JSON pointer: `/1020`

提示 使用 User Defined Component Wizard 用户定义的智能工具 帮助你输入一些一

## UG10-CH06-D047

PDF page: 74; original JSON pointer: `/1021`

使用用户定义的组分智能工具

## UG10-CH06-D048

PDF page: 74; original JSON pointer: `/1022`

你可以使用 User Defined Component Wizard 用户定义的智能工具 定义常规组分 固

## UG10-CH06-D049

PDF page: 74; original JSON pointer: `/1023`

体组分和非常规组分所需的物性 你随时都可以修改提供的参数 通过返回 User Defined

## UG10-CH06-D050

PDF page: 74; original JSON pointer: `/1024`

Component Wizard 用户定义的智能工具 或通过将要保存数据的窗口

## UG10-CH06-D051

PDF page: 74; original JSON pointer: `/1025`

使用这个工具定义不在任何纯组分数据库中的组分 你可以定义常规组分 固体组分和

## UG10-CH06-D052

PDF page: 74; original JSON pointer: `/1026`

非常规组分 它也帮助你输入组分一般适用的数据 例如分子量 标准沸点 蒸汽压和热容

## UG10-CH06-D053

PDF page: 74; original JSON pointer: `/1027`

提示 你也可以在 Components Specifications Selection 页选择一个数据库 给它一个不

## UG10-CH06-D054

PDF page: 74; original JSON pointer: `/1028`

同的化学分子式 这个特殊的分子式可以用于标识在用户定义的子程序中的组分 这就允许

## UG10-CH06-D055

PDF page: 74; original JSON pointer: `/1029`

打开 User Defined Component Wizard 用户定义的智能工具

## UG10-CH06-D056

PDF page: 74; original JSON pointer: `/1030`

1. 从 Data 菜单 单击 Components

## UG10-CH06-D057

PDF page: 74; original JSON pointer: `/1031`

2. 在 Specifications Selection 页 单击 User Defined 按钮 User Defined Component Wizard 用户定义的智能工具 出现 提示 关于智能工具的帮助 单击向导对话框右角处的 What’s This 按钮 然后单击它 的任何部分 定义一个常规组分 定义一个常规组分 打开用户定义的智能工具 然后

## UG10-CH06-D058

PDF page: 74; original JSON pointer: `/1032`

1. 输入 Component ID 流程中的每个组分都必须有一个 Component ID 这个 ID 通常 表示整个模拟的某一组分

## UG10-CH06-D059

PDF page: 74; original JSON pointer: `/1033`

2. 从 Type 列表中 单击 Coventional

## UG10-CH06-D060

PDF page: 75; original JSON pointer: `/1035`

3. 可选地输入一个组分的分子式 分子式可以标识在用户定义的物性或单元操作模型 子程序中的组分 如果组分的分子式在 ASPEN PLUS 数据库中存在 那么会出现 一个警告信息

## UG10-CH06-D061

PDF page: 75; original JSON pointer: `/1036`

5. 在 Conventional Components Basic Data 常用的组分基本数据 上相应的框中输入 分子量和标准沸点 分子结构 分子量和标准沸点都是官能团贡献法和相应的状态方程法估算物性所需的最 基本的数据 分子量在所有模拟中都是必须的 如果分子结构是后输入的 模拟中使用的分子量能够 从原子数计算出来 标准沸点在物性计算中本来是不需要的 但是它用于估算很多其它参数例如临界温度和 临界压力 是应该输入的

## UG10-CH06-D062

PDF page: 75; original JSON pointer: `/1037`

6 可选择地输入下表中显示的数据 这个数据能够在后面的 Properties Parameters Pure Compoent USRDEF-1 窗口上找到 物性 信息 在 60°F 时比重 SG 标准生成焓 DHFORM 主要模拟包含能量平衡计算 因此焓是必须的 在 25°C 时理想气体标准生成焓用于焓的计算 但 是 如果模拟中有化学反应 它是不需要的 因为 DHFORM 缺省为零 标准生成吉布斯能 DGFORM 输入 25°C 时理想气体的标准生成吉布斯能

## UG10-CH06-D063

PDF page: 75; original JSON pointer: `/1038`

DGFORM 如果二者之一

## UG10-CH06-D064

PDF page: 75; original JSON pointer: `/1039`

7 如果你希望输入另外的物性数据 例如分子结构 蒸汽压或理想气体热容数据 单 击 Next 工具将帮助你输入物性数据 物性参数和分子结构或活化物性估算 -或- 单击 Finish 完成 保存你输入的数据 并退出向导

## UG10-CH06-D065

PDF page: 75; original JSON pointer: `/1040`

8 如果你单击了 Next 输入另外的物性数据 这个对话框出现

## UG10-CH06-D066

PDF page: 76; original JSON pointer: `/1042`

9 单击按钮输入另外的物性或数据 下面这个表提供了有关物性和数据的信息 类型 说明 分子结构 组分分子结构 对于所有用官能团贡献法分子结构是必需的 用于估算缺少的物 性参数 如果你输入分子结构 你也应该通过选择 Estimate All Missin g Parameters From Molecular Structure 复选框要求估算参数 如果需要 在下面的 Properties Molecular Structure 窗口上可以修

## UG10-CH06-D067

PDF page: 76; original JSON pointer: `/1043`

改分子结构 关于输入分子结构或 Property Estimation 物性估算

## UG10-CH06-D068

PDF page: 76; original JSON pointer: `/1044`

蒸汽压数据 蒸汽压数据用于使用 Data 方法从 Property Estimation 物性估算

## UG10-CH06-D069

PDF page: 76; original JSON pointer: `/1045`

如果你输入蒸汽压数据 你也应该要求通过选择 Estimate Al l Missing Parameters From Molecular Structure 复选框估算参数 你输入的数据以后也可以在 Properties Data 窗口上修改 使用你 定义的名称 蒸汽压数据也可以和 Data Regression 一起使用 关于输入纯组分 数据或 Data Regression 的信息 参见第三十一章 扩展的 Antoine 蒸汽压系数 扩展的 Antoine 蒸汽压方程 PLXANT 系数

## UG10-CH06-D070

PDF page: 76; original JSON pointer: `/1046`

这些参数以后可以在 Properties Parameters Pure Compents

## UG10-CH06-D071

PDF page: 76; original JSON pointer: `/1047`

PLXANT-1 窗口上修改 关于输入或修改物性参数的详细信息

## UG10-CH06-D072

PDF page: 76; original JSON pointer: `/1048`

理想气体热容数据用于从 Proterty Estimation 中使用 Data 方法来

## UG10-CH06-D073

PDF page: 77; original JSON pointer: `/1050`

如果你输入理想气体比热数据 你也应该要求通过选择 Estimate All Missing Parameters From Molecular Structure 复选框估算参数 你输入的数据以后也可以在 Properties Data 窗口上修改 使用你 定义的名称 蒸汽压数据也可以和 Data Regression 一起使用 关于输入纯组分 数据或 Data Regression 的信息 参见第三十一章 理想气体热容多 项式系数 理想气体热容方程 CPIG 系数

## UG10-CH06-D074

PDF page: 77; original JSON pointer: `/1051`

这些参数以后也可以在 Properties Patameters Pure Components

## UG10-CH06-D075

PDF page: 77; original JSON pointer: `/1052`

CPIG-1 窗口上修改 关于输入或修改物性参数更详细的信息 参

## UG10-CH06-D076

PDF page: 77; original JSON pointer: `/1053`

10 可选择地选 Estimate All Missing Parameters From Molecular Structure 复选框

## UG10-CH06-D077

PDF page: 77; original JSON pointer: `/1054`

11 单击 Finish 完成 关闭 返回 Components Specifications Selection 页 定义一个固体组分 定义一个固体组分的步骤几乎和定义常规组分的步骤一样 你必须按上述步骤 2 从 Type 列表中选择 Solid 固体 你可以输入的数据类型或参数是与固体组分有关的 标准沸点在物性计算中本来是不需要的 但是它用于估算很多其它参数例如临界温度和 临界压力 如果你知道一个经验的标准沸点 应该输入它 由于多数模拟包含能量平衡计算 所以焓是必须的 Solid 固体的焓的窗口 DHSFRM

## UG10-CH06-D078

PDF page: 77; original JSON pointer: `/1055`

用于焓计算 如果模拟中没有化学反应 焓不是必须的 因为 DHSFRM 缺省为零

## UG10-CH06-D079

PDF page: 77; original JSON pointer: `/1056`

定义一个非常规组分 打开 User Defined Component 用户定义的组分 工具 然后

## UG10-CH06-D080

PDF page: 77; original JSON pointer: `/1057`

1. 输入 Component ID 流程中的每个组分都必须有一个 Component ID 这个 ID 通常 表示整个模拟的组分

## UG10-CH06-D081

PDF page: 77; original JSON pointer: `/1058`

2. 从 Type 列表中选择 Nonconventional

## UG10-CH06-D082

PDF page: 77; original JSON pointer: `/1059`

4. 从相应的 Enthalpy 焓 和 Density 密度 列表中选择 Enthalpy 焓 和 Density 密度 模型 选择模型所需的组分属性列在模型选项的下面 关于非常规组分物性更详细的资料 参见第七章

## UG10-CH06-D083

PDF page: 77; original JSON pointer: `/1060`

5. 单击 Finish 关闭工具并返回到 Components Specifications Selection 页 你输入的非常用物性规定保存在下面的 Properties Advanced NC-Props 窗口上 增加一个组分 把一个组分加到现存的组分列表中

## UG10-CH06-D084

PDF page: 77; original JSON pointer: `/1061`

1. 从 Data 菜单 单击 Components

## UG10-CH06-D085

PDF page: 77; original JSON pointer: `/1062`

2. 在 Specifications Selection 页中 移到第一个空行上

## UG10-CH06-D086

PDF page: 77; original JSON pointer: `/1063`

3. 输入 Component ID 组分标识符 组分名或分子式

## UG10-CH06-D087

PDF page: 77; original JSON pointer: `/1064`

4. 如果你希望在列表内移动组分 做下面的两步 单击 Reorder 按钮 打开 Reorder Components 对话框

## UG10-CH06-D088

PDF page: 77; original JSON pointer: `/1065`

5. 选择新的组分 用向上箭头顺序地把它向上移动到组分列表的右侧

## UG10-CH06-D089

PDF page: 78; original JSON pointer: `/1067`

1 从 Data 菜单 单击 Components

## UG10-CH06-D090

PDF page: 78; original JSON pointer: `/1068`

2 在 Specifications Selection 页中 把箭头移到你要插入新组分那行

## UG10-CH06-D091

PDF page: 78; original JSON pointer: `/1069`

3 单击鼠标右键 从出现菜单上 单击 Insert Row

## UG10-CH06-D092

PDF page: 78; original JSON pointer: `/1070`

4 在新的一行输入 Component ID 组分标识符 组分名或分子式 重新命名一个组分 重新命名一个存在的组分

## UG10-CH06-D093

PDF page: 78; original JSON pointer: `/1071`

2 在 Specifications Selection 页中 移到你要重新命名的组分的 C omponent ID 框上

## UG10-CH06-D094

PDF page: 78; original JSON pointer: `/1072`

3 选上存在的 ID ASPEN PLUS 会提示你删除或重新命名存在的组分

## UG10-CH06-D095

PDF page: 78; original JSON pointer: `/1073`

4 选择 Rename 该组分在这个窗口上和所有其它出现的窗口上被重新命名 数据不丢失 如果你选择了 Delete Component ID 和数据都被删除了 删除一个组分 删除一个组分

## UG10-CH06-D096

PDF page: 78; original JSON pointer: `/1074`

2 在 Specifications Selection 页中 在你要删除组分的那行选择器上单击鼠标右键

## UG10-CH06-D097

PDF page: 78; original JSON pointer: `/1075`

3 从出现的菜单上选择 Delete Row 当你删除一个组分时 在其它页中涉及的所有组分都自动的被删除 例如 如果你在 Stream 物流 窗口上输入组分流率 然后在 Components Specifications Selection 页上删除 一个组分 那么 ASPEN PLUS 会自动的从 Stream 物流 窗口上删除组分 ID 和流率 重排组分列表 在 Components Specifications Selection 页上重排组分列表

## UG10-CH06-D098

PDF page: 78; original JSON pointer: `/1076`

1. 从 Data 菜单 单击 Components

## UG10-CH06-D099

PDF page: 78; original JSON pointer: `/1077`

2. 在 Specifications Selection 页上 单击 Reorder 按钮

## UG10-CH06-D100

PDF page: 78; original JSON pointer: `/1078`

3. 单击你要移动的组分的 ID

## UG10-CH06-D101

PDF page: 78; original JSON pointer: `/1079`

4. 单击上下箭头键以一定的方向移动组分 移到列表右侧

## UG10-CH06-D102

PDF page: 78; original JSON pointer: `/1080`

5. 重复步骤 3 和 4 直到所有的组分都被排列好为止

## UG10-CH06-D103

PDF page: 78; original JSON pointer: `/1081`

6. 单击 Close 关闭 返回 Specifications Selection 页 该页按新的顺序显示组分 ASPEN PLUS 在这个窗口和其它窗口保留组分的所有最初数据和参考信息

## UG10-CH06-D104

PDF page: 79; original JSON pointer: `/1083`

包含离子组分的电解质系统和反应必须完成组分规定 你可以使用 Electrolyte Wizard

## UG10-CH06-D105

PDF page: 79; original JSON pointer: `/1084`

电解质智能工具 生成离子反应 另外的组分会通过反应形成

## UG10-CH06-D106

PDF page: 79; original JSON pointer: `/1085`

打开 Electrolyte Wizard 电解质智能工具 之前

## UG10-CH06-D107

PDF page: 79; original JSON pointer: `/1086`

1. 从 Data 菜单 单击 Components

## UG10-CH06-D108

PDF page: 79; original JSON pointer: `/1087`

2. 在 Specifications Selection 页上 输入组分 Water (H2O) 电解质系统必须有水存在

## UG10-CH06-D109

PDF page: 79; original JSON pointer: `/1088`

3. 输入另外的分子组分定义系统 一些例子为 系统 分子组分 酸水系统 CO2 H2S O2S SO2 盐水系统 NACL 使用 Type=Conventional,不标识 Type 为 Solid

## UG10-CH06-D110

PDF page: 79; original JSON pointer: `/1089`

4. 单击 Elec Wizard 电解质智能工具 按钮

## UG10-CH06-D111

PDF page: 79; original JSON pointer: `/1090`

5. 在 Electrolyte Wizard 电解质智能工具 对话框 单击 Next 提示 对于 Wizard 上的 Help 单击工具中的 What’s This 按钮 然后单击 Wizard 中任何 活动区域 生成组分列表 生成所需组分的列表

## UG10-CH06-D112

PDF page: 79; original JSON pointer: `/1091`

1. 从 Data Browser 数据浏览器 左屏 双击 Components 文件夹 然后单击 Specifications

## UG10-CH06-D113

PDF page: 79; original JSON pointer: `/1092`

2. 在 Selection 窗口上 单击 Elec Wizard按钮

## UG10-CH06-D114

PDF page: 79; original JSON pointer: `/1093`

3. 在出现的第一个 Electrolyte 电解质 智能工具对话框上 单击 Next

## UG10-CH06-D115

PDF page: 79; original JSON pointer: `/1094`

4. 在 Base Components and Reactions Generatiion Option 基本组分和反应生成选项 对话框上 选择你要生成反应和各种离子形式的组分

## UG10-CH06-D116

PDF page: 79; original JSON pointer: `/1095`

5. 从 Available Components 列表中移动单个组分 单击各组分 然后单击向右单箭头 把所有的组分都移到 Selected 组分列表中 单击双箭头

## UG10-CH06-D117

PDF page: 80; original JSON pointer: `/1097`

6. 打开或关闭其它的选项 推荐的氢离子类型是水合氢离子 H3O+ 你可以选择使用氢离子 H+ 选择这个选项 去 Include Salt Formation 当新的形式生成时包括固体盐 缺省 On 包 括盐 Include Water Dissociation Reaction 在生成反应列表中包括水解 缺省 Off 不包 括水解反应

## UG10-CH06-D118

PDF page: 80; original JSON pointer: `/1098`

7. 单击 Next 在 Generated Species and Reactions 对话框中 ASPEN PLUS 显示了水合物 盐和反应 的列表

## UG10-CH06-D119

PDF page: 81; original JSON pointer: `/1100`

对于反应 双向箭头意思是离子平衡或盐析出 单方向箭头意思是完全水解 生成的固

## UG10-CH06-D120

PDF page: 81; original JSON pointer: `/1101`

8. 通过选择它们和单击 Remove 去掉一些不要的项 去掉一些物质将去掉包含那个物质的所有反应

## UG10-CH06-D121

PDF page: 81; original JSON pointer: `/1102`

10. 在 Simulation Approach 对话框上 选择模拟方式 选择这种方式 有 计算方法是 True* 所有计算结果都根据实际物质 的存在显示 同一电解 质的分 子 离子和固体形式将分别地显 示 电解质反应在单元操作模型中与 相平衡方程同时求解 Apparent 相同电解质的所有形式作为一 个单个组分显示 电解质反应在物性估算过程中求 解 * 缺省真实组分的方式一般指计算效率 两种方式给出相同的结果 你也可以显示 Chemistry ID(GLOBAL) 和 Henry -Comps ID(GLOBAL)名字

## UG10-CH06-D122

PDF page: 81; original JSON pointer: `/1103`

11. 单击 Next 建立 Chemistry 和 Henry-Comps 窗口 继续去 Summary 概述 页 Summary 对话框概括了由 Electrolyte Wizard 对你的物性 组分 数据库和化学物性规 定做的修改 在 Summary 对话框中也检查或修改亨利组分或电解质反应生成的规定 检查生成的亨利组分 检查或修改 Electrolyte Wizard 电解质智能工具 生成的 Henry Components 亨利组分 列表

## UG10-CH06-D123

PDF page: 81; original JSON pointer: `/1104`

1. 在 Electrolyte Wizard对话框中 单击 Review Generated Henry-Comps List 按钮

## UG10-CH06-D124

PDF page: 82; original JSON pointer: `/1106`

2. 在 Henry Components Global 对话框中 选择组分 使用右箭头和左箭头按钮从 Selected Components 列表中增加或去掉组分

## UG10-CH06-D125

PDF page: 82; original JSON pointer: `/1107`

3. 当完成时 单击对话框右上角的 X 关闭对话框 注意亨利组分规定以后可以使用 Components Henry-Comps 窗口进行修改 检查生成的电解质反应 检查或修改由 Electrolyte Wizard 电解质智能工具 生成的电解质反应

## UG10-CH06-D126

PDF page: 82; original JSON pointer: `/1108`

1. 单击 Summary 对话框中 Modify/Add Reactions 按钮

## UG10-CH06-D127

PDF page: 82; original JSON pointer: `/1109`

2. 在 Modify/Add Reactions G lobal 对话框中 Stoichiometry 化学计量系数 页显示 反应 它们的类型和它们的化学计量系数 改变一个反应的化学计量系数 从列表 中选择它 单击 Edit 当你完成改变化学计量系数时 单击 Close

## UG10-CH06-D128

PDF page: 82; original JSON pointer: `/1110`

3. 使用 Equilibrium Constants 平衡常数 页输入 检查或改变平衡常数 它们的浓 度基准或平衡接近温度 检查或修改其它反应的平衡常数数据 从 Equilibrium Reaction 平衡反应 列表中选择所需要的反应

## UG10-CH06-D129

PDF page: 82; original JSON pointer: `/1111`

4. 当完成时 单击对话框右上角的 X 关闭对话框 电解质化学物性规定以后使用 Reactions Chemistry 窗口可以修改 检查完 Summary 对话框上的数据以后 单击 Finish 保存所有相应窗口的变化 并返回 Components Specifications Selection 页 关于处理电解质模型的更详细资料 参见 ASPEN PLUS 物性方法和模型 标识固体组分 标识组分为固体

## UG10-CH06-D130

PDF page: 82; original JSON pointer: `/1112`

1. 从 Data 菜单 单击 Components

## UG10-CH06-D131

PDF page: 82; original JSON pointer: `/1113`

2. 在 Specifications Selection 页中 规定 Component ID

## UG10-CH06-D132

PDF page: 82; original JSON pointer: `/1114`

3. 如果组分是一个数据库组分 那么规定分子式和组分名 详细资料参见本章 Specifying Components from a Databank 从数据库规定组分

## UG10-CH06-D133

PDF page: 82; original JSON pointer: `/1115`

4. 在 Type 框中 规定 Solid 为一个常规固体或 Nonconventional 为一个非常规固体 常规固体 常规固体是纯物质 这些固体可以在相平衡和/或化学平衡的混合物中存在 包括电解 质盐 例如 NaCl 可以是从电解质溶液中析出的一个常规固体 这些固体在 MIXED 子物 流中存在 常规固体以物性来表征 例如

## UG10-CH06-D134

PDF page: 82; original JSON pointer: `/1116`

l 能参与由 RGibbs 单元操作模型模拟的化学平衡 其它的单元操作模型不能处理固

## UG10-CH06-D135

PDF page: 82; original JSON pointer: `/1117`

l 被指定为子物流类型 CISOLID 以区别其它的常规固体

## UG10-CH06-D136

PDF page: 83; original JSON pointer: `/1119`

非常规固体不参加相平衡或化学平衡计算 ASPEN PLUS 对非常规固体总是指定为子

## UG10-CH06-D137

PDF page: 83; original JSON pointer: `/1120`

组分的颜色和气味 你可以在你编写的物性模型或单元操作计算的 Fortran 子程序中使用组

## UG10-CH06-D138

PDF page: 83; original JSON pointer: `/1121`

4 灰分 干基准 ULTANAL 元素分析 重量% 1 灰分 干基准

## UG10-CH06-D139

PDF page: 83; original JSON pointer: `/1122`

7 氧 干基准 SULFANAL 硫分析的形式 原煤的重 量%

## UG10-CH06-D140

PDF page: 83; original JSON pointer: `/1123`

3 有机物 干基准 GENANAL 通用组成分析 重量% 1 组成 1

## UG10-CH06-D141

PDF page: 83; original JSON pointer: `/1124`

20 组成 20 关于在物流中输入组分属性值的资料 参见第九章 规定物流

## UG10-CH06-D142

PDF page: 84; original JSON pointer: `/1126`

1. 从 Data 菜单 单击 Components

## UG10-CH06-D143

PDF page: 84; original JSON pointer: `/1127`

2. 在 Data Brower 数据浏览器 的左屏中 单击 Attr-Comps

## UG10-CH06-D144

PDF page: 84; original JSON pointer: `/1128`

3. 在 Selection 页上 从 Component 列表选择 Component ID 你可以在第一个下面将 多个组分列表选择多个组分

## UG10-CH06-D145

PDF page: 84; original JSON pointer: `/1129`

4. 从 Attributes 列表选择一个组分属性 你可以列出每个组分的多种组分属性 在多数情况下 你给定属性的常规组分将是固体 在 Components Specifications Selection 页上 Type 是 Solid 关于在物流中输入组分属性值的信息 参见第九章 规定物流 给定非常规组分的属性 当你在 Properties Advanced NC -Props 窗口上或使用具有非常规组分的 User Defined Components 智能工具来选择非常用焓和密度模型时 非常规组分的属性会自动的给出 你可以给定非常规组分的其它属性 这样做

## UG10-CH06-D146

PDF page: 84; original JSON pointer: `/1130`

1. 从 Data 菜单 选择 Physical Properties 物性

## UG10-CH06-D147

PDF page: 84; original JSON pointer: `/1131`

2. 在 Data Brower 数据浏览器 的左屏中 双击 Advanced 文件夹

## UG10-CH06-D148

PDF page: 84; original JSON pointer: `/1132`

3. 单击 NC-Props

## UG10-CH06-D149

PDF page: 84; original JSON pointer: `/1133`

4. 从 Component 列表中 选择一个组分

## UG10-CH06-D150

PDF page: 84; original JSON pointer: `/1134`

5. 如果没有 输入那个组分的焓和密度模型名 选择模型所需的组分属性将自动的被列在页的底部

## UG10-CH06-D151

PDF page: 84; original JSON pointer: `/1135`

6. 通过从列表中选择组分属性 把它们加到 Required Component Attributes For The Selected Models 框里 关于更详细的资料 参见 非常规组分的物性方法 第七章 物性方法 非常规组分的参数 第八章 物性参数和数据 输入组分属性值 第九章 规定物流 规定超临界 HENRY 组分 在计算气--液平衡活度系数方法中 亨利定律用于描述溶解气体或其它超临界组分状 态 在 ASPEN PLUS 中使用亨利定律 你必须定义一组或多组超临界 或亨利 组分

## UG10-CH06-D152

PDF page: 84; original JSON pointer: `/1136`

在物性计算过程中使用亨利定律 你也必须在下面这些页之一上规定一个亨利

## UG10-CH06-D153

PDF page: 84; original JSON pointer: `/1137`

Components ID

## UG10-CH06-D154

PDF page: 84; original JSON pointer: `/1138`

l Properties Specifications Global 页

## UG10-CH06-D155

PDF page: 84; original JSON pointer: `/1139`

l Properties Specifications Flowsheet Sections 页

## UG10-CH06-D156

PDF page: 85; original JSON pointer: `/1141`

l 单元操作 BlockOptions Properties 页

## UG10-CH06-D157

PDF page: 85; original JSON pointer: `/1142`

l Property Analysis Properties 页

## UG10-CH06-D158

PDF page: 85; original JSON pointer: `/1143`

物 当你用 Henry Comps 亨利组分 规定一个物性方法时 这些参数在 Properties Parameters

## UG10-CH06-D159

PDF page: 85; original JSON pointer: `/1144`

Binary Iteraction HENRY-1 物性参数二元交互 HENRY-1 窗口上自动的被使用 对于没有

## UG10-CH06-D160

PDF page: 85; original JSON pointer: `/1145`

可用的亨利定律参数的组分 你必须在 Properties Parameters Binary Iteraction HENRY-1 窗口

## UG10-CH06-D161

PDF page: 85; original JSON pointer: `/1146`

上输入亨利定律参数 参见第八章讨论物性参数的要求

## UG10-CH06-D162

PDF page: 85; original JSON pointer: `/1147`

1. 从 Data 菜单 单击 Components

## UG10-CH06-D163

PDF page: 85; original JSON pointer: `/1148`

2. 在 Data Brower 数据浏览器 的左屏中 单击 Henry Comps

## UG10-CH06-D164

PDF page: 85; original JSON pointer: `/1149`

3. 在 Henry Components Object Manager 上 单击 New

## UG10-CH06-D165

PDF page: 85; original JSON pointer: `/1150`

4. 在 Create New ID 对话框中 对 Henry Components 新的列表输入一个 ID 或接受 缺省的 ID

## UG10-CH06-D166

PDF page: 85; original JSON pointer: `/1151`

5. 在 Selected 组分列表中规定 Component IDs 选择在 Available 组分列表中的亨利组分 并使用右箭头按钮把它们移到 Selected 组分列表里 左箭头按钮用来移出 Selected 组分列表中的组分 双箭头按钮用来同 时把所有的组分都移到一个列表中 规定亨利组分的例子 在这个例子中 N2 CO2 和 H2S 表示亨利组分 BZ CH 和 H2O 不是亨利组分 规定 UNIFAC官能团 使用 Components UNIFAC Groups Selection 页标识 UNIFAC官能团或引入新的官能团

## UG10-CH06-D167

PDF page: 85; original JSON pointer: `/1152`

如果你要输入 UNIFAC 官能团参数或官能团和官能团之间的交互参数 你必须对每个官能 团给出一个 ID 在 Properties Parameters UNIFAC Group窗口上使用官能团 ID 或在 UNIFAC Group Binary 窗口中输入官能团参数 规定 UNIFAC官能团

## UG10-CH06-D168

PDF page: 86; original JSON pointer: `/1154`

1. 从 Data 菜单 选择 Components

## UG10-CH06-D169

PDF page: 86; original JSON pointer: `/1155`

2. 在 Data Brower 数据浏览器 的左屏中 单击 UNIFAC

## UG10-CH06-D170

PDF page: 86; original JSON pointer: `/1156`

3. 在 UNIFAC Groups Selection 页上 在 Group ID 框选上官能团名字 每个官能团必 须有一个在其它窗口上可以参考的名字

## UG10-CH06-D171

PDF page: 86; original JSON pointer: `/1157`

4. 从 Group 数字列表上选择一个数 当你滚动时 每个官能团的简要说明出现在说明 区域 如果你要定义一个新的 UNIFAC 官能团 在 Group 数字框上 4000 到 5000 之间选一个 数 定义组分组 你可以在一股撕裂物流中规定一组被收敛的组分 一个组分组由其中之一组成

## UG10-CH06-D172

PDF page: 86; original JSON pointer: `/1158`

l Components Specifications Selection 页中的组分范围

## UG10-CH06-D173

PDF page: 86; original JSON pointer: `/1159`

1. 从 Data 菜单 单击 Components

## UG10-CH06-D174

PDF page: 86; original JSON pointer: `/1160`

2. 在 Data Brower 数据浏览器 的左屏中 单击 Comp-Group

## UG10-CH06-D175

PDF page: 86; original JSON pointer: `/1161`

3. 在 Component Group Object Manager 上 单击 New

## UG10-CH06-D176

PDF page: 86; original JSON pointer: `/1162`

4. 在 Create New ID 对话框中 对新的 Component Group 输入一个 ID 或接受缺省的

## UG10-CH06-D177

PDF page: 86; original JSON pointer: `/1163`

5. 在 Component List 页中 从 Substream 列表中选择一个子物流

## UG10-CH06-D178

PDF page: 86; original JSON pointer: `/1164`

6. 规定一个包括在组分组里的组分 选择在 Available 组分列表中的组分 并使用右箭头按钮把它们移到 Selected 组分列表 里 左箭头按钮用来移出 Selected 组分列表中的组分 双箭头按钮用来同时把所有的组分都 移到一个列表中 另一方面 你可以单击 Component Range 页 输入代表你的组分组的组分范围

## UG10-CH06-D179

PDF page: 86; original JSON pointer: `/1165`

7. 如果你从一个以上的子物流建立一个组分的组分组 重复步骤 5 和 6 当你使用 NEWTON BROYDEN或 SQP 收敛方法并且你的流程具有下面所列的全部时 用组分组能够有助于撕裂物流收敛

## UG10-CH06-D180

PDF page: 86; original JSON pointer: `/1166`

使用组分组的收敛方法 你必须在下面页之一中规定 Component Group ID:

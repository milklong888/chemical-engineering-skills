# UG10-CH08 Detail Operation Index - 第8章 物性参数和数据

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH08-D001

PDF page: 103; original JSON pointer: `/1274`

在开始任何新的模拟时 检查你已经正确的表示模拟系统的物性是很重要的 当你按前

## UG10-CH08-D002

PDF page: 103; original JSON pointer: `/1275`

面章节所描述的方法选择物性方法后 你必须确定物性参数需求并且保证能得到所有需要的

## UG10-CH08-D003

PDF page: 103; original JSON pointer: `/1276`

依据模拟的类型 你的模型将需要不同的参数 下面章节描述一些基本性质计算要求的

## UG10-CH08-D004

PDF page: 103; original JSON pointer: `/1277`

为了得到有意义的结果 许多状态方程和活度系数模型需要二元参数 若想根据所选性

## UG10-CH08-D005

PDF page: 103; original JSON pointer: `/1278`

质方法确定需要的参数 对于你选择的每种物性方法 参见 ASPEN PLUS物性方法和模

## UG10-CH08-D006

PDF page: 104; original JSON pointer: `/1280`

质量和能量平衡模拟要求的参数

## UG10-CH08-D007

PDF page: 104; original JSON pointer: `/1281`

对于涉及质量和能量平衡计算的模拟 必须输入或从数据库检索下列必需的参数

## UG10-CH08-D008

PDF page: 104; original JSON pointer: `/1282`

输入或检索的参数 用于 物性参数表的类型

## UG10-CH08-D009

PDF page: 104; original JSON pointer: `/1283`

MW 分子量 Pure Component Scalar 纯组分标量

## UG10-CH08-D010

PDF page: 104; original JSON pointer: `/1284`

PLXANT 扩展Antoine 蒸汽压方法 Pure Component T-Dependent(纯组分

## UG10-CH08-D011

PDF page: 104; original JSON pointer: `/1285`

CPIG 或CPIGDP 理想气体热容模型 Pure Component T-Dependent(纯组分

## UG10-CH08-D012

PDF page: 104; original JSON pointer: `/1286`

汽化热模型 Pure Component T-Dependent(纯组分

## UG10-CH08-D013

PDF page: 104; original JSON pointer: `/1287`

目的 必需的参数 输入物性参数表类型

## UG10-CH08-D014

PDF page: 104; original JSON pointer: `/1288`

规定使用标准液体体积基准

## UG10-CH08-D015

PDF page: 104; original JSON pointer: `/1289`

标准液体体积参数 VLSTD Pure Component Scalar

## UG10-CH08-D016

PDF page: 104; original JSON pointer: `/1290`

要求的游离水计算 水溶解度模型的参数 Pure Component

## UG10-CH08-D017

PDF page: 104; original JSON pointer: `/1291`

提示 如果你在Setup Simulation Options Calculations 建立模拟选项计算 页面上取 消选择Perform Heat Balance Calculations 进行热平衡计算 选项 ASPEN PLUS就不计算 焓 熵 或吉布斯自由能 就不需要计算这些性质所用的参数 亨利定律要求的参数 如果你使用亨利定律计算超临界组分 或不溶气体组分 则需要所有不溶气体组分相 对于溶剂的亨利常数模型参数 HENRY 你必须在Component Henry Comps Selection 组

## UG10-CH08-D018

PDF page: 104; original JSON pointer: `/1292`

分 亨利组分 选择 页面上列出超临界组分

## UG10-CH08-D019

PDF page: 104; original JSON pointer: `/1293`

混合物中不只一个溶剂 每个不溶气体-溶剂对的亨利常数参数

## UG10-CH08-D020

PDF page: 104; original JSON pointer: `/1294`

利常数时 ASPEN PLUS 使用严格的缺省方法

## UG10-CH08-D021

PDF page: 104; original JSON pointer: `/1295`

在Properties Parameters Binary Interaction Henry-1 (物性参数 二元交互参数 亨利-1)

## UG10-CH08-D022

PDF page: 104; original JSON pointer: `/1296`

表页上的Henry-1对象的Input 输入 页面上 输入亨利常数模型参数

## UG10-CH08-D023

PDF page: 104; original JSON pointer: `/1297`

热力学参考状态要求的参数

## UG10-CH08-D024

PDF page: 104; original JSON pointer: `/1298`

热力学性质的参考状态是25和1atm理想气体状态下的各组成要素 为了计算焓 熵

## UG10-CH08-D025

PDF page: 105; original JSON pointer: `/1300`

l 标准生成热 DHFORM

## UG10-CH08-D026

PDF page: 105; original JSON pointer: `/1301`

l 标准吉布斯生成自由能 DGFORM

## UG10-CH08-D027

PDF page: 105; original JSON pointer: `/1302`

对于不涉及化学反应的系统 允许DHFORM和DGFORM缺省值为零

## UG10-CH08-D028

PDF page: 105; original JSON pointer: `/1303`

下列参数的值 必须对下列组分都可得到

## UG10-CH08-D029

PDF page: 105; original JSON pointer: `/1304`

DHFORM 参加化学反应的组分

## UG10-CH08-D030

PDF page: 105; original JSON pointer: `/1305`

DGFORM 用RGibbs 反应模型模拟的平衡反应中涉及的组分

## UG10-CH08-D031

PDF page: 105; original JSON pointer: `/1306`

l 标准固体生成热 DHSFRM

## UG10-CH08-D032

PDF page: 105; original JSON pointer: `/1307`

l 标准固体吉布斯生成自由能 DGSFRM

## UG10-CH08-D033

PDF page: 105; original JSON pointer: `/1308`

在Properties Parameters Pure Component Scalar Input 性质参数 纯组分标量 输入

## UG10-CH08-D034

PDF page: 105; original JSON pointer: `/1309`

离子类的参考状态是水中无限稀释溶液 为了计算离子的焓 熵 和吉布斯自由能

## UG10-CH08-D035

PDF page: 105; original JSON pointer: `/1310`

l 在无限稀释的水中的标准生成热 DHAQFM

## UG10-CH08-D036

PDF page: 105; original JSON pointer: `/1311`

l 在无限稀释的水中的标准固体吉布斯生成自由能 DGAQFM

## UG10-CH08-D037

PDF page: 105; original JSON pointer: `/1312`

对于许多组分 ASPEN PLUS 自动从它的纯组分数据库检索纯组分参数 使用

## UG10-CH08-D038

PDF page: 105; original JSON pointer: `/1313`

Componets Specifications Databanks 组分规定 数据库 页面指定所要查找数据库和查找

## UG10-CH08-D039

PDF page: 105; original JSON pointer: `/1314`

若输入你自己的参数值 使用Properties Parameters (物性参数)的Pure Component Scalar Input 纯组分标量 输入 和 T-Dependent Input 温度相关参数输入)页面来输入 参见 输入纯组分常数 因为内置的纯组参数是和模拟引擎放在一起的 所以在任何Parameters Pure Component Input (纯组分参数输入)页面上都不能自动出现可用的参数 用户输入的参数将取代从ASPEN PLUS 数据库检索出的参数值

## UG10-CH08-D040

PDF page: 106; original JSON pointer: `/1316`

对于所指定组分和性质方法 若想生成模拟中将用到的所有可用的纯组分参数报告

## UG10-CH08-D041

PDF page: 106; original JSON pointer: `/1317`

1. 从Tools(工具)菜单中 单击Retrieve Parameters Results(检索参数结果)

## UG10-CH08-D042

PDF page: 106; original JSON pointer: `/1318`

2. 在Retrieve Parameters Results对话框中 单击OK生成一个报表

## UG10-CH08-D043

PDF page: 106; original JSON pointer: `/1319`

3. 在下一个Retrieve Parameters Results对话框中 单击OK浏览该报表 数据浏览器自动打开Properties Parameters Results(物性参数结果)文件夹

## UG10-CH08-D044

PDF page: 106; original JSON pointer: `/1320`

4. 在数据浏览器的左窗格内 从Results(结果)文件夹中选择Pure Component (纯组分) 表 Parameters Results Pure Component (参数结果 纯组分)表包含一个所有标量参数 页面和一个温度相关参数页面 在每个页面上 你可以选择浏览参数值 或状态 关于参数结果状态 可能有下列状态 状态 表示 参数是 Available 可用的 在数据库可以查到 在Parameters Input (参数输入)页面上已

## UG10-CH08-D045

PDF page: 106; original JSON pointer: `/1321`

Default 缺省 一个系统缺省值

## UG10-CH08-D046

PDF page: 106; original JSON pointer: `/1322`

除了用上述方法检索参数结果外 你也可以在ASPEN PLUS 报告文件中生成一个详细

## UG10-CH08-D047

PDF page: 106; original JSON pointer: `/1323`

的参数报告 关于这个和其它报告选项的详细内容 参见第十二章

## UG10-CH08-D048

PDF page: 106; original JSON pointer: `/1324`

ASPEN PLUS 检索每个数据库值并自动使用它们 不论你输入自己的参数还是从一个

## UG10-CH08-D049

PDF page: 106; original JSON pointer: `/1325`

数据库检索它们 你都可从相应Properties Parameters Binary Interaction Input (二元交互物

## UG10-CH08-D050

PDF page: 106; original JSON pointer: `/1326`

性参数输入)页面来参看它们 ASPEN PLUS 为每个二元参数生成一个表

## UG10-CH08-D051

PDF page: 106; original JSON pointer: `/1327`

如果你不想检索内置状态方程二元参数 那么 在你状态方程模型的 Properties Parameters Binary Interaction(物性参数 二元交互作用参数 )表页的 Databanks页面上的 Selected Databanks列表中删掉数据库名 使用Input页面输入你自己的二元参数值 更详细 的信息参见 输入二元标量参数 检索活度系数二元参数 对于汽-液应用 可以得到下列性质方法的许多组分对的二元参数

## UG10-CH08-D052

PDF page: 107; original JSON pointer: `/1329`

无论何时选择这些性质方法 ASPEN PLUS都自动检索这些参数并在 Properties

## UG10-CH08-D053

PDF page: 107; original JSON pointer: `/1330`

Parameters Binary Interaction 物性参数 二元交互作用参数 表页的Input 输入 页面上

## UG10-CH08-D054

PDF page: 107; original JSON pointer: `/1331`

显示它们 ASPEN PLUS 为每个二元参数生成一个表

## UG10-CH08-D055

PDF page: 107; original JSON pointer: `/1332`

如果你不想检索内置二元参数 那么 在Properties Parameters Binary Interaction(物性 参数 二元交互作用参数)表页的Databanks 数据库 页面上的Selected Databanks 所选的 数据库 列表上删除数据库名 使用Input 输入 页面输入你自己的二元参数值 更详细的信息参见 输入温度相关的二元参数 对于从数据库检索出的二元参数 借助Help(帮助)获得参数质量的信息 例如 误差平 方和 拟合的平均和最大值偏差 检索亨利定律常数 对于大量的溶剂中的溶质 可以得到亨利定律常数 溶剂是水和许多有机组分

## UG10-CH08-D056

PDF page: 107; original JSON pointer: `/1333`

如果你使用了一个活度系数方法并定义一组亨利组分 ASPEN PLUS 自动检索亨利常 数并在 Properties Parameters Binary Interaction HENRY-1 (物性参数 二元交互作用参数 HENRY-1)表页上的Input 输入 页面显示它们 如果你不想检索内置亨利定律常数 就在HENRY-1表页的Databanks 数据库 页面上 的Selected Databanks 所选数据库 列表中的删除BINARY和HENRY数据库 检索电解质二元和电解质对参数 对于许多工业上重要的电解质系统 可以得到电解质NRTL模型的二元参数和成对参数

## UG10-CH08-D057

PDF page: 107; original JSON pointer: `/1334`

ASPEN PLUS 检索二元参数并在Properties Parameters Binary Interaction (物性参数 二

## UG10-CH08-D058

PDF page: 108; original JSON pointer: `/1336`

元交互作用参数 )表页上显示它们 对于参数对 ASPEN PLUS 在Properties Parameters

## UG10-CH08-D059

PDF page: 108; original JSON pointer: `/1337`

Electrolyte Pair (性质参数 电解质对)表页上显示它们

## UG10-CH08-D060

PDF page: 108; original JSON pointer: `/1338`

l 使用Data Regression( 数据回归)由实验数据来回归参数 更多的内容 参见三十一

## UG10-CH08-D061

PDF page: 108; original JSON pointer: `/1339`

这一节解释怎样直接输入下列参数

## UG10-CH08-D062

PDF page: 108; original JSON pointer: `/1340`

下面的表显示在哪里输入不同类型的参数

## UG10-CH08-D063

PDF page: 108; original JSON pointer: `/1341`

使用下面 Properties Parameters 表页

## UG10-CH08-D064

PDF page: 108; original JSON pointer: `/1342`

二元交互参数 二元标量参数 例如 Redlich-Kwong-Soave 状态

## UG10-CH08-D065

PDF page: 108; original JSON pointer: `/1343`

温度相关的二元参数 即 用一个以上元素定义的

## UG10-CH08-D066

PDF page: 109; original JSON pointer: `/1345`

输入所有物性参数的一般过程如下 关于输入具体类型参数的详细介绍 参见这一章后

## UG10-CH08-D067

PDF page: 109; original JSON pointer: `/1346`

1. 从Data(数据)菜单单击Properties(物性)

## UG10-CH08-D068

PDF page: 109; original JSON pointer: `/1347`

2. 在Data Browser(数据浏览器)的左画面 双击Parameter 参数 文件夹

## UG10-CH08-D069

PDF page: 109; original JSON pointer: `/1348`

3. 单击你要输入参数类型的文件夹 纯组分 二元参数 电解质对 电解质三元参数 UNIFAC基团或UNIFAC基团二元参数 这些参数的描述在上面的表中 ASPEN PLUS 自动为任意二元交互参数 电解质对参数和在 Properties Specifications 性质 规定 表页上所 指定的性质方法所需的参数建立参数集 相应参数类型的 Object Manager 对象管理器 显示这些参数集的标识号

## UG10-CH08-D070

PDF page: 109; original JSON pointer: `/1349`

4. 在你选择的参数类型的对象管理器中 你可以

## UG10-CH08-D071

PDF page: 109; original JSON pointer: `/1350`

l 通过选择参数和单击Edit (编辑)为现有的参数集输入参数

## UG10-CH08-D072

PDF page: 109; original JSON pointer: `/1351`

l 建立一个新的参数集 在Object Manager 对象管理器 中 单击New(新建)

## UG10-CH08-D073

PDF page: 109; original JSON pointer: `/1352`

如果有提示 那么 按提示选择相应的参数类型和参数名 并点OK

## UG10-CH08-D074

PDF page: 109; original JSON pointer: `/1353`

5. 使用Parameters 参数 输入页面

## UG10-CH08-D075

PDF page: 109; original JSON pointer: `/1354`

l 输入不在ASPEN PLUS 数据库的参数

## UG10-CH08-D076

PDF page: 109; original JSON pointer: `/1355`

l 通过输入参数值替换缺省值或数据库值

## UG10-CH08-D077

PDF page: 109; original JSON pointer: `/1356`

你可以按任何单位输入参数值 在你规定参数名之后 ASPEN PLUS 自动填充缺省单

## UG10-CH08-D078

PDF page: 109; original JSON pointer: `/1357`

如果你在输入参数值后想改变参数的测量单位 ASPEN PLUS 不改变所显示的值 提示 当使用Components Specification Selection 组分 规定 选择 页面定义非数据 库组分时 你可以使用 User Defined Components Wizard 用户定义的组分向导 向导指 导你输入所需的基本纯组分参数 关于用户定义的组分向导的更多信息 参见第六章 输入纯组分常数 若输入纯组分常数

## UG10-CH08-D079

PDF page: 109; original JSON pointer: `/1358`

1. 从Data(数据)菜单 单击Properties(物性)

## UG10-CH08-D080

PDF page: 109; original JSON pointer: `/1359`

3. 单击纯组分文件夹 在Parameter Pure Component Object Manager 参数 纯组分 对象管理器 中 你可以建 立新参数的标识号或修改现有的标识号

## UG10-CH08-D081

PDF page: 109; original JSON pointer: `/1360`

4. 若生成一个新的参数集 在Object Manager 对象管理器 中 单击New(新建)

## UG10-CH08-D082

PDF page: 110; original JSON pointer: `/1362`

5. 在New Pure Component Parameter( 新纯组分参数)对话框中 缺省参数类型是Scalar 标量 输入一个ID号或用缺省的ID号并单击OK

## UG10-CH08-D083

PDF page: 110; original JSON pointer: `/1363`

6. 若修改现有的参数ID号 在Object Manager 对象管理器 选择参数集的名 并单 击Edit

## UG10-CH08-D084

PDF page: 110; original JSON pointer: `/1364`

7. 在纯组分标量参数的Input 输入 页面上 定义你要输入数据值的组分和参数 矩阵 并定义相应的单位 输入纯组分常数的例子 为组分 C1输入临界温度 410.2K和临界压力 40 .7atm 为组分 C2输入临界压力 36.2atm 输入纯组分关联式参数 若输入温度相关的纯组分物性关联式系数

## UG10-CH08-D085

PDF page: 110; original JSON pointer: `/1365`

1. 从Data(数据)菜单 单击Properties(物性)

## UG10-CH08-D086

PDF page: 110; original JSON pointer: `/1366`

2. 在Data Browser(数据浏览器)的左画面 双击Parameter 参数 文件夹

## UG10-CH08-D087

PDF page: 110; original JSON pointer: `/1367`

3. 单击Pure Component 纯组分 文件夹 在Parameter Pure Component Object Manager 参数 纯组分 对象管理器 中 你可 以建立新参数的标识号或修改现有的ID号

## UG10-CH08-D088

PDF page: 110; original JSON pointer: `/1368`

4. 若建立一个新的参数集 在Object Manager 对象管理器 中 单击New(新建) 出现New Pure Component Parameter( 新纯组分参数)对话框

## UG10-CH08-D089

PDF page: 111; original JSON pointer: `/1370`

5 在 New Pure Component Parameter( 新纯组分参数 )对话框中 选择T-dependent correlation 温度相关关联式 并从列表中选择相应的参数名

## UG10-CH08-D090

PDF page: 111; original JSON pointer: `/1371`

7 若修改现有的参数ID号 在Object Manager 对象管理器 选择参数集的名 并单 击Edit

## UG10-CH08-D091

PDF page: 111; original JSON pointer: `/1372`

8 在Input 输入 页面上 从Component 组分 列表中选择一个组分 对于所选择 的温度相关参数 使用本页面为你有参数的所有组分输入参数值

## UG10-CH08-D092

PDF page: 111; original JSON pointer: `/1373`

9 规定相应的单位并输入作为顺序元素的每个参数的系数 关于模型和参数的更详细 的描述 参见ASPEN PLUS 物性方法和模型 你不能在同一个表页内为同一参数输入多组值 输入理想气体热容系数的例子 对于组分CLP 输入理想气体热容多项式模型 CPIG 的系数 C T T T TP IG = − + − + × − ×− −2001 2 358 9 0 515 4 41 10 158 102 4 3 7 4. . . . . CP IG的单位为J/kmol-K,温度的单位为K

## UG10-CH08-D093

PDF page: 112; original JSON pointer: `/1375`

1. 从Data(数据)菜单 单击Properties(物性)

## UG10-CH08-D094

PDF page: 112; original JSON pointer: `/1376`

2. 在Data Browser(数据浏览器)的左画面 双击Parameter 参数 文件夹

## UG10-CH08-D095

PDF page: 112; original JSON pointer: `/1377`

3. 单击纯组分文件夹 在Parameter Pure Component Object Manager 参数 纯组分 对象管理器 中 你可 以建立新参数的ID号或修改现有的ID号

## UG10-CH08-D096

PDF page: 112; original JSON pointer: `/1378`

4. 若建立一个新的参数集 在Object Manager 对象管理器 中 单击New(新建) 出现New Pure Component Parameter( 新纯组分参数)对话

## UG10-CH08-D097

PDF page: 112; original JSON pointer: `/1379`

5. 在 New Pure Component Parameters ( 新的纯组分参数 )对话框中 选择 Nonconventional(非常规)

## UG10-CH08-D098

PDF page: 112; original JSON pointer: `/1380`

6. 输入一个ID号或采用缺省的ID号 然后 单击OK

## UG10-CH08-D099

PDF page: 113; original JSON pointer: `/1382`

7. 若修改现有的参数ID 在Object Manager 对象管理器 中选择参数集的名 并单 击Edit

## UG10-CH08-D100

PDF page: 113; original JSON pointer: `/1383`

8. 在Input(输入)页中 从Parameter(参数)列表中选择一个参数

## UG10-CH08-D101

PDF page: 113; original JSON pointer: `/1384`

正文待来源表达/OCR边界复核；原文本 SHA256: `1a74bc55693e2984e411a3ab92ede1d551aee13ac56fd6bffc6c46d8c3a3d1f7`。

## UG10-CH08-D102

PDF page: 113; original JSON pointer: `/1385`

另一种方法是 你可直接输入焓和密度的表列 (tabular)数据 非常规组分没有多项式

## UG10-CH08-D103

PDF page: 113; original JSON pointer: `/1386`

1. 从Data(数据)菜单上 单击Properties(物性)

## UG10-CH08-D104

PDF page: 113; original JSON pointer: `/1387`

2. 在Data Browser(数据浏览器)的左画面中 双击Parameter(参数)文件夹

## UG10-CH08-D105

PDF page: 113; original JSON pointer: `/1388`

3. 单击二元交互参数文件夹 打开含有由所指定物性方法使用的二元参数集的Object Manager(对象管理器)

## UG10-CH08-D106

PDF page: 113; original JSON pointer: `/1389`

4. 在Object Manager(对象管理器)中 选择想要选择的标量参数并单击Edit(编辑)

## UG10-CH08-D107

PDF page: 113; original JSON pointer: `/1390`

5. 为你要输入二元参数值的组分定义ij矩阵

## UG10-CH08-D108

PDF page: 113; original JSON pointer: `/1391`

6. 输入参数值 输入 Redlich-Kwong-Soave二元参数的例子 Redlich-Kwong-Soave状态方程的二元参数RKSKIJ是对称的 即kij=kji 为三组分系统 C1-C2-C3输入下列二元参数值:

## UG10-CH08-D109

PDF page: 114; original JSON pointer: `/1393`

注释 除非你以前选择了 RK-SOAVE物性方法 , 否则在 Binary Interaction Object

## UG10-CH08-D110

PDF page: 114; original JSON pointer: `/1394`

Manager(二元交互参数 对象管理器)看不到RKSKIJ-1参数 (关于 规定物性方法 参见第7

## UG10-CH08-D111

PDF page: 114; original JSON pointer: `/1395`

输入温度相关的二元交互参数

## UG10-CH08-D112

PDF page: 114; original JSON pointer: `/1396`

若输入温度相关的二元交互参数

## UG10-CH08-D113

PDF page: 114; original JSON pointer: `/1397`

1. 从Data(数据)菜单上 单击Properties(物性)

## UG10-CH08-D114

PDF page: 114; original JSON pointer: `/1398`

2. 在Data Browser(数据浏览器)的左画面中 双击Parameter(参数)文件夹

## UG10-CH08-D115

PDF page: 114; original JSON pointer: `/1399`

3. 单击 二元交互参数文件夹 打开含有由你指定的物性方法使用的二元参数集的 Object Manager(对象管理器)

## UG10-CH08-D116

PDF page: 114; original JSON pointer: `/1400`

4. 在Object Manager( 对象管理器 )中,选择想要选择的温度相关二元交互参数 (例 如,NRTL-1)并单击Edit(编辑)

## UG10-CH08-D117

PDF page: 114; original JSON pointer: `/1401`

5. 在Input(输入)页面上的Component i和Component j框里输入组分对

## UG10-CH08-D118

PDF page: 114; original JSON pointer: `/1402`

6. 规定二元参数的单位

## UG10-CH08-D119

PDF page: 114; original JSON pointer: `/1403`

7. 为每个组分对输入作为顺序元素的参数系数 输入 NRTL二元参数的例子 NRTL二元参数aij和bij 是不对称的 即aij aji且bij bji 二元参数cij和dij是对称的 eij和 fij缺省为零 输入组分C1和C2的下列NRTL二元参数 二元参数的单位是开尔文 a12 = 0 a21 = 0 b12= -74.18 b21= 270.8

## UG10-CH08-D120

PDF page: 115; original JSON pointer: `/1405`

注释 除非你以前选择了一个基于 NRTL的物性方法 ,否则在 Binary Interaction Object

## UG10-CH08-D121

PDF page: 115; original JSON pointer: `/1406`

Manager(二元交互参数 对象管理器)看不到NRTL-1参数 (关于 规定物性方法 参见第7

## UG10-CH08-D122

PDF page: 115; original JSON pointer: `/1407`

输入来自 DECHEMA的二元参数

## UG10-CH08-D123

PDF page: 115; original JSON pointer: `/1408`

ASPEN PLUS 使用的方程形式不一致 然而 ,你可以使用 Properties Parameters Binary

## UG10-CH08-D124

PDF page: 115; original JSON pointer: `/1409`

Interaction 物性参数 二元交互参数 页面上的Dechema按钮 无需任何转换 直接输入温

## UG10-CH08-D125

PDF page: 115; original JSON pointer: `/1410`

若输入来自DECHEMA的二元参数:

## UG10-CH08-D126

PDF page: 115; original JSON pointer: `/1411`

1. 从Data(数据)菜单上 单击Properties(物性)

## UG10-CH08-D127

PDF page: 115; original JSON pointer: `/1412`

2. 在Data Browser(数据浏览器)的左画面中 双击Parameter(参数)文件夹

## UG10-CH08-D128

PDF page: 115; original JSON pointer: `/1413`

3. 单击Binary Interaction 二元交互参数 文件夹 打开含有由你指定的物性方法使 用的二元参数集的Object Manager(对象管理器)

## UG10-CH08-D129

PDF page: 115; original JSON pointer: `/1414`

4. 在Object Manager(对象管理器)上 选择NRTL-1 ,WILSON-1或UNIQ-1并选择 Edit

## UG10-CH08-D130

PDF page: 115; original JSON pointer: `/1415`

5. 在Input 输入 页面上的Component i和组分Component j框里输入组分对

## UG10-CH08-D131

PDF page: 115; original JSON pointer: `/1416`

6. 针对所选择的适当的组分对,单击Dechema按钮

## UG10-CH08-D132

PDF page: 115; original JSON pointer: `/1417`

7. 在Dechema Binary Parameters (Dechema 二元参数)对话框里,输入二元参数值 你还可以指定参数是来自VLE集还是来自LLE集

## UG10-CH08-D133

PDF page: 115; original JSON pointer: `/1418`

8. 单击OK. ASPEN PLUS 转换你输入的二元参数并在Input(输入)菜单显示被转换数值 ASPEN PLUS 数据库包含Aspen Technologhy公司开发的参数和由DECHEMA Chemistry Data Series(DECHEMA 化学数据系列)得到的参数(数据库名=VLE-LIT) 你一般很少需要 输入来自DECHEMA Chemistry Data Series(DECHEMA 化学数据系列)的二元参数

## UG10-CH08-D134

PDF page: 116; original JSON pointer: `/1420`

输入来自 DECHEMA的NRTL二元参数的例子

## UG10-CH08-D135

PDF page: 116; original JSON pointer: `/1421`

输入下列乙醇 (i)和水 (j)的二元参数 ,这些参数来自 DECHEMA Chemistry Data

## UG10-CH08-D136

PDF page: 116; original JSON pointer: `/1422`

使用Properties Parameter Binary Interaction ( 物性参数 二元交互作用参数)表,你可以

## UG10-CH08-D137

PDF page: 116; original JSON pointer: `/1423`

进入Properties Parameters Binary Interaction Object Manager(物性参数 二元交互

## UG10-CH08-D138

PDF page: 116; original JSON pointer: `/1424`

选择想要选择的WILSON-1 NRTL-1或UNIQ-1二元参数表并选择Edit(编辑)

## UG10-CH08-D139

PDF page: 116; original JSON pointer: `/1425`

在Input(输入)页中, 选择Estimate All Missing Parameters by UNIFAC 由UNIFAC

## UG10-CH08-D140

PDF page: 116; original JSON pointer: `/1426`

估计所有缺少的参数 检查框

## UG10-CH08-D141

PDF page: 116; original JSON pointer: `/1427`

使用Properties Parameters Electrolyte Pair 物性参数 电解质对 表页来输入用于电解

## UG10-CH08-D142

PDF page: 116; original JSON pointer: `/1428`

1. 从Data(数据)菜单上 单击Properties(物性)

## UG10-CH08-D143

PDF page: 116; original JSON pointer: `/1429`

2. 在Data Browser(数据浏览器)的左画面中 双击Parameter(参数)文件夹

## UG10-CH08-D144

PDF page: 116; original JSON pointer: `/1430`

3. 单击Electrolyte Pair 电解质对 文件夹

## UG10-CH08-D145

PDF page: 116; original JSON pointer: `/1431`

4. 在Electrolyte Pair Object Manager(电解质对 对象管理器)上 选择一个参数名 并单击Edit 编辑

## UG10-CH08-D146

PDF page: 116; original JSON pointer: `/1432`

5. 在Input(输入)菜单上 定义你要输入值的分子 电解质和电解质 电解质对

## UG10-CH08-D147

PDF page: 117; original JSON pointer: `/1434`

6. 为指定的对输入参数值 输入 NRTL电解质对参数的例子 对于盐水系统 输入下列NRTL电解质对参数(GMELCC) tH O NaCl2 8 572, .= tNaCl H O, .2 4 435= − NaCL完全电离成 a+和CL- 输入三元参数 当使用 Pitzer 电解质活度系数模型时 你可以用 Properties Parameters Electrolyte Ternary (物性参数 电解质三元参数)表来输入Pitzer三元参数

## UG10-CH08-D148

PDF page: 117; original JSON pointer: `/1435`

例如 你可以输入阳离子 阳离子 公共阴离子参数和阴离子 阴离子

## UG10-CH08-D149

PDF page: 117; original JSON pointer: `/1436`

1. 从Data(数据)菜单上 单击Properties(物性)

## UG10-CH08-D150

PDF page: 117; original JSON pointer: `/1437`

2. 在Data Browser(数据浏览器)的左画面中 双击Parameter(参数)文件夹

## UG10-CH08-D151

PDF page: 117; original JSON pointer: `/1438`

3. 单击电解质三元参数 Electrolyte Ternary 文件夹 在Electrolyte Ternary Object Manager(电解质三元参数 对象管理器)中 你可以建 立新的参数ID号 或者修改现有的ID号

## UG10-CH08-D152

PDF page: 117; original JSON pointer: `/1439`

4. 在Object Manager(对象管理器)中单击New,建立一个新的参数集

## UG10-CH08-D153

PDF page: 117; original JSON pointer: `/1440`

5. 在Create New ID 建立新的ID 对话框中 在ID框里输入一个ID号,或采用缺省 的ID号

## UG10-CH08-D154

PDF page: 117; original JSON pointer: `/1441`

7. 要修改现有的参数ID 需在Object Manager(对象管理器)上选择参数集的名 并单 击Edit(编辑)

## UG10-CH08-D155

PDF page: 118; original JSON pointer: `/1443`

8. 从Parameter(参数)列表中选择电解质三元参数

## UG10-CH08-D156

PDF page: 118; original JSON pointer: `/1444`

9. 用从View 视图 列表中选择Cation 阳离子 视图 通过列出两个阳离子和公共 阴离子来输入阳离子 阳离子 同阴离子参数和各自参数值 用所选择Cation 阳离子 视图 输入所有阳离子 阳离子 公共阴离子参数

## UG10-CH08-D157

PDF page: 118; original JSON pointer: `/1445`

10. 从View列表中选择Anion 阴离子

## UG10-CH08-D158

PDF page: 118; original JSON pointer: `/1446`

11. 通过列出两个阴离子和公共阳离子输入阴离子 阴离子 公共阳离子参数及 各自参数值 用所选择的Anion 阴离子 视图 输入所有阴离子 阴离子 公共阳离子参数 关于使用ASPEN PLUS的电解质功能的更多信息 参见第 章 输入 Pitzer电解质三元参数的例子 为NaCL/CaSO4系统 输入下列Pitzer三元参数 GMPTPS i j k ijky Na+ Ca+ Cl- -0.014 Na+ Ca+2 SO4-2 -0.023 Cl- SO4-2 Na+ 0.0014 Cl- SO4-2 Ca+2 0.0 Cation 阳离子 视图 Anion 阴离子 视图

## UG10-CH08-D159

PDF page: 119; original JSON pointer: `/1448`

l 给普通多项式模型输入多项式系数

## UG10-CH08-D160

PDF page: 119; original JSON pointer: `/1449`

l 为列表数据和多项式调整参考状态

## UG10-CH08-D161

PDF page: 120; original JSON pointer: `/1451`

ASPEN PLUS使用输入的列表数据和多项式系数计算组分的性质 如果你没有为所有

## UG10-CH08-D162

PDF page: 120; original JSON pointer: `/1452`

果有必要的话 ASPEN PLUS使用二次插入法模型来确定一给定温度的物性值 你应该按

## UG10-CH08-D163

PDF page: 120; original JSON pointer: `/1453`

如果温度超出你输入的最低或最高温度数据 ASPEN PLUS使用线性外插值法计算物 性 如果模型形式是对数的 ASPEN PLUS使用物性对数转换来内插和外插 对于多项式 模式 当温度超出关联式的上下限时 ASPEN PLUS使用线性外插法计算物性 如果你输入 那么 焓或热容数据 你可以使用Specifications页面上的Data Generation Options 来产生熵和Gibbs自由能 蒸汽焓数据 也输入理想气体焓以确保一致性 焓 熵和Gibbs自由能 确保它们是一致的 G=H-TS

## UG10-CH08-D164

PDF page: 120; original JSON pointer: `/1454`

若输入用于物性估算或数据回归的实验数据 请使用物性数据表 有关输入用于估算和 回归的数据的信息 请参见第三十和三十一章 输入表数据 若输入表数据

## UG10-CH08-D165

PDF page: 120; original JSON pointer: `/1455`

1. 在Data菜单上单击Properties

## UG10-CH08-D166

PDF page: 120; original JSON pointer: `/1456`

2. 从Data Browser 数据浏览器 左边面板上进到Properties Advanced Tabpoly Object Manager 物性 高级 列表 对象管理器

## UG10-CH08-D167

PDF page: 120; original JSON pointer: `/1457`

3. 单击New来建立一个新对象

## UG10-CH08-D168

PDF page: 121; original JSON pointer: `/1459`

4. 输入一个ID或接受缺省ID 然后单击OK

## UG10-CH08-D169

PDF page: 121; original JSON pointer: `/1460`

5. 在Specifications 规定 页面上 在Property 物性 列表中选择你要输入数据的 性质 在每一个Tabpoly表页上 你只能为一个性质输入数据 你只要需要 可以 使用任意多的表来输入数据

## UG10-CH08-D170

PDF page: 121; original JSON pointer: `/1461`

6. 在For Property Method 列表内 选择Tabpoly性质所用于的性质方法 指定All 时将数据用于模拟中所有的物性方法

## UG10-CH08-D171

PDF page: 121; original JSON pointer: `/1462`

7. 在Data 数据 页面上 从Component 组分 列表框内选择你已有数据的组分

## UG10-CH08-D172

PDF page: 121; original JSON pointer: `/1463`

8. 选择数据类型tabular Data 然后为组分输入列表数据 物性对应温度 你必须按递增的温度点次序来输入温度相关的列表数据 ASPEN PLUS根据你在 Data Browser 数据浏览器 工具栏上的Units 单位 列表框内所指定的Units-Set 单位集 来确定温度和物性数据的单位 为组分 CLP输入蒸汽压力数据的示例 本例中假定Data Browser 数据浏览器 工具栏上的Units 单位 列表框是引用一个新 单位集 该单位集的温度是0 C 压力是mmHg

## UG10-CH08-D173

PDF page: 121; original JSON pointer: `/1464`

8200 160 规定 页面和 数据 页面如下所示

## UG10-CH08-D174

PDF page: 122; original JSON pointer: `/1466`

为一般多项式模型输入多项式系数

## UG10-CH08-D175

PDF page: 122; original JSON pointer: `/1467`

若为一般多项式模型输入多项式系数

## UG10-CH08-D176

PDF page: 122; original JSON pointer: `/1468`

1. 在Data 数据 菜单上单击Properties 物性

## UG10-CH08-D177

PDF page: 122; original JSON pointer: `/1469`

2. 在数据浏览器左面板上双击Advanded 高级 文件夹

## UG10-CH08-D178

PDF page: 122; original JSON pointer: `/1470`

3. 单击Tabpoly 文件夹

## UG10-CH08-D179

PDF page: 122; original JSON pointer: `/1471`

4. 在Tabpoly Objeect Manager 列表多项式 对象管理器 上 单击New 来建立一个 对象

## UG10-CH08-D180

PDF page: 122; original JSON pointer: `/1472`

5. 输入一个ID或接受缺省ID 然后单击OK

## UG10-CH08-D181

PDF page: 122; original JSON pointer: `/1473`

6. 在Specifications (规定)页面上 在Property (物性)列表框内指定你要为其输入多 项式系数的物性 在每一个表内你只能为一个物性输入多项式系数 你可以使用任 意多的表来输入系数

## UG10-CH08-D182

PDF page: 122; original JSON pointer: `/1474`

7. 在For Property Method 列表框 选择用于Tabploy性质的性质方法 你可以指定All 来将数据用于模拟中所有性质方法

## UG10-CH08-D183

PDF page: 122; original JSON pointer: `/1475`

8. 在Data (数据)页面上 从Component 组分 列表中选择你已有其系数的组分

## UG10-CH08-D184

PDF page: 122; original JSON pointer: `/1476`

9. 选择数据类型 Polynomial Coefficient 多项式系数 然后 输入所选组分的一 般多项式系数 多项式模型具有下列形式 Ta T a T a T aTaTaTaa ln y)ln(propert property

## UG10-CH08-D185

PDF page: 122; original JSON pointer: `/1477`

321 +++++++=    或 参见Tabpoly Properties(Tabploy 物性)表确定你要输入的物性是使用普通形式还是使用 对数形式 系数a2到a8缺省为零 关联式温度下限 最小温度 缺省为 0 K 温度上限 最大温度 缺省为1000K 当温度超出限制时 ASPEN PLUS按线性外推法计算物性 在Data Browser(数据浏览器)工具栏上Units (单位)列表框里规定的单位集确定了系数 值的单位 如果a5 a6 a7 a8不是零 ASPEN PLUS认为所有参数为绝对温度单位

## UG10-CH08-D186

PDF page: 123; original JSON pointer: `/1479`

调整 Tabular(表)数据和多项式的参考状态

## UG10-CH08-D187

PDF page: 123; original JSON pointer: `/1480`

ASPEN PLUS 可以调整输入的焓 熵 和Gibbs自由能数据的参考状态 若指定使用该

## UG10-CH08-D188

PDF page: 123; original JSON pointer: `/1481`

1. 在Tabpoly Specification Tabpoly规定 页面上 对于你的表列数据或多项式数据 取消选择Do Not Adjust Reference State 不调整参考状态 检查框

## UG10-CH08-D189

PDF page: 123; original JSON pointer: `/1482`

2. 在Basis 基准 列表框里 为你的参考值和数据指定基准 Mole或Mass

## UG10-CH08-D190

PDF page: 123; original JSON pointer: `/1483`

3. 在Reference Points(参考点)页面上 在Component 组分 列表框里 选择要调整 参考状态的组分

## UG10-CH08-D191

PDF page: 123; original JSON pointer: `/1484`

4. 在Reference Points 参考点 框里输入焓 熵 或Gibbs自由能的参考温度和参考 值

## UG10-CH08-D192

PDF page: 123; original JSON pointer: `/1485`

5. 如果你要输入参考值并让ASPEN PLUS由你输入焓 热容数据来生成熵 Gibbs自 由能 你必须输入三个物性中的两个物性的参考值 参考值必须在同一温度下

## UG10-CH08-D193

PDF page: 123; original JSON pointer: `/1486`

6. 若使用ASPEN PLUS 缺省参考状态 在Reference Points(参考点)页面上不要输入 任何数据 然而 必须提供下列参数值 或在数据库中能得到下列参数值

## UG10-CH08-D194

PDF page: 123; original JSON pointer: `/1487`

l DHFORM DGFORM PLXANT

## UG10-CH08-D195

PDF page: 123; original JSON pointer: `/1488`

ASPEN PLUS 热力学参考状态是处于25和1atm理想气体状态下的组分构成元素

## UG10-CH08-D196

PDF page: 123; original JSON pointer: `/1489`

没有化学反应 你可以任意选择参考状态

## UG10-CH08-D197

PDF page: 123; original JSON pointer: `/1490`

有化学反应 你必须选择包括所有参加反应组分的DHFORM的参考状态

## UG10-CH08-D198

PDF page: 123; original JSON pointer: `/1491`

有平衡反应 你必须选择包括所有参加反应组分的DHFORM的参考状态

## UG10-CH08-D199

PDF page: 124; original JSON pointer: `/1493`

1. 进入有Tabpoly表的Reference Points(参考点)页面

## UG10-CH08-D200

PDF page: 124; original JSON pointer: `/1494`

2. 从Component 组分 列表框中选择你要指定参考压力的组分

## UG10-CH08-D201

PDF page: 124; original JSON pointer: `/1495`

正文待来源表达/OCR边界复核；原文本 SHA256: `412bde48746bb43855c505e0b73829c7e198cfe4852029bf49435b3a72a98ed9`。

## UG10-CH08-D202

PDF page: 124; original JSON pointer: `/1496`

需要增加或去掉一些组分并提供附加的交互作用参数

## UG10-CH08-D203

PDF page: 124; original JSON pointer: `/1497`

1 从File 文件 菜单中 单击Import 输入

## UG10-CH08-D204

PDF page: 124; original JSON pointer: `/1498`

2 在Import(输入)对话框里 单击Look In Favorites(在偏爱的文件夹中查找)按纽

## UG10-CH08-D205

PDF page: 124; original JSON pointer: `/1499`

3 从偏爱文件夹列表中 选择Data Packages

## UG10-CH08-D206

PDF page: 124; original JSON pointer: `/1500`

4 选择所需的数据包并单击Open(打开) 氨-水数据包 对于氨和水组成的系统请使用这个数据包 这个数据包使用电解质NRTL模型 这个数据包适用于温度范围是5-250C 压力最大100bar 乙烯数据包 请使用这个数据包模拟乙烯过程 这个数据包使用SR-POLAR状态方程模型 因为该方

## UG10-CH08-D207

PDF page: 125; original JSON pointer: `/1502`

这个数据包为建立乙烯过程模型提供非常好的起始点 通过回归缺少的二元参数或用基

## UG10-CH08-D208

PDF page: 125; original JSON pointer: `/1503`

于最新的实验数据更新现有参数 模拟结果可得以改进

## UG10-CH08-D209

PDF page: 125; original JSON pointer: `/1504`

ASPEN PLUS 为胺系统提供特殊数据包 插入包 MDEA DEA MEA DGA和AMP

## UG10-CH08-D210

PDF page: 125; original JSON pointer: `/1505`

这些插入数据包使用电解质功能 但是 也考虑了CO2在液相中的动力学反应 反应动

## UG10-CH08-D211

PDF page: 125; original JSON pointer: `/1506`

工业应用证实 这些数据包得到的结果比那些不考虑动力学反应的数据包更准确

## UG10-CH08-D212

PDF page: 125; original JSON pointer: `/1507`

系统 插入包名 温度 C 胺浓度

## UG10-CH08-D213

PDF page: 125; original JSON pointer: `/1508`

1. 进入File(文件)菜单 单击Import(输入)

## UG10-CH08-D214

PDF page: 125; original JSON pointer: `/1509`

2. 在Import(输入)对话框 单击Look In Favorites 在喜爱文件夹中查找 按钮

## UG10-CH08-D215

PDF page: 125; original JSON pointer: `/1510`

3. 从喜爱文件夹列表中 选择Data Packages(数据包)

## UG10-CH08-D216

PDF page: 125; original JSON pointer: `/1511`

4. 选择想要选择的数据包并单击Open 打开)

## UG10-CH08-D217

PDF page: 125; original JSON pointer: `/1512`

5. 在Parameter Values (参数值)对话框里 通过首先选择Parameter(参数) 然后 单击 Edit Value(编辑参数值)按钮 为胺 CO2和H2S输入组分ID号 确保在一个单元操作模型的 Properties Specifications Global页面和 Block Options Proerties页面上使用真实组分方法 对于所有使用动力学反应的氨数据包 这是必 需的

## UG10-CH08-D218

PDF page: 125; original JSON pointer: `/1513`

6. 如果你正在使用RADFRAC或RATEFRAC 对于模型的Reactions 反应 表页上指 定下列的反应ID之一: 反应 ID 所模拟的应用 所使用数据包 MDEA-CO2 CO2/H2S吸收 KEMDEA MDEA-ACID CO2/H2S吸收 KEMDEA MEA-CO2 CO2吸收 KEDEA MEA-ACID CO2/H2S吸收 KEDEA DEA-CO2 CO2/H2S吸收 KEDEA DEA-ACID CO2/H2S吸收 KEDEA

## UG10-CH08-D219

PDF page: 126; original JSON pointer: `/1515`

这个数据包使用Schwartzentruber -Renon状态方程模型 SR-POLAR

## UG10-CH08-D220

PDF page: 126; original JSON pointer: `/1516`

1. PITZ-1:用于预测 250 C 水中矿物质溶解度 系统是 Na-K-Mg-ca-H-Cl-SO4-OH-HCO3_CO2_H2O

## UG10-CH08-D221

PDF page: 126; original JSON pointer: `/1517`

2. PITZ-2: 用于预测水中矿物质溶解度 系统是 Na-K-Ca-Cl-H2O和Na-Ca-Cl- SO4-H2O 表观组分是 H2O NACL KCL CACL2 ACL2*4H2O CACL2*6H2O BACL2 ACL2*2H2O 温度范围 最高2000 C 压力范围 1个大气压

## UG10-CH08-D222

PDF page: 127; original JSON pointer: `/1519`

3. PITZ-3 用于Na-K-Ca-Cl-SO4-NO3_H2O系统 表观组分是 H2O NA2SO4 NACL NA2SO4*10H2O NA2CA(SO4)2 NA4CA(SO4)3*2H2O NANO3 K2SO4 KCL K2CA(SO4)2*H2O KNO3 CACL2 CASO4 CACL2 CACL2*6H2O CASO4*2H2O 2(CASO4)**H2O CACL2*4H2O CA(NO3)2 CA(NO3)2*4H2O. 温度范围 0-2500 C

## UG10-CH08-D223

PDF page: 127; original JSON pointer: `/1520`

4. PITZ-4用于 H2O-NaCl-Na2SO4-KCl-K2SO4-CaCl2-CaSO4-MgCl2-MgSO4-CaCl12*6H2O- MgCl12*6H2O-MgCl12*8H2O-MgCl12*12H2O-KMgCl13*6H2O-Mg2CaCl6*12H 2O-Na2SO4*10H2O-MgSO4*6H2O-MgSO4*7H2O-K2Mg(SO4)2*6H2O 温度范围 -60--250 C 甲基胺数据包 这个数据包用于模拟甲基胺工艺过程 这个系统是高度非理想系统 组分包括 胺 水 甲醇 甲基胺 二甲基胺和三甲基胺

## UG10-CH08-D224

PDF page: 127; original JSON pointer: `/1521`

用于描述VLE数据的物性模型是SR-POLAR状态等式 回归中使用了NH3-H2O和甲醇-

## UG10-CH08-D225

PDF page: 127; original JSON pointer: `/1522`

H2ohc.bkp H2O-HCL(作为HENRY组分)

## UG10-CH08-D226

PDF page: 127; original JSON pointer: `/1523`

Ehno3.bkp H2O-HNO3

## UG10-CH08-D227

PDF page: 127; original JSON pointer: `/1524`

Enaoh.bkp H2O-NAOH

## UG10-CH08-D228

PDF page: 127; original JSON pointer: `/1525`

Eso4br.bkp H2O-H2SO4-HBR

## UG10-CH08-D229

PDF page: 127; original JSON pointer: `/1526`

Ehbr.bkp H2O-HBR

## UG10-CH08-D230

PDF page: 127; original JSON pointer: `/1527`

Ehi.bkp H2O-HI

## UG10-CH08-D231

PDF page: 127; original JSON pointer: `/1528`

Eh2so4.bkp H2O-H2SO4

## UG10-CH08-D232

PDF page: 127; original JSON pointer: `/1529`

Ehclmg.bkp H2O-HCL-MGCL2

## UG10-CH08-D233

PDF page: 127; original JSON pointer: `/1530`

Enaohs.bkp H2O-NAOH-SO2

## UG10-CH08-D234

PDF page: 127; original JSON pointer: `/1531`

Eso4cl.bkp H2O-H2SO4-HCL

## UG10-CH08-D235

PDF page: 127; original JSON pointer: `/1532`

Ecauts.bkp H2O-NAOH-NACL-NA2SO4-NA2SO4.HH2OH2O-NA2SO4.NA

## UG10-CH08-D236

PDF page: 127; original JSON pointer: `/1533`

Ekoh.bkp H2O-KOH

## UG10-CH08-D237

PDF page: 127; original JSON pointer: `/1534`

Ecaust.bkp H2O-NAOH-NACL-NA2SO4

## UG10-CH08-D238

PDF page: 127; original JSON pointer: `/1535`

Ehcl.bkp H2O-HCL(作为溶剂)

## UG10-CH08-D239

PDF page: 127; original JSON pointer: `/1536`

Ehclle.bkp H2O-HCL(作为溶剂,推荐LLE)

## UG10-CH08-D240

PDF page: 127; original JSON pointer: `/1537`

Edea.bkp H2O-DEA-H2S-CO2

## UG10-CH08-D241

PDF page: 127; original JSON pointer: `/1538`

Ehotde.bkp H2O-DEA-K2CO3-H2S-CO2

## UG10-CH08-D242

PDF page: 127; original JSON pointer: `/1539`

Emea.bkp H2O-MWA-H2S-CO2

## UG10-CH08-D243

PDF page: 128; original JSON pointer: `/1541`

Ecl2.bkp H2O-CL2-HCL

## UG10-CH08-D244

PDF page: 128; original JSON pointer: `/1542`

Enh3co.bkp H2H2O-NH3-CO2

## UG10-CH08-D245

PDF page: 128; original JSON pointer: `/1543`

Enh3so.bkp H2H2O-NH3-SO2

## UG10-CH08-D246

PDF page: 128; original JSON pointer: `/1544`

Esouro.bkp H2O-NH3-H2S-CO2-NAOH

## UG10-CH08-D247

PDF page: 128; original JSON pointer: `/1545`

Edga.bkp H2O-DGA-H2S-CO2

## UG10-CH08-D248

PDF page: 128; original JSON pointer: `/1546`

Enh3h2.bkp H2O-NH3-H2S

## UG10-CH08-D249

PDF page: 128; original JSON pointer: `/1547`

Eamp.bkp H2O-AMP-H2S-CO2

## UG10-CH08-D250

PDF page: 128; original JSON pointer: `/1548`

Ehotca.bkp H2O-K2CO3-CO2

## UG10-CH08-D251

PDF page: 128; original JSON pointer: `/1549`

Enh3hc.bkp H2O-NH3-HCN

## UG10-CH08-D252

PDF page: 128; original JSON pointer: `/1550`

Ebrine.bkp H2O-CO2-H2S-NACL

## UG10-CH08-D253

PDF page: 128; original JSON pointer: `/1551`

Ebrinx.bkp H2O-CO2-H2S-NCAL(扩展的温度范围)

## UG10-CH08-D254

PDF page: 128; original JSON pointer: `/1552`

Eclscr.bkp H2O-CL2-CO2-HCL-NAOH-NACL-NA2CO3

## UG10-CH08-D255

PDF page: 128; original JSON pointer: `/1553`

Ekohx.bkp H2O-KOH(高浓度)

## UG10-CH08-D256

PDF page: 128; original JSON pointer: `/1554`

Ehf.bkp H2O-HF

## UG10-CH08-D257

PDF page: 128; original JSON pointer: `/1555`

Ehotcb.bkp H2O-K2CO3-CO2-KHCO3

## UG10-CH08-D258

PDF page: 128; original JSON pointer: `/1556`

Emdea.bkp H2O-MDEA-CO2-H2S

## UG10-CH08-D259

PDF page: 128; original JSON pointer: `/1557`

Enh3po.bkp H2O-NH3-H3PO4-H2S

## UG10-CH08-D260

PDF page: 128; original JSON pointer: `/1558`

Esour.bkp H2O-NH3-H2S-CO2

## UG10-CH08-D261

PDF page: 128; original JSON pointer: `/1559`

Brine.bkp H2O-CO2-H2S-NACL

## UG10-CH08-D262

PDF page: 128; original JSON pointer: `/1560`

Caust.bkp H2O-NAOH-NACL-NA2SO4

## UG10-CH08-D263

PDF page: 128; original JSON pointer: `/1561`

Causts.bkp H2O-NAOH-NACL-NA2SO4-NA2SO4.10H2O-NA2SO4.NAOH

## UG10-CH08-D264

PDF page: 128; original JSON pointer: `/1562`

Dea.bkp H2O-DEA-H2S-CO2

## UG10-CH08-D265

PDF page: 128; original JSON pointer: `/1563`

Dga.bkp H2O-DGA-H2S-CO2

## UG10-CH08-D266

PDF page: 128; original JSON pointer: `/1564`

H2ohbr.bkp H2O-HBR

## UG10-CH08-D267

PDF page: 128; original JSON pointer: `/1565`

H2ohf.bkp H2O-HF

## UG10-CH08-D268

PDF page: 128; original JSON pointer: `/1566`

H2ohi.bkp H2O-HI

## UG10-CH08-D269

PDF page: 128; original JSON pointer: `/1567`

Hotca.bkp H2O-K2CO3-CO2

## UG10-CH08-D270

PDF page: 128; original JSON pointer: `/1568`

Hotcb.bkp H2O-K2CO3-CO2-KHCO3

## UG10-CH08-D271

PDF page: 128; original JSON pointer: `/1569`

Hotdea.bkp H2O-DEA-K2CO3-H2S-CO2

## UG10-CH08-D272

PDF page: 128; original JSON pointer: `/1570`

Mcl2.bkp H2O-CL2

## UG10-CH08-D273

PDF page: 128; original JSON pointer: `/1571`

Mdea.bkp H2O-MDEA-H2S-CO2

## UG10-CH08-D274

PDF page: 128; original JSON pointer: `/1572`

Mea.bkp H2O-MEA-H2S-CO2

## UG10-CH08-D275

PDF page: 128; original JSON pointer: `/1573`

Mh2so4.bkp H2O-H2SO4

## UG10-CH08-D276

PDF page: 128; original JSON pointer: `/1574`

Mhbr.bkp H2O-HBR

## UG10-CH08-D277

PDF page: 128; original JSON pointer: `/1575`

Mhcl.bkp H2O-HCL

## UG10-CH08-D278

PDF page: 128; original JSON pointer: `/1576`

Mhcl1.bkp H2O-HCL

## UG10-CH08-D279

PDF page: 128; original JSON pointer: `/1577`

Mhclmg.bkp H2O-HCL-MGCL2

## UG10-CH08-D280

PDF page: 128; original JSON pointer: `/1578`

Mhf.bkp H2O-HF

## UG10-CH08-D281

PDF page: 128; original JSON pointer: `/1579`

Mhf2.bkp H2O-HF(至100%HF)

## UG10-CH08-D282

PDF page: 128; original JSON pointer: `/1580`

Mhno3.bkp H2O-HNO3

## UG10-CH08-D283

PDF page: 128; original JSON pointer: `/1581`

Mnzoh.bkp H2O-NAOH

## UG10-CH08-D284

PDF page: 129; original JSON pointer: `/1583`

Mnaoh1.bkp H2O-NAOH

## UG10-CH08-D285

PDF page: 129; original JSON pointer: `/1584`

Mso4br.bkp H2O-H2SO4-HBR

## UG10-CH08-D286

PDF page: 129; original JSON pointer: `/1585`

Mso4cl.bkp H2O-H2SO4-HCL

## UG10-CH08-D287

PDF page: 129; original JSON pointer: `/1586`

Naohso.bkp H2O-NAOH-SO2

## UG10-CH08-D288

PDF page: 129; original JSON pointer: `/1587`

Nh3co2.bkp H2O-NH3-CO2

## UG10-CH08-D289

PDF page: 129; original JSON pointer: `/1588`

Nh3h2s.bkp H2O-NH3-H2S

## UG10-CH08-D290

PDF page: 129; original JSON pointer: `/1589`

Nh3hcn.bkp H2O-HCN

## UG10-CH08-D291

PDF page: 129; original JSON pointer: `/1590`

Nh3po4.bkp H2O-NH3-H2S-H3PO4

## UG10-CH08-D292

PDF page: 129; original JSON pointer: `/1591`

Nh3so2.bkp H2O-NH3-SO2

## UG10-CH08-D293

PDF page: 129; original JSON pointer: `/1592`

Sour.bkp H2O-NH3-H2S-CO2

## UG10-CH08-D294

PDF page: 129; original JSON pointer: `/1593`

Souroh.bkp H2O-NH3-H2S-CO2-NAOH

## UG10-CH08-D295

PDF page: 129; original JSON pointer: `/1594`

Pnh3co.bkp H2O-NH3-CO2

## UG10-CH08-D296

PDF page: 129; original JSON pointer: `/1595`

Pnh3h2.bkp H2O-NH3

## UG10-CH08-D297

PDF page: 129; original JSON pointer: `/1596`

Pnh3so.bkp H2O-NH3-SO2

## UG10-CH08-D298

PDF page: 129; original JSON pointer: `/1597`

Psour.bkp H2O-NH3-H2S-CO2

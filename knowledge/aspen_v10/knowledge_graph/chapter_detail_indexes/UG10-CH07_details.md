# UG10-CH07 Detail Operation Index - 第7章 物性方法

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH07-D001

PDF page: 87; original JSON pointer: `/1168`

选择接近的物性方法经常是决定你的模拟结果的精确度的关键步骤 本章提供了选择接

## UG10-CH07-D002

PDF page: 87; original JSON pointer: `/1169`

l 规定一个流程段的物性方法

## UG10-CH07-D003

PDF page: 87; original JSON pointer: `/1170`

ASPEN PLUS 包括大量内置的物性方法 足以满足大部分的应用 但是 你可以建立

## UG10-CH07-D004

PDF page: 87; original JSON pointer: `/1171`

你必须选择一个或多个 Property Methods 物性方法 做流程中特殊系统物性的模型

## UG10-CH07-D005

PDF page: 88; original JSON pointer: `/1173`

你可以改变这些已有的方法或建立新的方法 有关更详细的资料 参见第七章 修改物

## UG10-CH07-D006

PDF page: 88; original JSON pointer: `/1174`

状态方程物性方法 K 值方法

## UG10-CH07-D007

PDF page: 89; original JSON pointer: `/1176`

WILS-LR Wilson (液体焓参考状态) 理想气体

## UG10-CH07-D008

PDF page: 89; original JSON pointer: `/1177`

CHAO-SEA Chao-Seader 对应的状态模型 石油

## UG10-CH07-D009

PDF page: 89; original JSON pointer: `/1178`

GRAYSON Grayson-Streed 对应的状态

## UG10-CH07-D010

PDF page: 89; original JSON pointer: `/1179`

STEAMNBS NBS/NRC 蒸汽表状态方程 水/蒸汽

## UG10-CH07-D011

PDF page: 89; original JSON pointer: `/1180`

使用本章从下表开始到下一节的表和图给你的模拟选择最好的物性方法 更详细的资

## UG10-CH07-D012

PDF page: 89; original JSON pointer: `/1181`

料 也看第八章对每个物性方法的数据要求的详细说明 很多方法包含扩展的内置二元参数

## UG10-CH07-D013

PDF page: 89; original JSON pointer: `/1182`

用这些表作为指南给你的模拟选择最好的物性方法

## UG10-CH07-D014

PDF page: 93; original JSON pointer: `/1187`

下图指出了选择物性方法的过程

## UG10-CH07-D015

PDF page: 94; original JSON pointer: `/1189`

选择极性非电解质系统的物性方法指南

## UG10-CH07-D016

PDF page: 95; original JSON pointer: `/1191`

选择活度系数物性方法常用指南

## UG10-CH07-D017

PDF page: 96; original JSON pointer: `/1193`

如果你没有对一个特殊的流程段 单元操作模块或物性分析规定一个不同的物性方法 ASPEN PLUS 对所有物性计算使用全局的物性方法 规定全局的物性方法

## UG10-CH07-D018

PDF page: 96; original JSON pointer: `/1194`

1. 从 Data 菜单 单击 Properties

## UG10-CH07-D019

PDF page: 96; original JSON pointer: `/1195`

2. 在 Global 页的 Property Method 列表框中 规定物性方法 你也可以使用 Process Type 列表框帮助你选择一个合适的物性方法 在 Process Type 列 表框中 选择你要模拟的工艺过程类型 每个工艺过程类型都有一个推荐的物性方法列表 关于工艺类型的更详细资料 参见第二章

## UG10-CH07-D020

PDF page: 96; original JSON pointer: `/1196`

3. 在 Base Method 列表框中 选择一个基本的物性方法

## UG10-CH07-D021

PDF page: 96; original JSON pointer: `/1197`

4. 如果你正在使用一个活度系数物性方法 并且对超临界组分要使用亨利定律 在 Henry Components 列表框中规定亨利组分列表 ID 标识 关于亨利组分的更详细 资料 参见本章 定义超临界组分

## UG10-CH07-D022

PDF page: 96; original JSON pointer: `/1198`

5. 如果你做一个石油方面的应用 需要游离水计算 在 Free-Water Method 列表框中 规定游离水相的物性方法 在 Water Solubility 列表框中规定水的溶解度选项 关 于更详细资料 参见本章 使用游离水计算

## UG10-CH07-D023

PDF page: 96; original JSON pointer: `/1199`

6. 对于电解质的应用 你必须选择电解质物性方法 然后在 Chemistry ID 列表框中选 择 Chemistry ID 你也可以在 Use True-Components 复选框中规定电解质计算方法 规定流程段的物性方法 当你在模拟中正在使用不只一种物性方法时 使用流程段去简化物性方法的分配 例如 你可以把一个流程段分成高压和低压段 并对每一段给出一个接近的物性方法 有关流程段的详细资料参见第三章 包括怎样去建立一个流程段 规定一个流程段的物性方法

## UG10-CH07-D024

PDF page: 96; original JSON pointer: `/1200`

1 从 Data 菜单 单击 Properties

## UG10-CH07-D025

PDF page: 96; original JSON pointer: `/1201`

2 在 Flowsheet Sections 页上 从 Flowsheet Section ID 列表框选择流程段

## UG10-CH07-D026

PDF page: 96; original JSON pointer: `/1202`

3 在 Property Method 列表框中 规定物性方法 你也可以使用 Process Type 列表框帮助你选择一个合适的物性方法 在 Process Type 列 表框中 选择你要模拟的工艺过程类型 每个工艺过程类型都有一个推荐的物性方法列表 关于过程类型的更详细资料 参见第二章

## UG10-CH07-D027

PDF page: 96; original JSON pointer: `/1203`

4 在 Base Method 列表框中 选择一个基本的物性方法

## UG10-CH07-D028

PDF page: 96; original JSON pointer: `/1204`

5 如果你正在使用一个活度系数物性方法 并且对超临界组分要使用亨利定律 在 Henry Components 列表框中规定亨利组分列表 ID 标识 关于亨利组分的更详细 资料 参见本章上 Defining Supercritical Components 定义超临界组分

## UG10-CH07-D029

PDF page: 96; original JSON pointer: `/1205`

6 如果你做一个石油方面的应用 需要游离水计算 在 Free-Water Method列表框中规 定游离水相的物性方法 在 Water Solubility 列表框中规定水的溶解性选项 关于更 详细资料 参见本章上 Using Free Water Calculations 使用游离水计算

## UG10-CH07-D030

PDF page: 96; original JSON pointer: `/1206`

7 对于电解质的应用 你必须选择电解质物性方法 然后在 Chemistry ID 列表框中选 择 Chemistry ID 你也可以在 Use True-Components 复选框中规定电解质计算方法

## UG10-CH07-D031

PDF page: 97; original JSON pointer: `/1208`

你可以不考虑全局的物性方法 规定一个局部的物性方法在

## UG10-CH07-D032

PDF page: 97; original JSON pointer: `/1209`

l BlockOptions Properties 页 对单元操作模块

## UG10-CH07-D033

PDF page: 97; original JSON pointer: `/1210`

l Properties 页 对 Properties Analysis

## UG10-CH07-D034

PDF page: 97; original JSON pointer: `/1211`

你在 Properties 页上输入的规定仅用于单元操作模块或物性分析

## UG10-CH07-D035

PDF page: 97; original JSON pointer: `/1212`

对下面的单元操作模型 你可以给模块中的物流或段规定不同的物性方法

## UG10-CH07-D036

PDF page: 97; original JSON pointer: `/1213`

模型 页 允许你规定物性方法对

## UG10-CH07-D037

PDF page: 97; original JSON pointer: `/1214`

Decanter Decanter Properties Phase Property 液相 1 和液相 2

## UG10-CH07-D038

PDF page: 97; original JSON pointer: `/1215`

RadFrac Radfrac Properties Property Sections 塔段 倾析器 热虹吸式再沸器

## UG10-CH07-D039

PDF page: 97; original JSON pointer: `/1216`

RGibbs Rgibbs Setup Products 每个相态

## UG10-CH07-D040

PDF page: 97; original JSON pointer: `/1217`

MultiFrac Multifrac Properties Property Sections 塔段

## UG10-CH07-D041

PDF page: 97; original JSON pointer: `/1218`

PetroFrac Petrofrac Properties Property Sections

## UG10-CH07-D042

PDF page: 97; original JSON pointer: `/1219`

Petrofrac Stripper Properties Property

## UG10-CH07-D043

PDF page: 97; original JSON pointer: `/1220`

HeatX Heatx BlockOptions Properties 换热器的热侧和冷侧

## UG10-CH07-D044

PDF page: 97; original JSON pointer: `/1221`

MHeatX Mheatx BlockOptions Properties 换热器中的每股物流

## UG10-CH07-D045

PDF page: 97; original JSON pointer: `/1222`

RPlug Rplug BlockOptions Properties 反应物和外部冷剂物流

## UG10-CH07-D046

PDF page: 97; original JSON pointer: `/1223`

使用 Properties Specifications Referenced 页输入单元操作模块或物性分析计算中使用的

## UG10-CH07-D047

PDF page: 97; original JSON pointer: `/1224`

当完成一个交互的物性分析时 你可以选择在 Properties Specifications Referenced 页上

## UG10-CH07-D048

PDF page: 97; original JSON pointer: `/1225`

正文待来源表达/OCR边界复核；原文本 SHA256: `1f6cfbf6d68c507ce9de55fb180fd1c796b45a20fa9e2ba10143607199c25074`。

## UG10-CH07-D049

PDF page: 97; original JSON pointer: `/1226`

2. 使用 Henry Comps 窗口定义亨利组分组 关于更详细资料参见第 6 章

## UG10-CH07-D050

PDF page: 97; original JSON pointer: `/1227`

3. 在 Properties Specifications Global 页 使用流程段规定的 Flowsheet Sections 页 或 BlockOptions Properties 页 单元操作模型局部的规定 上输入亨利组分组的 ID 关于亨利定律的更详细资料 参见 ASPEN PLUS 物性方法和模型 状态方程物性方法对于超临界组分不需要特殊处理

## UG10-CH07-D051

PDF page: 98; original JSON pointer: `/1229`

关于游离水计算要求的更详细资料 参见第五章

## UG10-CH07-D052

PDF page: 98; original JSON pointer: `/1230`

注意 你也可以对各物流和模块局部地规定游离水计算 关于游离水计算的更详细资料

## UG10-CH07-D053

PDF page: 98; original JSON pointer: `/1231`

当你使用游离水近似法时 你必须规定适用于游离水相的物性方法 这种物性方法计算

## UG10-CH07-D054

PDF page: 98; original JSON pointer: `/1232`

1. 打开单元操作模型的 Properties Specifications Global 页或 Flowsheet Sections 页或 BlockOptions Properties 页

## UG10-CH07-D055

PDF page: 98; original JSON pointer: `/1233`

正文待来源表达/OCR边界复核；原文本 SHA256: `bc258b45b76c9df9c5db24aa9765912f711b82e111991718e5ede1ae9c8bdd17`。

## UG10-CH07-D056

PDF page: 99; original JSON pointer: `/1235`

1. 打开单元操作模型的 Properties Specifications Global 页或 Flowsheet Sections 页或 BlockOptions Properties 页

## UG10-CH07-D057

PDF page: 99; original JSON pointer: `/1236`

正文待来源表达/OCR边界复核；原文本 SHA256: `a18512a739658f49e41fc6ee6a543c56dd545bbd8be322a49865519083065514`。

## UG10-CH07-D058

PDF page: 99; original JSON pointer: `/1237`

模拟一个电解质系统 你必须

## UG10-CH07-D059

PDF page: 99; original JSON pointer: `/1238`

l 在 Reactions Chemistry Stoichiometry 页上定义溶液化学组成

## UG10-CH07-D060

PDF page: 99; original JSON pointer: `/1239`

l 在单元操作模型的 Properties Specifications Global 页或 Flowsheet Sections 页或

## UG10-CH07-D061

PDF page: 99; original JSON pointer: `/1240`

BlockOptions Properties 页上 在 Chemistry ID 列表框中选择适用于电解质物性方

## UG10-CH07-D062

PDF page: 99; original JSON pointer: `/1241`

l 使用 Use True Components 复选框规定真实组分或表观组分模拟方法

## UG10-CH07-D063

PDF page: 99; original JSON pointer: `/1242`

使用 Components Specifications Selection 页上的按钮 打开 Electrolytes Wizard 电解质

## UG10-CH07-D064

PDF page: 99; original JSON pointer: `/1243`

智能工具 它可以为你建立所有的这些规定 关于怎样使用 Electrolyte Wizard 电解质智

## UG10-CH07-D065

PDF page: 99; original JSON pointer: `/1244`

物性方法由计算路径 路线 和物性方程 模型 来定义 它决定怎样计算物性

## UG10-CH07-D066

PDF page: 100; original JSON pointer: `/1246`

l 所有气相物性计算的不同状态方程模型

## UG10-CH07-D067

PDF page: 100; original JSON pointer: `/1247`

l 使用 Racket 模型而不是立方状态方程计算液体摩尔体积的路线

## UG10-CH07-D068

PDF page: 100; original JSON pointer: `/1248`

关于物性模型和模型选项代码以及有关路线和怎样去创建它们的更详细资料 参见

## UG10-CH07-D069

PDF page: 100; original JSON pointer: `/1249`

在 Properties Specifications Global 页上或 Flowsheet Section 页上你可以对物性方法做上

## UG10-CH07-D070

PDF page: 100; original JSON pointer: `/1250`

1. 从 Data 菜单 单击 Properties

## UG10-CH07-D071

PDF page: 100; original JSON pointer: `/1251`

2. 在 Global 或 Flowsheet Sections 页上 在 Base Method 列表框中选择你要改变的物 性方法

## UG10-CH07-D072

PDF page: 100; original JSON pointer: `/1252`

3. 检查 Modify Property Models 复选框

## UG10-CH07-D073

PDF page: 100; original JSON pointer: `/1253`

4. 当提示时 给改变的物性方法输入一个新名 并且单击 OK 尽管它不需要 但是 高度推荐的是给改变物性方法规定一个新名 你可以做这些改变 在这个框中 去做这个 Vapor EOS 给所有气相物性计算选择一个状态方程模型 Liquid gamma 选择活度系数模型 Data set 给 EOS 或液体γ模型规定参数数据集号 Liquid enthalpy 选择计算液体混合物焓的路线 Liquid volume 选择计算液体混合物体积的路线

## UG10-CH07-D074

PDF page: 100; original JSON pointer: `/1254`

Poynting correction 规定是否在计算液体逸度系数时进行 Poynting 校正 当选

## UG10-CH07-D075

PDF page: 100; original JSON pointer: `/1255`

Heat of mixing 规定是否在液体混合物焓中包括混合热 当选择时 包括

## UG10-CH07-D076

PDF page: 100; original JSON pointer: `/1256`

对附加的和高级的修改 使用 Properties Methods 窗口

## UG10-CH07-D077

PDF page: 100; original JSON pointer: `/1257`

2. 在 Data Browser 的左屏中 双击 Property Methods 文件夹

## UG10-CH07-D078

PDF page: 100; original JSON pointer: `/1258`

3. Object Manager 出现

## UG10-CH07-D079

PDF page: 100; original JSON pointer: `/1259`

4. 选择你要修改的 Property Method 物性方法 并单击 Edit -或- 建立一个新的物性方法 单击 New 然后规定新的物性方法 使用 Routes 页规定物性路线 使用 Models 页规定物性模型 Routes 页显示用于计算每个物性基本的物性方法 物性和路线 ID 为了方便起见 物 性如下分类

## UG10-CH07-D080

PDF page: 101; original JSON pointer: `/1261`

若想在物性方法中修改路线 可以在 Route ID 框中选择想要的路线 你也可以 单击这个按钮 做这 个 Create 给选择的物性建立一个新的路线 Edit 修改一个选择的路线 View 看选择的路线的结构 结构准确地显示出路线是怎 样计算的和通过什么方法和模型 Models 页显示用于在物性方法中计算物性的物性模型 若想修改物性模型 在 Model Name 列中选择想要的模型 这个表描述了 Models 页上不同的框 使用这个框 规定 Model mame 你要用来计算每个物性的模型

## UG10-CH07-D081

PDF page: 101; original JSON pointer: `/1262`

Data set 模型参数的数据集数

## UG10-CH07-D082

PDF page: 101; original JSON pointer: `/1263`

Affected properties 影响模型的物性列表 模型用来计算一种以上的物

## UG10-CH07-D083

PDF page: 101; original JSON pointer: `/1264`

Option codes 模型选项代码 选项代码用来规定特殊的计算选项

## UG10-CH07-D084

PDF page: 101; original JSON pointer: `/1265`

这个表显示了煤和煤的衍生物的专用模型

## UG10-CH07-D085

PDF page: 102; original JSON pointer: `/1267`

规定用来计算非常规组分物性的模型:

## UG10-CH07-D086

PDF page: 102; original JSON pointer: `/1268`

1. 从 Data 菜单 单击 Properties

## UG10-CH07-D087

PDF page: 102; original JSON pointer: `/1269`

2. 双击 Advanced 文件夹

## UG10-CH07-D088

PDF page: 102; original JSON pointer: `/1270`

3. 选择 NC-Props 窗口

## UG10-CH07-D089

PDF page: 102; original JSON pointer: `/1271`

4. 在 Property Methods 页的 Component 列表框中 选择一个组分

## UG10-CH07-D090

PDF page: 102; original JSON pointer: `/1272`

5. 规定焓和密度模型 ASPEN PLUS 自动的给你规定的模型填充需要的组分属性

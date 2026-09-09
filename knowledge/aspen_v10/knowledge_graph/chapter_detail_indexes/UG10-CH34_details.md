# UG10-CH34 Detail Operation Index - 第34章 插入

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH34-D001

PDF page: 501; original JSON pointer: `/5989`

一个插入是可以转入运行的部分备用文件 ASPEN PLUS 提供专用数据包 作为插入

## UG10-CH34-D002

PDF page: 501; original JSON pointer: `/5990`

它可以用来作为创建新模拟的启动点 或把它们转入到已有的模拟中 在以后使用时你可以

## UG10-CH34-D003

PDF page: 501; original JSON pointer: `/5991`

本章讨论这些文件的使用 包括

## UG10-CH34-D004

PDF page: 501; original JSON pointer: `/5992`

l 使用 ASPEN PLUS插入库的电解质插入

## UG10-CH34-D005

PDF page: 501; original JSON pointer: `/5993`

l 物性包 包括组分和物性定义

## UG10-CH34-D006

PDF page: 501; original JSON pointer: `/5994`

你可以创建自己的插入 或者从 ASPEN PLUS 插入库转换插入 关于详细信息 参见

## UG10-CH34-D007

PDF page: 501; original JSON pointer: `/5995`

要创建一个插入 你必须保存一个备用文件 该文件包含你在插入中所需要的信息

## UG10-CH34-D008

PDF page: 501; original JSON pointer: `/5996`

1. 运行开始 它已有关于定义的插入的所有输入 运行不一定完成 它可以包含 可能的模拟输入 如组分 物性 物流 模块 流程选项 模型分析工具 等等

## UG10-CH34-D009

PDF page: 501; original JSON pointer: `/5997`

2. 在 File菜单上 单击 Export

## UG10-CH34-D010

PDF page: 501; original JSON pointer: `/5998`

3. 在 Save As Type 框里 选择 ASPEN PLUS Backup Files(*.bkp)

## UG10-CH34-D011

PDF page: 501; original JSON pointer: `/5999`

4. 对于你想包含插入的备用文件 为其输入目录和一个文件名

## UG10-CH34-D012

PDF page: 501; original JSON pointer: `/6000`

5. 单击 Save 你可以将创建的备用文件转入到运行里 转入插入 在已存在的 ASPEN PLUS 模拟中转入插入

## UG10-CH34-D013

PDF page: 501; original JSON pointer: `/6001`

1 在 ASPEN PLUS主窗口中有活动的模拟时 在 File菜单上 单击 Import

## UG10-CH34-D014

PDF page: 501; original JSON pointer: `/6002`

2 在 Save As Type 框里 选择 ASPEN PLUS Backup Files(*.bkp)

## UG10-CH34-D015

PDF page: 501; original JSON pointer: `/6003`

3 在 Import 对话框里 找到插入 然后单击 Open

## UG10-CH34-D016

PDF page: 501; original JSON pointer: `/6004`

4 如果出现 Resolve ID Conflicts 对话框 请参见后面的 Resolving ID Conflicts 部分 把插入已存在的运行中后 你的模拟就包括来自两个文件的输入 解决 ID 矛盾 当你把一个文件转入到另一个文件 一些被转入的对象可能和已有运行中的对象有相 同的 Ids 如果出现这个问题 ASPEN PLUS 就出现 Resolve ID Conflicts 对话框 它列出这 两个文件中的所有有匹配 IDs 的对象

## UG10-CH34-D017

PDF page: 502; original JSON pointer: `/6006`

用 Resolve ID Conflicts 对话框来解决 ID 矛盾 所用方法如下

## UG10-CH34-D018

PDF page: 502; original JSON pointer: `/6007`

替代存在对象 1 选择一个或多个对象

## UG10-CH34-D019

PDF page: 502; original JSON pointer: `/6008`

2 单击 Replace. ASPEN PLUS 删除当前运行中的对象并用转入的对象替代 合并新对象和存在对 象

## UG10-CH34-D020

PDF page: 502; original JSON pointer: `/6009`

2 单击 Merge. ASPEN PLUS合并插入对象和当前运行的对象的规定 如果两个对 象值有相同的规定 插入对象就取代当前运行的对象 直接编辑 IDs 1 一次选择一个对象

## UG10-CH34-D021

PDF page: 502; original JSON pointer: `/6010`

2 单击 Edit ID.

## UG10-CH34-D022

PDF page: 502; original JSON pointer: `/6011`

3 在 Object Name 对话框里 规定一个新的对象 ID 对存在的 IDs 加前缀 或后缀

## UG10-CH34-D023

PDF page: 502; original JSON pointer: `/6012`

2 单击 Add Prefix 或 Add Suffix

## UG10-CH34-D024

PDF page: 502; original JSON pointer: `/6013`

3 在 Prefix 或 Suffix 对话框里 输入字符加到当前运行的 IDs. 删除转换对象 1 选择一个或多个对象

## UG10-CH34-D025

PDF page: 502; original JSON pointer: `/6014`

2 单击 Delete. ASPEN PLUS从转换运行中删除选择对象 保持那些在当前运行中 的对象不变 当解决完每个 ID 矛盾后 单击 OK 合并的对象必须是同一类型 例如 你可以合并两个 RadFrac 模块 但不能合并 RadFra 模块和 Flash2 模块 转入插入和解决 ID 矛盾的例子 模拟一个在同一运行中有两个不同进料的蒸馏塔 蒸馏塔的规定是相似的

## UG10-CH34-D026

PDF page: 502; original JSON pointer: `/6015`

1 创建第一个进料的流程 完成所有问题规定

## UG10-CH34-D027

PDF page: 503; original JSON pointer: `/6017`

2 在 File菜单上 单击 Save As

## UG10-CH34-D028

PDF page: 503; original JSON pointer: `/6018`

3 在 Save As Type 框里 规定 ASPEN PLUS Backup Files(*.bkp) 在 File Name框里 给文件规定一个文件名 单击 OK

## UG10-CH34-D029

PDF page: 503; original JSON pointer: `/6019`

4 在 File菜单上 单击 Import

## UG10-CH34-D030

PDF page: 503; original JSON pointer: `/6020`

5 在 Save As Type 框里 选择 ASPEN PLUS Backup Files(*.bkp) 找到和选择你刚存 的文件 单击 OK

## UG10-CH34-D031

PDF page: 503; original JSON pointer: `/6021`

6 在 Resolve ID Conflicts 对话框里 选择模块和物流 在单击每一项时 按住 Ctrl 键 然后单击 Add Suffix.

## UG10-CH34-D032

PDF page: 503; original JSON pointer: `/6022`

7 在 Suffix 对话框里 输入-2 并单击 OK Resolve ID Conflicts 对话框就显示新的插入对象的 IDs

## UG10-CH34-D033

PDF page: 503; original JSON pointer: `/6023`

8. 在 Resolve ID Conflicts 对话框选择所有剩下的对象并单击 Delete

## UG10-CH34-D034

PDF page: 503; original JSON pointer: `/6024`

9. 在 Resolve ID Conflicts 对话框里 单击 OK ASPEN PLUS将新模块和物流加入到流程里 从一次运行拷贝一个模块到另一次运行的例子 该例子假定两次运行有相同的 Sep2 组分分离塔 在这两次运行中 关于 Sep2 的模块 ID 和入口与出口物流 IDs 是相同的 在这两次运行中 用一个相同的 RadFrac 严格蒸馏模块来 替代 Sep2

## UG10-CH34-D035

PDF page: 503; original JSON pointer: `/6025`

1 在第一次运行中 用 RadFrac 替代 Sep2 并完成规定

## UG10-CH34-D036

PDF page: 503; original JSON pointer: `/6026`

2 在 File菜单上 单击 Save As 并把文件保存为 ASPEN PLUS Backup Files(*.bkp)

## UG10-CH34-D037

PDF page: 503; original JSON pointer: `/6027`

4 在 File菜单上 单击 Import 选择你在第二步里保存的文件并单击 OK

## UG10-CH34-D038

PDF page: 503; original JSON pointer: `/6028`

5 在 Resolve ID Conflicts 对话框里 选择 RadFrac 模块和列出的所有物流 单击 Replace 按钮

## UG10-CH34-D039

PDF page: 503; original JSON pointer: `/6029`

6 选择 Resolve ID Conflicts 对话框里所有剩下的对象 并单击 Delete

## UG10-CH34-D040

PDF page: 503; original JSON pointer: `/6030`

7 在 Resolve ID Conflicts 对话框里 单击 OK 带有所有规定的新 RadFrac 模块 现在替代了流程中的 Sep2 模块 创建一个物性包 创建一个物性包

## UG10-CH34-D041

PDF page: 503; original JSON pointer: `/6031`

1 运行开始 它已有关于定义的物性包的所有输入 包含所有组分和物性规定 运行 不一定完成 典型的物性包包括

## UG10-CH34-D042

PDF page: 503; original JSON pointer: `/6032`

l Henry-Comps 规定 如果已定义

## UG10-CH34-D043

PDF page: 503; original JSON pointer: `/6033`

l 化学规定 如果已定义

## UG10-CH34-D044

PDF page: 503; original JSON pointer: `/6034`

l 物性方法定义而不是内置物性方法

## UG10-CH34-D045

PDF page: 503; original JSON pointer: `/6035`

l 带有规定数据的 Properties Parameters 对象

## UG10-CH34-D046

PDF page: 503; original JSON pointer: `/6036`

l 物性包里任意一个窗口所使用的单位集 而不是 SI MET 或 ENG

## UG10-CH34-D047

PDF page: 503; original JSON pointer: `/6037`

2 在 File菜单上 单击 Export. 转出

## UG10-CH34-D048

PDF page: 503; original JSON pointer: `/6038`

3 在 Export 对话框里 输入你想包含物性包的备用文件的路径和文件名

## UG10-CH34-D049

PDF page: 503; original JSON pointer: `/6039`

4 单击 Save 你可以转换你在任意一次运行里所创建的备用文件 例如 假设你用 NRTL 物性方法开发一个关于乙醇-水的物性包 在 ASPEN PLUS 里规 定如下信息 并把规定保存为一个备用文件

## UG10-CH34-D050

PDF page: 503; original JSON pointer: `/6040`

l Components Specifications Selection 页

## UG10-CH34-D051

PDF page: 503; original JSON pointer: `/6041`

l Properties Specifications Global 页

## UG10-CH34-D052

PDF page: 503; original JSON pointer: `/6042`

l Properties Parameters Binary Interaction NRTL-1 表

## UG10-CH34-D053

PDF page: 504; original JSON pointer: `/6044`

使用 ASPEN PLUS插入库的电解质插入表格

## UG10-CH34-D054

PDF page: 504; original JSON pointer: `/6045`

使用 ASPEN PLUS库中的插入

## UG10-CH34-D055

PDF page: 504; original JSON pointer: `/6046`

1 在 File菜单上 单击 Import

## UG10-CH34-D056

PDF page: 504; original JSON pointer: `/6047`

2 在 Import 对话框里 单击工具棒上的 Favorites 按钮

## UG10-CH34-D057

PDF page: 504; original JSON pointer: `/6048`

3 在 Favorites 文件夹里 双击 Elecins 文件夹

## UG10-CH34-D058

PDF page: 504; original JSON pointer: `/6049`

4 从列表里选择一个插入 单击 OK

## UG10-CH34-D059

PDF page: 504; original JSON pointer: `/6050`

5 如果出现 Resolve ID Conflicts 对话框 请参见前面的 Resolving ID Conflicts 部分 提示 用 Import 对话框工具棒上的 Preview 按钮 请看插入的说明 提示 在使用插入前应按上面描述过程浏览插入的详细内容 用 File Open打开插入 而 不用 File Import. 然后用 Data Browser 来看哪些输入在插入里进行了定义 并看插入内容 隐藏对象 你可以使用 Hide 特性来从模拟中把可选的对象暂时除掉 而不删除它们 例如 当你

## UG10-CH34-D060

PDF page: 504; original JSON pointer: `/6051`

不想在模拟中用一个设计规定时 你可以把该设计规定隐藏掉

## UG10-CH34-D061

PDF page: 504; original JSON pointer: `/6052`

l 全局规定 如 Setup Specifications 和 Properties Specifications 表

## UG10-CH34-D062

PDF page: 504; original JSON pointer: `/6053`

l Properties Parameters 和 Molecular Structure 分子结构 对象

## UG10-CH34-D063

PDF page: 504; original JSON pointer: `/6054`

1 对于隐藏的对象类型 显示 Object Manager,

## UG10-CH34-D064

PDF page: 504; original JSON pointer: `/6055`

2 选择你想隐藏的一个或多个对象 如果 Hide 按钮是虚的 你就不能隐藏该对象类型

## UG10-CH34-D065

PDF page: 504; original JSON pointer: `/6056`

3 单击 Hide按钮 ASPEN PLUS 从 Object Manager 列表里去掉所选的对象 它们不再是问题定义的一部分 显示对象 显示 取消隐藏 对象

## UG10-CH34-D066

PDF page: 504; original JSON pointer: `/6057`

1. 对于你想显示的对象类型 打开 Object Manager

## UG10-CH34-D067

PDF page: 504; original JSON pointer: `/6058`

2. 单击 Reveal按钮 注 Reveal按钮只在有隐藏对象时才激活

## UG10-CH34-D068

PDF page: 504; original JSON pointer: `/6059`

3. 在 Reveal对话框里 选择你想显示的隐藏对象 然后单击 OK 如果没出现 ID 矛盾 ASPEN PLUS 就把对象存到问题定义中 并把它们显示在 Object Manager 上 如果关于隐藏对象规定和当前问题的定义不一致 例如 如果一股参考物流不存在 对象就没完成 用 Next 来确定你必须做哪些工作才能完成输入 如果发生 ID 矛盾 如果一个隐藏对象和当前问题定义的对象有相同的 ID 就出现 Resolve ID Conflicts 对话框

## UG10-CH34-D069

PDF page: 504; original JSON pointer: `/6060`

提示 用 Reveal对话框上的 Remove 按钮从模拟中永久删掉隐藏对象

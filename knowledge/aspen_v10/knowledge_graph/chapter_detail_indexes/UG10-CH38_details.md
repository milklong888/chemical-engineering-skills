# UG10-CH38 Detail Operation Index - 第38章 使用ASPEN PLUS的ActiveX自动控制服务器

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH38-D001

PDF page: 545; original JSON pointer: `/6632`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D002

PDF page: 545; original JSON pointer: `/6633`

第38章 使用 ASPEN PLUS的ActiveX自动控

## UG10-CH38-D003

PDF page: 545; original JSON pointer: `/6634`

本章介绍如何使用 ASPEN PLUS 的 ActiveX 自动控制服务器 包含如下主题

## UG10-CH38-D004

PDF page: 545; original JSON pointer: `/6635`

l 浏览 ASPEN PLUS 对象的性质和方法

## UG10-CH38-D005

PDF page: 545; original JSON pointer: `/6636`

l 自动控制服务器列出的对象

## UG10-CH38-D006

PDF page: 545; original JSON pointer: `/6637`

l 在自动控制界面导航树状结构

## UG10-CH38-D007

PDF page: 545; original JSON pointer: `/6638`

l 流程的连接和自动控制

## UG10-CH38-D008

PDF page: 545; original JSON pointer: `/6639`

本章中的示例使用了 Visual Basic 5.0 和作为自动控制客户的应用程序 VBA(Visual

## UG10-CH38-D009

PDF page: 545; original JSON pointer: `/6640`

Basic for Applications) 所有的示例都建立在 pfdtut 实例问题基础上 这些实例问题与 ASPEN

## UG10-CH38-D010

PDF page: 545; original JSON pointer: `/6641`

PLUS 的标准安装程序一同提供 名字是 pfdtut.bkp 备份文件 如果你按照缺省设置安装

## UG10-CH38-D011

PDF page: 545; original JSON pointer: `/6642`

ASPEN PLUS 这个文件将被放在 ProgramFiles \AspenTech\APUI100\xmp 目录下

## UG10-CH38-D012

PDF page: 545; original JSON pointer: `/6643`

如果你按照缺省设置安装 ASPEN PLUS 本章中 Visual Basic的示例将被放在 Program Files\AspenTech\APUI100\vbexample 目录下 关于自动控制服务器 ASPEN PLUS 的 Windows 用户界面是一个 ActiveX 自动控制服务器 ActiveX 技术(对 象自动连接和嵌入)能使一个外部的 Windows应用程序与 ASPEN PLUS通过一个程序接口相 互作用 这个接口程序一般用微软的 Visual Basic语言设计的 服务器通过 COM 对象方式 列出对象

## UG10-CH38-D013

PDF page: 545; original JSON pointer: `/6644`

使用自动控制接口 你能够

## UG10-CH38-D014

PDF page: 545; original JSON pointer: `/6645`

l 将输入报告和 ASPEN PLUS 的模拟结果与其它一些应用程序相连接 例如设计程

## UG10-CH38-D015

PDF page: 545; original JSON pointer: `/6646`

为了使用 ASPEN PLUS 自动控制服务器 你必须

## UG10-CH38-D016

PDF page: 546; original JSON pointer: `/6648`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D017

PDF page: 546; original JSON pointer: `/6649`

ASPEN PLUS 安装在缺省目录下 它将存放在 Program Files\AspenTech\AP100UI\xeq 下

## UG10-CH38-D018

PDF page: 546; original JSON pointer: `/6650`

该服务器是一个来自过程的服务器 执行程序是 apwn.exe.

## UG10-CH38-D019

PDF page: 546; original JSON pointer: `/6651`

参考工程对话框中 你必须选中 ASPEN PLUS GUI 10.0 的类型库框

## UG10-CH38-D020

PDF page: 546; original JSON pointer: `/6652`

在通过 Excel VBA 电子表格的可视化 BASIC 扩展库 访问 ASPEN PLUS 的类型库

## UG10-CH38-D021

PDF page: 546; original JSON pointer: `/6653`

(type library)之前 在 Excel Tools 下的参考对话框中 必须选中 ASPEN PLUS GUI 10.0 的类

## UG10-CH38-D022

PDF page: 546; original JSON pointer: `/6654`

如果 ASPEN PLUS GUI 10.0 的类型库不存在 请单击 Browse 按钮去找 ASPEN PLUS 用户界面的系统目录 选中 happ.tlb 文件. 错误处理 在调用方法或访问 ASPEN PLUS 对象属性过程中可能发生异常 给所有访问自动控制 界面的程序代码建立一个错误处理方法是非常重要的 自动控制界面能够根据各种不同情况 相应显示一个异常 但大多数并不是严重或致命的错误 如果在错误发生处没有错误处理方法 许多错误通常会在你的用户屏幕上产生一个对话

## UG10-CH38-D023

PDF page: 546; original JSON pointer: `/6655`

框 在 VB 中 错误处理方法是在错误指令表中 例如 On Error Goto <line> 如果在计算

## UG10-CH38-D024

PDF page: 546; original JSON pointer: `/6656`

时遇到严重的错误 通常会建立一个错误处理子程序 以整理应用并完整退出

## UG10-CH38-D025

PDF page: 546; original JSON pointer: `/6657`

浏览 ASPEN PLUS 对象的属性和方法

## UG10-CH38-D026

PDF page: 546; original JSON pointer: `/6658`

ASPEN PLUS 对象的属性和方法可以在自动控制客户对象浏览器上浏览

## UG10-CH38-D027

PDF page: 546; original JSON pointer: `/6659`

Ø 在 Visual Basic 5 和 Excel 中 在 View 菜单中单击 Object Browser 使用 Excel

## UG10-CH38-D028

PDF page: 546; original JSON pointer: `/6660`

目前菜单项的分页模块必须是活动的

## UG10-CH38-D029

PDF page: 546; original JSON pointer: `/6661`

针对模拟问题 ASPEN PLUS 对象的大多数性质可以通过自动控制界面更改设置 但有

## UG10-CH38-D030

PDF page: 546; original JSON pointer: `/6662`

些模拟对象的性质是只读的 如果性质是只读的 那么它将显示在 VB的对象浏览器下而不

## UG10-CH38-D031

PDF page: 546; original JSON pointer: `/6663`

是在 Excel VBA的对象浏览器下

## UG10-CH38-D032

PDF page: 546; original JSON pointer: `/6664`

ASPEN PLUS 列出的对象是 Ihapp 对象 一个对象浏览器可以在 Ihapp 位置上显示出的

## UG10-CH38-D033

PDF page: 546; original JSON pointer: `/6665`

IHNode ASPEN PLUS 问题的树状结构显示的由 IHNode 对象组成的输入和

## UG10-CH38-D034

PDF page: 547; original JSON pointer: `/6667`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D035

PDF page: 547; original JSON pointer: `/6668`

下面的示例获得一个模拟问题的模拟对象存入备份文件 pfdtut.bkp 中 并且设置它的可

## UG10-CH38-D036

PDF page: 547; original JSON pointer: `/6669`

视属性显示在 ASPEN PLUS 的图形用户界面上

## UG10-CH38-D037

PDF page: 547; original JSON pointer: `/6670`

Function OpenSimulation() As IHApp

## UG10-CH38-D038

PDF page: 547; original JSON pointer: `/6671`

On Error GoTo ErrorHandler

## UG10-CH38-D039

PDF page: 547; original JSON pointer: `/6672`

ˊopen existing simulation

## UG10-CH38-D040

PDF page: 547; original JSON pointer: `/6673`

Set ihAPSim = GetObject("C: \Program Files\AspenTech\Apui100\xmp\pfdtut.bkp")

## UG10-CH38-D041

PDF page: 547; original JSON pointer: `/6674`

ˊdisplay the GUI

## UG10-CH38-D042

PDF page: 547; original JSON pointer: `/6675`

Set OpenSimulation = ihAPSim

## UG10-CH38-D043

PDF page: 547; original JSON pointer: `/6676`

ErrorHandler: MsgBox "OpenSimulation raised erro r " & Err & ": " & Error(Err) End End Function GetObject (获得对象)的参考结果将被用来建立一个运行 Apwn.exe 对象服务器的过程 从相同或不同过程中获得的关于同一题目的信息 将被连接到 Apwn 服务器上相同的运行事 例上 ASPEN PLUS 的树状结构 每个 ASPEN PLUS 模拟问题的输入和结果数据都被组织在一个树状结构里 为了访问

## UG10-CH38-D044

PDF page: 547; original JSON pointer: `/6677`

你所需的 ASPEN PLUS 模拟数据 你必须理解并能通过树状结构的导航找到和鉴别出你所

## UG10-CH38-D045

PDF page: 547; original JSON pointer: `/6678`

使用 Variable Explorer (变量探测器)可以浏览和访问与你的模拟问题相关的变量

## UG10-CH38-D046

PDF page: 547; original JSON pointer: `/6679`

Variable Explorer在模拟过程中将显示出一个类似 Data Browser 数据浏览器 的窗口 它

## UG10-CH38-D047

PDF page: 547; original JSON pointer: `/6680`

现在我们打开 Variable Explorer:

## UG10-CH38-D048

PDF page: 547; original JSON pointer: `/6681`

Ø 从 Tools 工具 菜单下单击 Variable Explorer.

## UG10-CH38-D049

PDF page: 548; original JSON pointer: `/6683`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D050

PDF page: 548; original JSON pointer: `/6684`

Variable Explorer(变量探测器) 显示一个与 Data Browser 数据浏览器 类似的树状视图

## UG10-CH38-D051

PDF page: 548; original JSON pointer: `/6685`

它们的不同在于 Data Browser 数据浏览器 能方便地显示出分组的变量 并且变量被放

## UG10-CH38-D052

PDF page: 548; original JSON pointer: `/6686`

置在 form(表)上 表上有提示符 滚动控制 选择框和区域以便于数据输入 Variable

## UG10-CH38-D053

PDF page: 548; original JSON pointer: `/6687`

Explorer(变量探测器) 则显示出在模拟问题里的重要变量

## UG10-CH38-D054

PDF page: 548; original JSON pointer: `/6688`

Variable Explorer(变量探测器)对自动控制用户是非常重要的 因为它能显示出你通过自

## UG10-CH38-D055

PDF page: 548; original JSON pointer: `/6689`

注 Variable Explorer(变量探测器)是只读的 你不能使用 Variable Explorer(变量探测器)

## UG10-CH38-D056

PDF page: 548; original JSON pointer: `/6690`

去改变这些变量的值或其它属性

## UG10-CH38-D057

PDF page: 548; original JSON pointer: `/6691`

注 如果通过 Variable Explorer (变量探测器)的树结构来导航 它有可能建立一个新的 对象 但你也许不能将它删除掉 正因为如此 在你使用了 Variable Explorer(变量探测器) 之前 你必须存储你的 ASPEN PLUS 运行 而使用 Variable Explorer(变量探测器) 之后不存 储它们 使用 Variable Explorer的示例 这个示例给出了使用 Variable Explorer(变量探测器)访问 pfdtut.bkp 文件在 RadFrac 模块 (Block B6)中的数据的详细步骤

## UG10-CH38-D058

PDF page: 548; original JSON pointer: `/6692`

1. 从 Tools 工具 菜单下单击 Variable Explorer 来打开 Variable Explorer(变量探测器) 左边的树状视图显示着根标签下的节点

## UG10-CH38-D059

PDF page: 548; original JSON pointer: `/6693`

2. 双击根目录图标或单击 + 图标来立刻显示如下这些节点 Data 数据 , Unit Table 单位表 and Settings 设置

## UG10-CH38-D060

PDF page: 548; original JSON pointer: `/6694`

3. 展开 Data 来显示它下面节点的标签 从 Setup 安装 到 Results Summary 结果 汇总

## UG10-CH38-D061

PDF page: 548; original JSON pointer: `/6695`

4. 展开 Blocks 块 的图标获得流程中模块的列表 B1 到 B6

## UG10-CH38-D062

PDF page: 548; original JSON pointer: `/6696`

5. 展开 B6 节点显示出如下节点标签 从 Input 输入 到 Work Results 工作结果 . 展开 Input 节点来显示出从 Unit Set 单元设置 到 Y_EST 的节点标签列表 这些

## UG10-CH38-D063

PDF page: 549; original JSON pointer: `/6698`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D064

PDF page: 549; original JSON pointer: `/6699`

节点代表着 RADFRAC块的模拟输入数据 例如 在 Input 节点下 被标记着

## UG10-CH38-D065

PDF page: 549; original JSON pointer: `/6700`

NSTAGE 的节点保存了塔的级数的输入值

## UG10-CH38-D066

PDF page: 549; original JSON pointer: `/6701`

6. 单击 Output 输出 来显示一个从 Unit 单元 到 Y_MS 的节点标签列表 这些节点代表着 RadFrac 模块的输入数据 例如 在 Output 节点下 被标记着 BU_RATIO的节点保存了蒸发率的结果值 Variable Explorer上显示的节点域路径 是当前被打开的节点的路径 从这个域 你可以直接拷贝和粘贴到你的程序中 要 做到这样 必须按照如下步骤

## UG10-CH38-D067

PDF page: 549; original JSON pointer: `/6702`

7. 在节点域的路径上选中 text 文本 单击鼠标右键

## UG10-CH38-D068

PDF page: 549; original JSON pointer: `/6703`

8. 从出现的菜单上单击 Copy 拷贝

## UG10-CH38-D069

PDF page: 549; original JSON pointer: `/6704`

9. 再回到你的应用程序上(例如 Visual Basic或 Excel Module 页)

## UG10-CH38-D070

PDF page: 549; original JSON pointer: `/6705`

正文待来源表达/OCR边界复核；原文本 SHA256: `b5495c5a38dbf36f815b4a1e99d229e421466a9e4041901c8eb0abd3709b9a3e`。

## UG10-CH38-D071

PDF page: 549; original JSON pointer: `/6706`

On Error GoTo ErrorHandler

## UG10-CH38-D072

PDF page: 549; original JSON pointer: `/6707`

ErrorHandler: MsgBox "GetCollectionExample raised error" & Err & ": " & Error(Err) End Sub 集合对象 ihcolOffspring 包含了在根下一级的节点集合 比如那些在 Variable Explorer 中可视的带有卷标数据 单位表和设置的节点

## UG10-CH38-D073

PDF page: 550; original JSON pointer: `/6709`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D074

PDF page: 550; original JSON pointer: `/6710`

每个集合对象内的节点都可以按以下两个方法之一来访问

## UG10-CH38-D075

PDF page: 550; original JSON pointer: `/6711`

l 你可以使用一个 For Each …Next 结构反复通过这个集合对象 在循环中访问每一

## UG10-CH38-D076

PDF page: 550; original JSON pointer: `/6712`

别一个特殊项 这项的属性有一个或很多参数 每个参数可以是字符串 用来规定

## UG10-CH38-D077

PDF page: 550; original JSON pointer: `/6713`

类型的数 用来规定在这个子节点集合中节点数 Item (项)属性必须的参数个数由

## UG10-CH38-D078

PDF page: 550; original JSON pointer: `/6714`

通过 ihcolOffspring 集合详细列举了每个节点 并且通过这个标签 Data 数据 获得

## UG10-CH38-D079

PDF page: 550; original JSON pointer: `/6715`

Set ihDataNode = ihcolOffspring.Item("Da ta")

## UG10-CH38-D080

PDF page: 550; original JSON pointer: `/6716`

Set ihDataNode = ihcolOffspring.Item("Data")

## UG10-CH38-D081

PDF page: 550; original JSON pointer: `/6717`

Set ihDataNode = ihcolOffspring.Item("Data","id2")

## UG10-CH38-D082

PDF page: 550; original JSON pointer: `/6718`

Item ( 项)属性是 IHNodeCol的缺省属性 正以为如此 这条语句可以被简略写成如下

## UG10-CH38-D083

PDF page: 550; original JSON pointer: `/6719`

Set ihDataNode = ihcolOffspring( Data )

## UG10-CH38-D084

PDF page: 550; original JSON pointer: `/6720`

Set ihNStageNode = ihAPsim.Elements("Data"). _

## UG10-CH38-D085

PDF page: 550; original JSON pointer: `/6721`

Elements("Blocks").Elements("B6"). _

## UG10-CH38-D086

PDF page: 550; original JSON pointer: `/6722`

一个非常简明的表示法在向下操作树时是很有用的 它只须允许连上 item (项)的名字同

## UG10-CH38-D087

PDF page: 550; original JSON pointer: `/6723`

时不规定元素或 Item (项)的属性 例如 上面的语句可以这样写

## UG10-CH38-D088

PDF page: 550; original JSON pointer: `/6724`

Set ihNStageNode = ihAPSim.Tree.Data.Blocks.B6.Input.NSTAGE

## UG10-CH38-D089

PDF page: 550; original JSON pointer: `/6725`

l 在这个的 Visual Basic示例中 只有 item ( 项)名字与自动控制客户的语言里的标

## UG10-CH38-D090

PDF page: 550; original JSON pointer: `/6726`

识符语法保持一致时 它才有效 Item (项)的 name ( 名字)必需不包含内部嵌入的

## UG10-CH38-D091

PDF page: 550; original JSON pointer: `/6727`

接 ,port 端口 , setting table 设置表 , route 路线 , label 标签 和 unit table

## UG10-CH38-D092

PDF page: 551; original JSON pointer: `/6729`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D093

PDF page: 551; original JSON pointer: `/6730`

ValueType 值类型 返回下列表中的一个值

## UG10-CH38-D094

PDF page: 551; original JSON pointer: `/6731`

ValueType 描述 Visual Basic Data Type 数据类型

## UG10-CH38-D095

PDF page: 551; original JSON pointer: `/6732`

1 Integer 整数 Long 长整型

## UG10-CH38-D096

PDF page: 551; original JSON pointer: `/6733`

2 Real 实数 Double 双精度实型

## UG10-CH38-D097

PDF page: 551; original JSON pointer: `/6734`

3 String 字符串 String 字符串型

## UG10-CH38-D098

PDF page: 551; original JSON pointer: `/6735`

正文待来源表达/OCR边界复核；原文本 SHA256: `3efa809cbe9690f18fd892b8cb7c373345636cf151fa67e8e81ede5aaf9efe12`。

## UG10-CH38-D099

PDF page: 551; original JSON pointer: `/6736`

On Error GoTo ErrorHandler

## UG10-CH38-D100

PDF page: 551; original JSON pointer: `/6737`

Set ihColumn = ihAPsim.Tree.Data.Blocks.B6

## UG10-CH38-D101

PDF page: 551; original JSON pointer: `/6738`

ErrorHandler: MsgBox "GetScalarValuesExample raised error" & Err & ": " & Error(Err) End Sub

## UG10-CH38-D102

PDF page: 552; original JSON pointer: `/6740`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D103

PDF page: 552; original JSON pointer: `/6741`

这些表显示了一些通常使用的属性和它们的描述 属性的名字与 Variable Explorer中的

## UG10-CH38-D104

PDF page: 552; original JSON pointer: `/6742`

你能看到在你的自动控制客户的 Object Browser 对象浏览器 中的全部可能出现值的

## UG10-CH38-D105

PDF page: 552; original JSON pointer: `/6743`

列表和描述 在通常 你只需要属性的一个小的子集

## UG10-CH38-D106

PDF page: 552; original JSON pointer: `/6744`

性值 来检查一个属性是否被支持 这属性的 AttributeType 属性类型 值返回象上面显示

## UG10-CH38-D107

PDF page: 552; original JSON pointer: `/6745`

ValueType 值类型 如果一个属性的 AttributeType 属性类型 返回一个零值 那么那个

## UG10-CH38-D108

PDF page: 552; original JSON pointer: `/6746`

Basis 基础数 HAP_BASIS 值的基准 例如 MOLE 或

## UG10-CH38-D109

PDF page: 552; original JSON pointer: `/6747`

Option List 操作显示 HAP_OPTIONLIST 一个节点 这个节点包含了带

## UG10-CH38-D110

PDF page: 552; original JSON pointer: `/6748`

Completion Status 完成状态

## UG10-CH38-D111

PDF page: 552; original JSON pointer: `/6749`

HAP_COMPSTATUS 返回一个给出的完成状态的整

## UG10-CH38-D112

PDF page: 552; original JSON pointer: `/6750`

HAPCompStatusCode 中 解释

## UG10-CH38-D113

PDF page: 552; original JSON pointer: `/6751`

Output 输出 HAP_OUTVAR 这个变量节点是一个结果变量吗

## UG10-CH38-D114

PDF page: 552; original JSON pointer: `/6752`

Enterable 能否进入 HAP_ENTERABLE 这个值的属性能否修改

## UG10-CH38-D115

PDF page: 553; original JSON pointer: `/6754`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D116

PDF page: 553; original JSON pointer: `/6755`

Default Value 缺省值 HAP_VALUEDEFAULT 这个值属性的缺省值

## UG10-CH38-D117

PDF page: 553; original JSON pointer: `/6756`

向控制的第一项被建立第一个索引

## UG10-CH38-D118

PDF page: 553; original JSON pointer: `/6757`

In or Out 输入或输出 HAP_INOUT 端口节点是 inlet 还是

## UG10-CH38-D119

PDF page: 553; original JSON pointer: `/6758`

1 = Outlet 对于物流

## UG10-CH38-D120

PDF page: 553; original JSON pointer: `/6759`

1 = Inlet Gender 种类 HAP_PORTSEX 块或流的端口类型

## UG10-CH38-D121

PDF page: 553; original JSON pointer: `/6760`

1 = Block Multiport 多向端口 HAP_MULTIPORT 这个端口节点是否能被连到 多个流上 0=No 1=Yes Port Type 端口类型 HAP_PORTTYPE 端口节点的类型

## UG10-CH38-D122

PDF page: 553; original JSON pointer: `/6761`

1 = Material

## UG10-CH38-D123

PDF page: 553; original JSON pointer: `/6762`

正文待来源表达/OCR边界复核；原文本 SHA256: `f85535b940464b79dbb781083da67a88db6db8041d8070182bce4109d9bb07c6`。

## UG10-CH38-D124

PDF page: 553; original JSON pointer: `/6763`

On Error GoTo ErrorHandler

## UG10-CH38-D125

PDF page: 553; original JSON pointer: `/6764`

Set ihBlockList = ihAPSim.Tree.Data.Blocks.Elements

## UG10-CH38-D126

PDF page: 553; original JSON pointer: `/6765`

& Chr(9) & "Section " & Chr(9) & "Results status"

## UG10-CH38-D127

PDF page: 554; original JSON pointer: `/6767`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D128

PDF page: 554; original JSON pointer: `/6768`

Status(ihBlock.AttributeValue(HAP_COMPSTATUS))

## UG10-CH38-D129

PDF page: 554; original JSON pointer: `/6769`

Next ihBlock

## UG10-CH38-D130

PDF page: 554; original JSON pointer: `/6770`

MsgBox strOut, , "ListBlocksExample"

## UG10-CH38-D131

PDF page: 554; original JSON pointer: `/6771`

ErrorHandler: MsgBox "ListBlocksExample raised error" & Err & ": " & Error(Err) End Sub Function Status(CompStat As Integer) As String ´This function interprets a status variable and returns a string If ((CompStat And HAP_RESULTS_SUCCESS) = HAP_RESULTS_SUCCESS) Then Status = "Success"

## UG10-CH38-D132

PDF page: 554; original JSON pointer: `/6772`

ElseIf ((CompStat And HAP_RESULTS_ERRORS) = HAP_RESULTS_ERRORS)

## UG10-CH38-D133

PDF page: 554; original JSON pointer: `/6773`

Status = "Errors"

## UG10-CH38-D134

PDF page: 554; original JSON pointer: `/6774`

ElseIf ((CompStat And HAP_RESULTS_WARNINGS) =

## UG10-CH38-D135

PDF page: 554; original JSON pointer: `/6775`

HAP_RESULTS_WARNINGS) Then

## UG10-CH38-D136

PDF page: 554; original JSON pointer: `/6776`

Status = "Warnings"

## UG10-CH38-D137

PDF page: 554; original JSON pointer: `/6777`

ElseIf ((CompStat And HAP_NORESULTS) = HAP_NORESULTS) Then

## UG10-CH38-D138

PDF page: 554; original JSON pointer: `/6778`

Status = "No results"

## UG10-CH38-D139

PDF page: 554; original JSON pointer: `/6779`

ElseIf ((CompStat And HAP_RESULTS_INCOMPAT) = HAP_RESULTS_INCOMPAT)

## UG10-CH38-D140

PDF page: 554; original JSON pointer: `/6780`

Status = "Incompatible with input"

## UG10-CH38-D141

PDF page: 554; original JSON pointer: `/6781`

ElseIf ((CompStat And HAP_RESULTS_INACCESS) = HAP_RESULTS_INACCESS)

## UG10-CH38-D142

PDF page: 554; original JSON pointer: `/6782`

这个示例显示了如下消息框 .

## UG10-CH38-D143

PDF page: 555; original JSON pointer: `/6784`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D144

PDF page: 555; original JSON pointer: `/6785`

l 在运行 ASPEN PLUS 时改变这个单位

## UG10-CH38-D145

PDF page: 555; original JSON pointer: `/6786`

下面的子程序使用了 UnitString 单位串 属性显示了带度量单位的闪蒸块的出口压力

## UG10-CH38-D146

PDF page: 555; original JSON pointer: `/6787`

On Error GoTo ErrorHandler

## UG10-CH38-D147

PDF page: 555; original JSON pointer: `/6788`

Set ihPresNode = ihAPSim.Tree.Data.Blocks.B3.Output.B_PRES

## UG10-CH38-D148

PDF page: 555; original JSON pointer: `/6789`

正文待来源表达/OCR边界复核；原文本 SHA256: `07dba374cab2d93a9123160ea3a4ce3d883b0efa4fe9afd8a3fd8d7497d5c50f`。

## UG10-CH38-D149

PDF page: 556; original JSON pointer: `/6791`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D150

PDF page: 556; original JSON pointer: `/6792`

号 注意属性值是实际的行号和列号 而当你用单位表的集合参考行号时 你必须从这些值

## UG10-CH38-D151

PDF page: 556; original JSON pointer: `/6793`

检索 B3 块的压力 在这个运行着的指定单元和异步传输模式里都是在单位表的第三

## UG10-CH38-D152

PDF page: 556; original JSON pointer: `/6794`

This example retrieves a value both in the display units and an alternative

## UG10-CH38-D153

PDF page: 556; original JSON pointer: `/6795`

Dim strDisplayUnits As String

## UG10-CH38-D154

PDF page: 556; original JSON pointer: `/6796`

On Error GoTo ErrorHandler

## UG10-CH38-D155

PDF page: 556; original JSON pointer: `/6797`

Set ihPres = ihAPSim.Tree.Data.Blocks.B3.Output.B_PRES

## UG10-CH38-D156

PDF page: 556; original JSON pointer: `/6798`

retrieve the attributes for the display units (psi)

## UG10-CH38-D157

PDF page: 556; original JSON pointer: `/6799`

strDisplayUnits = UnitsString(ihAPSim, nRow, nCol)

## UG10-CH38-D158

PDF page: 556; original JSON pointer: `/6800`

select the alternative unit table column (atm)

## UG10-CH38-D159

PDF page: 556; original JSON pointer: `/6801`

" " & strDisplayUnits & Chr$(13) & _

## UG10-CH38-D160

PDF page: 556; original JSON pointer: `/6802`

ihPres.ValueForUnit(nRow, nCol) & " " & strConvertedUnits, _

## UG10-CH38-D161

PDF page: 556; original JSON pointer: `/6803`

ErrorHandler: MsgBox "UnitsConversionExample raised error " & Err & ": " & Error(Err) End Sub Public Function UnitsString(ihAPSim As IHApp, nRow As Long, nCol As Long) This function returns the units of measurement symbol given the unit table row and column

## UG10-CH38-D162

PDF page: 556; original JSON pointer: `/6804`

On Error GoTo UnitsStringFailed

## UG10-CH38-D163

PDF page: 557; original JSON pointer: `/6806`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D164

PDF page: 557; original JSON pointer: `/6807`

为 ASPEN PLUS 运行改变度量单位

## UG10-CH38-D165

PDF page: 557; original JSON pointer: `/6808`

在 ASPEN PLUS 运行时你能够使用 HAP_UNITCOL 属性直接改变度量单位 改变

## UG10-CH38-D166

PDF page: 557; original JSON pointer: `/6809`

HAP_UNITCO属性值将会产生不同结果 这要看这个值是输入还是输出值 情况如下

## UG10-CH38-D167

PDF page: 557; original JSON pointer: `/6810`

l 改变一个输出值的 HAP_UNITCOL属性将使检索到的输出值转换成你选中的度量

## UG10-CH38-D168

PDF page: 557; original JSON pointer: `/6811`

单位 它相当于在 ASPEN PLUS GUI 图形用户界面 的一个 Result(结果)表上改

## UG10-CH38-D169

PDF page: 557; original JSON pointer: `/6812`

l 改变一个输入值节点的 HAP_UNITCOL 属性将会改变这个输入的规定单位 它不

## UG10-CH38-D170

PDF page: 557; original JSON pointer: `/6813`

的一个 Input(输入)表上改变了单位

## UG10-CH38-D171

PDF page: 557; original JSON pointer: `/6814`

On Error GoTo ErrorHandler

## UG10-CH38-D172

PDF page: 557; original JSON pointer: `/6815`

Set ihPres = ihAPsim.Tree.Data.Blocks.B3.Output.B_PRES

## UG10-CH38-D173

PDF page: 557; original JSON pointer: `/6816`

MsgBox "Pressure in selected units: " _

## UG10-CH38-D174

PDF page: 557; original JSON pointer: `/6817`

ErrorHandler: MsgBox "UnitsChangeExample raised error " & Err & ": " & Error(Err) End Sub 在自动控制界面引用非标量变量 大多数模拟问题中的数据都被组织在数组 列表和数据表中 因此它被包含在多值变量 里 通过自动控制界面的 Value 属性叶节点来访问非标量数据的值 这个产生数值的节点结 构必须标识值的标识符数和上下文 例如

## UG10-CH38-D175

PDF page: 557; original JSON pointer: `/6818`

l 一个塔的温度分布值要求变量名和一个附加的标识符 级数

## UG10-CH38-D176

PDF page: 557; original JSON pointer: `/6819`

l 一个塔的组成分布值要求有变量名和两个附加的标识符 级数和组分

## UG10-CH38-D177

PDF page: 557; original JSON pointer: `/6820`

一旦一个多值变量节点被找到 选择标识符找到你所需要的值沿着这个树来回找 在一

## UG10-CH38-D178

PDF page: 558; original JSON pointer: `/6822`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D179

PDF page: 558; original JSON pointer: `/6823`

些示例中 查找单一的节点意味着对一个单一标识符的选择 在其它一些示例中 查找一个

## UG10-CH38-D180

PDF page: 558; original JSON pointer: `/6824`

节点意味着对不止一个标识符的选择 每个节点都有 Dimension 量纲 属性 如果 Dimension

## UG10-CH38-D181

PDF page: 558; original JSON pointer: `/6825`

0 最后一个尺寸数是 Dimension 属性的值减一 以下两种方法的任意一个都可以获得子节点

## UG10-CH38-D182

PDF page: 558; original JSON pointer: `/6826`

l 在一个集合对象中使用 Item 项 属性并且给这个集合每个的 Dimension 规定一

## UG10-CH38-D183

PDF page: 558; original JSON pointer: `/6827`

对于每个尺寸 你都能得到从集合的 Rowcount 属性得到的有效的位置数或者标签

## UG10-CH38-D184

PDF page: 558; original JSON pointer: `/6828`

结果 温度的描述被显示在 Data Browser 数据浏览器 里 在 Blocks>B6>Profiles>TPFQ 下

## UG10-CH38-D185

PDF page: 558; original JSON pointer: `/6829`

面以表格 form 形式显示

## UG10-CH38-D186

PDF page: 558; original JSON pointer: `/6830`

Root>Data>Blocks>B6>Output>B_TEMP 变量节点下面发现 在这个节点下有十五个叶节点

## UG10-CH38-D187

PDF page: 559; original JSON pointer: `/6832`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D188

PDF page: 559; original JSON pointer: `/6833`

通过自动控制界面显示怎样访问温度描述列的示例

## UG10-CH38-D189

PDF page: 559; original JSON pointer: `/6834`

Set ihTVar =ihA PSim.Tree.Data.Blocks.B6.Output.B_TEMP

## UG10-CH38-D190

PDF page: 559; original JSON pointer: `/6835`

下一步 建立一个简单的循环反复访问代表各级的子节点

## UG10-CH38-D191

PDF page: 559; original JSON pointer: `/6836`

Next ihStage

## UG10-CH38-D192

PDF page: 559; original JSON pointer: `/6837`

On Error GoTo ErrorHandler

## UG10-CH38-D193

PDF page: 559; original JSON pointer: `/6838`

Set ihTVar = ihAPsim.Tree.Data.Blocks.B6.Output.B_TEMP

## UG10-CH38-D194

PDF page: 559; original JSON pointer: `/6839`

& Chr(9) & Format(ihStage.Value, "###.00") _

## UG10-CH38-D195

PDF page: 559; original JSON pointer: `/6840`

ErrorHandler: MsgBox "TempProfExample raised error " & Err & ": " & Error(Err) End Sub

## UG10-CH38-D196

PDF page: 560; original JSON pointer: `/6842`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D197

PDF page: 560; original JSON pointer: `/6843`

RadFrac 的液态组分分布是一个使用两个标识符的示例 对于 pfdtut 的模拟结果,

## UG10-CH38-D198

PDF page: 560; original JSON pointer: `/6844`

Variable Explorer 变量探测器 的树视图中的变量 X 被显示在这个图表中

## UG10-CH38-D199

PDF page: 560; original JSON pointer: `/6845`

的那级组分的组成 图解显示如下

## UG10-CH38-D200

PDF page: 561; original JSON pointer: `/6847`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D201

PDF page: 561; original JSON pointer: `/6848`

Public Sub CompProfExample(ihAPsim As IHApp)

## UG10-CH38-D202

PDF page: 561; original JSON pointer: `/6849`

Dim ihCompNode As ihNode

## UG10-CH38-D203

PDF page: 561; original JSON pointer: `/6850`

On Error GoTo ErrorHandler

## UG10-CH38-D204

PDF page: 561; original JSON pointer: `/6851`

Set ihXNode = ihAPsim.Tree.Data.Blocks.B6.Output.Elements("X")

## UG10-CH38-D205

PDF page: 561; original JSON pointer: `/6852`

For Each ihCompNode In ihTrayNode.Elements

## UG10-CH38-D206

PDF page: 561; original JSON pointer: `/6853`

Chr(9) & ihCompNode.Name & Chr(9) & _

## UG10-CH38-D207

PDF page: 561; original JSON pointer: `/6854`

ihCompNode.Value

## UG10-CH38-D208

PDF page: 561; original JSON pointer: `/6855`

Next ihCompNode

## UG10-CH38-D209

PDF page: 561; original JSON pointer: `/6856`

Next ihTrayNode

## UG10-CH38-D210

PDF page: 561; original JSON pointer: `/6857`

MsgBox strOut, , "CompProfExample"

## UG10-CH38-D211

PDF page: 561; original JSON pointer: `/6858`

ErrorHandler: MsgBox "CompProfExample raised error " & Err & ": " & Error(Err) End Sub 使用三个标识符访问变量 反应系数 下面的图表显示了在 pfdtut 模拟中 Rstoic 反应模块的 Variable Explorer 变量探测器 树视图 在这个 RStoic 反应器模型中 这个反应的 stochiometric 化学计量系数 被保存在输入 变量 COEF 和 COEF1 中 这两个变量分别代表反应物和产物的反应系数

## UG10-CH38-D212

PDF page: 562; original JSON pointer: `/6860`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D213

PDF page: 562; original JSON pointer: `/6861`

因为这个模块仅有一个反应 所以 COEF 和 COEF1 都只有一个被标记为 1 的子节

## UG10-CH38-D214

PDF page: 562; original JSON pointer: `/6862`

这反应节点有两个量纲 这个节点的 Dimension 量纲 属性返回一个值 2 每个子节

## UG10-CH38-D215

PDF page: 562; original JSON pointer: `/6863`

在以下的图表中显示了这个结构

## UG10-CH38-D216

PDF page: 562; original JSON pointer: `/6864`

这反应节点是一个节点使用成对控制标识符的示例 这里只有那些在每个量纲中有相同

## UG10-CH38-D217

PDF page: 562; original JSON pointer: `/6865`

存在 如果这个节点使用了子节点的成对控制 这个属性就返回这对控制第一项的基于 1

## UG10-CH38-D218

PDF page: 563; original JSON pointer: `/6867`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D219

PDF page: 563; original JSON pointer: `/6868`

以下的程序代码显示了在 COEF 节点下怎样使用相关的标识符检索系数

## UG10-CH38-D220

PDF page: 563; original JSON pointer: `/6869`

On Error GoTo ErrorHandler

## UG10-CH38-D221

PDF page: 563; original JSON pointer: `/6870`

Set ihCoeffNode = ihAPsim.Tree.Data.Blocks.B2.Input.COEF

## UG10-CH38-D222

PDF page: 563; original JSON pointer: `/6871`

loop through coefficient nodes retrieving component and substream

## UG10-CH38-D223

PDF page: 563; original JSON pointer: `/6872`

Next ihReacNode

## UG10-CH38-D224

PDF page: 563; original JSON pointer: `/6873`

ErrorHandler: MsgBox "ReacCoeffExample raised error " & Err & ": " & Error(Err) End Sub 下面的图形显示了消息框

## UG10-CH38-D225

PDF page: 564; original JSON pointer: `/6875`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D226

PDF page: 564; original JSON pointer: `/6876`

在流程的模块和物流之间的关系可以通过自动控制服务器来访问

## UG10-CH38-D227

PDF page: 564; original JSON pointer: `/6877`

下面这个示例显示一个表格 表格中显示流程中所有物流的源和目的模块和端口

## UG10-CH38-D228

PDF page: 564; original JSON pointer: `/6878`

This example displays a table showing flowsheet connectivity

## UG10-CH38-D229

PDF page: 564; original JSON pointer: `/6879`

On Error GoTo ErrorHandler

## UG10-CH38-D230

PDF page: 564; original JSON pointer: `/6880`

Set ihStreamList = ihAPsim.Tree.Data.Streams

## UG10-CH38-D231

PDF page: 564; original JSON pointer: `/6881`

Set i hBlockList = ihAPsim.Tree.Data.Blocks

## UG10-CH38-D232

PDF page: 564; original JSON pointer: `/6882`

`it`s a flowsheet product

## UG10-CH38-D233

PDF page: 565; original JSON pointer: `/6884`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D234

PDF page: 565; original JSON pointer: `/6885`

`it`s a flowsheet feed

## UG10-CH38-D235

PDF page: 565; original JSON pointer: `/6886`

Next ihStream

## UG10-CH38-D236

PDF page: 565; original JSON pointer: `/6887`

ErrorHandler: MsgBox "ConnectivityExample raised error" & Err & ": " & Error(Err) End Sub 从自动控制客户端控制模拟 一个 Happ 对象的 Engine 属性返回一个 IHAPEngine 对象 它是一个模拟引擎的界面 Happ 和 IHAPEngine 对象提供了能使一个自动控制客户程序运行和控制模拟的方法 下面的程序代码段告诉一个用户怎样按照提示使用一个模拟参数 来重新运行模拟并使

## UG10-CH38-D237

PDF page: 566; original JSON pointer: `/6889`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D238

PDF page: 566; original JSON pointer: `/6890`

Public Sub RunExample(ihAPsim As IHApp)

## UG10-CH38-D239

PDF page: 566; original JSON pointer: `/6891`

This example changes a simulation parameter and re -runs the simulation

## UG10-CH38-D240

PDF page: 566; original JSON pointer: `/6892`

On Error GoTo ErrorHandler

## UG10-CH38-D241

PDF page: 566; original JSON pointer: `/6893`

nStages = ihAPsim.Tree.Data.Block s.B6.Input.Elements("NSTAGE").Value

## UG10-CH38-D242

PDF page: 566; original JSON pointer: `/6894`

& Chr(13) & "Enter new value for number of stages."

## UG10-CH38-D243

PDF page: 566; original JSON pointer: `/6895`

ihAPsim.Tree.Data.Blocks.B6.Input.Elements("NSTAGE").Value = nStages

## UG10-CH38-D244

PDF page: 566; original JSON pointer: `/6896`

run the simulation

## UG10-CH38-D245

PDF page: 566; original JSON pointer: `/6897`

look at the status and results

## UG10-CH38-D246

PDF page: 566; original JSON pointer: `/6898`

Call ListBlocksExample(ihAPsim)

## UG10-CH38-D247

PDF page: 566; original JSON pointer: `/6899`

ErrorHandler: MsgBox "RunExample failed with error " & Err & Chr(13) & Error(Err) End Sub ASPEN PLUS类的成员 下面这部分列出了每个 ASPEN PLUS 类的所有成员 IHApp类的成员 标准 VB性质和操作主窗口的性质 名字和变量 成员类型 只读 说明 Activate() Sub 激活应用 Application As Happ Property Yes 返回对象的应用

## UG10-CH38-D248

PDF page: 566; original JSON pointer: `/6900`

FullName As String Property Yes 返回应用的完整名字

## UG10-CH38-D249

PDF page: 566; original JSON pointer: `/6901`

Name As String Property Yes 返回应用的名字

## UG10-CH38-D250

PDF page: 566; original JSON pointer: `/6902`

Parent As Happ Property Yes 返回对象的创建者

## UG10-CH38-D251

PDF page: 566; original JSON pointer: `/6903`

Visible As Boolean Property 返回的可视状态

## UG10-CH38-D252

PDF page: 567; original JSON pointer: `/6905`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D253

PDF page: 567; original JSON pointer: `/6906`

名字和变量 成员类型 只读 说明

## UG10-CH38-D254

PDF page: 567; original JSON pointer: `/6907`

Engine As IHAPEngine Property Yes 返回模拟引擎的界面

## UG10-CH38-D255

PDF page: 567; original JSON pointer: `/6908`

Tree As IHNode Property Yes 获得文件的顶部节点

## UG10-CH38-D256

PDF page: 567; original JSON pointer: `/6909`

Save() Sub 存储当前文件

## UG10-CH38-D257

PDF page: 567; original JSON pointer: `/6910`

SaveAs(filename As String,

## UG10-CH38-D258

PDF page: 567; original JSON pointer: `/6911`

[overwrite]) Sub 用一个新的名字存储当前文件

## UG10-CH38-D259

PDF page: 567; original JSON pointer: `/6912`

Restore(filename As String) Property Yes 恢复或将一个存档文件合并到这个当

## UG10-CH38-D260

PDF page: 567; original JSON pointer: `/6913`

WriteArchive(filename As

## UG10-CH38-D261

PDF page: 567; original JSON pointer: `/6914`

String) Sub 输出一个存档文件

## UG10-CH38-D262

PDF page: 567; original JSON pointer: `/6915`

InitFromArchive(filename

## UG10-CH38-D263

PDF page: 567; original JSON pointer: `/6916`

Sub 打开一个档案文件并进行初始化

## UG10-CH38-D264

PDF page: 567; original JSON pointer: `/6917`

InitFromFile(filename As

## UG10-CH38-D265

PDF page: 567; original JSON pointer: `/6918`

Sub 打开一个文件并进行初始化

## UG10-CH38-D266

PDF page: 567; original JSON pointer: `/6919`

Sub 打开一个模板并进行初始化

## UG10-CH38-D267

PDF page: 567; original JSON pointer: `/6920`

InitNew([filename],

## UG10-CH38-D268

PDF page: 567; original JSON pointer: `/6921`

Run() Sub 运行模拟工况

## UG10-CH38-D269

PDF page: 567; original JSON pointer: `/6922`

通过自动控制选择用于 Cut 剪切 和 Paste粘贴 缓冲区操作

## UG10-CH38-D270

PDF page: 567; original JSON pointer: `/6923`

DeleteSelection(Key As

## UG10-CH38-D271

PDF page: 567; original JSON pointer: `/6924`

Sub 删除一个选择的缓冲区

## UG10-CH38-D272

PDF page: 567; original JSON pointer: `/6925`

NewSelection(Key As

## UG10-CH38-D273

PDF page: 567; original JSON pointer: `/6926`

String) As IHSelection

## UG10-CH38-D274

PDF page: 567; original JSON pointer: `/6927`

Function 建立并返回一个新的选择缓冲区

## UG10-CH38-D275

PDF page: 567; original JSON pointer: `/6928`

SaveSelection(Key As

## UG10-CH38-D276

PDF page: 567; original JSON pointer: `/6929`

Sub 存储一个选择缓冲区

## UG10-CH38-D277

PDF page: 567; original JSON pointer: `/6930`

Selection(Key As String)

## UG10-CH38-D278

PDF page: 567; original JSON pointer: `/6931`

Property Yes 检索一个选择缓冲区

## UG10-CH38-D279

PDF page: 568; original JSON pointer: `/6933`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D280

PDF page: 568; original JSON pointer: `/6934`

名字和变量 成员类型 只读 说明

## UG10-CH38-D281

PDF page: 568; original JSON pointer: `/6935`

Application As Happ Property Yes 返回对象的应用

## UG10-CH38-D282

PDF page: 568; original JSON pointer: `/6936`

Parent As Happ Property Yes 返回这个对象的创建者

## UG10-CH38-D283

PDF page: 568; original JSON pointer: `/6937`

Dimension As Long Property Yes 返回目录的量纲数

## UG10-CH38-D284

PDF page: 568; original JSON pointer: `/6938`

Elements As IHNodeCol Property Yes 返回一个包含了这个节点的所有子节点的集

## UG10-CH38-D285

PDF page: 568; original JSON pointer: `/6939`

Integer) As Boolean

## UG10-CH38-D286

PDF page: 568; original JSON pointer: `/6940`

Property Yes 检查 attrnum 属性是否被定义

## UG10-CH38-D287

PDF page: 568; original JSON pointer: `/6941`

Sub 同时存储这个对象的值属性和度量单

## UG10-CH38-D288

PDF page: 568; original JSON pointer: `/6942`

Sub 同时存储这个对象的值属性 度量单位

## UG10-CH38-D289

PDF page: 568; original JSON pointer: `/6943`

ValueForUnit(unitrow As

## UG10-CH38-D290

PDF page: 569; original JSON pointer: `/6945`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D291

PDF page: 569; original JSON pointer: `/6946`

名字和变量 成员类型 只读 说明

## UG10-CH38-D292

PDF page: 569; original JSON pointer: `/6947`

Name([force]) As String Property 返回对象的名字 力变量没被使用

## UG10-CH38-D293

PDF page: 569; original JSON pointer: `/6948`

UnitString As String Property Yes 返回一个节点的度量单位的字符串

## UG10-CH38-D294

PDF page: 569; original JSON pointer: `/6949`

Clear() Sub 清除节点的内容

## UG10-CH38-D295

PDF page: 569; original JSON pointer: `/6950`

Delete() Sub 删除元素

## UG10-CH38-D296

PDF page: 569; original JSON pointer: `/6951`

Application As Happ Property Yes 返回对象的应用

## UG10-CH38-D297

PDF page: 569; original JSON pointer: `/6952`

Parent As Happ Property Yes 返回对象的创建者

## UG10-CH38-D298

PDF page: 569; original JSON pointer: `/6953`

Function 建立并增加一个子类型

## UG10-CH38-D299

PDF page: 569; original JSON pointer: `/6954`

1 = scalar 标量

## UG10-CH38-D300

PDF page: 569; original JSON pointer: `/6955`

5 = named list 命名列表 , 值的类型 如下 0=没定义 1=int 整数 2=real 实数 3=string 字符串 4=node 节点 5=memory block 模块 . Insert(element As IHNode, [loc_or_name], [loc_or_name2], [loc_or_name3], [loc_or_name4], [loc_or_name5]) Sub 插入一个元素到集合里

## UG10-CH38-D301

PDF page: 570; original JSON pointer: `/6957`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D302

PDF page: 570; original JSON pointer: `/6958`

插入一个新的行到这个指定量纲 dim

## UG10-CH38-D303

PDF page: 570; original JSON pointer: `/6959`

Sub 移走指定量纲位置上的一行

## UG10-CH38-D304

PDF page: 570; original JSON pointer: `/6960`

名字和变量 成员类型 只读 说明

## UG10-CH38-D305

PDF page: 570; original JSON pointer: `/6961`

Dimension As Long Property Yes 返回这个目录的量纲数

## UG10-CH38-D306

PDF page: 570; original JSON pointer: `/6962`

Property 返回在指定量纲内指定行的行标签 力参

## UG10-CH38-D307

PDF page: 570; original JSON pointer: `/6963`

Property Yes 返回量纲 dim 标签的位置或行数

## UG10-CH38-D308

PDF page: 570; original JSON pointer: `/6964`

Property Yes 返回量纲中的元素个数

## UG10-CH38-D309

PDF page: 570; original JSON pointer: `/6965`

Count Property Yes 返回集合中对象通道的总数

## UG10-CH38-D310

PDF page: 570; original JSON pointer: `/6966`

Property Yes 得到给定变量量纲或表格显示名称

## UG10-CH38-D311

PDF page: 570; original JSON pointer: `/6967`

Property Yes 返回一个可操作标签的节点

## UG10-CH38-D312

PDF page: 570; original JSON pointer: `/6968`

Property Yes 返回这个集合量纲的行是否被命名

## UG10-CH38-D313

PDF page: 570; original JSON pointer: `/6969`

Property 返回位置的元素名或行名 力变元没被使

## UG10-CH38-D314

PDF page: 570; original JSON pointer: `/6970`

Property 返回 attrnum 量纲的行 位置 dim 的

## UG10-CH38-D315

PDF page: 570; original JSON pointer: `/6971`

Property Yes 返回 attrnum 量纲的行 位置 dim 的

## UG10-CH38-D316

PDF page: 571; original JSON pointer: `/6973`

第 38 章 使用 ASPEN PLUS 的 ActiveX 自动控制服务器

## UG10-CH38-D317

PDF page: 571; original JSON pointer: `/6974`

object_type 已经被使用 它必须是

## UG10-CH38-D318

PDF page: 571; original JSON pointer: `/6975`

Run() Sub 运行模拟题目

## UG10-CH38-D319

PDF page: 571; original JSON pointer: `/6976`

Stop() Sub 停止模拟运行

## UG10-CH38-D320

PDF page: 571; original JSON pointer: `/6977`

名字和变量 成员类型 只读 说明

## UG10-CH38-D321

PDF page: 571; original JSON pointer: `/6978`

2 = after. ClearStopPoints() Sub 清除所有断点 DeleteStopPoint(index As Long) Sub 删除基于索引 1 的断点 StopPointCount As Long Property Yes 被设置了多少个断点 GetStopPoint(index As Long, type As IAP_STOPPOINT_TYPE ,object_id As String, before_or_after As Long) Sub 检索一个断点信息 索引是 基于 1 的断 点索引 before 在前 或 after 在后

## UG10-CH38-D322

PDF page: 571; original JSON pointer: `/6979`

2 = after 操作客户 /服务器的通讯 名字和变量 成员类型 只读 说明 Host(host_type As Long, [node], [username], [password], [working_directory]) As Boolean Function 通过 host_type 连接到指定的主机 基于 0 索引的有用的主机类型 HostCount As Long Property Yes 返回被连接的有效的主机类型的个数 HostDescription (host_type As Long) As String

## UG10-CH38-D323

PDF page: 571; original JSON pointer: `/6980`

Function 通过基于 0 的 host_type 索引返回一个专门

## UG10-CH38-D324

PDF page: 571; original JSON pointer: `/6981`

EngineFilesSettings(file As

## UG10-CH38-D325

PDF page: 571; original JSON pointer: `/6982`

IAP_ENGINEFILES) As

## UG10-CH38-D326

PDF page: 571; original JSON pointer: `/6983`

Property 查看引擎 驱动 文件的设置

## UG10-CH38-D327

PDF page: 571; original JSON pointer: `/6984`

IAP_RUN_OPTION) As

## UG10-CH38-D328

PDF page: 571; original JSON pointer: `/6985`

Property 查看模拟运行操作的设置

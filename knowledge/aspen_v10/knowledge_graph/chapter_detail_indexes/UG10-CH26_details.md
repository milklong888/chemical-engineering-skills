# UG10-CH26 Detail Operation Index - 第26章 工况研究

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH26-D001

PDF page: 374; original JSON pointer: `/4422`

l 规定工况研究报告选项

## UG10-CH26-D002

PDF page: 374; original JSON pointer: `/4423`

在你运行一个基础工况模拟后 你可能想要对同一流程运行几种参数的工况 当你批处

## UG10-CH26-D003

PDF page: 374; original JSON pointer: `/4424`

理运行时你可以使用工况研究的工具对同一流程来运行多个模拟工况 工况研究将顺序执行

## UG10-CH26-D004

PDF page: 374; original JSON pointer: `/4425`

同一流程的模拟 工况研究模块不影响基础工况的模拟或基础工况报告

## UG10-CH26-D005

PDF page: 374; original JSON pointer: `/4426`

ASPEN PLUS 对每个工况产生一个报告 你可以根据兴趣产生一定形式的工况报告

## UG10-CH26-D006

PDF page: 374; original JSON pointer: `/4427`

当你从用户图形界面以交互方式运行时 ASPEN PLUS 忽略工况研究模块 见第十一

## UG10-CH26-D007

PDF page: 374; original JSON pointer: `/4428`

章 关于批处理运行你的模拟

## UG10-CH26-D008

PDF page: 374; original JSON pointer: `/4429`

1. 从 Data 菜单 点向 Model Analysis Tools 然后 Case Study

## UG10-CH26-D009

PDF page: 374; original JSON pointer: `/4430`

2. 在 Case Study Setup Vary 页 标识你想要从一个工况到另一个工况改变的变量 见 本章关于表示工况研究变量的部分

## UG10-CH26-D010

PDF page: 374; original JSON pointer: `/4431`

3. 在 Case Study Setup Specifications 页上 规定每个工况的工况研究变量数值 见本 章关于规定工况研究变量值的部分

## UG10-CH26-D011

PDF page: 374; original JSON pointer: `/4432`

4. 如果你想要规定报告形式 使用 Case Study ReportOptions 表 见本章规定报告选 项的部分 标识工况研究变量 使用 Case Study Setup Vary 页标识你想要从一个工况到另一个工况改变的变量 你只能 改变模块输入 工艺进料物流和其它输入变量 结果变量不能被直接改变 标识你想要从一个工况到另一个工况改变的变量按以下步骤

## UG10-CH26-D012

PDF page: 374; original JSON pointer: `/4433`

1. 在 Case Study Setup 表上 选择 Vary 标签

## UG10-CH26-D013

PDF page: 374; original JSON pointer: `/4434`

2. 在 Variable Number 区域 单击向下箭头并从列表中选择<new>

## UG10-CH26-D014

PDF page: 374; original JSON pointer: `/4435`

3. 在 Manipulated Variable Type 区域 选择一个变量类型

## UG10-CH26-D015

PDF page: 374; original JSON pointer: `/4436`

4. ASPEN PLUS 自动显示必要的区域以唯一地表示流程变量 完成该区域以定义变 量 见第十八章关于访问流程变量的内容

## UG10-CH26-D016

PDF page: 374; original JSON pointer: `/4437`

5. 你可以选择给报告中的变量做标签 使用 Report Labels Line1 到 Line4 区域定义这 些变量

## UG10-CH26-D017

PDF page: 374; original JSON pointer: `/4438`

6. 重复步骤 2-5 直到你标识了所有的工况研究变量

## UG10-CH26-D018

PDF page: 375; original JSON pointer: `/4440`

使用 Case Study Setup Specifications 页规定工况研究变量的值

## UG10-CH26-D019

PDF page: 375; original JSON pointer: `/4441`

规定工况研究变量的值采取以下步骤

## UG10-CH26-D020

PDF page: 375; original JSON pointer: `/4442`

1. 在 Case Study Setup 表上 选择 Specifications 标签

## UG10-CH26-D021

PDF page: 375; original JSON pointer: `/4443`

2. 在 Case Number 区域 单击向下箭头并从列表中选择<new>

## UG10-CH26-D022

PDF page: 375; original JSON pointer: `/4444`

3. 在 New Item 对话框中 输入一个 ID 或接受缺省 ID ID 必须是整数

## UG10-CH26-D023

PDF page: 375; original JSON pointer: `/4445`

4. 在 Values for Manipulated Variable Type 区域 输入每个变量的一个值 以你在 Vary 页中标识的顺序输入多个变量值

## UG10-CH26-D024

PDF page: 375; original JSON pointer: `/4446`

5. 输入另一个工况 重复步骤 2-3 直到你定义了想运行的所有工况 在 Case Study Setup Specifications 页 你也可以

## UG10-CH26-D025

PDF page: 375; original JSON pointer: `/4447`

计规定 优化模块和 Fortran 模块所控制的撕裂流 进料物流的初始值 缺省情况下 模块

## UG10-CH26-D026

PDF page: 375; original JSON pointer: `/4448`

或物流不重新初始化 用先前工况的结果开始一个新工况的计算通常是最有效的

## UG10-CH26-D027

PDF page: 375; original JSON pointer: `/4449`

1. 在 Case Study Setup 表 选择 Specifications 标签

## UG10-CH26-D028

PDF page: 375; original JSON pointer: `/4450`

2. 在 Blocks to be Reinitialized 区域 选择 Include S pecified Blocks 或者 Reinitialized All Blocks

## UG10-CH26-D029

PDF page: 375; original JSON pointer: `/4451`

3. 如果你选择 Include Specified Blocks, 选择要被初始化的单元操作模块和/或收敛模 块 重新初始化物流

## UG10-CH26-D030

PDF page: 375; original JSON pointer: `/4452`

2. 在 Stream to be Reinitialized 区域 选择 Include Specified Streams 或者 Reinitialize All Blocks

## UG10-CH26-D031

PDF page: 375; original JSON pointer: `/4453`

3. 如果你选择 Include Specified Streams, 选择要被初始化的物流 输入一个说明 使用 Case Study Setup Specifications 页输入工况报告的说明 它将出现在工况报告中 输入一个报告说明

## UG10-CH26-D032

PDF page: 375; original JSON pointer: `/4454`

2. 单击 Description 按钮

## UG10-CH26-D033

PDF page: 375; original JSON pointer: `/4455`

4. 单击 Close 规定工况研究的报告选项 使用 Case Study Report Options 表规定报告的哪一部分包括在工况报告中 每个工况将

## UG10-CH26-D034

PDF page: 376; original JSON pointer: `/4457`

产生一个独立的报告 并且附在报告文件的末尾 如果你在 Setup Report Options 表上规定

## UG10-CH26-D035

PDF page: 376; original JSON pointer: `/4458`

了基础工况的报告选项 并且希望在这个工况仍然使用同样的形式 你必须在 Case Study

## UG10-CH26-D036

PDF page: 376; original JSON pointer: `/4459`

Report Options 页上再规定报告的选项

## UG10-CH26-D037

PDF page: 376; original JSON pointer: `/4460`

在模块的 Setup Report Options Block 页上或者 Block Options Report Options 页上对基础

## UG10-CH26-D038

PDF page: 376; original JSON pointer: `/4461`

工况规定的 Block 报告选项 也可用于工况报告

## UG10-CH26-D039

PDF page: 376; original JSON pointer: `/4462`

下表显示你可规定的选项以及在何处规定

## UG10-CH26-D040

PDF page: 376; original JSON pointer: `/4463`

规定 ReportOptions 页

## UG10-CH26-D041

PDF page: 376; original JSON pointer: `/4464`

是否产生一个报告文件以及包括哪部分报告 General

## UG10-CH26-D042

PDF page: 376; original JSON pointer: `/4465`

流程选项报告包括在报告文件中 Flowsheet

## UG10-CH26-D043

PDF page: 376; original JSON pointer: `/4466`

模块报告包括在报告文件中 Block

## UG10-CH26-D044

PDF page: 376; original JSON pointer: `/4467`

物流以及物流的格式包括在物流报告中 Stream

## UG10-CH26-D045

PDF page: 376; original JSON pointer: `/4468`

是否产生一个附加的物流报告 如果是这样 那

## UG10-CH26-D046

PDF page: 376; original JSON pointer: `/4469`

么物流以及物流的格式将报告在报告文件中

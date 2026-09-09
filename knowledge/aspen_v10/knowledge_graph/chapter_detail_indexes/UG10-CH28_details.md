# UG10-CH28 Detail Operation Index - 第28章 物性集

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH28-D001

PDF page: 394; original JSON pointer: `/4749`

l 怎样定义一个新的物性集或已存在的物性集

## UG10-CH28-D002

PDF page: 394; original JSON pointer: `/4750`

l 怎样在物性集中定义使用用户的物性集

## UG10-CH28-D003

PDF page: 394; original JSON pointer: `/4751`

l 单元操作模型加热/冷却曲线报告

## UG10-CH28-D004

PDF page: 394; original JSON pointer: `/4752`

l 蒸馏塔段物性报告和操作规定

## UG10-CH28-D005

PDF page: 394; original JSON pointer: `/4753`

l Fortran 和敏感性模块

## UG10-CH28-D006

PDF page: 394; original JSON pointer: `/4754`

你创建一个新的运行时所选择的模板来决定的 过于模板的更多的内容见第二章

## UG10-CH28-D007

PDF page: 394; original JSON pointer: `/4755`

的下拉列表来浏览所提供的内置的物性集或选择一个物性集 该表描述了每个内置的物性集

## UG10-CH28-D008

PDF page: 394; original JSON pointer: `/4756`

定义一个物性集采取如下步骤

## UG10-CH28-D009

PDF page: 394; original JSON pointer: `/4757`

1. 从 Data 菜单 单击 Properties

## UG10-CH28-D010

PDF page: 394; original JSON pointer: `/4758`

2. 在 Data Browser 的左屏上双击 Prop-Sets 文件夹

## UG10-CH28-D011

PDF page: 394; original JSON pointer: `/4759`

3. 创建一个新的物性集时 双击 New 在 Create New ID 对话框 输入一个新的物性 集 ID 或接受一个缺省的 ID 并且单击 OK

## UG10-CH28-D012

PDF page: 394; original JSON pointer: `/4760`

4. 一旦创建了新的物性集 要修改它 或任何已有的物性集 可以从 Object Manager 中选择名称 并且单击 Edit

## UG10-CH28-D013

PDF page: 394; original JSON pointer: `/4761`

5. 在 Prop-Sets 表的 Properties 页上 你可以在 Physical Properties 区域的下拉列表中 选择物性 可以选择一个或更多的物性包括在你的物性集中 当你选择时每个物性 将出现一个命令符 提示 可以使用 Search 按钮来寻找在物性集中你想要的物性 见本章的使用寻找 对话框中的关于寻找对话框部分

## UG10-CH28-D014

PDF page: 394; original JSON pointer: `/4762`

6. 使用 Units 区域来选择一个或多个物性的单位 如果你选择了多个单位 那么在报告中物性将以选择的每个单位报告

## UG10-CH28-D015

PDF page: 394; original JSON pointer: `/4763`

7. 在 Pop-Sets Qualifiers 页 规定下述的限定以计算物性

## UG10-CH28-D016

PDF page: 395; original JSON pointer: `/4765`

当你选择多个单位和限定时 ASPEN PLUS 将对于每个单位规定和每个有效的限定组合

## UG10-CH28-D017

PDF page: 395; original JSON pointer: `/4766`

如果你想要通过它的名称来寻找物性 那么单击在 Prop-Sets Properties 页上的 Search 按 钮 当你键入你想要找的物性的名称或部分名称时 将出现一个对话框 要加入一个物性到 你的物性集中 选择你期望的物性并且单击 Add 一旦你已经加入了你要的所有物性 那么 单击 OK 返回到 Prop-Sets 表 使用 Search 查找物性的示例 查找单词 viscosity 显示一些物性 动力学粘度已被选择并且被加入到物性集中

## UG10-CH28-D018

PDF page: 395; original JSON pointer: `/4767`

缺省的相态是 Total 如果一个物性不能接受 Total 作为限定条件 你必须输入一个适

## UG10-CH28-D019

PDF page: 396; original JSON pointer: `/4769`

你所选择的相态应该是与所期望计算的类型相一致 比如 如果你需要第一液相和第二

## UG10-CH28-D020

PDF page: 396; original JSON pointer: `/4770`

在缺省情况下 ASPEN PLUS 在物流的条件下计算物性 你也可以采取另一种方法

## UG10-CH28-D021

PDF page: 396; original JSON pointer: `/4771`

在 Prop-Sets Qualifiers 页的 Temperature and Pressure 区域规定温度和压力以计算物性 这些

## UG10-CH28-D022

PDF page: 396; original JSON pointer: `/4772`

规定不影响气相和液相的组成 这些组成是由物流的温度和压力决定的 ASPEN PLUS 从

## UG10-CH28-D023

PDF page: 396; original JSON pointer: `/4773`

你所规定的 Unit-Set 单位集 来决定温度和压力规定的单位

## UG10-CH28-D024

PDF page: 396; original JSON pointer: `/4774`

定义一个物性集 它由组分 C1 C2 和 C3 的纯组分液相 气相焓以及液 气相混合焓

## UG10-CH28-D025

PDF page: 397; original JSON pointer: `/4776`

定义一个物性集 它由液相中的组分 C1 和 C2 的活度系数组成 活度系数是在 100 200

## UG10-CH28-D026

PDF page: 397; original JSON pointer: `/4777`

输入的温度单位将是 ENG Units-Set 的温度的单位℉

## UG10-CH28-D027

PDF page: 398; original JSON pointer: `/4779`

你可以定义你自己的物性在物性集中使用 你必须提供一个 Fortran 子程序以计算每个

## UG10-CH28-D028

PDF page: 398; original JSON pointer: `/4780`

为了定义一个附加的物性到物性集中

## UG10-CH28-D029

PDF page: 398; original JSON pointer: `/4781`

1 从 Data 菜单中 单击 Properties

## UG10-CH28-D030

PDF page: 398; original JSON pointer: `/4782`

2 在 Data Brower 的左屏上双击 Advanced 文件夹打开它

## UG10-CH28-D031

PDF page: 398; original JSON pointer: `/4783`

3 选择 UserProperties

## UG10-CH28-D032

PDF page: 398; original JSON pointer: `/4784`

4 在 UserProperties Object Manager 上 单击 New

## UG10-CH28-D033

PDF page: 398; original JSON pointer: `/4785`

5 输入一个用户物性 ID 或者接受一个缺省 ID 并且单击 OK

## UG10-CH28-D034

PDF page: 398; original JSON pointer: `/4786`

6 在 Specifications 页 选择是否你的用户子程序将是一个标准的物性或者是分析曲 线性质

## UG10-CH28-D035

PDF page: 398; original JSON pointer: `/4787`

7 对于标准的物性 在 User Subroutine Name 区域内 输入用于计算物性的子程序的 名称

## UG10-CH28-D036

PDF page: 398; original JSON pointer: `/4788`

8 使用 Specifications 页的保留区输入关于该物性的信息

## UG10-CH28-D037

PDF page: 398; original JSON pointer: `/4789`

9 在 Units 页 规定是否你想要由 ASPEN PLUS 自动完成单位的转换 或者在你的用 户子程序内完成

# UG10-CH27 Detail Operation Index - 第27章 规定反应和化学

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH27-D001

PDF page: 377; original JSON pointer: `/4471`

第 27 章 规定反应和化学

## UG10-CH27-D002

PDF page: 377; original JSON pointer: `/4472`

本章描述了如何使用 ASPEN PLUS 定义反应系统 包括

## UG10-CH27-D003

PDF page: 377; original JSON pointer: `/4473`

l 规定反应器和泄压系统的幂定律方程

## UG10-CH27-D004

PDF page: 377; original JSON pointer: `/4474`

l 规定反应器和泄压系统的 LHHW反应

## UG10-CH27-D005

PDF page: 377; original JSON pointer: `/4475`

反应系统 说明 使用 Data Brower 表

## UG10-CH27-D006

PDF page: 377; original JSON pointer: `/4476`

控制的流率和非电解质平衡反应可以以 Reaction ID 规定 它可参见动力学反应器和泄

## UG10-CH27-D007

PDF page: 377; original JSON pointer: `/4477`

l 用户定义的动力学模型

## UG10-CH27-D008

PDF page: 377; original JSON pointer: `/4478`

电解质溶液化学采用 Chemistry ID 对规定 可参考在 Properties Specification Global 页

## UG10-CH27-D009

PDF page: 377; original JSON pointer: `/4479`

和各单元操作模块的 BlockOptions Prope rties 页 它不象非电解质反应只在一定的单元操作

## UG10-CH27-D010

PDF page: 377; original JSON pointer: `/4480`

模块和泄压计算中规定和运行 电解质化学定义是模拟或流程部分的物性规定的一部分 它

## UG10-CH27-D011

PDF page: 377; original JSON pointer: `/4481`

们用于使用那个物性规定的所有计算

## UG10-CH27-D012

PDF page: 378; original JSON pointer: `/4483`

第 27 章 规定反应和化学

## UG10-CH27-D013

PDF page: 378; original JSON pointer: `/4484`

l 物质间通过化学反应生成的化合物

## UG10-CH27-D014

PDF page: 378; original JSON pointer: `/4485`

选择反应和种类应属电解质化学 必须要正确做电解质化学的模型才能得到精确模拟结

## UG10-CH27-D015

PDF page: 378; original JSON pointer: `/4486`

数数据和可能的离子种类的基本知识为你生成种类和反应 参见第六章关于电解质智能系统

## UG10-CH27-D016

PDF page: 378; original JSON pointer: `/4487`

为一个模拟规定电解质化学 你必须

## UG10-CH27-D017

PDF page: 378; original JSON pointer: `/4488`

1. 在 Components Specifications Selection 页定义所出现的完整的组分系列 包括离子 盐和其它反应产生的物质

## UG10-CH27-D018

PDF page: 378; original JSON pointer: `/4489`

2. 用 Reactions Chemistry Stoichiometry 页定义化学计量系数以及反应类型

## UG10-CH27-D019

PDF page: 378; original JSON pointer: `/4490`

3. 使用 Reactions Chemistry Equilibrium Constants 页规定浓度基准 平衡接近温度以 及平衡常数表达式的系数 建议你使用电解质智能系统定义组分和反应 电解质智能系统

## UG10-CH27-D020

PDF page: 378; original JSON pointer: `/4491`

l 使用内置的基本知识生成电解质的种类和反应

## UG10-CH27-D021

PDF page: 378; original JSON pointer: `/4492`

你可以定义自己的电解质化学 或你可浏览或修改由电解质智能系统产生的化学数据

## UG10-CH27-D022

PDF page: 378; original JSON pointer: `/4493`

定义 浏览或修改电解质化学采取以下步骤

## UG10-CH27-D023

PDF page: 378; original JSON pointer: `/4494`

1. 从 Data 菜单 点 Reactions ,然后 Chemistry

## UG10-CH27-D024

PDF page: 378; original JSON pointer: `/4495`

2. 创建一个新的 Chemistry ID, 在 Reactions Chemistry Object Manager 中单击 New 在 Create new ID 对话框中输入一个 ID 然后单击 OK

## UG10-CH27-D025

PDF page: 378; original JSON pointer: `/4496`

3. 若修改已存在的化学 ID 在 Object Manager 中选择它的名字 并选择 Exit

## UG10-CH27-D026

PDF page: 378; original JSON pointer: `/4497`

4. 按本章后面的各节的详细指导 在一个化学 ID 中定义每个反应类型 下述各节解释了怎样通过规定化学计量系数和平衡常数的计算选项在一个已存在的化

## UG10-CH27-D027

PDF page: 379; original JSON pointer: `/4499`

第 27 章 规定反应和化学

## UG10-CH27-D028

PDF page: 379; original JSON pointer: `/4500`

学 ID 中创建一个新反应 你可规定在一个化学 ID 中的反应数

## UG10-CH27-D029

PDF page: 379; original JSON pointer: `/4501`

定义的一部分 你可在使用不同物性方法的地方规定不同的化学 ID 比如流程段或各单元

## UG10-CH27-D030

PDF page: 379; original JSON pointer: `/4502`

操作模块 见第七章关于在一个流程中规定多个物性方法

## UG10-CH27-D031

PDF page: 379; original JSON pointer: `/4503`

为电解质化学定义化学计量系数

## UG10-CH27-D032

PDF page: 379; original JSON pointer: `/4504`

定义一个新的反应标号且规定离子反应的平衡反应化学计量常数如下步骤

## UG10-CH27-D033

PDF page: 379; original JSON pointer: `/4505`

1. 在你的化学 ID 内的 Reactions Chemistry Stoichiometry 页单击 New

## UG10-CH27-D034

PDF page: 379; original JSON pointer: `/4506`

2. 在 Select Reaction Type 对话框 Equilibrium 是缺省的反应类型 输入一个 ID 或接 受缺省 ID 且单击 OK ID 必须是一个整数

## UG10-CH27-D035

PDF page: 379; original JSON pointer: `/4507`

3. 在 Equilibrium Reaction Stoichiometry 对话框 输入补充你的反应的组分和化学计量 系数 对于反应物系数为负数 生成物系数为正数

## UG10-CH27-D036

PDF page: 379; original JSON pointer: `/4508`

4. 完成时单击 Close 见在 Stoichiometry 页的新反应列表 相关的内容在方程的表中

## UG10-CH27-D037

PDF page: 379; original JSON pointer: `/4509`

5. 对于每个附加的离子平衡反应重复步骤 1-4 盐沉降反应 盐沉降反应描述了在液相平衡体系中盐的溶解的形成 在一个化学 ID 中的每个盐溶解 的反应用盐的组分名称标识 定义一个新的盐沉降反应的化学计量系数

## UG10-CH27-D038

PDF page: 379; original JSON pointer: `/4510`

2. 在 Select Reaction Type 对话框中 在 Choose Reaction Type 窗口选择 Salt

## UG10-CH27-D039

PDF page: 379; original JSON pointer: `/4511`

3. 在 Enter Salt Component ID 区域 为你定义的反应选择盐的名称 单击 OK

## UG10-CH27-D040

PDF page: 379; original JSON pointer: `/4512`

4. 在 Salt Dissolution Stoichiometry 对话框 输入由于盐的溶解生成的产品 离子 的组分和化学计量系数

## UG10-CH27-D041

PDF page: 379; original JSON pointer: `/4513`

5. 完成时单击 Close 见在 Stoichiometry 页的新反应列表 相关的内容在方程的表中

## UG10-CH27-D042

PDF page: 379; original JSON pointer: `/4514`

6. 对于每个附加的盐沉降反应重复步骤 1-5 完全电离反应 完全电离反应描述了强电解质在液相中的完全的电离 这些反应没有平衡常数 每个在 化学 ID 中的完全电离反应使用电离组分的名标识 定义一个新的完全电离的反应的化学计量系数采取如下步骤

## UG10-CH27-D043

PDF page: 379; original JSON pointer: `/4515`

2. 在 Select Reaction Type 对话框中 在 Choose Reaction Type 窗口选择 Dissociation

## UG10-CH27-D044

PDF page: 379; original JSON pointer: `/4516`

3. 在 Enter Dissociating Electrolyte 区域 为你定义的反应选择组分的名称 单击 OK

## UG10-CH27-D045

PDF page: 379; original JSON pointer: `/4517`

4. 在 Electrolyte Dissociating Stoichiometry 对话框 输入电离产品的组分和化学计量 系数

## UG10-CH27-D046

PDF page: 379; original JSON pointer: `/4518`

6. 对于每个附加的完全电离的反应重复步骤 1-5

## UG10-CH27-D047

PDF page: 380; original JSON pointer: `/4520`

第 27 章 规定反应和化学

## UG10-CH27-D048

PDF page: 380; original JSON pointer: `/4521`

定义电解质化学的平衡常数

## UG10-CH27-D049

PDF page: 380; original JSON pointer: `/4522`

做平衡离子反应和盐沉降反应平衡常数是必须的 ASPEN PLUS 可从关联式 温度的

## UG10-CH27-D050

PDF page: 380; original JSON pointer: `/4523`

函数 或者从参考状态的 Gibbs 自由能 在 ASPEN PLUS 数据库中可得到 计算这些平衡

## UG10-CH27-D051

PDF page: 380; original JSON pointer: `/4524`

定义在你的化学 ID 中的平衡离子反应和盐沉降反应的平衡常数采取如下步骤

## UG10-CH27-D052

PDF page: 380; original JSON pointer: `/4525`

1 在你的化学 ID 的 Reactions Chemistry 表中 选择 Equilibrium Constants页

## UG10-CH27-D053

PDF page: 380; original JSON pointer: `/4526`

2 选择在 Concentration Basis For Keq 列表中平衡常数的浓度基准 浓度基准决定怎 样计算平衡常数: 浓度基准 平衡常数定义 * 摩尔分率 缺省 K= ( i i) i 摩尔 K= (mi i) i * 这里 K = 平衡常数 = 组分摩尔分率 m = 克分子浓度(gmole/kg-H2O) = 活度系数 = 化学计量系数 i = 组分标号 是产品运算符 所有物性为液相

## UG10-CH27-D054

PDF page: 380; original JSON pointer: `/4527`

3 你可以规定一个平衡接近温度应用于在化学 ID 中定义的所有的离子平衡和盐沉降反 应 你规定的接近温度加在物流或模块上以计算平衡常数 如果你不规定一个平衡 接近温度 ASPEN PLUS 使用缺省值 0

## UG10-CH27-D055

PDF page: 380; original JSON pointer: `/4528`

4 使用 Hydrate-Check 区域的 ASPEN PLUS 使用的方法 可决定当你规定多个水合物 作为盐沉降反应时哪个水合物将沉降 Hydrate-Check 方法 说 明 Rigorious(缺省) 使用 Gibbs 最小自由能选择水合物 允许 ASPEN PLUS 预测带有多个水合物时盐的正 确的水合物的形成 Approximate 使用在系统温度下的最低溶解度的产品选择 水合物 计算时间比严格方法短

## UG10-CH27-D056

PDF page: 380; original JSON pointer: `/4529`

5 选择合适的反应类型 平衡反应或盐沉降反应 并且从列表中选择合适的反应类 型

## UG10-CH27-D057

PDF page: 380; original JSON pointer: `/4530`

6 使平衡常数为空 或 输入内置的平衡常数表达式的系数 ln(Keq) = A + B /T +C*ln(T) + D*T 这里 Keq = 平衡常数 T = 开尔文温度

## UG10-CH27-D058

PDF page: 381; original JSON pointer: `/4532`

第 27 章 规定反应和化学

## UG10-CH27-D059

PDF page: 381; original JSON pointer: `/4533`

K 的定义依赖于选择的浓度基准

## UG10-CH27-D060

PDF page: 381; original JSON pointer: `/4534`

如果系数没有输入 ASPEN PLUS 从参考状态的 Gibbs 生成自由能计算平衡常数 重复步骤 5 到 6 定义所有在化学 ID 中的离子平衡反应和盐沉降反应 因为完全电离 反应没有平衡常数 所以在这类反应中没有平衡常数页 规定反应器和泄压系统的幂定律反应 Powerlaw Reaction ID 可以表示幂律的平衡反应或流率控制的反应 为了在 ASPEN PLUS 反应器模型 RCSTR RPlug 和 RBatch 或计算泄压系统的 Pres-Relief 中使用幂定律反 应 ID 你需要

## UG10-CH27-D061

PDF page: 381; original JSON pointer: `/4535`

l 定义反应的类型和化学计量系数

## UG10-CH27-D062

PDF page: 381; original JSON pointer: `/4536`

l 输入平衡或动力学参数

## UG10-CH27-D063

PDF page: 381; original JSON pointer: `/4537`

为了创建一个幂定律反应 ID

## UG10-CH27-D064

PDF page: 381; original JSON pointer: `/4538`

1. 从 Data 菜单 点 Reactions ,然后 Chemistry

## UG10-CH27-D065

PDF page: 381; original JSON pointer: `/4539`

2. 创建一个新的 Chemistry ID, 在 Reactions Chemistry Object Manager 中单击 New

## UG10-CH27-D066

PDF page: 381; original JSON pointer: `/4540`

3. 在 Create new ID 对话框中 ID 区域输入一个反应 ID 或接受一个缺省 ID

## UG10-CH27-D067

PDF page: 381; original JSON pointer: `/4541`

4. 在 Select Type 列表中选择 Powerlaw 然后单击 OK 一旦创建了反应 ID ASPEN PLUS 将打开化学计量系数页 你可定义在反应 ID 内的反 应 在反应 ID 内有两种类型的反应 类 型 用 于 Equilibrium 平衡反应 Kinetic 流率控制的反应

## UG10-CH27-D068

PDF page: 381; original JSON pointer: `/4542`

5. 为了规定你的反应 ID 中的各反应 遵循本章的以后各节中你想要创建的反应类型 的部分 平衡反应 只对于 RCSTR 加入平衡类型到你的 Powerlaw Reaction 幂律反应 ID 中

## UG10-CH27-D069

PDF page: 381; original JSON pointer: `/4543`

1. 单击你的 Powerlaw Reaction ID 中的 Reactions Stoichiometry 页上的 New

## UG10-CH27-D070

PDF page: 381; original JSON pointer: `/4544`

2. 在 Edit Reaction 对话框 选择 Reaction Type 列表中的 Equilibrium 反应标号自动 输入

## UG10-CH27-D071

PDF page: 381; original JSON pointer: `/4545`

3. 输入组分和化学计量系数定义反应 对反应物系数为负数 生成物为正数 你不应 规定平衡反应的幂

## UG10-CH27-D072

PDF page: 381; original JSON pointer: `/4546`

4. 完成时单击 Close 你应该能看见新的反应标号 类型和方程显示在 Stoichiometry 页上

## UG10-CH27-D073

PDF page: 381; original JSON pointer: `/4547`

5. 对于每个附加的平衡反应重复步骤 1 到 4

## UG10-CH27-D074

PDF page: 381; original JSON pointer: `/4548`

6. 选择在 Reactions 表中的 Equilibrium标签 打开那页

## UG10-CH27-D075

PDF page: 381; original JSON pointer: `/4549`

7. 在 Equilibrium页 从页的上部的列表中选择一个反应

## UG10-CH27-D076

PDF page: 381; original JSON pointer: `/4550`

8. 在 Reacting Phase 列表中规定反应发生的相态 缺省为液相

## UG10-CH27-D077

PDF page: 381; original JSON pointer: `/4551`

9. 如果反应没有达到平衡 你可在 Temperate Approach to Equilibrium 区域输入一个 反应的平衡接近温度 你输入温度数将被加到反应器的温度上以计算平衡常数

## UG10-CH27-D078

PDF page: 382; original JSON pointer: `/4553`

第 27 章 规定反应和化学

## UG10-CH27-D079

PDF page: 382; original JSON pointer: `/4554`

10. 选择你是否想要从 Gibbs 能计算 Keq 或者从一个内置的多项式的适宜形式来计算 Keq 如果你选择从 Gibbs 能计算 Keq 你不需要输入平衡常数的系数 ASPEN PLUS 将 从组分的参考状态的 Gibbs 自由能计算 Keq

## UG10-CH27-D080

PDF page: 382; original JSON pointer: `/4555`

11. 如果你选择从一个内置的多项式来计算 Keq 输入一个内置的平衡常数表达式的系 数 并且选择平衡常数的基准 ln Keq = A + B /T +C*ln(T) + D*T 这里 Keq = 平衡常数 T = 开尔文温度 A B C D=用户提供的系数 K 的定义依赖于你在 Keq Basis 列表中选择的浓度基准 Keq 基准 平衡常数定义 * Mole gamma(缺省) K= ( i i) i (仅液相) Mole gamma K= (mi i) i (仅电解质 液相)

## UG10-CH27-D081

PDF page: 382; original JSON pointer: `/4556`

Mole fraction K= ( i) i

## UG10-CH27-D082

PDF page: 382; original JSON pointer: `/4557`

C = 克分子浓度(kgmole/m3)

## UG10-CH27-D083

PDF page: 382; original JSON pointer: `/4558`

m = 克分子浓度(gmole/kg-H2O)

## UG10-CH27-D084

PDF page: 382; original JSON pointer: `/4559`

12. 如果有固体存在 单击 Solids 按钮并且选择浓度计算的适宜选项 见本章带有固体 的反应的内容

## UG10-CH27-D085

PDF page: 382; original JSON pointer: `/4560`

13. 对每个平衡反应重复步骤 7 到 12 流率控制的反应

## UG10-CH27-D086

PDF page: 382; original JSON pointer: `/4561`

1. 单击你的 Powerlaw Reaction ID 中的 Reactions Stoichiometry 页上的 New

## UG10-CH27-D087

PDF page: 382; original JSON pointer: `/4562`

2. 在 Edit Reaction 对话框 Reaction Type 缺省为 Kinetic, 反应标号自动输入 输入组

## UG10-CH27-D088

PDF page: 383; original JSON pointer: `/4564`

第 27 章 规定反应和化学

## UG10-CH27-D089

PDF page: 383; original JSON pointer: `/4565`

分和化学计量系数定义反应 对反应物系数为负数 生成物为正数

## UG10-CH27-D090

PDF page: 383; original JSON pointer: `/4566`

3. 规定组分的幂律的幂 这些幂代表相应于每个组分的反应次序 如果你不规定每个 组分的幂 ASPEN PLUS 使用缺省值 0

## UG10-CH27-D091

PDF page: 383; original JSON pointer: `/4567`

4. 完成时单击 Close 你应该能看见新的反应标号 类型和方程显示在 Stoichiometry 页上

## UG10-CH27-D092

PDF page: 383; original JSON pointer: `/4568`

5. 对于每个附加的动力学反应重复步骤 1 到 4

## UG10-CH27-D093

PDF page: 383; original JSON pointer: `/4569`

6. 选择 Kinetic 页

## UG10-CH27-D094

PDF page: 383; original JSON pointer: `/4570`

7. 在 Kinetic 页 从页的上部的列表中选择一个反应

## UG10-CH27-D095

PDF page: 383; original JSON pointer: `/4571`

8. 在 Reacting Phase 区域中规定反应发生的相态 缺省为液相

## UG10-CH27-D096

PDF page: 383; original JSON pointer: `/4572`

9. 在相应的区域内输入指前因子 k 温度指数 n 和活化能 E 指前因子必 须是本节后面叙述的 SI 制 温度指数指开尔文温度

## UG10-CH27-D097

PDF page: 383; original JSON pointer: `/4573`

10. 在[Ci] Basis 列表中 选择浓度基准 浓度基准决定了使用的幂率形式 本节后面将 叙述

## UG10-CH27-D098

PDF page: 383; original JSON pointer: `/4574`

11. 如果有固体存在 单击 Solids 按钮并且选择浓度计算的适宜选项 见本章带有固体 的反应的内容

## UG10-CH27-D099

PDF page: 383; original JSON pointer: `/4575`

正文待来源表达/OCR边界复核；原文本 SHA256: `9be6ea4795382249fe32ed5e3eb287a6b94542d34dfc7e98fbfa56b06d409e10`。

## UG10-CH27-D100

PDF page: 383; original JSON pointer: `/4576`

C = 克分子浓度(kgmole/m3)

## UG10-CH27-D101

PDF page: 383; original JSON pointer: `/4577`

m = 克分子浓度(gmole/kg-H2O)

## UG10-CH27-D102

PDF page: 383; original JSON pointer: `/4578`

l 在[Ci] Basis 列表中选择的浓度基准

## UG10-CH27-D103

PDF page: 384; original JSON pointer: `/4580`

第 27 章 规定反应和化学

## UG10-CH27-D104

PDF page: 384; original JSON pointer: `/4581`

度的体积基准方面的影响 本节的内容意在帮助你规定反应的 ID 它将很精确地反映你的

## UG10-CH27-D105

PDF page: 384; original JSON pointer: `/4582`

当在 Edit Reaction 对话框中规定一个反应时

## UG10-CH27-D106

PDF page: 384; original JSON pointer: `/4583`

参与反应但不控制反应速度 只输入这些固体的化学计量系数 不输入指

## UG10-CH27-D107

PDF page: 384; original JSON pointer: `/4584`

Mole fraction 或 Mass fraction

## UG10-CH27-D108

PDF page: 385; original JSON pointer: `/4586`

第 27 章 规定反应和化学

## UG10-CH27-D109

PDF page: 385; original JSON pointer: `/4587`

作为催化剂控制反应速度但不参与反应 只输入这些固体的指数 不输入化学计量系

## UG10-CH27-D110

PDF page: 385; original JSON pointer: `/4588`

惰性的 化学计量系数和指数都不输入

## UG10-CH27-D111

PDF page: 385; original JSON pointer: `/4589`

当做一些规定 以计算平衡反应的平衡常数或动力学反应的反应速率时 固体组分可以

## UG10-CH27-D112

PDF page: 385; original JSON pointer: `/4590`

Solids 按钮 可以控制这些计算怎样完成

## UG10-CH27-D113

PDF page: 385; original JSON pointer: `/4591`

Solids 对话框关于组分的命名允许有下述规定

## UG10-CH27-D114

PDF page: 385; original JSON pointer: `/4592`

对于液体和气体组分浓度 你可以通过单击在 For Liquid 或 Vapor Component 窗口中的

## UG10-CH27-D115

PDF page: 385; original JSON pointer: `/4593`

适宜选项仅仅包括反应相态 或者反应相态和固态 缺省的是只包括反应相态

## UG10-CH27-D116

PDF page: 385; original JSON pointer: `/4594`

对于固体组分浓度 你可以通过单击在 For Solid Component 窗口中的适宜选项仅仅包

## UG10-CH27-D117

PDF page: 385; original JSON pointer: `/4595`

括固相 或者固相和全液相 缺省的是只包括固相

## UG10-CH27-D118

PDF page: 385; original JSON pointer: `/4596`

对于 wolid 组分浓度 你也可通过单击适宜的选项来包括所有子物流的固体组分 或者

## UG10-CH27-D119

PDF page: 385; original JSON pointer: `/4597`

反应固体的子物流中的组分 缺省的是包括所有子物流中的固体

## UG10-CH27-D120

PDF page: 385; original JSON pointer: `/4598`

规定反应器和泄压系统的 LHHW 反应

## UG10-CH27-D121

PDF page: 385; original JSON pointer: `/4599`

你需要以下步 骤来规定 Langmuir-hinshelwood-Hougen-Watson(LHHW)动力学以模拟

## UG10-CH27-D122

PDF page: 385; original JSON pointer: `/4600`

l 定义反应的类型和计量系数

## UG10-CH27-D123

PDF page: 385; original JSON pointer: `/4601`

l 输入平衡或动力学参数

## UG10-CH27-D124

PDF page: 385; original JSON pointer: `/4602`

l 规定可选的吸附表达式

## UG10-CH27-D125

PDF page: 385; original JSON pointer: `/4603`

1. 从 Data 菜单中 指向 Reactions , 然后选 Reactions

## UG10-CH27-D126

PDF page: 385; original JSON pointer: `/4604`

2. 在 Reactions Object Manager 单击 New 创建一个新的 Reaction ID

## UG10-CH27-D127

PDF page: 385; original JSON pointer: `/4605`

3. 在 Create New ID 对话框中 在 Enter ID 区域输入一个反应名 或者接受一个缺省 的 ID

## UG10-CH27-D128

PDF page: 385; original JSON pointer: `/4606`

4. 在 Select Type 列表中选择 LHHW 单击 OK 一旦创建了反应 ID 那么你可在反应 ID 中定义反应 在 LHHW类型的反应 ID 中允许 有两种类型的反应 类 型 用 于 Equilibrium 平衡反应 Kinetic 流率控制的反应 为了在你的 LHHW 反应 ID 中规定各反应 遵循本章后面的各节关于你要创建的反应类 型的指导 LHHW 的平衡反应 只用于 RCSTR 采用与幂率反应同样的方式规定 LHHW平衡反应 见本章关于规定反应器和泄压系统

## UG10-CH27-D129

PDF page: 386; original JSON pointer: `/4608`

第 27 章 规定反应和化学

## UG10-CH27-D130

PDF page: 386; original JSON pointer: `/4609`

C = 组分分子浓度(kgmole/m3)

## UG10-CH27-D131

PDF page: 386; original JSON pointer: `/4610`

浓度项 C i 和 C j 依赖于你所选择的浓度基准

## UG10-CH27-D132

PDF page: 386; original JSON pointer: `/4611`

Molarity 组分摩尔浓度(kgmole/m3)

## UG10-CH27-D133

PDF page: 386; original JSON pointer: `/4612`

Molarity 组分克分子浓度(gmole/kgH2O)

## UG10-CH27-D134

PDF page: 386; original JSON pointer: `/4613`

Mole fraction 组分摩尔分率

## UG10-CH27-D135

PDF page: 386; original JSON pointer: `/4614`

1. 单击你的 LHHW Reaction ID 中的 Reactions Stoichiometry 页上的 New g = ( )( exp ) ( exp ) kinetic factor driving force ression adsorption ression Kinetic factor kT en E RTa= − / ( ) ( )Driving force ression K C Ci i v j vi iexp = −∏ ∏ ( ){ }Adsorption ression K Ci j v m iexp = ∏∑

## UG10-CH27-D136

PDF page: 387; original JSON pointer: `/4616`

第 27 章 规定反应和化学

## UG10-CH27-D137

PDF page: 387; original JSON pointer: `/4617`

2. 在 Edit Reaction 对话框 Reaction Type 缺省为 Kinetic, 反应标号自动输入 输入 组分和化学计量系数定义反应 对反应物系数为负数 生成物为正数

## UG10-CH27-D138

PDF page: 387; original JSON pointer: `/4618`

3. 完成时单击 Close 你应该能看见新的反应标号 类型和方程显示在 Stoichiometry 页上

## UG10-CH27-D139

PDF page: 387; original JSON pointer: `/4619`

4. 对于每个附加的动力学反应重复步骤 1 到 3

## UG10-CH27-D140

PDF page: 387; original JSON pointer: `/4620`

5. 选择 Kinetic 页

## UG10-CH27-D141

PDF page: 387; original JSON pointer: `/4621`

6. 在 Kinetic 页 从页的上部的列表中选择一个反应

## UG10-CH27-D142

PDF page: 387; original JSON pointer: `/4622`

7. 在 Reacting Phase 区域中规定反应发生的相态 缺省为液相

## UG10-CH27-D143

PDF page: 387; original JSON pointer: `/4623`

8. 在相应的 Kinetic Factor 窗口区域内输入指前因子 k 温度指数 n 和活化能 E 指前因子必须是在规定反应器和泄压系统幂率反应部分所叙述的 SI 制 温 度指数指开尔文温度

## UG10-CH27-D144

PDF page: 387; original JSON pointer: `/4624`

9. 如果有固体存在 单击 Solids 按钮并且选择浓度计算的适宜选项 见本章带有固体 的反应的内容

## UG10-CH27-D145

PDF page: 387; original JSON pointer: `/4625`

10. 单击 Driving Force 按钮

## UG10-CH27-D146

PDF page: 387; original JSON pointer: `/4626`

11. 在 Driving Force Expression 对话框中 在[Ci]基准列表中选择浓度基准 见本章的 规定反应器和泄压系统的幂率反应部分中的关于浓度基准选项

## UG10-CH27-D147

PDF page: 387; original JSON pointer: `/4627`

12. Term1 的 Enter Term 有缺省值 输入反应物和生成物的浓度指数以及驱动力表达式 中项 1 的动力常数系数 A B C 和 D

## UG10-CH27-D148

PDF page: 387; original JSON pointer: `/4628`

13. 在 Enter Term 列表中选 Term 2

## UG10-CH27-D149

PDF page: 387; original JSON pointer: `/4629`

14. 输入反应物和生成物的浓度指数以及驱动力表达式中的项 2 的动力常数系数 A B C 和 D

## UG10-CH27-D150

PDF page: 387; original JSON pointer: `/4630`

15. 两项的输入完成后单击 Close

## UG10-CH27-D151

PDF page: 387; original JSON pointer: `/4631`

16. 单击 Adsorption 按钮 规定可选的吸附表达式

## UG10-CH27-D152

PDF page: 387; original JSON pointer: `/4632`

17. 在 Adsorption Expression 对话框中 在 Adsorption Expression Exponent 区域中输入 吸附各项的指数

## UG10-CH27-D153

PDF page: 387; original JSON pointer: `/4633`

18. 选择组分并且输入吸附表达式中的各项的指数已规定浓度的指数

## UG10-CH27-D154

PDF page: 387; original JSON pointer: `/4634`

19. 通过输入 Term No.和规定系数来规定吸附常数 系数是在下述关联式中 ln Ki = Ai + Bi /T +Ci*ln(T) + Di*T 这里 Ki = 平衡常数 T = 开尔文温度 Ai Bi Ci D i = 用户提供的系数

## UG10-CH27-D155

PDF page: 387; original JSON pointer: `/4635`

20. 对于每个附加的 LHHW动力学反应重复步骤 6 到 19 规定反应蒸馏的反应 使用 REAC-DIST 表 以规定蒸馏模型 RadFrac,BatchFrac 和 RateFrac 带有反应的蒸馏的 反应

## UG10-CH27-D156

PDF page: 387; original JSON pointer: `/4636`

l 定义反应的化学计量系数

## UG10-CH27-D157

PDF page: 387; original JSON pointer: `/4637`

l 输入平衡或动力学参数

## UG10-CH27-D158

PDF page: 387; original JSON pointer: `/4638`

l 规定用户提供的动力学参数

## UG10-CH27-D159

PDF page: 387; original JSON pointer: `/4639`

对于 RadFrac,和 RateFrac 你也可使用 Reactions User 表规定用户定义的动力学 见本

## UG10-CH27-D160

PDF page: 387; original JSON pointer: `/4640`

章关于使用用户子程序 Reactions User 表是较好的 因为你可以使用同样的用户定义动

## UG10-CH27-D161

PDF page: 388; original JSON pointer: `/4642`

第 27 章 规定反应和化学

## UG10-CH27-D162

PDF page: 388; original JSON pointer: `/4643`

为了创建一个新的蒸馏反应 ID

## UG10-CH27-D163

PDF page: 388; original JSON pointer: `/4644`

1. 从 Data 菜单 指向 Reactions ,然后选 Reactions

## UG10-CH27-D164

PDF page: 388; original JSON pointer: `/4645`

2. 在 Reaction Object Manager 中 单击 New,创建一个新的反应 ID

## UG10-CH27-D165

PDF page: 388; original JSON pointer: `/4646`

3. 在 Create New ID 对话框 在 Enter ID 区域中输入一个反应名称 或者接受一个缺 省的 ID

## UG10-CH27-D166

PDF page: 388; original JSON pointer: `/4647`

4. 在 Select Type 列表中 选择 REAC-DIST 单击 OK 一旦创建了反应 ID 那么你可在反应 ID 中定义反应 在 REAC-DIST 反应 ID 中允许 有四种类型的反应 类 型 用 于 Equilibrium 平衡反应 Kinetic 流率控制的反应 Conversion 部分转换反应 只对 RadFrac Salt 电解质盐沉降反应 只对 RadFrac

## UG10-CH27-D167

PDF page: 388; original JSON pointer: `/4648`

5 为了在你的 REAC-DIST 反应 ID 中规定各反应 遵循本章后面的各节关于在前表 中你要创建的反应类型的指导 平衡反应

## UG10-CH27-D168

PDF page: 388; original JSON pointer: `/4649`

1. 单击你的 Powerlaw Reaction ID 中的 Reactions Stoichiometry 页上的 New

## UG10-CH27-D169

PDF page: 388; original JSON pointer: `/4650`

2. 在 Select Reaction Type 对话框 Kinetic/Equilibrium/Conversion 是缺省的反应类型 接受缺省的 Reaction No.或输入一个新的 Reaction No. 然后单击 OK

## UG10-CH27-D170

PDF page: 388; original JSON pointer: `/4651`

3. 在 Edit Reaction 对话框 反应类型缺省为 Equilibrium 输入组分和化学计量系数定 义反应 对反应物系数为负数 生成物为正数 你不应规定平衡反应的幂

## UG10-CH27-D171

PDF page: 388; original JSON pointer: `/4652`

4. 完成时单击 Close 你应该能看见新的反应标号 类型和方程显示在 Stoichiometry 页上

## UG10-CH27-D172

PDF page: 388; original JSON pointer: `/4653`

5. 对于每个附加的平衡反应重复步骤 1 到 4

## UG10-CH27-D173

PDF page: 388; original JSON pointer: `/4654`

6. 单击 Equilibrium页

## UG10-CH27-D174

PDF page: 388; original JSON pointer: `/4655`

7. 在 Equilibrium页 从页的上部的列表中选择一个反应

## UG10-CH27-D175

PDF page: 388; original JSON pointer: `/4656`

8. 在 Reacting Phase 列表中规定反应发生的相态 缺省为液相

## UG10-CH27-D176

PDF page: 388; original JSON pointer: `/4657`

9. 在 Keq Basis 列表中选择一个选项以规定平衡常数的计算基准 你所选择的基准定 义平衡常数是怎样计算的 在本节后面的我们将讨论

## UG10-CH27-D177

PDF page: 388; original JSON pointer: `/4658`

10. 如果反应没有达到平衡 你可在 Temperate Approach to Equilibrium 区域输入一个 反应的平衡接近温度 你输入温度数将被加到反应段的温度上以计算平衡常数

## UG10-CH27-D178

PDF page: 388; original JSON pointer: `/4659`

11. 选择你是否想要从 Gibbs 能计算 Keq 或者从一个内置的多项式的适宜形式来计算 Keq 如果你选择从 Gibbs 能计算 Keq 你不需要输入平衡常数的系数 ASPEN PLUS 将 从组分的参考状态的 Gibbs 自由能计算 Keq 你可跳到步骤 12

## UG10-CH27-D179

PDF page: 388; original JSON pointer: `/4660`

12. 如果你选择从一个内置的多项式来计算 Keq 输入一个内置的平衡常数表达式的系 数 并且选择平衡常数的基准 ln Keq = A + B /T +C*ln(T) + D*T 这里 Keq = 平衡常数

## UG10-CH27-D180

PDF page: 389; original JSON pointer: `/4662`

第 27 章 规定反应和化学

## UG10-CH27-D181

PDF page: 389; original JSON pointer: `/4663`

K 的定义依赖于你在 Keq Basis 列表中选择的浓度基准

## UG10-CH27-D182

PDF page: 389; original JSON pointer: `/4664`

Keq 基准 平衡常数定义 *

## UG10-CH27-D183

PDF page: 389; original JSON pointer: `/4665`

Mole gamma(缺省) K= ( i i) i (仅液相)

## UG10-CH27-D184

PDF page: 389; original JSON pointer: `/4666`

Mole gamma K= (mi i) i (仅电解质 液相)

## UG10-CH27-D185

PDF page: 389; original JSON pointer: `/4667`

Mole fraction K= ( i) i

## UG10-CH27-D186

PDF page: 389; original JSON pointer: `/4668`

C = 克分子浓度(kgmole/m3)

## UG10-CH27-D187

PDF page: 389; original JSON pointer: `/4669`

m = 克分子浓度(gmole/kg-H2O)

## UG10-CH27-D188

PDF page: 389; original JSON pointer: `/4670`

所有的物性参见在 Reacting Phase 区域输入的相态

## UG10-CH27-D189

PDF page: 389; original JSON pointer: `/4671`

13. 对每个平衡反应重复步骤 7 到 12 流率控制的反应 反应蒸馏的动力学可以使用一个内置的幂率方程 或者一个用户动力学子程序来表示 下述步骤指示怎样使用这两种方法 加入动力学类型反应到你的 Reaction ID 中

## UG10-CH27-D190

PDF page: 389; original JSON pointer: `/4672`

1. 单击你的 Reac-Dist ID 的 Reactions Stoichiometry 页上的 New

## UG10-CH27-D191

PDF page: 389; original JSON pointer: `/4673`

2. 在 Select Reaction Type 对话框 Kinetic/Equilibrium/Conversion 是缺省的反应类型 接受缺省的 Reaction No.或输入一个新的 Reaction No. 然后单击 OK

## UG10-CH27-D192

PDF page: 389; original JSON pointer: `/4674`

3. 在 Edit Reaction 对话框 从 Reaction Type 列表中选择 Kinetic

## UG10-CH27-D193

PDF page: 389; original JSON pointer: `/4675`

4. 输入组分和化学计量系数以定义反应 系数对于反应物为负数 对于生成物为正数

## UG10-CH27-D194

PDF page: 389; original JSON pointer: `/4676`

5. 规定组分的幂律的幂 这些幂代表相应于每个组分的反应次序 如果你希望用用户 子程序来计算反应速度 那么不需要在该页输入指数

## UG10-CH27-D195

PDF page: 389; original JSON pointer: `/4677`

6. 完成时单击 Close 你应该能看见新的反应标号 类型和方程显示在 Stoichiometry 页上

## UG10-CH27-D196

PDF page: 389; original JSON pointer: `/4678`

7. 对于每个附加的动力学反应重复步骤 1 到 6

## UG10-CH27-D197

PDF page: 390; original JSON pointer: `/4680`

第 27 章 规定反应和化学

## UG10-CH27-D198

PDF page: 390; original JSON pointer: `/4681`

8. 选择 Kinetic 页

## UG10-CH27-D199

PDF page: 390; original JSON pointer: `/4682`

9. 在 Kinetic 页 选择使用内置的幂率表达式的适宜选项 或一个用户子程序的适宜 选项来代表当前反应 ID 的动力学

## UG10-CH27-D200

PDF page: 390; original JSON pointer: `/4683`

10. 从列表中选择一个反应或使用 Reacting Phase 列表规定反应发生的相态 缺省的反 应相态为液相

## UG10-CH27-D201

PDF page: 390; original JSON pointer: `/4684`

11. 使用用户子程序 你不需要在该页输入任何额外的信息 选择反应表中的 Subroutine 标签 并且在 Name 区域规定子程序名 对于 RadFrac,和 RateFrac 你也可使用 Reactions User 表规定用户定义的动力学 见 本章关于使用用户子程序 Reactions User 表是较好的 因为你可以使用同样的用 户定义动力学在反应器和泄压系统的计算中 更多的内容请见 ASPEN PLUS 用户 模型 中的使用和编写用户动力学模型 下述步骤告诉你怎样使用内置的幂率方程

## UG10-CH27-D202

PDF page: 390; original JSON pointer: `/4685`

12. 使用内置的幂率方程 在 Reactions 表的 Kinetic 页上输入指前因子 k 温度指 数 n 和活化能 E 指前因子必须是在本节后面所叙述的 SI 制 温度指数是 指开尔文温度

## UG10-CH27-D203

PDF page: 390; original JSON pointer: `/4686`

13. 在[Ci] Basis 列表中 选择浓度基准 浓度基准决定了使用的幂率形式 本节后面 将叙述

## UG10-CH27-D204

PDF page: 390; original JSON pointer: `/4687`

正文待来源表达/OCR边界复核；原文本 SHA256: `a55034f1c85a09fff40af1eab728b33e091ed6234779a811e103764609b2367a`。

## UG10-CH27-D205

PDF page: 390; original JSON pointer: `/4688`

C = 克分子浓度(kgmole/m3)

## UG10-CH27-D206

PDF page: 390; original JSON pointer: `/4689`

m = 克分子浓度(gmole/kg-H2O)

## UG10-CH27-D207

PDF page: 391; original JSON pointer: `/4691`

第 27 章 规定反应和化学

## UG10-CH27-D208

PDF page: 391; original JSON pointer: `/4692`

l 在[Ci] Basis 列表中选择的浓度基准

## UG10-CH27-D209

PDF page: 391; original JSON pointer: `/4693`

其中的停留单位是 在使用反应的蒸馏模块规定如下

## UG10-CH27-D210

PDF page: 391; original JSON pointer: `/4694`

kgmole 摩尔停留时间

## UG10-CH27-D211

PDF page: 391; original JSON pointer: `/4695`

部分转换反应 只对 RadFrac

## UG10-CH27-D212

PDF page: 391; original JSON pointer: `/4696`

有另一种方法可以蒸馏塔中的定义反应 是基于内置的温度函数的关联式来计算转化

## UG10-CH27-D213

PDF page: 391; original JSON pointer: `/4697`

Mole fraction 或 Mass fraction

## UG10-CH27-D214

PDF page: 392; original JSON pointer: `/4699`

第 27 章 规定反应和化学

## UG10-CH27-D215

PDF page: 392; original JSON pointer: `/4700`

1. 单击你的 Reac-Dist ID 的 Reactions Stoichiometry 页上的 New

## UG10-CH27-D216

PDF page: 392; original JSON pointer: `/4701`

2. 在 Select Reaction Type 对话框 Kinetic/Equilibrium/Conversion 是缺省的反应类型 接受缺省的 Reaction No.或输入一个新的 Reaction No. 然后单击 OK

## UG10-CH27-D217

PDF page: 392; original JSON pointer: `/4702`

3. 在 Edit Reaction 对话框 从 Reaction Type 列表中选择 Conversion

## UG10-CH27-D218

PDF page: 392; original JSON pointer: `/4703`

4. 输入组分和化学计量系数以定义反应 系数对于反应物为负数 对于生成物为正数 你不应该规定转换反应的指数

## UG10-CH27-D219

PDF page: 392; original JSON pointer: `/4704`

5. 完成时单击 Close 你应该能看见新的反应标号 类型和方程显示在 Stoichiometry 页上

## UG10-CH27-D220

PDF page: 392; original JSON pointer: `/4705`

6. 对于每个附加的转换反应重复步骤 1 到 6

## UG10-CH27-D221

PDF page: 392; original JSON pointer: `/4706`

7. 选择 Conversion 页

## UG10-CH27-D222

PDF page: 392; original JSON pointer: `/4707`

8. 如果你有多个转换反应在你的反应 ID 中 那么规定你是否想要各个转换反应同时 计算 或者按次序计算 在缺省情况下 转换反应被假定是同时发生 如果你想要 转换反应按次序计算 那么使 Reaction Occur in Series 有效 你必须规定所有的转 换反应为同一类型 系列反应的发生以你输入的次序为准

## UG10-CH27-D223

PDF page: 392; original JSON pointer: `/4708`

9. 从列表中选择一个反应

## UG10-CH27-D224

PDF page: 392; original JSON pointer: `/4709`

10. 在 Conversion Expression 窗口 选择你选定的反应的转化率基准组分 在 Key Component 列表中 转化率定义是关键组分的转化分率

## UG10-CH27-D225

PDF page: 392; original JSON pointer: `/4710`

11. 输入部分转化关联式的系数 Conv= A + B /T +C*ln(T) + D*T 你也可以输入在 RadFrac Reactions Conversion 页上的转化率 以替换从转化关联式计 算的值 盐沉降反应 只对 RadFrac 除了可以规定液相和气相反应外 你也可规定盐沉降反应 这些反应是液/固相平衡反 应 这里的固相是由单一的盐组成 加入盐沉降反应类型到你的 Reac-Dist 反应 ID 中

## UG10-CH27-D226

PDF page: 392; original JSON pointer: `/4711`

1. 单击你的 Powerlaw Reaction ID 中的 Reactions Stoichiometry 页上的 New

## UG10-CH27-D227

PDF page: 392; original JSON pointer: `/4712`

2. 在 Select Reaction Type 对话框 从 Choose Reaction Type 窗口选择 Salt Precipitating

## UG10-CH27-D228

PDF page: 392; original JSON pointer: `/4713`

3. 从 Precipitatying Salt 的列表中选择盐的组分名称 并且单击 OK

## UG10-CH27-D229

PDF page: 392; original JSON pointer: `/4714`

4. 在 Edit Salt 对话框 输入盐电离反应产品的组分和化学计量系数

## UG10-CH27-D230

PDF page: 392; original JSON pointer: `/4715`

5. 完成时单击 Close 你应该能看见新的反应显示在 Stoichiometry 页上且有盐的组分 名

## UG10-CH27-D231

PDF page: 392; original JSON pointer: `/4716`

6. 对于每个附加的盐沉降反应重复步骤 1 到 5

## UG10-CH27-D232

PDF page: 392; original JSON pointer: `/4717`

7. 单击 Salt 页

## UG10-CH27-D233

PDF page: 392; original JSON pointer: `/4718`

8. 在 Salt 页 从 Salt 列表中选择一个盐

## UG10-CH27-D234

PDF page: 392; original JSON pointer: `/4719`

9. 如果反应没有达到平衡 你可规定反应的平衡接近温度 Temperate Approach to Equilibrium 你输入温度数将被加到反应段的温度上以计算平衡常数

## UG10-CH27-D235

PDF page: 392; original JSON pointer: `/4720`

10. 选择你是否想要从 Gibbs能计算 Keq或者从一个内置的多项式的选择适宜的按钮来 计算平衡常数 溶解性产品

## UG10-CH27-D236

PDF page: 392; original JSON pointer: `/4721`

11. 如果你选择从 Gibbs 能计算 Keq 你不需要输入平衡常数的系数 ASPEN PLUS 将 从组分的参考状态的 Gibbs 自由能计算 Keq

## UG10-CH27-D237

PDF page: 392; original JSON pointer: `/4722`

12. 如果你选择从一个内置的多项式来计算 Keq 输入一个内置的平衡常数表达式的系 数 并且在 Keq Basis 区域选择平衡常数的浓度基准

## UG10-CH27-D238

PDF page: 393; original JSON pointer: `/4724`

第 27 章 规定反应和化学

## UG10-CH27-D239

PDF page: 393; original JSON pointer: `/4725`

表达式和平衡常数的定义与流项平衡反应的定义相同 更多的内容见本章的平衡反应部

## UG10-CH27-D240

PDF page: 393; original JSON pointer: `/4726`

如果没有流率控制的或部分转化流相出现 那么建议你规定盐沉降反应为电解质化学反 应 电解质化学反应优点如下

## UG10-CH27-D241

PDF page: 393; original JSON pointer: `/4727`

l 可以自动有电解质智能系统生成

## UG10-CH27-D242

PDF page: 393; original JSON pointer: `/4728`

见本章的规定电解质化学部分

## UG10-CH27-D243

PDF page: 393; original JSON pointer: `/4729`

使用用户提供的动力学子程序计算反应速度 你需要规定 Fortran 子程序名称 使用

## UG10-CH27-D244

PDF page: 393; original JSON pointer: `/4730`

Reaction User 表规定用户定义的动力学 用于

## UG10-CH27-D245

PDF page: 393; original JSON pointer: `/4731`

对于 RadFrac 和 RateFrac,你也可以使用 Reactions Reacp -Dist 表来规定用户定义的动力

## UG10-CH27-D246

PDF page: 393; original JSON pointer: `/4732`

学 见本章关于规定反应蒸馏的反应部分 你可以定义平衡反应与流率控制的反应同时求

## UG10-CH27-D247

PDF page: 393; original JSON pointer: `/4733`

解 只有 RCSTR,RadFrac 和 RateFrac 可以处理平衡反应

## UG10-CH27-D248

PDF page: 393; original JSON pointer: `/4734`

规定一个用户的 Fortran 子程序计算反应速度采取如下步骤

## UG10-CH27-D249

PDF page: 393; original JSON pointer: `/4735`

1. 从 Data 菜单 指向 Reactions ,然后选 Reactions

## UG10-CH27-D250

PDF page: 393; original JSON pointer: `/4736`

2. 在 Reaction Object Manager 中 单击 New,创建一个新的反应 ID

## UG10-CH27-D251

PDF page: 393; original JSON pointer: `/4737`

3. 在 Create New ID 对话框 在 Enter ID 区域中输入一个反应名称 或者接受一个缺 省的 ID

## UG10-CH27-D252

PDF page: 393; original JSON pointer: `/4738`

4. 在 Select Type 列表中 选择 User 单击 OK

## UG10-CH27-D253

PDF page: 393; original JSON pointer: `/4739`

5. 在 Reactions Stoichiometry 页上 单击 New

## UG10-CH27-D254

PDF page: 393; original JSON pointer: `/4740`

6. 在 Edit Reaction 对话框 缺省的反应类型为 Kinetic 并且反应标号自动输入 输入 组分和化学计量系数以定义反应 系数对于反应物为负数 对于生成物为正数

## UG10-CH27-D255

PDF page: 393; original JSON pointer: `/4741`

7. 当完成时单击 Close 你应该看见新的反应显示在 Stoichiometry 页上

## UG10-CH27-D256

PDF page: 393; original JSON pointer: `/4742`

8. 对于每个附加的用户动力学反应重复步骤 7 到 9

## UG10-CH27-D257

PDF page: 393; original JSON pointer: `/4743`

9. 选择 Kinetic 页

## UG10-CH27-D258

PDF page: 393; original JSON pointer: `/4744`

10. 在 Kinetic 页 从列表中选择一个反应 并且使用 Reacting Phase 列表规定反应发 生的相态 缺省的相态是液相

## UG10-CH27-D259

PDF page: 393; original JSON pointer: `/4745`

11. 如果有固体存在 单击 Solids 按钮 并且选择计算浓度的适宜选项 见本章关于带 有固体的反应

## UG10-CH27-D260

PDF page: 393; original JSON pointer: `/4746`

12. 选择 Subroutine 页

## UG10-CH27-D261

PDF page: 393; original JSON pointer: `/4747`

13. 在 Subroutine 页 在 Name 区域输入用户子程序的名称 更多的内容请见 ASPEN PLUS 用户模型 中的使用和编写用户动力学模型 对于在一个用户类型的反应 ID 中的任何平衡反应 可以按你的意愿 规定它们为在一 个幂率反应 ID 中的平衡反应 详细的内容见本章关于规定反应器和泄压系统的幂率反应部 分

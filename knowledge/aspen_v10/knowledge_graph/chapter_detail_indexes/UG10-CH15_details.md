# UG10-CH15 Detail Operation Index - 第15章 管理文件

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH15-D001

PDF page: 218; original JSON pointer: `/2538`

这一章描述了当你运行ASPEN PLUS时怎样管理你所创建的文件 其中包括

## UG10-CH15-D002

PDF page: 218; original JSON pointer: `/2539`

l ASPEN PLUS 文档文件存储

## UG10-CH15-D003

PDF page: 218; original JSON pointer: `/2540`

l ASPEN PLUS 文件转出

## UG10-CH15-D004

PDF page: 218; original JSON pointer: `/2541`

l ASPEN PLUS 运行期间所使用的文件格式

## UG10-CH15-D005

PDF page: 218; original JSON pointer: `/2542`

l ASPEN PLUS 文件转入

## UG10-CH15-D006

PDF page: 218; original JSON pointer: `/2543`

l ASPEN PLUS 运行的存储

## UG10-CH15-D007

PDF page: 218; original JSON pointer: `/2544`

l 在客户/服务器环境下管理文件

## UG10-CH15-D008

PDF page: 218; original JSON pointer: `/2545`

ASPEN PLUS 的文件格式

## UG10-CH15-D009

PDF page: 218; original JSON pointer: `/2546`

ASPEN PLUS中使用如下几种主要的文件类型

## UG10-CH15-D010

PDF page: 218; original JSON pointer: `/2547`

文件类型 扩展名 格式 * 描述

## UG10-CH15-D011

PDF page: 218; original JSON pointer: `/2548`

文档 *.apw 二进制 快速重启动包含模拟输入

## UG10-CH15-D012

PDF page: 218; original JSON pointer: `/2549`

备份 *.bkp ASCII 存档包含模拟输入和结果

## UG10-CH15-D013

PDF page: 218; original JSON pointer: `/2550`

模板 *.apt ASCII 包含缺省输入的模板

## UG10-CH15-D014

PDF page: 218; original JSON pointer: `/2551`

输入 *.inp 文本 模拟程序输入

## UG10-CH15-D015

PDF page: 218; original JSON pointer: `/2552`

运行信息 *.cpn 文本 控制面板中显示的计算历

## UG10-CH15-D016

PDF page: 218; original JSON pointer: `/2553`

汇总 *.sum ASCII 模拟结果

## UG10-CH15-D017

PDF page: 218; original JSON pointer: `/2554`

问题定义 *.appdf 二进制 二进制文件 包含模拟计算

## UG10-CH15-D018

PDF page: 218; original JSON pointer: `/2555`

报告 *.rep 文本 模拟报告

## UG10-CH15-D019

PDF page: 218; original JSON pointer: `/2556`

* 这一列中 文本 文件是指可由标准编辑器如 Notepad打开的文件 用户不能打开二进制文

## UG10-CH15-D020

PDF page: 218; original JSON pointer: `/2557`

件 ASCII文件可用编辑器打开 但它的格式只能由程序打开 ASCII文件可在不同的硬件平台

## UG10-CH15-D021

PDF page: 218; original JSON pointer: `/2558`

文档文件 (*.apw)

## UG10-CH15-D022

PDF page: 218; original JSON pointer: `/2559`

ASPEN PLUS 文档文件包含所有输入规定 模拟结果和中间收敛信息 在退出

## UG10-CH15-D023

PDF page: 218; original JSON pointer: `/2560`

ASPEN PLUS之前 如果你以文档文件格式保存一个运行过程 下次你打开它时 它的

## UG10-CH15-D024

PDF page: 218; original JSON pointer: `/2561`

状态与你保存时的运行状态完全相同 如果你重新打开一个存储为文档格式的文件

## UG10-CH15-D025

PDF page: 218; original JSON pointer: `/2562`

ASPEN PLUS使用先前的结果重新启动计算

## UG10-CH15-D026

PDF page: 218; original JSON pointer: `/2563`

文档文件可在ASPEN PLUS 用户界面中打开和保存

## UG10-CH15-D027

PDF page: 218; original JSON pointer: `/2564`

文档文件 .apw 在ASPEN PLUS的不同版本之间不能互相兼容

## UG10-CH15-D028

PDF page: 219; original JSON pointer: `/2566`

对于较长的文件 文档文件可以非常快速地从ASPEN PLUS用户界面装载和保存

## UG10-CH15-D029

PDF page: 219; original JSON pointer: `/2567`

由于文档文件包含中间收敛信息 所以可在运行过程保存的地方准确地启动它 在

## UG10-CH15-D030

PDF page: 219; original JSON pointer: `/2568`

收敛一个大的流程中保存文件时 中间结果特别有用

## UG10-CH15-D031

PDF page: 219; original JSON pointer: `/2569`

备份文件 (*.bkp)

## UG10-CH15-D032

PDF page: 219; original JSON pointer: `/2570`

ASPEN PLUS 备份文件是ASPEN PLUS运行过程的一个压缩版本 它们占用的磁

## UG10-CH15-D033

PDF page: 219; original JSON pointer: `/2571`

盘空间要大大少于文档格式保存的文件 因此适用于长文件的保存

## UG10-CH15-D034

PDF page: 219; original JSON pointer: `/2572`

备份文件包含所有输入规定和模拟结果 但没有中间收敛信息 如果你重新打开一

## UG10-CH15-D035

PDF page: 219; original JSON pointer: `/2573`

个已收敛的 且按备份格式保存的运行文件 那么ASPEN PLUS重新运行模拟程序时需

## UG10-CH15-D036

PDF page: 219; original JSON pointer: `/2574`

备份文件是ASCII码文件 你可以互相传递运行过程 在下述之间

## UG10-CH15-D037

PDF page: 219; original JSON pointer: `/2575`

备份 .bkp 文件优于文档 .apw 文件的是 备份文件在不同版本的ASPEN PLUS

## UG10-CH15-D038

PDF page: 219; original JSON pointer: `/2576`

间是向上兼容的 并且文件较小 例如 它们适宜电子邮件传送

## UG10-CH15-D039

PDF page: 219; original JSON pointer: `/2577`

备份文件可在ASPEN PLUS中被打开和保存 它们也可被转入到当前运行中 并且

## UG10-CH15-D040

PDF page: 219; original JSON pointer: `/2578`

部分或全部流程可被转出 更详细的信息参见本章的转出ASPEN PLUS文件部分

## UG10-CH15-D041

PDF page: 219; original JSON pointer: `/2579`

你可将以备份格式保存的进程文件转入到当前运行中 ASPEN PLUS将备份文件中

## UG10-CH15-D042

PDF page: 219; original JSON pointer: `/2580`

所包含的信息和规定与当前运行相合并

## UG10-CH15-D043

PDF page: 219; original JSON pointer: `/2581`

例如 将一个流程分成两部分 保存为两个独立的备份文件 你可将这两个备份文

## UG10-CH15-D044

PDF page: 219; original JSON pointer: `/2582`

件转入到一个单独运行中 将流程的两部分合并在一起

## UG10-CH15-D045

PDF page: 219; original JSON pointer: `/2583`

关于插入过程的信息 你可在任何时间里转入部分备份文件 参见第三十四章

## UG10-CH15-D046

PDF page: 219; original JSON pointer: `/2584`

当转入备份文件时 你可以控制ASPEN PLUS版本之间的兼容

## UG10-CH15-D047

PDF page: 219; original JSON pointer: `/2585`

当你打开一个由ASPEN PLUS 模拟引擎或先前版本的 ASPEN PLUS 创建的备份文

## UG10-CH15-D048

PDF page: 219; original JSON pointer: `/2586`

件时 出现向上兼容对话框

## UG10-CH15-D049

PDF page: 219; original JSON pointer: `/2587`

ASPEN PLUS 10 版的新特性可能意味着你的结果不同于先前版本的结果 为了保

## UG10-CH15-D050

PDF page: 219; original JSON pointer: `/2588`

持向上兼容 并且使结果与先前版本ASPEN PLUS 的相同 可以忽略ASPEN PLUS 10

## UG10-CH15-D051

PDF page: 219; original JSON pointer: `/2589`

Ø 在向上兼容对话框中 选择保持完全向上兼容

## UG10-CH15-D052

PDF page: 219; original JSON pointer: `/2590`

Ø 在向上兼容对话框中 选择选择使用以下新特性选项 并且从中选择你所需要

## UG10-CH15-D053

PDF page: 219; original JSON pointer: `/2591`

如果你打开一个由ASPEN PLUS 9 版用户界面创建的文件,那么你只能选择新的纯 组分数据库 PURE10 选项

## UG10-CH15-D054

PDF page: 220; original JSON pointer: `/2593`

当创建一个新的运行时 你可以选择一个模板 模板设置以下的部分或全部缺省值

## UG10-CH15-D055

PDF page: 220; original JSON pointer: `/2594`

l 报告物流物性的物性集

## UG10-CH15-D056

PDF page: 220; original JSON pointer: `/2595`

l 输入规定的全流程基准

## UG10-CH15-D057

PDF page: 220; original JSON pointer: `/2596`

关于内置模板和创建模板的详细信息 参见第二章

## UG10-CH15-D058

PDF page: 220; original JSON pointer: `/2597`

ASPEN PLUS 输入文件是一个流程模拟规定的压缩汇总 一个输入文件可以包括

## UG10-CH15-D059

PDF page: 220; original JSON pointer: `/2598`

流程图窗口中单元操作模块和物流布局的图形信息

## UG10-CH15-D060

PDF page: 220; original JSON pointer: `/2599`

l 作为一个单独 ASPEN PLUS 引擎运行输入文件使用

## UG10-CH15-D061

PDF page: 220; original JSON pointer: `/2600`

l 提供一个模拟输入规定的压缩汇总 例如 包括在报告中

## UG10-CH15-D062

PDF page: 220; original JSON pointer: `/2601`

l 帮助专家级用户诊断错误

## UG10-CH15-D063

PDF page: 220; original JSON pointer: `/2602`

你可在任何时候从模拟规定中生成一个 ASPEN PLUS 输入文件 为了保存一个输

## UG10-CH15-D064

PDF page: 220; original JSON pointer: `/2603`

入文件 你必须从 ASPEN PLUS 用户界面中将它转出

## UG10-CH15-D065

PDF page: 220; original JSON pointer: `/2604`

输入文件可由模拟引擎直接运行 关于怎样使用模拟引擎运行输入文件 更详细的

## UG10-CH15-D066

PDF page: 220; original JSON pointer: `/2605`

转入备份文件参见第十五章中转入 ASPEN PLUS 文件的描述

## UG10-CH15-D067

PDF page: 220; original JSON pointer: `/2606`

报告文件 (*.rep)

## UG10-CH15-D068

PDF page: 220; original JSON pointer: `/2607`

ASPEN PLUS 报告文件保存所有输入数据和 ASPEN PLUS 运行中使用的缺省值

## UG10-CH15-D069

PDF page: 220; original JSON pointer: `/2608`

包括模拟结果 这些文本文件可被用户读出

## UG10-CH15-D070

PDF page: 220; original JSON pointer: `/2609`

报告文件必须从模拟中转出并保存 报告文件不能在 ASPEN PLUS 用户界面中打

## UG10-CH15-D071

PDF page: 220; original JSON pointer: `/2610`

如果可能的话 DFMS 输入文件 *.dfm 物性数据文件(*.prd)和项目文件(*.prj) 可以同报告文件一起被转出 汇总文件 (*.sum) ASPEN PLUS 汇总文件包含所有 ASPEN PLUS 用户界面中显示的模拟结果 汇总 文件是 ASCII 格式的文件 用于将结果装载到用户界面中 汇总文件也可被其它程序 使用来检索模拟结果 汇总文件必须从模拟程序中转出并保存 更详细的信息 参见第十五章中的转出 ASPEN PLUS 文件 当单独运行 ASPEN PLUS 模拟引擎时 汇总文件可自动被生成

## UG10-CH15-D072

PDF page: 220; original JSON pointer: `/2611`

生成的文件名是 runid.sum

## UG10-CH15-D073

PDF page: 220; original JSON pointer: `/2612`

汇总文件中包括的结果可被转入到 ASPEN PLUS 用户界面中 更详细的信息可参

## UG10-CH15-D074

PDF page: 220; original JSON pointer: `/2613`

见第十五章中的转入 ASPEN PLUS 文件

## UG10-CH15-D075

PDF page: 221; original JSON pointer: `/2615`

运行信息文件 (*.cpm)

## UG10-CH15-D076

PDF page: 221; original JSON pointer: `/2616`

ASPEN PLUS 运行信息文件是文本文件 它包括运行中的错误 警告和诊断信息

## UG10-CH15-D077

PDF page: 221; original JSON pointer: `/2617`

这些信息在运行期间被显示在控制面板上 信息的个数和详细内容可由 Setup

## UG10-CH15-D078

PDF page: 221; original JSON pointer: `/2618`

Specification Diagnostics( 设置规定诊断 ) 页全局控制 你也可用 BlockOptions

## UG10-CH15-D079

PDF page: 221; original JSON pointer: `/2619`

运行信息文件与历史文件很相似 历史文件和控制面板上的诊断级别可被分别调

## UG10-CH15-D080

PDF page: 221; original JSON pointer: `/2620`

整 如果你需要一个高级别的诊断 那么将它输出到历史文件中 而不是控制面板上 这可以防止由于在屏幕上显示冗长的诊断信息而造成的性能下降 运行信息文件必须由模拟程序中转出并被保存 历史文件 (*.his) 历史文件是文本文件 它包括输入总的反馈 运行中的错误 警告和诊断信息 信 息的个数和详细内容可由 Setup Specifications Diagnostics 设置规定诊断 页全局控制 你也可用模块选项诊断页来局部地控制每一模块的信息

## UG10-CH15-D081

PDF page: 221; original JSON pointer: `/2621`

当从视图 View 菜单中选择历史选项后 ASPEN PLUS 历史文件由主机拷贝到

## UG10-CH15-D082

PDF page: 221; original JSON pointer: `/2622`

你本地的计算机 ASPEN PLUS 运行你本地的文件编辑器来浏览历史文件

## UG10-CH15-D083

PDF page: 221; original JSON pointer: `/2623`

历史文件不能在 ASPEN PLUS 用户界面中被保存或转出 使用视图 View 菜单

## UG10-CH15-D084

PDF page: 221; original JSON pointer: `/2624`

中的 History(历史)选项保存 当你将一个运行保存为文档文件时 ASPEN PLUS 自动保

## UG10-CH15-D085

PDF page: 221; original JSON pointer: `/2625`

历史文件与运行文件相似 它和控制面板上的诊断级别可被分别调整 如果你需要

## UG10-CH15-D086

PDF page: 221; original JSON pointer: `/2626`

一个高级别的诊断 那么将它输出到历史文件中 而不是控制面板上 这可以防止由

## UG10-CH15-D087

PDF page: 221; original JSON pointer: `/2627`

于在屏幕上显示冗长的诊断信息而造成的性能下降

## UG10-CH15-D088

PDF page: 221; original JSON pointer: `/2628`

打开 ASPEN PLUS文件

## UG10-CH15-D089

PDF page: 221; original JSON pointer: `/2629`

你可以从 ASPEN PLUS 中打开一个已存在的 ASPEN PLUS 文件

## UG10-CH15-D090

PDF page: 221; original JSON pointer: `/2630`

1. 从 File 文件 菜单中 单击 Open 打开

## UG10-CH15-D091

PDF page: 221; original JSON pointer: `/2631`

2. 在 Open 打开 对话框中 从文件类型列表中选择文件类型

## UG10-CH15-D092

PDF page: 221; original JSON pointer: `/2632`

3. 输入文件名称或从所列出的文件中选择一个文件 然后单击 Open 打开 按 钮

## UG10-CH15-D093

PDF page: 221; original JSON pointer: `/2633`

4. 显示信息 在打开新的文件之前你希望关闭当前的运行吗 单击 No 在另一窗口打开一个新的模拟程序 单击 Yes 关闭当前运行 提示 为加速检索文件和目录的速度 在 Open 打开 对话框中 单击 Look i Favorites 查找常用目录 按钮 显示预选目录的列表 使用 Add to Favorites 添加常用目录 按钮 将最常用的目录添加到列表中 使用常用目录列表 缺省情况 常用目录列表中包括 5 个 ASPEN PLUS 提供的目录 这些目录中的文

## UG10-CH15-D094

PDF page: 221; original JSON pointer: `/2634`

件可帮助你创建一个合适的 ASPEN PLUS 模拟模型

## UG10-CH15-D095

PDF page: 221; original JSON pointer: `/2635`

分析库 原油分析数据取自世界各地区的文献 选定的原油分析取

## UG10-CH15-D096

PDF page: 222; original JSON pointer: `/2637`

电解质插入 许多重要工业系统的电解质数据包

## UG10-CH15-D097

PDF page: 222; original JSON pointer: `/2638`

要在 ASPEN PLUS 中保存一个文件

## UG10-CH15-D098

PDF page: 222; original JSON pointer: `/2639`

1. 从 File 文件 菜单中 单击 Save As 另存为

## UG10-CH15-D099

PDF page: 222; original JSON pointer: `/2640`

2. 在 Save As 另存为 对话框中 从另存文件列表中选择正确的文件类型

## UG10-CH15-D100

PDF page: 222; original JSON pointer: `/2641`

3. 输入文件名 这个文件可被保存在任意目录中

## UG10-CH15-D101

PDF page: 222; original JSON pointer: `/2642`

4. 单击 Save 保存 按钮 你可将文件保存为如下这些类型 文件类型 扩展名 描述 文档 *.apw 快速重新启动包含模拟输入 结果和中间即收 敛信息的文件 备份 *.bkp 存档包含模拟输入和结果的文件 模板 *.apt 包含缺省输入的模板 转出 ASPEN PLUS文件 要生成和转出一个 ASPEN PLUS 文件

## UG10-CH15-D102

PDF page: 222; original JSON pointer: `/2643`

1. 从 File 文件 菜单中 单击 Export 转出

## UG10-CH15-D103

PDF page: 222; original JSON pointer: `/2644`

2. 在 Export 转出 对话框中 从另存文件列表中选择正确的文件类型

## UG10-CH15-D104

PDF page: 222; original JSON pointer: `/2645`

4. 单击 Save 保存 按钮 你可转出如下类型的 ASPEN PLUS 文件 文件类型 扩展名 格式 描述 备份 .bkp ASCII 存档包含模拟输入和结果的文件 报告 .rep 文本 报告文件 汇总 .sum ASCII 模拟结果 输入 .inp 文本 无图形的模拟输入信息 带有图形的输 入文件 .inp 文本 模拟输入和图形信息 运行信息 .cpn 文本 计算历史信息 动态模拟流程 驱动 .spf . inp 文本 ASPEN 动态输入和 ASPEN PLUS输 入 动态模拟压力 驱动 .spe .i np

## UG10-CH15-D105

PDF page: 222; original JSON pointer: `/2646`

文本 ASPEN 动态输入和 ASPEN PLUS 输

## UG10-CH15-D106

PDF page: 223; original JSON pointer: `/2648`

转入 ASPEN PLUS文件

## UG10-CH15-D107

PDF page: 223; original JSON pointer: `/2649`

要转入一个 ASPEN PLUS 文件

## UG10-CH15-D108

PDF page: 223; original JSON pointer: `/2650`

1. 从 File 文件 菜单中 单击 Import 转入

## UG10-CH15-D109

PDF page: 223; original JSON pointer: `/2651`

2. 在 Improt 转入 对话框中 从另存文件列表中选择正确的文件类型

## UG10-CH15-D110

PDF page: 223; original JSON pointer: `/2652`

3. 输入文件名 这个文件可被保存在任意目录中

## UG10-CH15-D111

PDF page: 223; original JSON pointer: `/2653`

4. 单击 Open 打开 按钮

## UG10-CH15-D112

PDF page: 223; original JSON pointer: `/2654`

5. 如果 Resolve ID Conflicts 冲突标识符 对话框出现 说明有一个与当前运行 相同的目标标识存在 关于使用标识符冲突对话框的信息 参见第三十八章 提示 为加快检索文件和目录的速度 在 Open 打开 对话框中 单击 Look i Favorites 查找常用目录 按钮 显示预选择目录的列表 使用 Add to Favorites 添加常用目录 按钮 将最常用的目录添加到列表中 你可转入如下类型的文件 文件类型 扩展名 格式 描述

## UG10-CH15-D113

PDF page: 223; original JSON pointer: `/2655`

备份 *.bkp ASCII 存档文件包含模拟输入和结果

## UG10-CH15-D114

PDF page: 223; original JSON pointer: `/2656`

模板 *.apt ASCII 作为模板使用的ASCII文件

## UG10-CH15-D115

PDF page: 223; original JSON pointer: `/2657`

IK-Cape .ikc ASCII IK-Cape中间文件的物性信息

## UG10-CH15-D116

PDF page: 223; original JSON pointer: `/2658`

汇总 *.sum ASCII 模拟结果

## UG10-CH15-D117

PDF page: 223; original JSON pointer: `/2659`

你可以使用如下三种方法保存 ASPEN PLUS 模拟程序

## UG10-CH15-D118

PDF page: 223; original JSON pointer: `/2660`

l 保存为 ASPEN PLUS 文档文件

## UG10-CH15-D119

PDF page: 223; original JSON pointer: `/2661`

l 保存为 ASPEN PLUS 备份文件

## UG10-CH15-D120

PDF page: 223; original JSON pointer: `/2662`

l 作为输入文件格式转出

## UG10-CH15-D121

PDF page: 223; original JSON pointer: `/2663`

下表汇总了用于保存模拟问题的文件格式的特性

## UG10-CH15-D122

PDF page: 223; original JSON pointer: `/2664`

在客户 /服务器环境下管理文件

## UG10-CH15-D123

PDF page: 223; original JSON pointer: `/2665`

你可运行 ASPEN PLUS 用户界面和模拟引擎

## UG10-CH15-D124

PDF page: 223; original JSON pointer: `/2666`

一些文件的管理要点 这在下述各节中描述

## UG10-CH15-D125

PDF page: 223; original JSON pointer: `/2667`

本地计算机是正在运行 ASPEN PLUS 用户界面的计算机 主机是运行 ASPEN

## UG10-CH15-D126

PDF page: 224; original JSON pointer: `/2669`

如果你还没有指定工作目录 由 ASPEN PLUS 模拟引擎创建的文件被保存在主机 的缺省登录目录中 要指定模拟引擎执行的工作目录 如下

## UG10-CH15-D127

PDF page: 224; original JSON pointer: `/2670`

Ø 在运行 Run 菜单中 单击连接到引擎 Connect to Engine

## UG10-CH15-D128

PDF page: 224; original JSON pointer: `/2671`

当你从文件菜单中使用 Save 保存 或 Save As 另存为 菜单项将一个运行保存

## UG10-CH15-D129

PDF page: 224; original JSON pointer: `/2672`

为 ASPEN PLUS 文档 .apw 文件时 ASPEN PLUS 在如下位置处创建这些文件

## UG10-CH15-D130

PDF page: 224; original JSON pointer: `/2673`

runid.apw 你运行用户界面的本地目录或 Save As 另存为 对话框指

## UG10-CH15-D131

PDF page: 224; original JSON pointer: `/2674`

runid.his 在 Connect to Engine 连接到引擎 对话框中指定的主机上

## UG10-CH15-D132

PDF page: 224; original JSON pointer: `/2675`

runid.appdf 在 Connect to Engine 连接到引擎 对话框中指定的主机上

## UG10-CH15-D133

PDF page: 224; original JSON pointer: `/2676`

要从主机将 ASPEN PLUS 历史文件拷贝到你的本地计算机上

## UG10-CH15-D134

PDF page: 224; original JSON pointer: `/2677`

Ø 在 View 浏览 菜单中 单击 History 历史 菜单项

## UG10-CH15-D135

PDF page: 224; original JSON pointer: `/2678`

ASPEN PLUS 执行你的文件编辑器来浏览历史文件

## UG10-CH15-D136

PDF page: 224; original JSON pointer: `/2679`

如果文件较大 将它拷贝到你本地的计算机将需要很长的时间 在这种情况下 你 应当登录到主机上浏览文件 指定文本编辑器 要指定文本编辑器

## UG10-CH15-D137

PDF page: 224; original JSON pointer: `/2680`

1. 在 Tools 工具 菜单中 单击 Options 选项

## UG10-CH15-D138

PDF page: 224; original JSON pointer: `/2681`

2. 单击 Startup 启动 标签

## UG10-CH15-D139

PDF page: 224; original JSON pointer: `/2682`

3. 在 Text Editor 文本编辑器 框中 输入编辑器名称

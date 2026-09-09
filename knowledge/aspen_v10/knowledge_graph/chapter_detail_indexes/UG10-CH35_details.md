# UG10-CH35 Detail Operation Index - 第35章 创建物流库

原记录逐项保留；源教材页面不随包。数值属于原手册版本，不是项目默认值。

## UG10-CH35-D001

PDF page: 505; original JSON pointer: `/6062`

第 35 章 创建物流库

## UG10-CH35-D002

PDF page: 505; original JSON pointer: `/6063`

本章阐述如何创建物流库 关于如何检索在模拟中用到的物流库信息 参见第九章

## UG10-CH35-D003

PDF page: 505; original JSON pointer: `/6064`

你能从物流库中检索关于物流组分和条件的信息 而不用从物流表中输入数据

## UG10-CH35-D004

PDF page: 505; original JSON pointer: `/6065`

下表显示使用物流库能做到的功能

## UG10-CH35-D005

PDF page: 505; original JSON pointer: `/6066`

将经常使用的进料物流组成和状态存储在物流数据库中 从一

## UG10-CH35-D006

PDF page: 505; original JSON pointer: `/6067`

个模拟的不同模型中检索该信息 而不用重新输入

## UG10-CH35-D007

PDF page: 505; original JSON pointer: `/6068`

模拟一段流程 把出口物流存储在一个库中 在另一个模拟过

## UG10-CH35-D008

PDF page: 505; original JSON pointer: `/6069`

初始化撕裂流 把一个模拟过程的最终撕裂流的值存储在库中

## UG10-CH35-D009

PDF page: 505; original JSON pointer: `/6070`

果你不知道选哪一个作为撕裂流 从第一个模拟过程存储所有

## UG10-CH35-D010

PDF page: 505; original JSON pointer: `/6071`

物流 在新运行时检索所有物流

## UG10-CH35-D011

PDF page: 505; original JSON pointer: `/6072`

把一个大流程的物流存储在一个库中

## UG10-CH35-D012

PDF page: 505; original JSON pointer: `/6073`

从已存储的流程中检索分析一个模块 并单独模拟它 也可用

## UG10-CH35-D013

PDF page: 505; original JSON pointer: `/6074`

更高级诊断或改变条件 对于一个隔离模块可以省去重新输入

## UG10-CH35-D014

PDF page: 505; original JSON pointer: `/6075`

l 使用已创建的物流库并通过你的 ASPEN PLUS 系统管理器维护

## UG10-CH35-D015

PDF page: 505; original JSON pointer: `/6076`

为了创建或修改一个物流库 可以使用 STRLIB 它是与 ASPEN PLUS 程序一同提供

## UG10-CH35-D016

PDF page: 505; original JSON pointer: `/6077`

的 每次 ASPEN PLUS 运行创建一个汇总文件 该文件包括模拟的全部结果 STRLIB 从

## UG10-CH35-D017

PDF page: 505; original JSON pointer: `/6078`

ASPEN PLUS 的汇总文件中将物流结果拷贝到物流库中 可以把 ASPEN PLUS 任何次运行

## UG10-CH35-D018

PDF page: 505; original JSON pointer: `/6079`

每一个工况通常和 ASPEN PLUS 一次运行相对应 然而 你可以将 ASPEN PLUS 的

## UG10-CH35-D019

PDF page: 505; original JSON pointer: `/6080`

多次运行中的物流存储到一个工况中 你也可以将一次运行数据存储在多个工况中

## UG10-CH35-D020

PDF page: 505; original JSON pointer: `/6081`

使用 STRLIB 命令创建或修改一个物流库 STRLIB 涉及到的最常用的步骤如下

## UG10-CH35-D021

PDF page: 505; original JSON pointer: `/6082`

1. 用 OPEN 命令打开一个汇总文件

## UG10-CH35-D022

PDF page: 505; original JSON pointer: `/6083`

2. 用 OPEN 或 CASE 命令建立你想要拷贝物流的工况

## UG10-CH35-D023

PDF page: 505; original JSON pointer: `/6084`

3. 用 ADD 或 REPLACE 命令在库中添加或取代物流 交互运行 STRLIB 交互运行 STRLIB 在操作系统提示下输入该命令 strlib libname 库名

## UG10-CH35-D024

PDF page: 506; original JSON pointer: `/6086`

第 35 章 创建物流库

## UG10-CH35-D025

PDF page: 506; original JSON pointer: `/6087`

LIBNAME 是你想要创建或修改的物流库 物流库名最长八个字符

## UG10-CH35-D026

PDF page: 506; original JSON pointer: `/6088`

库文件扩展名 *.slb.

## UG10-CH35-D027

PDF page: 506; original JSON pointer: `/6089`

当有 STRLIB> 提示出现时 可以输入命令

## UG10-CH35-D028

PDF page: 506; original JSON pointer: `/6090`

用批处理方式运行 STRLIB

## UG10-CH35-D029

PDF page: 506; original JSON pointer: `/6091`

可以非交互运行 STRLIB 以 创建或更新一个 物流 数据库 在批处理方式下运行

## UG10-CH35-D030

PDF page: 506; original JSON pointer: `/6092`

STRLIB 将自动加入 ASPEN PLUS 运行所产生的汇总文件中的所有物流

## UG10-CH35-D031

PDF page: 506; original JSON pointer: `/6093`

如果在批处理方式下运行 STRLIB 在系统操作提示符下输入该命令 STRLIB libname(库名) runid(运行标识号) [case](工况) Libname(库名) 是你想要创建或修改的库名 如果该库不存在 它将按照包含 10个工 况进行创建和初始化 runid(运行标识号) 是 ASPEN PLUS 汇总文件名 可以从那里传递物流 case 是你想要添加物流的工况名 如果你没规定工况名 STRLIB 用从汇总文件得到

## UG10-CH35-D032

PDF page: 506; original JSON pointer: `/6094`

当交互运行 STRLIB 时 交互方式的 STRLIB 命令等同于下述的命令顺序

## UG10-CH35-D033

PDF page: 506; original JSON pointer: `/6095`

STRLIB> OPEN runid [ case]

## UG10-CH35-D034

PDF page: 506; original JSON pointer: `/6096`

你能缩写任何 STRLIB 命令 在 STRLIB> 提示符下输入的所有命令 只要打出字母

## UG10-CH35-D035

PDF page: 506; original JSON pointer: `/6097`

DELCASE 从库中删除一个工况

## UG10-CH35-D036

PDF page: 506; original JSON pointer: `/6098`

DELSTREAM 从库中删除一个物流

## UG10-CH35-D037

PDF page: 506; original JSON pointer: `/6099`

DUMP 将物流信息写入一个文件

## UG10-CH35-D038

PDF page: 506; original JSON pointer: `/6100`

HELP 在 STRLIB 命令中显示交互运行的帮助

## UG10-CH35-D039

PDF page: 506; original JSON pointer: `/6101`

LIST 列出汇总文件中的物流

## UG10-CH35-D040

PDF page: 506; original JSON pointer: `/6102`

LOAD 从存放的文件中加载物流信息

## UG10-CH35-D041

PDF page: 506; original JSON pointer: `/6103`

OPEN 打开一个汇总文件

## UG10-CH35-D042

PDF page: 506; original JSON pointer: `/6104`

RENAME 在库中更改一个物流名

## UG10-CH35-D043

PDF page: 506; original JSON pointer: `/6105`

QUIT 停止更新数据库退出 STRLIB

## UG10-CH35-D044

PDF page: 507; original JSON pointer: `/6107`

第 35 章 创建物流库

## UG10-CH35-D045

PDF page: 507; original JSON pointer: `/6108`

ADD 命令把来自 ASPEN PLUS 汇总文件的一个物流拷贝到库中 被拷贝的物流在当

## UG10-CH35-D046

PDF page: 507; original JSON pointer: `/6109`

前工况的库中不能存在 用 REPLACE 命令取代一个已经存在的物流

## UG10-CH35-D047

PDF page: 507; original JSON pointer: `/6110`

定义 ADD ALL 把所有物流从汇总文件拷贝到库中

## UG10-CH35-D048

PDF page: 507; original JSON pointer: `/6111`

CASE 命令改变现有工况 物流库中的物流被组织到工况中 当你打开一个汇总文件时

## UG10-CH35-D049

PDF page: 507; original JSON pointer: `/6112`

用 OPEN 命令 或使用 CASE 命令时 你可以建立一个工况 关于工况的详细内容 参

## UG10-CH35-D050

PDF page: 507; original JSON pointer: `/6113`

见本章,创建或修改物流库

## UG10-CH35-D051

PDF page: 507; original JSON pointer: `/6114`

ADD DELSTREAM DUMP RENAME 和 REPLACE 命令适用于当前工况的物流

## UG10-CH35-D052

PDF page: 507; original JSON pointer: `/6115`

DELCASE 命令用于从库中删除一个工况 在工况中的所有物流都被删除

## UG10-CH35-D053

PDF page: 507; original JSON pointer: `/6116`

DELSTREAM 命令是从当前工况中删除一个物流

## UG10-CH35-D054

PDF page: 507; original JSON pointer: `/6117`

如果你从库中删除了物流 你应用 PACK 命令恢复删除的空间 参见本章 PACK 命 令说明 语法 DELSTREAM stream-id 物流号 DIRECTORY DIRECTORY 命令用来列出存储在物流库中的物流和工况 如果在 DIRECTORY 命令 中不定义工况 STRLIB 将列出库中的所有工况和每个工况中的物流号 如果你定义了工况 STRLIB 只列出该工况中的物流 语法 DIRECTORY [ casename] 工况名 DUMP

## UG10-CH35-D055

PDF page: 507; original JSON pointer: `/6118`

DUMP 命令写出存储在库中有关物流的信息 STRLIB 提示你是写到终端还是写到文

## UG10-CH35-D056

PDF page: 507; original JSON pointer: `/6119`

件 如果写到文件 STRLIB 提示你输入文件名 规定 DUMP ALL 来自所有工况的物流存 放到库中 使用 DUMP 可以

## UG10-CH35-D057

PDF page: 507; original JSON pointer: `/6120`

如果你需要重新初始化一个库 来增加能够存储的最大工况数 那么首先使用 DUMP ALL 命令保存库的内容 要想恢复信息 用 LOAD 命令 语法   − ALL IDstreamDUMP

## UG10-CH35-D058

PDF page: 508; original JSON pointer: `/6122`

第 35 章 创建物流库

## UG10-CH35-D059

PDF page: 508; original JSON pointer: `/6123`

END 命令终止 STRLIB 过程 物流数据库将在这期间按你改变的数据进行更新 END

## UG10-CH35-D060

PDF page: 508; original JSON pointer: `/6124`

和 EXIT 命令是相似的 要想不更新数据库退出,那么用 QUIT 命令终止 STRLIB 在这

## UG10-CH35-D061

PDF page: 508; original JSON pointer: `/6125`

期间你所做的改变将不会保存

## UG10-CH35-D062

PDF page: 508; original JSON pointer: `/6126`

EXIT 命令终止 STRLIB 过程 物流数据库将在这期间按你改变的数据进行更新 END

## UG10-CH35-D063

PDF page: 508; original JSON pointer: `/6127`

HELP [ command] 命令

## UG10-CH35-D064

PDF page: 508; original JSON pointer: `/6128`

INITIALIZE 命令破坏物流库中的所有数据 只有当创建一个库或使用 DUMP ALL 命

## UG10-CH35-D065

PDF page: 508; original JSON pointer: `/6129`

INITIALIZE 命令初始化一个新的物流库 你必须定义一个库中所能包含的工况的最大

## UG10-CH35-D066

PDF page: 508; original JSON pointer: `/6130`

数 对新的物流库执行任何操作前输入 INITIALIZE 命令

## UG10-CH35-D067

PDF page: 508; original JSON pointer: `/6131`

LIST 命令列出当前汇总文件中的物流

## UG10-CH35-D068

PDF page: 508; original JSON pointer: `/6132`

LOAD 命令可以从由 DUMP 命令生成的存放文件加载信息 STRLIB 能加载所有的工

## UG10-CH35-D069

PDF page: 508; original JSON pointer: `/6133`

LOAD filename

## UG10-CH35-D070

PDF page: 508; original JSON pointer: `/6134`

OPEN 命令打开一个汇总文件 这样由 ASPEN PLUS 运行生成物流能够传递到库中

## UG10-CH35-D071

PDF page: 508; original JSON pointer: `/6135`

如果你没规定工况名 STRLIB 用汇总文件中的 RUNID 作为工况名 语法 OPEN filename (文件名) [casename] 工况名 PACK PACK 命令压缩物流库 当物流被删除时使空白的空间恢复 PACK 命令只有当删除一 些物流后并且想恢复没有用的文件的空间才是必须的 语法 PACK

## UG10-CH35-D072

PDF page: 509; original JSON pointer: `/6137`

第 35 章 创建物流库

## UG10-CH35-D073

PDF page: 509; original JSON pointer: `/6138`

RENAME命令用来给库中的物流改名 RENAME只用于当前工况

## UG10-CH35-D074

PDF page: 509; original JSON pointer: `/6139`

RENAME oldname (原名) [newname] 新名

## UG10-CH35-D075

PDF page: 509; original JSON pointer: `/6140`

REPLACE 命令用汇总文件中同名的物流替换一个当前工况物流 如果库中不存在该物

## UG10-CH35-D076

PDF page: 509; original JSON pointer: `/6141`

用 REPLACE ALL 从汇总文件向库拷贝所有物流 替换库中的同名物流

## UG10-CH35-D077

PDF page: 509; original JSON pointer: `/6142`

QUIT 命令结束 STRLIB 过程 物流数据库没有被当前 STRLIB 过程中的任何改变所更

## UG10-CH35-D078

PDF page: 509; original JSON pointer: `/6143`

新 用 END 或 EXIT 命令终止 STRLIB 过程时 按过程中所做的改变更新物流库

## UG10-CH35-D079

PDF page: 509; original JSON pointer: `/6144`

创建一个含有两个工况的库的示例

## UG10-CH35-D080

PDF page: 509; original JSON pointer: `/6145`

创建一个含有两个工况的物流库 从汇总文件 RUN1添加物流 S1和 S2 从汇总文件

## UG10-CH35-D081

PDF page: 509; original JSON pointer: `/6146`

STRLIB> OPEN RUN1.SUM

## UG10-CH35-D082

PDF page: 509; original JSON pointer: `/6147`

STRLIB> OPEN RUN2.SUM

## UG10-CH35-D083

PDF page: 509; original JSON pointer: `/6148`

物流库将被组织到两个工况中 RUN1和RUN2

## UG10-CH35-D084

PDF page: 509; original JSON pointer: `/6149`

创建一个含有一个工况的库的示例

## UG10-CH35-D085

PDF page: 509; original JSON pointer: `/6150`

创建一个含有五个工况的物流库 创建一个工况 PROJECT 从汇总文件 RUN1中添加

## UG10-CH35-D086

PDF page: 509; original JSON pointer: `/6151`

物流 PROD1和 PROD2 从汇总文件 RUN2中添加物流 FEED1

## UG10-CH35-D087

PDF page: 509; original JSON pointer: `/6152`

如果没有定义工况名 OPEN 命令创建一个新的工况 库必须被初始化成至少容纳三个 工况 上述命令集将创建两个名为 RUN1和 RUN2的空工况 为避免生成空工况 在 OPEN 命令中使用工况名 STRLIB> INITIALIZE 5 STRLIB> OPEN RUN1.SUM PROJECT STRLIB> ADD PROD1 STRLIB> ADD PROD2 STRLIB> OPEN RUN2.SUM PROJECT STRLIB> ADD FEED1 STRLIB> END

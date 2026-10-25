# 工程模型图文与文件交付

在编写模型说明、文献式图形摘要、产品展示或重新打包时读取；纯计算任务不加载。

先确定读者需要作出的判断，再分配信息：主图表达真实流程和功能关系；局部机理图解释必要的传递/反应过程；公式标明量定义、单位和适用范围；参数表与运行证据放配套位置。流程图、机理示意、Aspen原生排图和可安装模型分别命名，不互相冒充完成状态。

用户指定ImageGen时实际使用；从当前依据冻结准确文字、物流与接口，生成后核中文、单位、箭头和邻接关系。局部定向编辑后同时复查受影响邻域，不把视觉好看当作拓扑/机理正确。工况说明沿进料、处理、产品和回流顺序写清，具体图例与布局交对应绘图Skill。

Aspen的PFD排布走`chemical-pfd-pid-cad`的`image_layout_only`前段：检索、内容审核、ImageGen单块/分块生成、看图反馈，通过后把布局交回Aspen任务。此分支不要求先做DWG；固定原生接口、Aspen排图写入及保存复开由原任务负责。完整PFD/PID交付另走绘图全流程。依赖入口见[绘图Skill的前段交接](https://github.com/milklong888/gpt-image-chemical-pfd-pid/blob/1e0ee0402312c1559d79cb13b0a4cb2431ab0900/skills/chemical-pfd-pid-cad/references/IMAGE_LAYOUT_HANDOFF.md)；未安装该Skill时明确缺项，不临时换成自造布局能力。

最终选用的图片、说明和模型清单进入当前交付目录；说明/图片改动后同步交付包，核真实文件存在、相对成员、字节身份和用户可打开的入口。模型/运行依赖未变与整个包未变是不同结论；照[文件范围规则](STRICT_ACCEPTANCE_AND_LEARNING.md#文件范围与证据复用)复用有效证据。

只有本地文件已生成而客户端链接确实失败时，才查看现有[文件交付通路案例工具](https://github.com/milklong888/chemical-engineering-experience-inbox/tree/03f436d3942086084a59ed6cfd9853f7c615ca55/pool/scripts/local-artifact-delivery)。它不诊断Aspen、不代替模型复开，也不因本页链接就启动服务器或暴露目录；优先采用当前应用支持的交付通路，额外服务按本任务授权范围处理。

来源：milklong888，[工程仿真图文方法](https://github.com/milklong888/chemical-engineering-experience-inbox/blob/03f436d3942086084a59ed6cfd9853f7c615ca55/pool/techniques/engineering-model-product-presentation.md)及EXP-20261012-operating-techniques（原文CC BY 4.0）。本页为当前Skill的独立编排；来源许可、项目资产许可与工程核验分别保留。

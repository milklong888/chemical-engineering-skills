# 来源、推导与适用边界

这是公开方法的结构审查资料，不含旧客户模型、项目数值或通用Aspen卡片默认值。箭头为基于守恒与服务职责的条件化工程综合，不声称逐字照抄文献流程或已在目标版本执行。

| 来源/定位 | 支持的范围 | 不支持的推断 |
|---|---|---|
| [He等，2023，DOI 10.1039/D3RA06235J](https://doi.org/10.1039/D3RA06235J)，§3.3/Fig.7 | 双效有不同进料/串联安排，需要明确跨塔物料 | 不能移用其组分、压力、级数、物性或节能结果；顺/逆流名称不能替代流股定义 |
| [AspenTech Distillation Modeling Study Guide](https://www.aspentech.com/en/-/media/aspentech/home/cst-certification/aspen-plus-certification/at-05198_aspen-plus-dm-study-guide)，p11 | 端器热曲线、再沸器型式和Reboiler Wizard外置HeatX分析入口 | 不是完整建卡手册，不证明本文职责标签就是COM端口或跨版本语法 |
| [HTRI：Demystifying thermosiphon operation](https://www.htri.net/news/demystifying-thermosiphon-operation)，Fig.1及自然循环/热水力说明 | 密度差和回路压降耦合，两相返回与净液采出有不同职责 | 不提供项目循环倍率、布置高度、面积或HeatX运行通过 |
| [Luyben，2022，DOI 10.1016/j.cep.2022.109068](https://doi.org/10.1016/j.cep.2022.109068)，Heat transfer issues / Aspen simulation implementation / Fig.3 | 区分过程物料侧显式换热与保留端器的公用工程/热负荷抽象 | 特定研究不是所有双效的唯一通式；版本接口仍需当前帮助/导出核实 |
| 同质量基准的总量/组分/能量守恒 | 本Skill槽账、分级冷凝账、循环与净流区分，明确稳态/积累和控制体 | 等式不求出未知分配比、分离效果、相平衡、传热能力或收敛性 |

适用结构与明确例外一起使用：外供/跨塔回流、合法双采出、相变后再闪蒸、内外端器混合、热虹吸和两相回塔均需按其真实接口判断。基础图不构成排除其他合法方案的理由。

任何实际建卡前，按目标Aspen版本帮助、向导或真实导出核接口、级数和自由度。运行状态及精度要求仅引用[操作owner](../../aspen-plus-operations/SKILL.md)，不在此维护第二套验收器。案例图和文字检查不能提供真实软件、设备或工程通过证据。

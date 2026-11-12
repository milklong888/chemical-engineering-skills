# 原创结构示意图

四图均为通用方法的原创表达，不取自客户案例或旧Aspen模型。只表示接口、物料相态与职责，未执行Aspen；各图范围、原料、剩余端器与净产品边界在旁注中另列。不存在项目数值、项目默认工况。

1. [一次通过外置釜式平衡近似](../assets/01-once-through-kettle-local.svg)：同一HX的热冷两侧、HP凝液分配及LP外置平衡分相。图中两个HX框表示同一设备的两个物料侧。
2. [部分回收与串联补冷/补热](../assets/02-partial-heat-recovery-local.svg)：全凝条件属于热侧整链；冷侧补热后分相。补冷后仍含气时先分相，不能用液体分流器分相。
3. [热虹吸与强制循环的冷侧比较](../assets/03-thermosiphon-vs-forced-circulation-local.svg)：两种替代布置；后者的液体泵位于受热前，前者自然循环须另核热水力。
4. [共同槽回流与净边界](../assets/04-common-tank-boundary-local.svg)：LP保留本地回流，LP净顶流与HP凝液入槽，槽供HP回流和最终混合产品；外供液、排气/排污及积累另记。LP釜式冷侧与HP热侧是同一HX两侧。该图表达一个有条件的通用变体，须结合当前边界使用。

热曲线及外置HeatX分析入口参考[Aspen官方学习指南p11](https://www.aspentech.com/en/-/media/aspentech/home/cst-certification/aspen-plus-certification/at-05198_aspen-plus-dm-study-guide)；自然循环机理参考[HTRI](https://www.htri.net/news/demystifying-thermosiphon-operation)。这些来源支持限定原理，不证明图中具体Aspen端口或目标版本已经验证。具体连接采用[基本连接](material_connections.md)、[循环与分相](phase_and_circulation.md)、[热服务](heat_services.md)及[净边界](boundaries.md)的条件化工程表达。

前三张SVG源可由[原生成脚本](../scripts/generate_structures.py)重复生成，第四张由[共同槽图脚本](../scripts/generate_common_tank.py)生成。PNG为本地视觉检查预览；公开包以SVG为主，不因图片美观而升级工程验证状态。

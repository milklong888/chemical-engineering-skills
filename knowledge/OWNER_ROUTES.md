# 知识治理的唯一责任入口

治理责任用逻辑 Skill ID 表达，不把源码仓库的 `plugins` 目录假定为安装后目录。

| 逻辑 owner | 职责 |
| --- | --- |
| chemical-engineering-expert | 中央错误检查、严格验收、任务结束后的双通道进化 |
| equipment-design-app | 设备参数、派生、选择及应用协议错误检查 |
| chemical-equipment-selection-audit | 设备身份、公式族、来源及软件/厂家证据边界 |

用本包 [只读定位器](scripts/resolve_knowledge_owner.py) 获取当前真实文件：

```text
python knowledge/scripts/resolve_knowledge_owner.py --owner chemical-engineering-expert
python knowledge/scripts/resolve_knowledge_owner.py --owner equipment-design-app --skills-root <安装时选定的绝对技能目录>
```

仓库内使用本产品自带19Skills。安装后读取当前工作区已绑定的
`LOCAL_KNOWLEDGE_GRAPH_LINKS.md`，或由调用者明确传入 `--skills-root`；
未知根目录时报最小缺口，不查旧电脑、不复制第二套owner、不自动修改配置。

原图谱正文及错误记录中保留的历史`skill_packages/...`路径是来源表达，
不作为当前运行路径执行；统一以本页逻辑owner解析。同一原记录的正文和ID不重写。

新来源增补是用户明确的资料维护，与从任务经验自进化不同。来源维护保留X类知识，
以逐节点来源、定位、哈希、许可和独立review为准；任务经验的
prompt_principle/data_pattern才额外要求中央关闭、谱系与候选质量门。
任何构建产物都先留独立候选目录，不自动写活动库或宣称工程验证通过。

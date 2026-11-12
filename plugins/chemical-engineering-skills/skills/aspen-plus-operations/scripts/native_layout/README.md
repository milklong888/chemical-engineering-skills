> Main-library relocation: plugins/chemical-engineering-skills/skills/aspen-plus-operations/scripts/native_layout. Source and transformations: [RELOCATION.json](RELOCATION.json). Historical source/admission statements below retain their original scope; current parent skill owns routing and acceptance.

# Aspen原生排布工具与子技能候选

条目：EXP-20261023-aspen-native-layout；priority：normal。原创代码MIT；方法文字CC BY 4.0。此处先收进experience普通池供审查，不是正式inbox准入，也没有自动安装活动Skill。

核心素材是可执行脚本和清楚的输入/输出接口。只操作Aspen Export18的comment图形记录，用完整Export4冻结真实物理输入。没有固定五级块名、工程参数、用户路径或某个图标的默认端口坐标。热泵另见[结构卡](https://github.com/milklong888/chemical-engineering-experience-inbox/blob/1e0a6c7a50b2233de02fb214f258444b1e0d33ab/pool/materials/five-stage-water-source-heat-pump.md)。

## 可执行接口

Python标准库即可运行离线核心。以下相对命令在本工具目录执行，文件由调用者明确给出，不扫描机器或打开商业软件。

```text
python pfs_layout.py inspect source18.inp --output inspected.json
python pfs_layout.py apply source18.inp --export4 source4.inp --plan plan.json --output candidate.inp
python pfs_layout.py verify candidate.inp native_readback18.inp --export4 source4.inp --output layout_qa.json
```

输出必须新路径；不能覆盖输入/证据。拒绝以非零退出码返回。verify仅检查图形与完整真实卡，不含求解或工程通过判定；拿candidate自身做readback只是离线自检，不是软件复开证据。

批量核对私有案例时可运行`python private_integration.py manifest.json`。manifest根为`{"cases":[{"source":"source18.inp","export4":"source4.inp","plan":"plan.json","readback":"native_readback18.inp"}]}`，路径相对manifest目录，readback可省略。生成INP仅在内存中；输出是摘要、数量与核对结果。真实manifest、坐标、模型和回执留在包外，不能因回执不含路径便默认可公开。

Plan v1：根字段`version=1`、`blocks`、`streams`和可选`size=[xmin,xmax,ymin,ymax]`。指定block必须含`at`、正`scale`、整数`modifier`、`label`；指定stream必须含正交`path`、`ports`、`label`。ports依真实源/目的端为`"0"/"1"`，只写图形向外的`direction=l/r/u/d`，应与path邻段相符；禁止替代物理block、port或canonical。path首尾给显示端点，脚本自动从原生canonical计算$D。

改变block位置/Scale/Modifier时，须给所有关联stream完整计划；feed只有目的端，product只有源端。未指定对象原样保持，不增删物理对象。

下面是整体平移的可执行计划构造例，保留相对布局、标签和方向；它展示接口，不是自动优化算法。

```python
import json
from pathlib import Path
data = json.loads(Path("inspected.json").read_text(encoding="utf-8"))
dx, dy = 4.0, -2.0
shift = lambda q: [q[0] + dx, q[1] + dy]
plan = {"version": 1, "blocks": {}, "streams": {}}
for name, block in data["blocks"].items():
    plan["blocks"][name] = {
        "at": shift(block["at"]), "scale": block["scale"],
        "modifier": block["modifier"], "label": block["label"],
    }
for name, stream in data["streams"].items():
    plan["streams"][name] = {
        "path": [shift(p) for p in stream["path"]],
        "ports": {side: {"direction": port["direction"]}
                  for side, port in stream["ports"].items()},
        "label": stream["label"],
    }
left, right, bottom, top = data["size"]
plan["size"] = [left + dx, right + dx, bottom + dy, top + dy]
Path("plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
```

示例平移量为图形坐标，不是工艺参数。程序比较阈值仅用于有限精度图形文本，不改变Aspen求解容差。源图已有共线重叠时需先改相应路由，不能制造物理接点。

## 排布、tools与子技能

[tools接口专节](references/tools-interface.md)包含坐标公式、Modifier矩阵、$D/$C、config/icon、E_LINK处理、COM初始化/导出编号、保存复开与包内验证。

离线核心消费显式计划；模块间距、走廊和实际分支由当前真实流程决定。它不是自动布线器，也不保证原生字体下没有文字碰撞。真实保存/复开复用已有aspen-plus-operations runtime/supervisor，不复制另一套COM或锁。没有新的COM薄封装脚本，勿把本包当成已配置MCP服务。

当前仅处理已识别的BLOCK/材料TYPE0 STREAM、空附加route层和空LEGEND；未知图元、非空图层及歧义明确拒绝，原件不丢。详见程序实际拒绝条件。

[METHOD_REFERENCE.md](METHOD_REFERENCE.md) preserves the source method. This helper is owned and routed by aspen-plus-operations; it is not a nested independently discoverable skill. Original discovery metadata was omitted during relocation.

## 验证和边界

从经验仓库根运行：

```text
python -B -X utf8 -m unittest discover -s plugins/chemical-engineering-skills/skills/aspen-plus-operations/scripts/native_layout/tests -v
```

公开fixture为小型合成文本，无真实模型/工程参数/商业原件。核查旋转镜像、Scale/$D恢复、多端角色、完整真实卡不变和错误拒绝；结果和文件摘要见SOURCE_METADATA。离线测试不证明Aspen运行。

原生机制依据合法本机V14帮助主题与样例坐标的独立核查，商业原文不随包。真实模型、运行日志、原INP、客户数字和私人路径保留本地。完整原生Summary、Control Panel/history、产品与硬件验收仍归原owner，本包不另造解析器或成功条件。

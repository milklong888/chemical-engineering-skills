# EDR与填料水力学离线诊断合同

实现唯一位置是本Skill的`scripts/engineering_checks.py`；命令行、独立
`scripts/checks_mcp.py`和专家`module_check`都调用其中四个函数，不建立另一套算法。

| 操作 | 实际检查 | 需保留的未知项 |
|---|---|---|
| `screen_pipe_candidates` | 显式目录的ID、流量/面积/速度 | 不生成国标目录、不自动圆整或批准最终口径 |
| `check_exchanger_basis` | 调用者给出的绝压与压降闭合、面积基准、端点主相Re | 不计算原生传热、分段相态或压降 |
| `check_packed_beds` | 显式级覆盖、FC、HETP与床高 | 不求原生容量、实体床连续性或操作图位置 |
| `audit_edr_geometry` | 已支持管行、唯一正常管数、边界和圆截面重叠 | 不覆盖全部板/条/壳/轴向结构、振动或机械强度 |

输入字段和单位见[API](offline_checks_api.md)，来源分类、尺寸圆整反馈、告警、
热阻/面积与逐级水力学范围见[方法边界](offline_checks_rules.md)。当前标准的编号、
版次、原页适用条件仍来自任务资料；这里没有国标PDF，也没有通用评分阈值。

四个完整合成输入位于`examples/offline_checks/`，不是项目值：

```text
python -B -X utf8 scripts/engineering_checks.py screen_pipe_candidates --input examples/offline_checks/pipe.json
python -B -X utf8 scripts/engineering_checks.py check_exchanger_basis --input examples/offline_checks/exchanger.json
python -B -X utf8 scripts/engineering_checks.py check_packed_beds --input examples/offline_checks/packed.json
python -B -X utf8 scripts/engineering_checks.py audit_edr_geometry --input examples/offline_checks/geometry.json
```

上述命令在本Skill目录执行。MCP可选依赖使用发行包已有的受检运行环境；不可用时
继续使用CLI。API调用成功、诊断通过、原生EDR运行、产品达标和制造批准分别记录。
既有操作图位置、1061及交付依赖拟定改进的状态见专家模块目录，不能由本工具消警或补零。

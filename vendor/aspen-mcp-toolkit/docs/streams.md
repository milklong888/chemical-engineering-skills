# 物流 BASIS 属性详解

## 背景

Aspen Plus 中**没有独立**的 MOLE-FRAC 或 MASS-FRAC 节点。所有组分输入都通过同一个路径：

```
\Data\Streams\{name}\Input\FLOW\MIXED\{component}
```

该节点的 **BASIS 属性** 决定值的解释方式。

## BASIS 有效值

| BASIS | 含义 | 示例 |
|-------|------|------|
| `MOLE-FLOW` | 摩尔流量（默认） | `ETHANOL=50` → 50 kmol/hr |
| `MASS-FLOW` | 质量流量 | `ETHANOL=2300` → 2300 kg/hr |
| `MOLE-FRAC` | 摩尔分数 | `ETHANOL=0.5` → 50% 摩尔分数 |
| `MASS-FRAC` | 质量分数 | `ETHANOL=0.46` → 46% 质量分数 |

## 设置 BASIS

使用 `set_stream_composition_batch`（推荐）：

```
set_stream_composition_batch("FEED", {"ETHANOL": 0.5, "WATER": 0.5},
                             basis="MOLE-FRAC", total_flow=100)
```

或单参数 + basis：

```
set_stream_param("FEED", "ETHANOL", value=0.5, basis="MOLE-FRAC")
```

## 完整工作流

```
add_stream("FEED")
set_stream_param("FEED", "TEMP", 25)
set_stream_param("FEED", "PRES", 1)
set_stream_composition_batch("FEED", {"ETHANOL": 0.5, "WATER": 0.5},
                             basis="MOLE-FRAC", total_flow=100)
```

## 注意事项

- 使用分数 BASIS（MOLE-FRAC / MASS-FRAC）时**必须**同时指定 total_flow
- 改 BASIS 不影响已设置的值——只是改变 Aspen 对其的解释
- 读取流量：`get_stream_composition_info("FEED", "ETHANOL", basis="MOLEFLOW")`
- 读取分数：`get_stream_composition_info("FEED", "ETHANOL", basis="MOLEFRAC")`

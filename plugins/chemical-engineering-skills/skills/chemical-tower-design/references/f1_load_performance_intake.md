# F1浮阀塔负荷性能边界检查

本模块对调用者提供的负荷边界进行确定性几何计算，不提供默认F1经验系数、
训练权重或厂家性能数据。

## 工具作用

检查对象包括漏液、雾沫夹带、降液管液泛、液相上下限和当前操作点。塔板类型、
几何、物性、单位及边界公式须由当前设备资料确定，其他塔型的专属参数不能直接套用。

`scripts/f1_load_performance.py`读取来源锁定的F1分段线性边界，分别判断五项
约束，计算操作射线与全部边界的可行区间，只对包含操作点的连续区间给出操作
弹性。计算不跨越不可行间隙，不把扫描终点当成交点；程序不启动COM或修改Aspen。

## 输入合同

使用 JSON，`schema_version=f1-load-performance-boundaries-1.0`，明确：

- `tray_family=F1_float_valve`、`equipment_tag`、`case_id`、`geometry_identity`；
- `flow_unit=m3/s` 或 `m3/h`，`flow_basis=actual_at_operating_state`；
- `boundary_inclusive` 布尔值；边界点是否准许由当前方法决定，不隐式猜测；
- `operating_point={liquid,vapor}`，`liquid_limits={minimum,maximum}`；
- `boundaries.weeping/entrainment/flooding`：每条为严格递增液量的 `[liquid,vapor]` 点列；
- `interpolation_model=piecewise_linear` 与 `applicability`；点列必须覆盖规定液量范围及当前操作点，禁止外推；
- `sources` 对 operating_point、geometry、liquid_limits、weeping、entrainment、flooding 分别记录 `path/sha256/locator/status/equipment_tag/case_id`。

来源哈希核对只证明实际文件身份和声明工况一致，不证明原页公式、经验适用域或厂家性能已核验。传入边界可以来自既有已核算流程；尚待核的候选边界仍可作带状态的初筛，不进入正式选型验收。

调用：

```powershell
python -B -X utf8 scripts/f1_load_performance.py --input <current-boundaries.json> --output <new-result.json> --plot <new-plot.png>
```

输出保持 `PROVISIONAL_SUPPLIED_BOUNDARY_SCREENING` 和 `formal_engineering_acceptance=false`。数值上精确仅针对给定分段线性模型；原曲线拟合误差、实际 F1 几何/物性、湍动/雾沫关联式适用域、Column Internals/厂家与机械证据仍独立。

## 数据与验证边界

发行包仅包含独立的边界计算程序及合成测试，不包含第三方训练模型、数据表或
来源附件代码。经验公式、厂家曲线和实际塔内件数据由使用者按授权提供。
数值计算正确与边界来源适用性分别核验；正式技术采纳由当前设备依据和工程审查确定。

# 本地查询方法

GitHub 用户可直接打开[公开资料索引](PUBLIC_CATALOG.md)。使用插件可由 `public` 命令返回匹配条目和官方链接。公开索引随 Skill 提供，可在无本地图谱的环境运行。

```powershell
python scripts/query_graph.py public 'GB/T 150.2-2024 表C.2'
python scripts/query_graph.py public 'NPSH' --kind method
python scripts/query_graph.py public '反应器' --kind book
```

`--kind` 也可选择 `standard`，默认搜索所有类别。标准的收录位置用于导航，项目依据从相应版次的官方文本或用户提供的原件确认。

从活动工作区或另一目录中解出的快照运行。先找到包含 `知识图谱/` 的根目录。命令使用本 Skill 同级 `scripts/query_graph.py`，可从任意当前目录执行。需要 Python 3.12 或提供 SQLite JSON 和 FTS5 的等效本机环境。查询直接读取该处的两份图谱数据库和原有查询脚本。

```powershell
$env:CHEMICAL_KG_ROOT = 'D:\化工设备资料'
python scripts/query_graph.py design 'NPSH' --role reference
python scripts/query_graph.py design --pressure-vessel-material 表C.2
python scripts/query_graph.py design --pressure-vessel-material 表C.3
python scripts/query_graph.py design --pressure-vessel-design 表9-9
python scripts/query_graph.py design --exchanger-legacy 表6-31
python scripts/query_graph.py design --pressure-vessel 式B.12
python scripts/query_graph.py design --vessel-head 表5
python scripts/query_graph.py design --series fixed --dn 600 --length 6000 --passes 2 --pn 1.6
python scripts/query_graph.py increment '安全技术' --scans
python scripts/query_graph.py image-ocr '.gif' --candidates --limit 2
python scripts/query_graph.py source '设备设计/容器/GB_T150.1-2024压力容器 第1部分：通用要求.pdf'
python scripts/query_graph.py source 'source:ed2c4355496c947be5636844'
```

材料分册用 `--pressure-vessel-material`，压力容器通用要求用 `--pressure-vessel`，设计分册用 `--pressure-vessel-design`，封头用 `--vessel-head`。GB/T 151-2014 历史标准用 `--exchanger-legacy`，结果含历史版标记和 GB/T 151-2026 替代信息。设计分册和历史换热器标准查询需使用包含这些记录的配套库。一般设备依据用 `--role reference` 或 `--role requirements`。文件级候选加 `--candidates`。增量查询可按需用 `--evidence`、`--tables`、`--objects`、`--visuals`、`--word-sections`、`--contexts`、`--materials`、`--chemicals`、`--code`、`--scans`、`--html`。详细示例见选定根目录的 `LOCAL_KNOWLEDGE_GRAPH_LINKS.md`。

异目录查询时，脚本直接生成的预览路径可能已经指向解压根目录。库、JSON和历史回执中已登记的绝对来源路径仍保留。`path_resolution` 会为结构化结果中指向原工作区的现存副本列出可打开位置，原路径字段保持来源含义。原始资料目录随活动工作区使用。如果原件也迁移了，查询时可用 `--source-root` 提供包含 `教材手册` 和 `设备设计` 的目录。个别资料正文内的路径文字以原样存档。

`source` 返回来源 ID、登记路径、SHA-256 与本机 `local_path`。原压缩档内展开的资料还返回 `parent_source_id`，可用此 ID 继续查原压缩档。查询使用从指定根目录读取的数据库。可用命令行 `--root` 覆盖环境变量。

查包内归档范围见 `SNAPSHOT_MANIFEST.json`。`knowledge.sqlite` 是冻结的原始来源与静态图谱，`increment.sqlite` 是后续成果，`ocr.sqlite` 是打包瞬时一致的候选快照。查询中的 OCR 证据来自已同步的增量库。历史阶段的明细及二进制预览可按记录打开。

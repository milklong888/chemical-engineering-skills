# 运行错误汇总表格式

当前解析器支持已核对的原生三列表：Physical Property、System、Simulation。
Physical Property在原日志中分成两行显示，但它是同一列名。四个计数行分别为
Terminal Errors、Severe Errors、Errors和Warnings。

以下两个文件保留软件原始表格片段，不附带项目名称、流程数据、文件目录或其他
运行上下文：

- [包含警告的片段](fixtures/native_summary_warning.txt)：Simulation警告计数23。
- [包含错误的片段](fixtures/native_summary_errors.txt)：Simulation严重错误6、
  错误145，Physical Property警告1。

这两份片段用于说明表头和非零计数的解释，均不能通过全零条件；它们也不用于
评价任何完整工程项目。对应原始记录SHA256分别为
`F1B53FC170C02E67645EEBA0FACB7FBB1D3B2082AA4EC74C7E276FBEED154E00`
和`1ACF565B48863C416F4D2E256BCA42D5B067BB9515773C1DB13681689E047A92`。
完整原记录由来源环境保留，公开片段自身的身份以本发行清单为准。

生产验收要求所有规定行列完整并全部为零，并核对本次完整运行历史及文件身份。
单独的“无错误或警告”短语不能生成缺失计数或抵消先前诊断信息。新增软件版本
或表格结构先取得实际来源，再增加明确的解析配置和反例测试。

五列合成矩阵仅用于解析诊断；没有登记相应真实表头来源时，不用于生产验收。

param(
    [string]$PackageRoot = $env:EQUIPMENT_DESIGN_PACKAGE
)

$ErrorActionPreference = 'Stop'
if (-not $PackageRoot) {
    throw '未找到“设备设计图谱与脚本”总包。请传入 -PackageRoot 或设置 EQUIPMENT_DESIGN_PACKAGE。'
}
$launcher = Join-Path $PackageRoot 'run_equipment_design_app.ps1'
if (-not (Test-Path -LiteralPath $launcher)) {
    throw "应用启动器不存在：$launcher"
}
& $launcher
exit $LASTEXITCODE


[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TargetSkillsRoot,

    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$skillSourceRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$errorSeed = Join-Path $skillSourceRoot 'references\SKILL_ERROR_MEMORY_SEED.md'
$knowledgeSeed = Join-Path $skillSourceRoot 'references\SKILL_NEW_KNOWLEDGE_SEED.md'

$skillNames = @(
    'aspen-adaptive-generalization-loop',
    'aspen-document-driven-flowsheet',
    'aspen-edr-rating-delivery',
    'aspen-flowsheet-cost-skill-builder',
    'aspen-flowsheet-error-repair',
    'aspen-heat-pump-distillation-replacement',
    'aspen-kinetics-documentation',
    'aspen-local-knowledge-pack',
    'aspen-non-reactor-equipment-cost',
    'aspen-plus-operations',
    'aspen-plus-template',
    'aspen-pressure-pfd-delivery',
    'aspen-project-equipment-cost-batch',
    'aspen-tower-optimization-workflow',
    'aspen-two-section-flowsheet',
    'chemical-equipment-selection-audit',
    'sw6-scripted-equipment-design',
    'subagent-dispatch',
    'chemical-design-project-doc-writer',
    'chem-systems-engineering'
)

if (-not (Test-Path -LiteralPath $TargetSkillsRoot -PathType Container)) {
    throw "Target skill root does not exist: $TargetSkillsRoot"
}
if (-not (Test-Path -LiteralPath $errorSeed -PathType Leaf)) {
    throw "Missing error-memory seed: $errorSeed"
}
if (-not (Test-Path -LiteralPath $knowledgeSeed -PathType Leaf)) {
    throw "Missing new-knowledge seed: $knowledgeSeed"
}

$actions = New-Object System.Collections.Generic.List[string]

# Preflight the complete destination set before creating any companion file.
$expertTarget = Join-Path $TargetSkillsRoot 'chemical-engineering-expert'
if (Test-Path -LiteralPath $expertTarget) {
    throw "Refusing to overwrite installed chemical-engineering-expert skill: $expertTarget"
}
foreach ($skillName in $skillNames) {
    $checkRoot = Join-Path $TargetSkillsRoot $skillName
    if (-not (Test-Path -LiteralPath (Join-Path $checkRoot 'SKILL.md') -PathType Leaf)) {
        throw "Registered skill is missing SKILL.md: $checkRoot"
    }
    foreach ($companion in @('ERROR_MEMORY.md', 'NEW_KNOWLEDGE.md')) {
        $checkFile = Join-Path $checkRoot ('references\' + $companion)
        if (Test-Path -LiteralPath $checkFile) {
            throw "Refusing to overwrite existing memory file: $checkFile"
        }
    }
}

foreach ($skillName in $skillNames) {
    $skillRoot = Join-Path $TargetSkillsRoot $skillName
    $skillFile = Join-Path $skillRoot 'SKILL.md'
    if (-not (Test-Path -LiteralPath $skillFile -PathType Leaf)) {
        throw "Registered skill is missing SKILL.md: $skillRoot"
    }

    $references = Join-Path $skillRoot 'references'
    $errorTarget = Join-Path $references 'ERROR_MEMORY.md'
    $knowledgeTarget = Join-Path $references 'NEW_KNOWLEDGE.md'

    foreach ($target in @($errorTarget, $knowledgeTarget)) {
        if (Test-Path -LiteralPath $target) {
            throw "Refusing to overwrite existing memory file: $target"
        }
    }

    $actions.Add("CREATE $errorTarget")
    $actions.Add("CREATE $knowledgeTarget")
    if (-not $DryRun) {
        if (-not (Test-Path -LiteralPath $references -PathType Container)) {
            New-Item -ItemType Directory -Path $references | Out-Null
        }
        [System.IO.File]::WriteAllText($errorTarget, [System.IO.File]::ReadAllText($errorSeed), $utf8NoBom)
        [System.IO.File]::WriteAllText($knowledgeTarget, [System.IO.File]::ReadAllText($knowledgeSeed), $utf8NoBom)
    }
}

$expertTarget = Join-Path $TargetSkillsRoot 'chemical-engineering-expert'
if (Test-Path -LiteralPath $expertTarget) {
    throw "Refusing to overwrite installed chemical-engineering-expert skill: $expertTarget"
}
$actions.Add("INSTALL $expertTarget")
if (-not $DryRun) {
    Copy-Item -LiteralPath $skillSourceRoot -Destination $expertTarget -Recurse
}

$actions
"SUMMARY companion_files=$($skillNames.Count * 2) expert_skill=1 dry_run=$DryRun"




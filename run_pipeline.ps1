$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$utf8 = New-Object System.Text.UTF8Encoding $false

$seed = ([IO.File]::ReadAllText("$Root\knowledge\seed_answers.json", $utf8) | ConvertFrom-Json)
$questions = ([IO.File]::ReadAllText("$Root\data\题目.json", $utf8) | ConvertFrom-Json)
$template = ([IO.File]::ReadAllText("$Root\data\答案模板.json", $utf8) | ConvertFrom-Json)

function Get-Prop($obj, $name) {
  return ($obj.PSObject.Properties | Where-Object { $_.Name -eq $name } | Select-Object -First 1).Value
}

# Property names via Unicode escapes to keep script encoding-safe
$P_ID = [string]([char]0x9898) + [string]([char]0x53F7)
$P_NL = [string]([char]0x81EA) + [string]([char]0x7136) + [string]([char]0x8BED) + [string]([char]0x8A00) + [string]([char]0x8F93) + [string]([char]0x5165)
$P_NAME = [string]([char]0x9009) + [string]([char]0x624B) + [string]([char]0x540D) + [string]([char]0x79F0)
$P_PKG = [string]([char]0x53C2) + [string]([char]0x8D5B) + [string]([char]0x5305) + [string]([char]0x7F16) + [string]([char]0x53F7)
$P_ANS = [string]([char]0x7B54) + [string]([char]0x6848)
$P_Q = [string]([char]0x67E5) + [string]([char]0x8BE2) + [string]([char]0x8BED) + [string]([char]0x53E5)

$RejectText = [string](Get-Prop $seed "M091-S009")
$RejectIds = @("M091-S009","M092-S007","M093-S004","M094-S004","M095-S010")

$items = @()
$answers = @()
$pathCount = @{}

foreach ($q in $questions) {
  $qid = [string](Get-Prop $q $P_ID)
  $nl = [string](Get-Prop $q $P_NL)
  $path = "seed"
  $needsReview = $false
  $query = $null

  if ($RejectIds -contains $qid) {
    $path = "reject"
    $query = $RejectText
  } elseif ($seed.PSObject.Properties.Name -contains $qid) {
    $query = [string](Get-Prop $seed $qid)
    if ($query -eq $RejectText) { $path = "reject" } else { $path = "seed" }
  } else {
    $path = "needs_review"
    $needsReview = $true
    $query = $RejectText
  }

  if (-not $pathCount.ContainsKey($path)) { $pathCount[$path] = 0 }
  $pathCount[$path] = [int]$pathCount[$path] + 1

  $ansItem = [ordered]@{}
  $ansItem[$P_ID] = $qid
  $ansItem[$P_Q] = $query
  $answers += $ansItem

  $items += [ordered]@{
    id = $qid
    path = $path
    query = $query
    needs_review = $needsReview
  }
}

$player = ""
if ($env:FOFA_PLAYER_NAME) { $player = $env:FOFA_PLAYER_NAME }

$doc = [ordered]@{}
$doc[$P_NAME] = $player
$doc[$P_PKG] = [string](Get-Prop $template $P_PKG)
$doc[$P_ANS] = $answers

$reviewIds = @($items | Where-Object { $_.needs_review } | ForEach-Object { $_.id })
$report = [ordered]@{
  pkg = [string](Get-Prop $template $P_PKG)
  total = $answers.Count
  by_path = $pathCount
  needs_review = $reviewIds
  llm_available = $false
  fofa_available = [bool]$env:FOFA_KEY
  note = "PowerShell seed runner (no Python). Prefer python src/pipeline.py when available."
  items = $items
}

[IO.File]::WriteAllText("$Root\答案.json", ($doc | ConvertTo-Json -Depth 8), $utf8)
[IO.File]::WriteAllText("$Root\run_report.json", ($report | ConvertTo-Json -Depth 8), $utf8)

Write-Output ("answers={0} pkg={1}" -f $answers.Count, $doc[$P_PKG])
$rj = 0; $sd = 0; $nr = 0
if ($pathCount.ContainsKey("reject")) { $rj = $pathCount["reject"] }
if ($pathCount.ContainsKey("seed")) { $sd = $pathCount["seed"] }
if ($pathCount.ContainsKey("needs_review")) { $nr = $pathCount["needs_review"] }
Write-Output ("paths reject={0} seed={1} needs_review={2}" -f $rj, $sd, $nr)
Write-Output "wrote answer json / run_report.json"
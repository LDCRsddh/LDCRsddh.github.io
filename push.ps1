# =====================================================
#  push.ps1
#  One-click git add / commit / push
# =====================================================

$ErrorActionPreference = 'Continue'

$Root = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
Set-Location $Root

# ---------- check git repo ----------
if (-not (Test-Path (Join-Path $Root '.git'))) {
    Write-Host "  Not a git repository" -ForegroundColor Red
    Write-Host "  Path: $Root" -ForegroundColor DarkGray
    exit 1
}

# ---------- branch info ----------
$branch = (git rev-parse --abbrev-ref HEAD 2>$null)
if ([string]::IsNullOrWhiteSpace($branch)) { $branch = '(unknown)' }

$upstream = (git rev-parse --abbrev-ref '@{u}' 2>$null)
$hasUpstream = -not [string]::IsNullOrWhiteSpace($upstream)

Write-Host ("  Branch : {0}" -f $branch) -ForegroundColor DarkGray
if ($hasUpstream) {
    Write-Host ("  Remote : {0}" -f $upstream) -ForegroundColor DarkGray
} else {
    Write-Host "  Remote : not set (will push and set upstream)" -ForegroundColor DarkGray
}
Write-Host ""

# ---------- show changes ----------
Write-Host "  Changes:" -ForegroundColor DarkGray
$statusRaw = git status --short
$statusLines = @()
if ($statusRaw) {
    $statusLines = @($statusRaw -split "`r?`n" | Where-Object { $_ -ne '' })
}

if ($statusLines.Count -eq 0) {
    Write-Host "    (none)" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  Nothing to commit" -ForegroundColor Yellow

    if ($hasUpstream) {
        $ahead = (git rev-list --count "$upstream..HEAD" 2>$null)
        if ($ahead -and [int]$ahead -gt 0) {
            Write-Host ("  {0} unpushed commit(s) found" -f $ahead) -ForegroundColor Yellow
            $ans = Read-Host "  Push now? (y/n)"
            if ($ans -eq 'y' -or $ans -eq 'Y') {
                Write-Host ""
                git push
                if ($LASTEXITCODE -eq 0) {
                    Write-Host ""
                    Write-Host "  Push done" -ForegroundColor Green
                } else {
                    Write-Host ""
                    Write-Host "  Push failed" -ForegroundColor Red
                }
            }
        }
    }
    exit 0
}

foreach ($line in $statusLines) {
    Write-Host ("    {0}" -f $line) -ForegroundColor Gray
}
Write-Host ""

# ---------- ask for commit message ----------
$autoMsg = "update " + (Get-Date -Format 'yyyy-MM-dd HH:mm')
Write-Host ("  Press Enter to use: [{0}]" -f $autoMsg) -ForegroundColor DarkGray
$msg = Read-Host "  Commit message"
if ([string]::IsNullOrWhiteSpace($msg)) {
    $msg = $autoMsg
}

Write-Host ""

# ---------- git add ----------
Write-Host "  > git add ." -ForegroundColor DarkGray
git add .
if ($LASTEXITCODE -ne 0) {
    Write-Host "  add failed" -ForegroundColor Red
    exit 1
}

# ---------- git commit ----------
Write-Host "  > git commit" -ForegroundColor DarkGray
git commit -m $msg
if ($LASTEXITCODE -ne 0) {
    Write-Host "  commit failed (nothing to commit?)" -ForegroundColor Red
    exit 1
}

# ---------- git push ----------
Write-Host "  > git push" -ForegroundColor DarkGray
if ($hasUpstream) {
    git push
} else {
    git push -u origin $branch
}

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "  Done" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "  Push failed. Check network or repo credentials." -ForegroundColor Red
    Write-Host "  (First time: configure SSH key or GitHub login)" -ForegroundColor DarkGray
}
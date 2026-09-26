# =====================================================
#  sync.ps1
#  扫描 docs / tools / drops 下的新文件，
#  交互式询问标题、日期、描述等，
#  自动写入对应的 JSON 清单。
# =====================================================

$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch { }

# ---------- 路径 ----------
$Root = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$DocsDir   = Join-Path $Root 'docs'
$DocsJson  = Join-Path $DocsDir 'docs.json'
$ToolsDir  = Join-Path $Root 'tools'
$ToolsJson = Join-Path $ToolsDir 'tools.json'
$DropsDir  = Join-Path $Root 'drops'
$DropsJson = Join-Path $DropsDir 'drops.json'

# ---------- 读写 JSON ----------
function Read-JsonList {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return @() }
    $raw = Get-Content -Path $Path -Raw -Encoding UTF8
    if ([string]::IsNullOrWhiteSpace($raw)) { return @() }
    try {
        $data = $raw | ConvertFrom-Json
    } catch {
        Write-Host "无法解析 JSON：$Path" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        return @()
    }
    if ($null -eq $data) { return @() }
    if ($data -is [array]) { return @($data) }
    foreach ($key in 'docs','tools','files') {
        if ($data.PSObject.Properties.Name -contains $key) {
            return @($data.$key)
        }
    }
    return @()
}

function Write-JsonList {
    param([string]$Path, $Items)
    $json = ConvertTo-Json -InputObject @($Items) -Depth 10
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $json, $utf8)
}

# ---------- 输入辅助 ----------
function Ask-Text {
    param([string]$Label, [string]$Default = '')
    if ($Default) {
        $v = Read-Host ("{0} [{1}]" -f $Label, $Default)
        if ([string]::IsNullOrWhiteSpace($v)) { return $Default }
        return $v.Trim()
    } else {
        $v = Read-Host $Label
        return $v.Trim()
    }
}

function Format-Size {
    param([long]$Bytes)
    if ($Bytes -lt 1024) { return "$Bytes B" }
    if ($Bytes -lt 1048576) { return ("{0:N1} KB" -f ($Bytes / 1024)) }
    if ($Bytes -lt 1073741824) { return ("{0:N1} MB" -f ($Bytes / 1048576)) }
    return ("{0:N2} GB" -f ($Bytes / 1073741824))
}

# ---------- 辅助：找文件夹的 HTML 入口 ----------
function Find-ToolEntry {
    param([string]$FolderPath)

    # 优先 index.html
    $indexPath = Join-Path $FolderPath 'index.html'
    if (Test-Path $indexPath) { return 'index.html' }

    # 否则取字母序第一个 .html
    $firstHtml = Get-ChildItem -Path $FolderPath -Filter '*.html' -File |
                 Sort-Object Name |
                 Select-Object -First 1
    if ($firstHtml) { return $firstHtml.Name }

    return $null
}

# ---------- 扫描 docs ----------
function Scan-Docs {
    Write-Host ""
    Write-Host "==> 检查 docs/ 下的新文档" -ForegroundColor Cyan

    if (-not (Test-Path $DocsDir)) {
        Write-Host "    没有 docs/ 目录，跳过" -ForegroundColor DarkGray
        return
    }

    $existing = @(Read-JsonList $DocsJson)
    $existingFiles = @{}
    foreach ($d in $existing) {
        if ($d.file) {
            $key = ($d.file -replace '\\','/').ToLowerInvariant()
            $existingFiles[$key] = $true
        }
    }

    $newFiles = @()
    Get-ChildItem -Path $DocsDir -Filter '*.md' -File | ForEach-Object {
        $rel = "docs/$($_.Name)".ToLowerInvariant()
        if (-not $existingFiles.ContainsKey($rel)) {
            $newFiles += $_
        }
    }

    if ($newFiles.Count -eq 0) {
        Write-Host "    没有新文档" -ForegroundColor DarkGray
        return
    }

    Write-Host ("    发现 {0} 个新文档" -f $newFiles.Count) -ForegroundColor Yellow

    $added = 0
    foreach ($file in $newFiles) {
        Write-Host ""
        Write-Host ("--- 新文档：{0} ---" -f $file.Name) -ForegroundColor Green

        $baseName = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)

        $id    = Ask-Text "  ID（用于路由，保持唯一）" $baseName
        $title = Ask-Text "  标题" $baseName
        $date  = Ask-Text "  日期（YYYY-MM-DD）" (Get-Date -Format 'yyyy-MM-dd')
        $desc  = Ask-Text "  描述（可留空）" ''

        $idConflict = $existing | Where-Object { $_.id -eq $id }
        if ($idConflict) {
            Write-Host ("  ! ID '{0}' 已存在，跳过此文档" -f $id) -ForegroundColor Red
            continue
        }

        $entry = [ordered]@{
            id    = $id
            title = $title
            file  = "docs/$($file.Name)"
            date  = $date
            issue = $null
            desc  = $desc
        }

        $existing += [pscustomobject]$entry
        $added++
        Write-Host "  已加入清单" -ForegroundColor Green
    }

    if ($added -gt 0) {
        Write-JsonList $DocsJson $existing
        Write-Host ("  写入 {0}" -f $DocsJson) -ForegroundColor Green
    }
}

# ---------- 扫描 tools ----------
function Scan-Tools {
    Write-Host ""
    Write-Host "==> 检查 tools/ 下的新工具" -ForegroundColor Cyan

    if (-not (Test-Path $ToolsDir)) {
        Write-Host "    没有 tools/ 目录，跳过" -ForegroundColor DarkGray
        return
    }

    $existing = @(Read-JsonList $ToolsJson)
    $existingPaths = @{}
    foreach ($t in $existing) {
        if ($t.path) {
            $key = ($t.path -replace '\\','/').TrimEnd('/').ToLowerInvariant()
            $existingPaths[$key] = $true
        }
    }

    $candidates = @()

    # 递归扫描所有工具文件
    Get-ChildItem -Path $ToolsDir -Recurse -File | Where-Object {
        $_.Extension.ToLowerInvariant() -in '.html','.htm','.bat','.cmd','.ps1','.exe'
    } | ForEach-Object {
        $rel = $_.FullName.Substring($Root.Length).TrimStart('\','/') -replace '\\','/'
        $key = $rel.ToLowerInvariant()
        if ($existingPaths.ContainsKey($key)) { return }

        $t = switch ($_.Extension.ToLowerInvariant()) {
            '.html' { 'html' }
            '.htm'  { 'html' }
            '.bat'  { 'bat' }
            '.cmd'  { 'bat' }
            default { 'other' }
        }

        $inFolder = ($_.DirectoryName -ne $ToolsDir)
        $folderName = if ($inFolder) { Split-Path $_.DirectoryName -Leaf } else { '' }

        $candidates += [pscustomobject]@{
            RelPath    = $rel
            FileName   = $_.Name
            BaseName   = [System.IO.Path]::GetFileNameWithoutExtension($_.Name)
            Type       = $t
            InFolder   = $inFolder
            FolderName = $folderName
        }
    }

    if ($candidates.Count -eq 0) {
        Write-Host "    没有新工具" -ForegroundColor DarkGray
        return
    }

    Write-Host ("    发现 {0} 个新工具" -f $candidates.Count) -ForegroundColor Yellow

    $added = 0
    foreach ($cand in $candidates) {
        Write-Host ""
        if ($cand.InFolder) {
            Write-Host ("--- 新工具：{0}/{1} ---" -f $cand.FolderName, $cand.FileName) -ForegroundColor Green
        } else {
            Write-Host ("--- 新工具：{0} ---" -f $cand.FileName) -ForegroundColor Green
        }

        # 默认 ID：把 父文件夹名-文件名 里非字母数字的字符换成短横线
        $defaultId = if ($cand.InFolder) { "$($cand.FolderName)-$($cand.BaseName)" } else { $cand.BaseName }
        $defaultId = $defaultId -replace '[^a-zA-Z0-9\-_]', '-'

        $id   = Ask-Text "  ID（用于路由，保持唯一）" $defaultId
        $name = Ask-Text "  显示名称" $cand.BaseName
        $desc = Ask-Text "  描述（可留空）" ''

        $idConflict = $existing | Where-Object { $_.id -eq $id }
        if ($idConflict) {
            Write-Host ("  ! ID '{0}' 已存在，跳过此工具" -f $id) -ForegroundColor Red
            continue
        }

        $entry = [ordered]@{
            id   = $id
            name = $name
            type = $cand.Type
            path = $cand.RelPath
            desc = $desc
        }

        $existing += [pscustomobject]$entry
        $added++
        Write-Host "  已加入清单" -ForegroundColor Green
    }

    if ($added -gt 0) {
        Write-JsonList $ToolsJson $existing
        Write-Host ("  写入 {0}" -f $ToolsJson) -ForegroundColor Green
    }
}

# ---------- 扫描 drops ----------
function Scan-Drops {
    Write-Host ""
    Write-Host "==> 检查 drops/ 下的新文件" -ForegroundColor Cyan

    if (-not (Test-Path $DropsDir)) {
        Write-Host "    没有 drops/ 目录，跳过" -ForegroundColor DarkGray
        return
    }

    # --- 1. 把 drops/ 下的每个文件夹压成同名 zip ---
    $folders = @(Get-ChildItem -Path $DropsDir -Directory)
    foreach ($folder in $folders) {
        $zipPath = Join-Path $DropsDir ($folder.Name + '.zip')

        # 若 zip 已存在且比文件夹里最新文件还新，跳过打包
        if (Test-Path $zipPath) {
            $zipTime = (Get-Item $zipPath).LastWriteTime
            $latest = (Get-ChildItem -Path $folder.FullName -Recurse -File |
                       Sort-Object LastWriteTime -Descending |
                       Select-Object -First 1).LastWriteTime
            if ($latest -le $zipTime) {
                Write-Host ("    已存在 {0}.zip，跳过打包" -f $folder.Name) -ForegroundColor DarkGray
                continue
            }
        }

        Write-Host ("    打包文件夹 {0} → {1}.zip" -f $folder.Name, $folder.Name) -ForegroundColor Yellow
        try {
            Compress-Archive -Path (Join-Path $folder.FullName '*') `
                             -DestinationPath $zipPath -Force -ErrorAction Stop
            Write-Host "      完成" -ForegroundColor Green
        } catch {
            Write-Host ("      打包失败：{0}" -f $_.Exception.Message) -ForegroundColor Red
        }
    }

    # --- 2. 扫描已有清单 ---
    $existing = @(Read-JsonList $DropsJson)
    $existingNames = @{}
    foreach ($f in $existing) {
        if ($f.name) {
            $existingNames[$f.name.ToLowerInvariant()] = $true
        }
        if ($f.path) {
            $k = ($f.path -replace '\\','/').ToLowerInvariant()
            $existingNames[$k] = $true
        }
    }

    # --- 3. 扫描普通文件（含自动生成的 zip） ---
    $newFiles = @()
    Get-ChildItem -Path $DropsDir -File | Where-Object {
        $_.Name -ne 'drops.json' -and -not $_.Name.StartsWith('.')
    } | ForEach-Object {
        $rel = "drops/$($_.Name)".ToLowerInvariant()
        if (-not $existingNames.ContainsKey($_.Name.ToLowerInvariant()) -and
            -not $existingNames.ContainsKey($rel)) {
            $newFiles += $_
        }
    }

    if ($newFiles.Count -eq 0) {
        Write-Host "    没有新文件" -ForegroundColor DarkGray
        return
    }

    Write-Host ("    发现 {0} 个新文件" -f $newFiles.Count) -ForegroundColor Yellow

    $added = 0
    foreach ($file in $newFiles) {
        Write-Host ""
        Write-Host ("--- 新文件：{0} ---" -f $file.Name) -ForegroundColor Green

        $sizeDefault = Format-Size $file.Length
        $size = Ask-Text "  大小（显示用）" $sizeDefault
        $desc = Ask-Text "  描述（可留空）" ''

        $entry = [ordered]@{
            name = $file.Name
            path = "drops/$($file.Name)"
            size = $size
            desc = $desc
        }

        $existing += [pscustomobject]$entry
        $added++
        Write-Host "  已加入清单" -ForegroundColor Green
    }

    if ($added -gt 0) {
        Write-JsonList $DropsJson $existing
        Write-Host ("  写入 {0}" -f $DropsJson) -ForegroundColor Green
    }
}

# ---------- 扫描 show ----------
function Scan-Show {
    Write-Host ""
    Write-Host "==> 检查 show/ 下的图片" -ForegroundColor Cyan

    $ShowDir  = Join-Path $Root 'show'
    $ShowJson = Join-Path $ShowDir 'show.json'

    if (-not (Test-Path $ShowDir)) {
        Write-Host "    没有 show/ 目录，跳过" -ForegroundColor DarkGray
        return
    }

    $imageExts = @('.jpg','.jpeg','.png','.gif','.webp','.bmp','.avif')

    # wallpaper
    $wallpapers = @()
    $wallpaperDir = Join-Path $ShowDir 'wallpaper'
    if (Test-Path $wallpaperDir) {
        Get-ChildItem -Path $wallpaperDir -File | Where-Object {
            $imageExts -contains $_.Extension.ToLowerInvariant()
        } | Sort-Object Name | ForEach-Object {
            $wallpapers += [ordered]@{
                name = $_.Name
                path = "show/wallpaper/$($_.Name)"
            }
        }
    }

    # record（每个子文件夹是一个游戏）
    $records = @()
    $recordDir = Join-Path $ShowDir 'record'
    if (Test-Path $recordDir) {
        Get-ChildItem -Path $recordDir -Directory | Sort-Object Name | ForEach-Object {
            $gameFolder = $_
            $images = @()
            Get-ChildItem -Path $gameFolder.FullName -File | Where-Object {
                $imageExts -contains $_.Extension.ToLowerInvariant()
            } | Sort-Object Name | ForEach-Object {
                $images += [ordered]@{
                    name = $_.Name
                    path = "show/record/$($gameFolder.Name)/$($_.Name)"
                }
            }
            if ($images.Count -gt 0) {
                $records += [ordered]@{
                    game   = $gameFolder.Name
                    images = $images
                }
            }
        }
    }

    $data = [ordered]@{
        wallpaper = $wallpapers
        record    = $records
    }

    Write-Host ("    壁纸 {0} 张，游戏记录 {1} 组" -f $wallpapers.Count, $records.Count) -ForegroundColor Green

    $json = ConvertTo-Json -InputObject $data -Depth 10
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($ShowJson, $json, $utf8)
    Write-Host ("    写入 {0}" -f $ShowJson) -ForegroundColor Green
}

# ---------- 主流程 ----------
Write-Host ""
Write-Host ("  根目录：{0}" -f $Root) -ForegroundColor DarkGray

Scan-Docs
Scan-Tools
Scan-Drops
Scan-Show

Write-Host ""
Write-Host "完成。" -ForegroundColor Magenta
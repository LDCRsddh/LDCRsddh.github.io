@echo off
setlocal
if "%~1"=="" (
    echo 请将包含文件结构的 txt 文档拖拽到本 bat 文件上。
    echo 或者：%~nx0 "文件路径.txt"
    pause
    exit /b
)
set "TXT=%~1"
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { $ErrorActionPreference='Stop'; $Path=$env:TXT; $content=Get-Content -LiteralPath $Path -Encoding UTF8; $rootDir=Split-Path -Parent $Path; $stack=@(); foreach($line in $content){ $line=$line -replace '\u2190.*$',''; $line=$line.TrimEnd(); if($line -eq '' -or $line -match '^[\u2502\s\u251C\u2514\u2500]*$'){continue}; $prefix=''; $i=0; while($i -lt $line.Length -and $line[$i] -match '[\u2502\s\u251C\u2514\u2500]'){ $prefix+=$line[$i]; $i++ }; $name=$line.Substring($i).Trim(); if($name -eq ''){continue}; $depth=[math]::Floor($prefix.Length/4); $stack=@($stack | Select-Object -First $depth); if($depth -eq 0){ $fullPath=Join-Path $rootDir $name } else { $parent=$stack[-1]; $fullPath=Join-Path $parent $name }; if($name.EndsWith('/')){ New-Item -ItemType Directory -Path $fullPath -Force | Out-Null; $stack+=$fullPath } else { New-Item -ItemType File -Path $fullPath -Force | Out-Null } } }"
echo 完成！已在 "%TXT%" 所在目录生成结构。
pause
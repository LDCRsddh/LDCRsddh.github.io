@echo off
setlocal enabledelayedexpansion

rem 询问用户输入文件夹路径
set /p input_dir=请输入要提取链接的文件夹路径: 

rem 询问用户输入输出文件夹路径
set /p output_dir=请输入输出文件夹路径: 

rem 创建输出文件夹
if not exist "%output_dir%" mkdir "%output_dir%"

rem 提取链接并保存为HTML文件
set /a count=0
for %%i in ("%input_dir%\*.txt") do (
    for /f "tokens=*" %%a in ('type "%%i" ^| findstr /r "http[s]*://"') do (
        set /a count+=1
        echo ^<a href="%%a" target="_blank"^>%%a^</a^> > "%output_dir%\link_!count!.html"
    )
)

echo HTML链接已保存成功！
pause

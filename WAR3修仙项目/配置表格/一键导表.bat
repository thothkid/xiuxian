@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set LUBAN_DLL=..\tools\Luban\Luban.dll
set CONF_ROOT=.
set OUTPUT_TYPES_DIR=..\map\src\game\data\data_models
set OUTPUT_JSON_DIR=export_json
set OUTPUT_DATA_DIR=..\map\src\game\data\data_tables

echo ========================================
echo   凡人修仙 - Luban 导表工具
echo ========================================
echo.
echo  类型定义 → %OUTPUT_TYPES_DIR%
echo  数据表    → %OUTPUT_DATA_DIR%
echo.

:: ========================================
:: 预清理：删除导出目录下的旧文件
:: ========================================
echo [预清理] 删除所有旧导出文件...
:: 三个输出目录统一「整目录删除 + 重建空目录」，避免任何陈旧产物残留
:: (data_models=Luban类型  export_json=Luban JSON  data_tables=内联TS)
for %%D in ("%OUTPUT_TYPES_DIR%" "%OUTPUT_JSON_DIR%" "%OUTPUT_DATA_DIR%") do (
    if exist "%%~D" rd /s /q "%%~D"
    mkdir "%%~D"
    echo ✅ 已重建: %%~D
)
echo.

:: ========================================
:: 步骤1: Luban 导出类型定义 + JSON 数据
:: ========================================
echo [步骤 1/3] Luban 导出 Excel 配置...
echo.
dotnet "%LUBAN_DLL%" ^
    -t client ^
    -c yy-ts-json ^
    -d json ^
    --conf %CONF_ROOT%\luban.conf ^
    -x yy-ts-json.outputCodeDir=%OUTPUT_TYPES_DIR% ^
    -x outputDataDir=%OUTPUT_JSON_DIR%

if %errorlevel% neq 0 (
    echo ❌ Luban 导出失败，错误码: %errorlevel%
    echo.
    pause
    exit /b %errorlevel%
)

echo ✅ Luban 导出成功！
echo.

:: ========================================
:: 步骤2: JSON → TypeScript 内联数据
:: ========================================
echo [步骤 2/3] 生成内联数据 TypeScript 文件...
echo.
echo 当前目录: %cd%
echo 脚本路径: %~dp0post-process.mjs
echo 参数: %OUTPUT_JSON_DIR% %OUTPUT_DATA_DIR%
echo.

node "%~dp0post-process.mjs" %OUTPUT_JSON_DIR% %OUTPUT_DATA_DIR%

if %errorlevel% neq 0 (
    echo ❌ 内联数据生成失败，错误码: %errorlevel%
    echo.
    pause
    exit /b %errorlevel%
)

echo ✅ 内联数据生成成功！
echo.

echo.
echo ========================================
echo   🎉 导表完成！
echo ========================================
echo.
echo  生成的类型定义: %OUTPUT_TYPES_DIR%
echo  生成的数据表:   %OUTPUT_DATA_DIR%
echo  导出的 JSON 文件: %OUTPUT_JSON_DIR%
echo.
echo  在代码中使用（全局唯一 Tables 实例）:
echo    import { tables } from 'game/data/data_tables';
echo    const scene = tables.TbSceneConfig.get(1);
echo.

pause

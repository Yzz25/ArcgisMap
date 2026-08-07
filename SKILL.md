---
name: ArcgisMap
description: ArcGIS 10.2 自定义工具开发（中文 Windows / GBK 编码环境）。用户需要创建或修改 ArcGIS 工具箱脚本（.tbx、.pyt）、arcpy 地理处理脚本、字段计算器、自定义 Python 工具箱，或任何 ArcGIS Desktop 自动化时使用。凡提到 ArcGIS、arcpy、ArcToolbox、脚本工具、地理处理、空间分析、字段计算/编号、工具自动化，都应使用本技能。
compatibility: arcpy (ArcGIS 10.2), Python 2.7
---

# ArcGIS 10.2 工具开发

环境：ArcGIS 10.2 Desktop + Python 2.7 + 中文 Windows（系统编码 GBK/CP936）。
文档来源：[ArcGIS 10.2 Help](https://resources.arcgis.com/en/help/main/10.2/) · [Python Toolbox 官方模板](https://resources.arcgis.com/en/help/main/10.2/0015/001500000023000000.htm)

## 铁律 0：源码里零中文

Write/Edit 工具生成 **UTF-8** 文件，而 ArcGIS 10.2 按系统 ANSI（GBK）读取源码，**不理会** `# -*- coding: utf-8 -*-` 声明。中文字符的 UTF-8 多字节序列被误读为 GBK 后产生非法字节 → `SyntaxError`。

**交付的 .py / .pyt 文件必须纯 ASCII：字符串、注释、任何地方都不许出现中文字符。**

```python
# BROKEN: Chinese in source -> UTF-8 bytes misread as GBK -> SyntaxError
# (below shows the escaped form; a real file would contain the literal bytes)
arcpy.AddMessage(u"中文")   # "中文" as runtime-escaped codepoints

# CORRECT: pure ASCII; build Chinese at runtime with unichr()
arcpy.AddMessage("Processing...")
```

需要中文输出时，用 `unichr()` 在运行时构造，见 `references/encoding-guide.md`。

## 工具类型选择：.pyt 还是 .tbx

| 需求 | 选择 | 原因 |
|------|------|------|
| 英文界面或无界面 | **.pyt** | 单个文本文件，直接写，参数用代码定义 |
| 中文界面 | **.tbx + .py** | 中文标签在 .pyt 源码里编码冲突，在 GUI 里设置安全 |
| 需要 GPValueTable + 要素图层列 | **.tbx** | .pyt 不支持（静默红叉） |
| 需要 isLicensed() 授权控制 | **.pyt** | 脚本工具没有授权方法 |
| 参数多且复杂 | **.pyt** | 参数代码化，比 GUI 逐条配置省事 |

`.tbx` **不内嵌**脚本，只引用 .py 文件路径——替换磁盘上的 .py 即可生效，无需在 ArcCatalog 里重新浏览。

## 编码三函数（写任何 arcpy 脚本都要用）

核心思路：所有字符串操作在 **unicode** 里做，到 **arcpy 边界**才转成系统编码 str。

| 函数 | 何时用 |
|------|--------|
| `_to_uni(val)` | 从 arcpy 拿值（`GetParameterAsText`、游标字段）后立刻转 unicode |
| `_to_sys(val)` | 传给 arcpy 地理处理函数（Erase/Intersect/Describe/Exists…）的路径参数 |
| `_msg(msg)` | 传给 `AddMessage/AddError/AddWarning` 的消息 |

完整实现见 `references/templates.py`（直接复制），原理见 `references/encoding-guide.md`。

**两条必守规则：**
1. 所有可能接收 unicode 的格式化串必须用 `u"..."` 前缀。`str.format(unicode)` 在 Python 2 内部调用 `str(unicode)` → `encode('ascii')` → **UnicodeEncodeError**（在字符串到达 arcpy 之前就炸）。
2. 每个 `AddMessage/AddError/AddWarning` 必须经 `_msg()`；每个可能含 unicode 的 arcpy 参数必须经 `_to_sys()`。对含非 ASCII 字节的 str 做 `.endswith()`/`==` 等比较前，先 `_to_uni()`。

## 代码模板

写脚本前先读 `references/templates.py`，**直接复制对应模板作为起点**，不要重写。
- **.pyt 模板**：Toolbox 类（工具箱名 = 文件名）+ Tool 类（工具名 = 类名），六种方法 `__init__` / `getParameterInfo` / `isLicensed` / `updateParameters` / `updateMessages` / `execute`。官方标准结构。
- **.py 模板**：脚本工具用，已含编码三函数、异常处理、`finally` 清理，符合本技能全部规则。

## .tbx 参数类型选择

| 场景 | 用 | 原因 |
|------|-----|------|
| 输入要素（需拖拽 SHP） | **Feature Layer** | Feature Class 有 SHP 拖拽 bug |
| 多输入要素（需拖拽 SHP） | **Feature Layer**（多值） | 同上 |
| 输出工作空间路径 | **Workspace** | 内置文件夹/GDB 浏览器 |
| 普通文本 | **String** | 无需选择器 |
| 数字输入 | **Long** / **Double** | 内置数字校验 |

`GetParameterAsText()` 对两种类型返回相同路径字符串，代码逻辑不受影响。完整参数 API 见 `references/parameter-guide.md`。

## Personal GDB (.mdb) 三大陷阱

Personal GDB 走 Microsoft Jet（Access）引擎，有三个 File GDB 没有的坑：

1. **Erase 中文输出名失败**（Jet 报「未找到表」）。先 Erase 到 `in_memory`，再用 `FeatureClassToFeatureClass_conversion` 写最终输出。
2. **`CopyFeatures_management` 从 in_memory 写 .mdb 损坏属性表**（打开报「语法错误在查询表达式」）。所有 .mdb 输出一律用 `FeatureClassToFeatureClass_conversion`。
3. **非字母开头的字段名破坏 Jet SQL**（数字、`_` 开头）。用 `FieldMappings` 给字段加 `F_` 前缀重命名。

## 空结果处理

地理处理工具（Erase/Intersect/Clip）在结果为空时**可能不创建输出数据集**（.mdb 尤甚）。每次地理处理后必须 `arcpy.Exists()` 检查；为空则用 `FeatureClassToFeatureClass_conversion(..., "1=0")` 生成同 schema 的空表。

## 其他关键要点

- `FeatureClassToFeatureClass_conversion(in, out_path, out_name, {where}, {field_mapping}, ...)`：`field_mapping` 是**第 5 位**参数。不用 where 子句时必须用关键字 `field_mapping=fm`，否则会被当成 where_clause → ERROR 000623。
- 多步批量处理：中间结果放 `in_memory`，只把最终/备份结果写盘，省去每步磁盘 I/O。
- .pyt 校验：`updateMessages` 必须 try-except 包裹（未捕获异常 = 工具静默红叉）；`updateMessages` 里不要设参数值（不被校验）；校验用 `arcpy.Describe()` 而非 `ListFields`（数据集不存在时崩溃）；`altered=False` 才设默认值。
- 字段名不能以数字开头：用 `arcpy.ValidateFieldName()` 或加 `_` 前缀。
- 异常处理用 `repr(e)` 而非 `str(e)`（str 可能再次编码失败）。
- 清理变量（`temp_fcs`）必须在 `try` 前初始化，否则 `finally` 里 NameError；`finally` 中的 `arcpy.Exists()`/`Delete_management` 参数也要过 `_to_sys()`。

## 交付清单

1. 源码纯 ASCII（零中文）
2. 编码守卫显式检查 'ascii'（不能只写 `or 'mbcs'`）
3. 所有 arcpy 值先过 `_to_uni()`
4. 所有 `.format()` 用 `u"..."`（参数可能含 unicode 时）
5. 所有 `AddMessage/AddError/AddWarning` 过 `_msg()`
6. 所有 arcpy 路径参数过 `_to_sys()`
7. 清理变量在 `try` 前初始化
8. `updateMessages` 用 try 包裹（.pyt）
9. 字段名合法（无数字开头）
10. `isLicensed()` 返回正确值
11. .tbx：附 GBK 编码的中文参数配置说明（用 `iconv -f UTF-8 -t GBK` 转换）
12. 异常处理用 `repr(e)`

## 排错

出错先查 `references/errors.md`——常见错误速查表（红色 X、SyntaxError、UnicodeDecodeError/EncodeError、.mdb 错误、参数错误等），含原因与修复。

## 参考文件

- `references/templates.py` — 可直接复制的完整模板（.pyt + .py + 编码三函数）**【写代码前必读】**
- `references/encoding-guide.md` — 编码原理：GBK/UTF-8、`unichr()` 码表、三函数用法、`str.format(unicode)` 机制详解
- `references/parameter-guide.md` — Parameter API：数据类型、过滤器、属性方法、校验规则、GPValueTable
- `references/errors.md` — 常见错误速查表

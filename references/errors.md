# ArcGIS 10.2 常见错误速查表

按症状查错。所有「修复」里的约定（`_to_uni/_to_sys/_msg`、`u""` 前缀、`"1=0"` 兜底）详见 `encoding-guide.md` 与 `templates.py`。

## 编码类

| 症状 | 原因 | 修复 |
|------|------|------|
| 工具箱红叉，无错误信息 | .pyt 源码含 UTF-8 中文 | 删掉所有中文；用英文，或改用 .tbx |
| `SyntaxError: EOL while scanning string literal` | 中文字节被当成 GBK 误读 | 源码去中文；运行时中文用 `unichr()` |
| `SyntaxError: invalid syntax (line N)` | 注释或 `u""` 里也混入中文 | 任何地方零中文（铁律 0） |
| `UnicodeDecodeError: 'utf8' can't decode byte 0xb1` | GBK str 直接给了 UpdateCursor | 赋值前先 `_to_uni()` |
| `UnicodeEncodeError: 'ascii' codec can't encode` | `str.format(unicode)` 内部调用 `str(unicode)` → `encode('ascii')` | 所有可能含 unicode 的格式化串加 `u"..."` 前缀 |
| `UnicodeEncodeError: 'ascii'`（已用 `u"..."`） | `AddMessage` 收到了 unicode | 包一层 `_msg()` |
| `UnicodeEncodeError: 'ascii'`（已用 `_msg()`） | `str.format()` 在 `_msg()` 之前执行 | 格式化串本身必须是 `u"..."`（发生在到达 _msg 之前） |
| `UnicodeDecodeError: 'ascii'` 出现在 `.endswith()`/`==` | str 方法对 unicode 参数触发 ascii 解码，碰到 GBK 字节 | 与 unicode 比较前先 `_to_uni()` |
| `AttributeError: 'NoneType' has no attribute 'format'` | `.format()` 用在了 `AddWarning()` 的 None 返回值上 | 字符串先加括号，或统一用 `_msg()` |
| `or 'mbcs'` 兜底不生效 | `getfilesystemencoding()` 返回 `'ascii'`（真值） | 编码守卫里显式检查 `'ascii'`，不能只 `or 'mbcs'` |

## Personal GDB (.mdb) 类

| 症状 | 原因 | 修复 |
|------|------|------|
| Erase 失败报「未找到表」 | Jet 引擎 + 中文输出名 | 先 Erase 到 `in_memory`，再用 `FeatureClassToFeatureClass_conversion` 写最终输出 |
| 打开 .mdb 属性表报「语法错误在查询表达式」 | (a) 用了 CopyFeatures 而非 FeatureClassToFeatureClass；(b) 字段名以数字/下划线开头 | 一律用 FeatureClassToFeatureClass；字段加 `F_` 前缀 |
| CopyFeatures 后 .mdb 属性表损坏 | `in_memory` → .mdb 写入跳过 Jet 表初始化 | 所有 .mdb 输出用 `FeatureClassToFeatureClass_conversion` |

## 工具与参数类

| 症状 | 原因 | 修复 |
|------|------|------|
| `ERROR 000310: field name cannot start with digit` | 字段名如 `123` | 加 `_` 前缀或 `ValidateFieldName` |
| `ERROR 000623: value type for where_clause invalid` | FieldMappings 对象被当位置参数传给 where_clause | 用关键字 `field_mapping=fm` |
| `ERROR 000732: dataset does not exist` | 地理处理结果为空，输出没创建 | 每次工具后 `Exists()` 检查；空则 `FeatureClassToFeatureClass(..., "1=0")` 兜底 |
| 参数不在对话框显示 | `parameterType="Derived"`（派生参数隐藏） | 可见参数用 Required / Optional |
| .pyt 改参数后出现红叉 | ArcToolbox.dat 缓存损坏 | 删除 `%AppData%\Roaming\ESRI\Desktop10.2\ArcToolbox\ArcToolbox.dat` |
| 工具静默无动作 | `isLicensed()` 返回 False | 检查授权方法 |
| 脚本修改后不生效 | Windows 文件系统缓存旧 .py | 关闭并重新打开 ArcCatalog 刷新 |
| `finally` 里 NameError | 变量在 try 内定义，报错发生在赋值前 | 清理变量（temp_fcs）在 try 前初始化 |
| SHP 拖拽提示「one or more dropped items invalid」 | Feature Class datatype 的 SHP 拖拽 bug | 参数 datatype 用 Feature Layer |

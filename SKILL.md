---
name: ArcgisMap
description: ArcGIS 10.2 custom tool development on Chinese Windows. Use when the user wants to create or modify ArcGIS toolbox scripts (.tbx, .pyt), arcpy geoprocessing scripts, field calculators, custom Python toolboxes, or any automation within ArcGIS Desktop. Trigger on mentions of ArcGIS, arcpy, ArcToolbox, script tool, geoprocessing, spatial analysis, field calculation/numbering, or tool automation. MUST use for any ArcGIS 10.2 development task.
compatibility: arcpy (ArcGIS 10.2), Python 2.7
---

# ArcGIS 10.2 Tool Development

Environment: ArcGIS 10.2 Desktop, Python 2.7, Chinese Windows (system encoding = GBK/CP936).

Source: [ArcGIS 10.2 Help](https://resources.arcgis.com/en/help/main/10.2/), [Python Toolbox docs](https://resources.arcgis.com/en/help/main/10.2/0015/001500000023000000.htm).

## Encoding — RULE ZERO

**The Write/Edit tools produce UTF-8. ArcGIS 10.2 reads source files as GBK. Chinese characters in source code WILL cause SyntaxError.**

Rule: **zero Chinese characters in any source file (.py or .pyt).** Not in strings, not in comments, nowhere.

```python
# BROKEN — Chinese in source, UTF-8 bytes misread as GBK
arcpy.AddMessage(u"Processing...")  # SyntaxError

# CORRECT — pure ASCII
arcpy.AddMessage("Processing...")
```

If Chinese output is needed (warnings, messages), use `unichr()` to construct at runtime. See `references/encoding-guide.md` for the character table and patterns.

### sys.getfilesystemencoding() Trap

ArcGIS 10.2 embedded Python reports `sys.getfilesystemencoding()` as `'ascii'` (NOT `None`).  The common `or 'mbcs'` fallback does NOT trigger because `'ascii'` is truthy.

```python
# BROKEN — 'ascii' is truthy, fallback never activates
_SYS_ENC = sys.getfilesystemencoding() or 'mbcs'  # stays 'ascii'

# CORRECT — explicit check for ASCII
_SYS_ENC = sys.getfilesystemencoding()
if not _SYS_ENC or _SYS_ENC.lower() in ('ascii', 'us-ascii', 'ansi_x3.4-1968'):
    _SYS_ENC = 'mbcs'
```

## Tool Type Selection

| Factor | .pyt (Python Toolbox) | .tbx + .py script |
|--------|----------------------|-------------------|
| File format | Single .pyt text file | Binary .tbx + separate .py |
| Chinese UI labels | Chinese `u""` in source → **red X** (encoding conflict) | Set via ArcGIS GUI → safe |
| Creation | Write file directly | GUI-only (ArcCatalog → Add Script) |
| Embedding | N/A | Embed .py into .tbx (also reads as GBK!) |
| Parameter setup | Code (`getParameterInfo`) | GUI (tedious for many params) |
| `GPValueTable` + FeatureLayer | **Not supported** (silent red X) | Supported |
| `isLicensed()` control | Supported | N/A (script tool has no license method) |
| Debugging red X | Delete `ArcToolbox.dat` cache | Re-embed script |
| Distribution | Single file | .tbx + .py pair |

**Decision:**
- User wants English UI or no UI → .pyt (simplest)
- User wants Chinese UI → .tbx + .py (GUI setup)
- User needs `GPValueTable` with FeatureLayer columns → .tbx (required)
- .py source for .tbx MUST be pure ASCII (same GBK constraint for embedding)

### .tbx Script Caching Warning

**ArcGIS .tbx embeds a copy of the script content.**  Editing the external .py file does NOT update the tool automatically.  After every edit to the .py file, you MUST re-select it in ArcCatalog:

1. Right-click the tool → Properties → Script tab
2. Re-browse and select the .py file again
3. Click OK

A debug `arcpy.AddMessage(...)` at the top of the script helps verify the new version is loaded.

## .pyt Template (from official docs)

Source: [Python toolbox template](https://resources.arcgis.com/en/help/main/10.2/0015/001500000023000000.htm)

```python
# -*- coding: utf-8 -*-
import arcpy

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (name = filename of .pyt)."""
        self.label = "Toolbox"     # ASCII only
        self.alias = ""
        self.tools = [Tool]


class Tool(object):
    def __init__(self):
        """Define the tool (name = class name)."""
        self.label = "Tool"        # ASCII only
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions."""
        params = []
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify parameters before internal validation.
        Called whenever a parameter has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify messages after internal validation.
        MUST wrap in try-except — uncaught exception = silent red X."""
        try:
            pass
        except Exception:
            pass
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        return
```

**All six methods are standard.** `isLicensed()` returns False to disable the tool (e.g., when required extensions are unavailable).

## .py Script Template (for .tbx script tool)

This template includes all necessary encoding helpers and the encoding-safety guard.  Use this as the starting point for any .tbx script tool.

```python
# -*- coding: utf-8 -*-
import arcpy
import os
import sys

# ---- encoding (MUST use this exact guard) ----
_SYS_ENC = sys.getfilesystemencoding()
if not _SYS_ENC or _SYS_ENC.lower() in ('ascii', 'us-ascii', 'ansi_x3.4-1968'):
    _SYS_ENC = 'mbcs'


def _to_uni(val):
    """Normalize arcpy value to unicode."""
    if val is None:
        return u""
    if isinstance(val, unicode):
        return val
    if isinstance(val, str):
        try:
            return val.decode(_SYS_ENC)
        except Exception:
            try:
                return val.decode("utf-8")
            except Exception:
                return val.decode("utf-8", "replace")
    return unicode(val)


def _to_sys(val):
    """Encode unicode to system str (for arcpy function arguments)."""
    if isinstance(val, unicode):
        try:
            return val.encode(_SYS_ENC)
        except Exception:
            return val.encode("utf-8")
    return str(val) if val is not None else ""


def _msg(msg):
    """Encode message to system str (for arcpy.AddMessage/AddError/AddWarning)."""
    if isinstance(msg, unicode):
        try:
            return msg.encode(_SYS_ENC)
        except Exception:
            return msg.encode("utf-8")
    return msg if isinstance(msg, str) else str(msg)


# ---- Message constants (u"" prefix is REQUIRED) ----
M_SEP = u"=" * 60

# ---- init cleanup vars before try (avoid NameError in finally) ----
temp_fcs = []

try:
    # Read parameters -> unicode
    param0 = _to_uni(arcpy.GetParameterAsText(0))

    # Environment
    arcpy.env.overwriteOutput = True

    # All messages via _msg(); all arcpy args via _to_sys()
    arcpy.AddMessage(_msg(M_SEP))

except arcpy.ExecuteError:
    arcpy.AddError(_msg(u"Erase Error: ") + arcpy.GetMessages(2))
    raise SystemExit
except Exception as e:
    arcpy.AddError(_msg(u"Unexpected Error: {0}".format(repr(e))))
    raise SystemExit
finally:
    for temp_fc in temp_fcs:
        try:
            if arcpy.Exists(_to_sys(temp_fc)):
                arcpy.Delete_management(_to_sys(temp_fc))
        except Exception:
            pass
```

## Key Patterns

### 1. `_to_uni()` — always normalize arcpy values

`arcpy.GetParameterAsText()` and cursor values may return GBK `str` or `unicode`. Normalize immediately.

### 2. `_to_sys()` — encode unicode for arcpy function arguments

arcpy geoprocessing functions (Erase_analysis, Intersect_analysis, Describe, Exists, etc.) may not accept unicode on Chinese Windows.  Encode to system str at every arcpy call boundary.

```python
# BROKEN — unicode path may cause UnicodeEncodeError inside arcpy
arcpy.Erase_analysis(unicode_input, unicode_erase, unicode_output)

# CORRECT — encode at boundary
arcpy.Erase_analysis(_to_sys(unicode_input), _to_sys(unicode_erase),
                     _to_sys(unicode_output))
```

### 3. `_msg()` — encode messages for arcpy UI functions

`arcpy.AddMessage()`, `arcpy.AddError()`, `arcpy.AddWarning()` do NOT accept unicode on ArcGIS 10.2 Chinese Windows.  Always wrap with `_msg()`.

```python
# BROKEN — unicode in AddMessage triggers UnicodeEncodeError internally
arcpy.AddMessage(u"Result: {0}".format(name))

# CORRECT — _msg() encodes to system str
arcpy.AddMessage(_msg(u"Result: {0}".format(name)))
```

**Rule: every `arcpy.AddMessage/AddError/AddWarning` call goes through `_msg()`.  Every arcpy geoprocessing function argument goes through `_to_sys()` when it may be unicode.**

### 4. `u"..."` prefix for format strings — CRITICAL

Python 2 `str.format(unicode_arg)` internally calls `str(unicode_arg)`, which triggers `unicode.encode(sys.getdefaultencoding())` = `unicode.encode('ascii')` → **UnicodeEncodeError** for any non-ASCII character.

This is a Python 2 language-level behavior, NOT an ArcGIS issue.  It happens BEFORE the string reaches arcpy.

```python
# BROKEN — str.format(unicode) calls str(unicode) -> encode('ascii')
arcpy.AddMessage("Field: {0}".format(unicode_val))        # UnicodeEncodeError
arcpy.AddMessage(_msg("Field: {0}".format(unicode_val)))  # STILL BROKEN

# CORRECT — unicode.format(unicode) works directly with unicode
arcpy.AddMessage(_msg(u"Field: {0}".format(unicode_val)))
```

**Deep dive — what actually happens in CPython 2.7:**

When `str.format()` receives any unicode argument, CPython's `string_format` function (in `Objects/stringobject.c`) detects the unicode arg and switches to unicode mode.  For each replacement field `{0}` with no format spec, it calls `PyObject_Str()` on the argument.  `PyObject_Str(unicode_obj)` internally calls `PyUnicode_AsEncodedString(obj, NULL, NULL)`, which uses `sys.getdefaultencoding()` — always `'ascii'` in Python 2.  This is where the `UnicodeEncodeError('ascii', ...)` originates.

**Rule: ALL format strings that may receive unicode arguments MUST use `u"..."` prefix.**

### 5. `.format()` on string, not function return

```python
# BROKEN — .format() on AddWarning's None return
arcpy.AddWarning(u"msg {}".format(x))

# CORRECT — parens around the string
arcpy.AddWarning((u"msg {}").format(x))
```

Or safer: use `_msg()` which handles this uniformly.

### 6. `updateMessages` must be try-wrapped (.pyt)

Uncaught exception = silent red X on tool.

```python
def updateMessages(self, parameters):
    try:
        if parameters[0].value and not parameters[1].value:
            parameters[1].setErrorMessage("Required.")
    except Exception:
        pass
```

### 7. Validation: don't override altered values

`parameter.altered` = True if the user changed the value. Only set defaults when `altered` is False.

```python
def updateParameters(self, parameters):
    if parameters[0].value and not parameters[1].altered:
        parameters[1].value = "default_value"
```

### 8. Validation: don't set values in `updateMessages`

Values set in `updateMessages` are NOT validated by internal validation. Set values only in `updateParameters`.

### 9. Validation: don't use catalog-path methods

`ListFields`, `ListFeatureClasses` etc. fail when the dataset doesn't exist yet (ModelBuilder validation). Use `arcpy.Describe()` instead.

```python
desc = arcpy.Describe(parameters[0].value)
field_names = [f.name for f in desc.fields]  # OK in validation
```

### 10. Field name safety

ArcGIS field names: no leading digit, no special chars beyond `_`. Use `arcpy.ValidateFieldName()`:

```python
safe_name = arcpy.ValidateFieldName(raw_name, gdb_workspace)
```

Or at minimum:
```python
if name and name[0] in u"0123456789":
    name = u"_" + name
```

### 11. Spatial sorting pattern

```python
# Read: (oid, x, y) tuples via SHAPE@XY
# Top-to-bottom, left-to-right:
data.sort(key=lambda t: (-t[2], t[1]))  # Y desc, X asc
# With grouping:
data.sort(key=lambda t: (t[1], -t[4], t[3]))  # (group, -Y, X)
```

### 12. Derived output parameters

For tools that modify input in-place (like Add Field, Calculate Field):

```python
param_out = arcpy.Parameter(
    displayName="Output Features",
    name="out_features",
    datatype="GPFeatureLayer",
    parameterType="Derived",
    direction="Output",
)
param_out.parameterDependencies = [param_in.name]
param_out.schema.clone = True
```

### 13. `repr(e)` not `str(e)` in exception handlers

`str(e)` on UnicodeEncodeError may itself fail. `repr(e)` is always ASCII-safe.

### 14. Environment setup

```python
arcpy.env.overwriteOutput = True
arcpy.env.workspace = "in_memory"  # or GDB path
```

### 15. finally block — initialize before try

If an exception occurs before a variable is assigned inside `try`, the `finally` block referencing it will get `NameError`.  Initialize ALL cleanup-required variables BEFORE the `try` block.

```python
# BROKEN — if error before temp_fcs = [], finally raises NameError
try:
    ...
    temp_fcs = []
    ...
finally:
    for fc in temp_fcs:  # NameError!

# CORRECT — init before try
temp_fcs = []
try:
    ...
finally:
    for fc in temp_fcs:  # safe
```

### 16. Encoding strategy summary

```
                    +-----------+
  GetParameterAsText |  str/unicode |  raw input
        |            +-----------+
        | _to_uni()
        v
    unicode  <---- all internal string ops (format, join, basename, split)
        |
        | _to_sys() / _msg()
        v
    sys str  <---- all arcpy calls (GP functions, AddMessage, AddError)
```

One golden path: unicode inside, sys str at the boundary.

## .tbx Script Tool Parameter Datatype Selection

ArcGIS 10.2 has known bugs with certain parameter datatypes when dragging SHP files.  Use this guide:

| Scenario | Use | Why |
|----------|-----|-----|
| Single input feature (SHP drag needed) | **Feature Layer** | Feature Class has SHP drag-drop bug |
| Multi input features (SHP drag needed) | **Feature Layer** (multi-value) | Same bug; Feature Layer works |
| Output workspace path | **Workspace** | Built-in folder/GDB browser |
| Plain text name | **String** | No selector needed |
| Numeric input | **Long** / **Double** | Built-in numeric validation |

**Feature Class vs Feature Layer:**
- Feature Class drag-drop of .shp files: "one or more dropped items are invalid"
- Feature Layer drag-drop of .shp files: works correctly
- `GetParameterAsText()` returns the same path string for both types — code is unaffected

## Common Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| Toolbox red X, no error message | UTF-8 Chinese in .pyt source | Remove ALL Chinese; use English or switch to .tbx |
| `SyntaxError: EOL while scanning string literal` | Chinese bytes misinterpreted as GBK | Remove Chinese from source; use `unichr()` |
| `SyntaxError: invalid syntax (line N)` | Chinese chars even in comments or u"" literals | Zero Chinese anywhere; use `unichr()` for runtime strings |
| `UnicodeDecodeError: 'utf8' can't decode byte 0xb1` | GBK str assigned to UpdateCursor | `_to_uni()` before cursor assignment |
| `UnicodeEncodeError: 'ascii' codec can't encode` | `str.format(unicode)` calls `str(unicode)` internally | `u"..."` prefix for ALL format strings that may get unicode args |
| `UnicodeEncodeError: 'ascii'` despite `u"..."` format | arcpy.AddMessage received unicode | Wrap AddMessage/AddError/AddWarning in `_msg()` |
| `UnicodeEncodeError: 'ascii'` with `_msg()` used | `str.format()` happened before `_msg()` call | Format string itself must be `u"..."` — happens BEFORE _msg |
| `AttributeError: 'NoneType' has no attribute 'format'` | `.format()` on `AddWarning()` return | Wrap string in parens first, or use `_msg()` |
| `ERROR 000310: field name cannot start with digit` | Field name like `123` | Auto-prefix with `_` or use `ValidateFieldName` |
| `.pyt` red X after parameter changes | Corrupted ArcToolbox.dat cache | Delete `%AppData%\Roaming\ESRI\Desktop10.2\ArcToolbox\ArcToolbox.dat` |
| Tool silently does nothing | `isLicensed()` returns False | Check license method |
| Parameter not showing in dialog | `parameterType="Derived"` — Derived params are hidden | Use Required or Optional for visible params |
| Script changes not taking effect | .tbx caches embedded script | Re-select .py file in tool Properties → Script tab |
| `NameError` in finally block | Variable defined inside try, error before assignment | Init cleanup vars BEFORE try block |
| SHP drag-drop: "one or more dropped items invalid" | Feature Class datatype SHP bug | Use Feature Layer datatype instead |
| `or 'mbcs'` fallback doesn't trigger | `getfilesystemencoding()` returns 'ascii' (truthy) | Explicit check for 'ascii' in encoding guard |

## Delivery Checklist

1. All source files are **pure ASCII** (zero Chinese bytes anywhere)
2. `sys.getfilesystemencoding()` guard with explicit ASCII check
3. All arcpy values go through `_to_uni()` before string operations
4. **ALL** `.format()` calls use `u"..."` when args may contain unicode
5. **ALL** `arcpy.AddMessage/AddError/AddWarning` calls go through `_msg()`
6. **ALL** arcpy function args go through `_to_sys()` when they may be unicode paths
7. Cleanup variables (temp_fcs, etc.) initialized **before** `try` block
8. `updateMessages` is try-wrapped (.pyt)
9. Field names validated (no leading digit)
10. `isLicensed()` returns True (or correct license check)
11. If .tbx: provide parameter table with Chinese UI setup instructions (GBK README)
12. `repr(e)` used in exception handlers
13. Environment (`overwriteOutput`, `workspace`) configured
14. .tbx parameters: use Feature Layer (not Feature Class) for SHP drag-drop support

## .tbx Script Tool README Template

When delivering .tbx script tools, always include a setup README (GBK-encoded `.txt`) with parameter configuration tables. The README tells the user how to create the .tbx in ArcCatalog and configure each script tool's parameters.

### README Structure

```
================================================================================
  [Toolbox Name] — ArcGIS 10.2 Setup Guide
================================================================================

  ...overview text...

---- Steps in ArcCatalog ----

  1. Open ArcCatalog
  2. Navigate to [project directory]
  3. Right-click → New → Toolbox → name it
  4. Right-click .tbx → Add → Script..., select the .py file
  5. In the script properties dialog, set each parameter per table below

================================================================================
  Tool XX: [Chinese Name]
================================================================================

  脚本文件: ...\scripts\tool_xxx.py

  参数0:
    显示名称: [Chinese label]
    数据类型: Feature Layer（要素图层）
    参数类型: Required（必填）
    方向: Input（输入）

  参数1:
    显示名称: [Chinese label]
    数据类型: Feature Layer（要素图层）
    参数类型: Required（必填）
    方向: Input（输入）
    多值: 是
```

### Parameter Config Format

Each parameter uses key-value pairs, one per line:

```
参数N:
  显示名称: <Chinese UI label>
  数据类型: <ArcGIS type>（<Chinese name>）
  参数类型: <Required/Optional/Derived>（<Chinese>）
  方向: <Input/Output>（<Chinese>）
  多值: <是/否>
  过滤器: <Value List / Range / Feature Class / ...>
    可选值: <value>（<note>）
```

Key rule: every DataType/Type/Direction value is followed by its Chinese name in full-width parentheses （）. This lets the user match the ArcCatalog UI exactly.

### ArcGIS Data Type Chinese Names

| DataType | Chinese |
|----------|---------|
| Feature Class | 要素类 |
| Feature Layer | 要素图层 |
| Table | 表 |
| Raster Layer | 栅格图层 |
| String | 字符串 |
| Long | 长整型 |
| Double | 双精度 |
| Boolean | 布尔型 |
| Workspace | 工作空间 |
| Field | 字段 |
| SQL Expression | SQL表达式 |

### Parameter Type Chinese Names

| Type | Chinese |
|------|---------|
| Required | 必填 |
| Optional | 可选 |
| Derived | 派生 |

### Direction Chinese Names

| Direction | Chinese |
|-----------|---------|
| Input | 输入 |
| Output | 输出 |

### Encoding Note

README must be GBK-encoded for Chinese Windows. After writing with the Write tool (UTF-8), convert with:
```
iconv -f UTF-8 -t GBK readme.txt > readme_gbk.txt && mv readme_gbk.txt readme.txt
```

## Reference Files

- `references/encoding-guide.md` — GBK/UTF-8 encoding, `unichr()` codepoint table, `_to_uni()` internals
- `references/parameter-guide.md` — Complete parameter API: data types, filters, methods, properties, validation

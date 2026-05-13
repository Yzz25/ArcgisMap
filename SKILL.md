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

```python
# -*- coding: utf-8 -*-
import arcpy
import sys

_SYS_ENC = sys.getfilesystemencoding()


def _to_uni(val):
    """Safe conversion to unicode — arcpy da cursors expect unicode."""
    if val is None:
        return u""
    if isinstance(val, unicode):
        return val
    if isinstance(val, str):
        try:
            return val.decode(_SYS_ENC)
        except Exception:
            return val.decode("utf-8", "replace")
    return unicode(val)


try:
    # Read parameters (order matches .tbx tool config)
    arcpy.env.overwriteOutput = True

    param0 = _to_uni(arcpy.GetParameterAsText(0))
    # ...

    # Use unicode for all arcpy data
    with arcpy.da.SearchCursor(fc, ["OID@", "FieldName", "SHAPE@XY"]) as cursor:
        for row in cursor:
            fld = _to_uni(row[1])

    # Write back — assign unicode, not GBK str
    with arcpy.da.UpdateCursor(fc, ["OID@", "TargetField"]) as cursor:
        for row in cursor:
            row[1] = unicode_value
            cursor.updateRow(row)

    # Use u"" for all format strings with unicode data
    arcpy.AddMessage(u"Done. {} features.".format(count))

except Exception as e:
    arcpy.AddError("Error: " + repr(e))
    raise
```

## Key Patterns

### 1. `_to_uni()` — always normalize arcpy values

`arcpy.GetParameterAsText()` and cursor values may return GBK `str` or `unicode`. Normalize immediately.

### 2. `u"..."` prefix for format strings

Python 2 `"...{}...".format(unicode_val)` tries ASCII → `UnicodeEncodeError`.

```python
# BROKEN
arcpy.AddMessage("Field: {}".format(unicode_val))

# CORRECT
arcpy.AddMessage(u"Field: {}".format(unicode_val))
```

### 3. `.format()` on string, not function return

```python
# BROKEN — .format() on AddWarning's None return
arcpy.AddWarning(u"msg {}".format(x))

# CORRECT — parens around the string
arcpy.AddWarning((u"msg {}").format(x))
```

### 4. `updateMessages` must be try-wrapped (.pyt)

Uncaught exception = silent red X on tool.

```python
def updateMessages(self, parameters):
    try:
        if parameters[0].value and not parameters[1].value:
            parameters[1].setErrorMessage("Required.")
    except Exception:
        pass
```

### 5. Validation: don't override altered values

`parameter.altered` = True if the user changed the value. Only set defaults when `altered` is False.

```python
def updateParameters(self, parameters):
    if parameters[0].value and not parameters[1].altered:
        parameters[1].value = "default_value"
```

### 6. Validation: don't set values in `updateMessages`

Values set in `updateMessages` are NOT validated by internal validation. Set values only in `updateParameters`.

### 7. Validation: don't use catalog-path methods

`ListFields`, `ListFeatureClasses` etc. fail when the dataset doesn't exist yet (ModelBuilder validation). Use `arcpy.Describe()` instead.

```python
desc = arcpy.Describe(parameters[0].value)
field_names = [f.name for f in desc.fields]  # OK in validation
```

### 8. Field name safety

ArcGIS field names: no leading digit, no special chars beyond `_`. Use `arcpy.ValidateFieldName()`:

```python
safe_name = arcpy.ValidateFieldName(raw_name, gdb_workspace)
```

Or at minimum:
```python
if name and name[0] in u"0123456789":
    name = u"_" + name
```

### 9. Spatial sorting pattern

```python
# Read: (oid, x, y) tuples via SHAPE@XY
# Top-to-bottom, left-to-right:
data.sort(key=lambda t: (-t[2], t[1]))  # Y desc, X asc
# With grouping:
data.sort(key=lambda t: (t[1], -t[4], t[3]))  # (group, -Y, X)
```

### 10. Derived output parameters

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

### 11. `repr(e)` not `str(e)` in exception handlers

`str(e)` on UnicodeEncodeError may itself fail. `repr(e)` is always ASCII-safe.

### 12. Environment setup

```python
arcpy.env.overwriteOutput = True
arcpy.env.workspace = "in_memory"  # or GDB path
```

## Common Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| Toolbox red X, no error message | UTF-8 Chinese in .pyt source | Remove ALL Chinese; use English or switch to .tbx |
| `SyntaxError: EOL while scanning string literal` | Chinese bytes misinterpreted as GBK | Remove Chinese from source |
| `UnicodeDecodeError: 'utf8' can't decode byte 0xb1` | GBK str assigned to UpdateCursor | `_to_uni()` before cursor assignment |
| `UnicodeEncodeError: 'ascii' codec can't encode` | ASCII format string + unicode arg | `u"..."` prefix for format strings |
| `AttributeError: 'NoneType' has no attribute 'format'` | `.format()` on `AddWarning()` return | Wrap string in parens first |
| `ERROR 000310: field name cannot start with digit` | Field name like `123` | Auto-prefix with `_` or use `ValidateFieldName` |
| `.pyt` red X after parameter changes | Corrupted ArcToolbox.dat cache | Delete `%AppData%\Roaming\ESRI\Desktop10.2\ArcToolbox\ArcToolbox.dat` |
| Tool silently does nothing | `isLicensed()` returns False | Check license method |
| Parameter not showing in dialog | `parameterType="Derived"` — Derived params are hidden | Use Required or Optional for visible params |

## Delivery Checklist

1. All source files are pure ASCII (zero Chinese bytes)
2. All arcpy values go through `_to_uni()` before string ops
3. All `.format()` calls use `u"..."` when args contain unicode
4. `updateMessages` is try-wrapped (.pyt)
5. Field names validated (no leading digit)
6. `isLicensed()` returns True (or correct license check)
7. If .tbx: provide parameter table with Chinese UI setup instructions
8. `repr(e)` used in exception handlers
9. Environment (`overwriteOutput`, `workspace`) configured

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
    数据类型: Feature Class（要素类）
    参数类型: Required（必填）
    方向: Input（输入）

  参数1:
    显示名称: [Chinese label]
    数据类型: String（字符串）
    参数类型: Optional（可选）
    方向: Input（输入）
    过滤器: 值列表
      可选值: option_a（说明）
             option_b（说明）
```

### Parameter Config Format

Each parameter uses key-value pairs, one per line:

```
参数N:
  显示名称: <Chinese UI label>
  数据类型: <ArcGIS type>（<Chinese name>）
  参数类型: <Required/Optional/Derived>（<Chinese>）
  方向: <Input/Output>（<Chinese>）
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

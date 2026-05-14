# ArcGIS 10.2 Encoding Guide

## The Core Problem

ArcGIS 10.2 runs on Python 2.7. On Chinese Windows, the system encoding is GBK (CP936). The Claude Code Write/Edit tools produce UTF-8 files.

When ArcGIS loads a `.pyt` file (or a `.py` script through a .tbx tool), it reads raw bytes using the system ANSI codepage (GBK). It does NOT respect the `# -*- coding: utf-8 -*-` PEP 263 declaration.

UTF-8 multi-byte sequences for Chinese characters, when misinterpreted as GBK, produce invalid byte sequences → `SyntaxError`.

## Solution Matrix

| Scenario | Approach |
|----------|----------|
| .pyt with Chinese labels | Label/displayName must be ASCII. User must accept English UI. |
| .tbx .py script | Source must be pure ASCII. Runtime Chinese via `unichr()`. |
| .py script (direct run) | Python's `# coding: utf-8` works for direct imports. But safer to keep pure ASCII. |
| Messages to user in Chinese | Build at runtime using `unichr()` with hex codepoints (`_w()` helper). |
| Chinese field values from data | `_to_uni()` converts GBK str to unicode safely. |
| Passing paths to arcpy functions | `_to_sys()` encodes unicode to system str at boundary. |
| Sending messages to arcpy UI | `_msg()` encodes unicode to system str for AddMessage/AddError/AddWarning. |

## sys.getfilesystemencoding() Trap

**Critical:** ArcGIS 10.2 embedded Python reports `sys.getfilesystemencoding()` as `'ascii'` (NOT `None`). The common `or 'mbcs'` fallback pattern does NOT work because `'ascii'` is truthy.

```python
# BROKEN — 'ascii' is truthy, fallback never activates
_SYS_ENC = sys.getfilesystemencoding() or 'mbcs'  # stays 'ascii'

# CORRECT — explicit check
_SYS_ENC = sys.getfilesystemencoding()
if not _SYS_ENC or _SYS_ENC.lower() in ('ascii', 'us-ascii', 'ansi_x3.4-1968'):
    _SYS_ENC = 'mbcs'
```

## Python 2 str.format(unicode) — The Hidden Trap

**This is the most insidious encoding bug in ArcGIS 10.2 development.** It happens at the Python 2 language level, BEFORE any arcpy code runs.

### Mechanism

When `str.format()` receives ANY unicode argument, CPython 2.7's `string_format` (in `Objects/stringobject.c`) detects the unicode arg and for each replacement field `{N}` with no format spec, calls `PyObject_Str()` on the argument. `PyObject_Str(unicode_obj)` → `PyUnicode_AsEncodedString(obj, NULL, NULL)` → uses `sys.getdefaultencoding()` which is ALWAYS `'ascii'` in Python 2.

```python
# This FAILS with UnicodeEncodeError('ascii', ...)
"    [{0}] {1}".format(1, u'子')  # str.format(unicode)
#                       ^^^^^^^^^
# str(u'子') -> u'子'.encode('ascii') -> BOOM

# This WORKS
u"    [{0}] {1}".format(1, u'子')  # unicode.format(unicode)
# No str() conversion needed — everything stays unicode
```

### The Complete Chain (all three levels must be right)

```python
# Level 1: str.format(unicode) → Python 2 calls str(unicode) → ascii encode → BOOM
arcpy.AddMessage("Result: {0}".format(unicode_name))        # BROKEN

# Level 2: unicode.format(unicode) → OK, but AddMessage gets unicode → BOOM
arcpy.AddMessage(u"Result: {0}".format(unicode_name))       # STILL BROKEN

# Level 3: u"" format + _msg() → CORRECT
arcpy.AddMessage(_msg(u"Result: {0}".format(unicode_name))) # CORRECT
```

**Level 1 fix**: All format strings that may receive unicode args MUST use `u"..."` prefix.
**Level 2 fix**: Every `arcpy.AddMessage/AddError/AddWarning` call MUST go through `_msg()`.
**Level 3 fix**: Every arcpy function arg MUST go through `_to_sys()` when it may be unicode.

## Encoding Boundary Strategy

```
                    +-----------+
  GetParameterAsText |  str/unicode |  raw input
        |            +-----------+
        | _to_uni()
        v
    unicode  <---- all internal string ops (format, join, basename, split, etc.)
        |
        | _to_sys() / _msg()
        v
    sys str  <---- all arcpy calls (GP functions, AddMessage, AddError, AddWarning)
```

One golden path: unicode inside, sys str at the boundary.

## Complete Safe String Helpers

```python
import sys

# Encoding setup (MUST use this guard, not 'or mbcs')
_SYS_ENC = sys.getfilesystemencoding()
if not _SYS_ENC or _SYS_ENC.lower() in ('ascii', 'us-ascii', 'ansi_x3.4-1968'):
    _SYS_ENC = 'mbcs'


def _to_uni(val):
    """Normalize any arcpy value to safe unicode.

    Use for: GetParameterAsText(), cursor field values,
             any value from arcpy that might be GBK str or unicode.
    """
    if val is None:
        return u""
    if isinstance(val, unicode):
        return val
    if isinstance(val, str):
        try:
            return val.decode(_SYS_ENC)  # GBK -> unicode
        except Exception:
            try:
                return val.decode("utf-8")
            except Exception:
                return val.decode("utf-8", "replace")
    return unicode(val)


def _to_sys(val):
    """Encode unicode to system-encoding str for arcpy function arguments.

    Use for: ALL arguments passed to arcpy geoprocessing functions
             (Erase_analysis, Intersect_analysis, Describe, Exists, etc.)
    """
    if isinstance(val, unicode):
        try:
            return val.encode(_SYS_ENC)
        except Exception:
            return val.encode("utf-8")
    return str(val) if val is not None else ""


def _msg(msg):
    """Encode message to system-encoding str for arcpy UI functions.

    Use for: EVERY arcpy.AddMessage(), arcpy.AddError(), arcpy.AddWarning() call.
    The message itself is built with u"..." format strings (unicode),
    and this function encodes it at the boundary.
    """
    if isinstance(msg, unicode):
        try:
            return msg.encode(_SYS_ENC)
        except Exception:
            return msg.encode("utf-8")
    return msg if isinstance(msg, str) else str(msg)
```

### Usage pattern

```python
# Always: _to_uni at entry
in_fc = _to_uni(arcpy.GetParameterAsText(0))

# Always: unicode internally, u"" for format strings
msg = u"Processing: {0} features in {1}".format(count, in_fc)

# Always: _msg() for arcpy UI
arcpy.AddMessage(_msg(msg))

# Always: _to_sys() for arcpy function args
arcpy.Erase_analysis(_to_sys(in_fc), _to_sys(erase_fc), _to_sys(out_fc))
```

## Safe Unicode Construction

Never put Chinese characters in source. Use `unichr()` with codepoints:

```python
_w = lambda *cps: u"".join(unichr(c) for c in cps)

# General ArcGIS vocabulary
CHU_LI    = _w(0x5904, 0x7406)               # 处理
WAN_CHENG = _w(0x5B8C, 0x6210)               # 完成
SHI_BAI   = _w(0x5931, 0x8D25)               # 失败
CHENG_GONG= _w(0x6210, 0x529F)               # 成功
CUO_WU    = _w(0x9519, 0x8BEF)               # 错误
JING_GAO  = _w(0x8B66, 0x544A)               # 警告
SHU_RU    = _w(0x8F93, 0x5165)               # 输入
SHU_CHU   = _w(0x8F93, 0x51FA)               # 输出
ZI_DUAN   = _w(0x5B57, 0x6BB5)               # 字段
YAO_SU    = _w(0x8981, 0x7D20)               # 要素
TU_CENG   = _w(0x56FE, 0x5C42)               # 图层
BIAO      = _w(0x8868)                        # 表
DU_QU     = _w(0x8BFB, 0x53D6)               # 读取
XIE_RU    = _w(0x5199, 0x5165)               # 写入
SHENG_CHENG = _w(0x751F, 0x6210)             # 生成
CHUANG_JIAN = _w(0x521B, 0x5EFA)             # 创建
SHAN_CHU  = _w(0x5220, 0x9664)               # 删除
GONG      = _w(0x5171)                        # 共
TIAO      = _w(0x6761)                        # 条
JI_LU     = _w(0x8BB0, 0x5F55)               # 记录
GE        = _w(0x4E2A)                        # 个

# Common message templates
MSG_DONE  = WAN_CHENG + u"。共{}" + TIAO + JI_LU + u"。"
# 完成。共{}条记录。
MSG_FAIL  = SHI_BAI + u"：{}"
# 失败：{}
MSG_START = _w(0x6B63, 0x5728)  # 正在
```

## Why `repr(e)` not `str(e)`

`str(e)` on a `UnicodeEncodeError` may itself fail with another encoding error. `repr(e)` always returns ASCII-safe output.

## `str` method vs `unicode` argument — implicit ascii decode

Python 2 `str` methods (`.endswith()`, `.startswith()`, `in` operator, `==`) trigger `str.decode(sys.getdefaultencoding())` when the argument is `unicode`.  `getdefaultencoding()` is ALWAYS `'ascii'` in Python 2.  If the `str` contains GBK bytes, this raises `UnicodeDecodeError`.

```python
path = u"C:\\新建文件夹\\data.gdb"
path_str = path.encode('gbk')  # GBK str

# BROKEN — str.endswith(unicode) -> str.decode('ascii') -> BOOM
path_str.endswith(u".gdb")                 # UnicodeDecodeError('ascii', ...)

# BROKEN — same mechanism
path_str == u"something"                   # may UnicodeDecodeError
u"prefix_" + path_str                      # str.decode('ascii') on path_str

# CORRECT — normalize to unicode first
path_str.decode('gbk').endswith(u".gdb")   # OK
```

**Rule: never call `str` methods with `unicode` arguments when the `str` may contain non-ASCII bytes.  Normalize to `unicode` first with `_to_uni()`.**

This is distinct from the `str.format(unicode)` trap — same root cause (Python 2 implicit ascii encode/decode), different trigger.

## GBK Re-Save (Last Resort)

If Chinese in source is unavoidable, the user can:
1. Write the file
2. Open in Windows Notepad
3. File → Save As → Encoding: ANSI
4. This converts UTF-8 → GBK
5. ArcGIS can then read it

This is fragile and not recommended. Pure ASCII source is the reliable approach.

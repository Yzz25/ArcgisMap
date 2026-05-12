# ArcGIS 10.2 Encoding Guide

## The Core Problem

ArcGIS 10.2 runs on Python 2.7. On Chinese Windows, the system encoding is GBK (CP936). The Claude Code Write/Edit tools produce UTF-8 files.

When ArcGIS loads a `.pyt` or embedded `.py` script, it reads raw bytes using the system ANSI codepage (GBK). It does NOT respect the `# -*- coding: utf-8 -*-` PEP 263 declaration.

UTF-8 multi-byte sequences for Chinese characters, when misinterpreted as GBK, produce invalid byte sequences → `SyntaxError`.

## Solution Matrix

| Scenario | Approach |
|----------|----------|
| .pyt with Chinese labels | Label/displayName must be ASCII. User must accept English UI. |
| .tbx .py script (embedded) | Source must be pure ASCII. Runtime Chinese via `unichr()`. |
| .tbx .py script (external file) | Python's `# coding: utf-8` works for direct imports. But safer to keep pure ASCII. |
| Messages to user in Chinese | Build at runtime using `unichr()` with hex codepoints (`_w()` helper). |
| Chinese field values from data | `_to_uni()` converts GBK str to unicode safely. |

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

## `_to_uni()` — The Essential Helper

```python
import sys
_SYS_ENC = sys.getfilesystemencoding()  # cp936 on Chinese Windows

def _to_uni(val):
    """Convert anything from arcpy to safe unicode."""
    if val is None:
        return u""
    if isinstance(val, unicode):
        return val
    if isinstance(val, str):
        try:
            return val.decode(_SYS_ENC)  # GBK → unicode
        except Exception:
            return val.decode("utf-8", "replace")  # fallback
    return unicode(val)
```

When to use:
- Wrapping ALL `arcpy.GetParameterAsText()` results
- Wrapping ALL cursor field values from `SearchCursor`
- Before any string concatenation or `.format()` involving arcpy data

## Why `repr(e)` not `str(e)`

`str(e)` on a `UnicodeEncodeError` may itself fail with another encoding error. `repr(e)` always returns ASCII-safe output.

## GBK Re-Save (Last Resort)

If Chinese in source is unavoidable, the user can:
1. Write the file
2. Open in Windows Notepad
3. File → Save As → Encoding: ANSI
4. This converts UTF-8 → GBK
5. ArcGIS can then read it

This is fragile and not recommended. Pure ASCII source is the reliable approach.

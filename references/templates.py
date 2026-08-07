"""
ArcGIS 10.2 templates -- copy the block you need, do NOT rewrite.

KEEP THIS FILE PURE ASCII. Everything in a delivered .py/.pyt must be
ASCII too (see SKILL.md Rule Zero). Chinese output is built at runtime
with unichr() (see encoding-guide.md).
"""


# ======================================================================
# 1) PYTHON TOOLBOX (.pyt) TEMPLATE -- official standard structure
#
#    Toolbox class name = the .pyt filename
#    Tool class name    = the tool name shown in ArcCatalog
#
#    All six methods are standard. isLicensed() returning False disables
#    the tool (e.g. when a required extension is unavailable).
# ======================================================================

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
        params = None
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
        MUST wrap in try-except -- uncaught exception = silent red X."""
        try:
            pass
        except Exception:
            pass
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        return


# ======================================================================
# 2) SCRIPT TOOL (.py) TEMPLATE -- used by a .tbx script tool
#
#    Includes the encoding guard + _to_uni/_to_sys/_msg helpers,
#    message constants, try/except/finally cleanup. Everything is
#    already compliant with this skill's rules.
# ======================================================================

# -*- coding: utf-8 -*-
import arcpy
import os
import sys

# ---- encoding (MUST use this exact guard, not 'or mbcs') ----
_SYS_ENC = sys.getfilesystemencoding()
if not _SYS_ENC or _SYS_ENC.lower() in ('ascii', 'us-ascii', 'ansi_x3.4-1968'):
    _SYS_ENC = 'mbcs'


def _to_uni(val):
    """Normalize any arcpy value to safe unicode.

    Use for: GetParameterAsText(), cursor field values, any value
             from arcpy that might be GBK str or unicode.
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
    """Encode unicode to system-encoding str for arcpy function args.

    Use for: ALL arguments passed to arcpy geoprocessing functions
             (Erase_analysis, Intersect_analysis, Describe, Exists...).
    """
    if isinstance(val, unicode):
        try:
            return val.encode(_SYS_ENC)
        except Exception:
            return val.encode("utf-8")
    return str(val) if val is not None else ""


def _msg(msg):
    """Encode message to system-encoding str for arcpy UI functions.

    Use for: EVERY arcpy.AddMessage/AddError/AddWarning call.
    Build the message with u"..." format strings, encode here.
    """
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

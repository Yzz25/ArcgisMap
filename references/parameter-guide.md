# ArcGIS 10.2 Parameter Reference

## Data Types

| English | Chinese UI | `datatype` string | Notes |
|---------|-----------|-------------------|-------|
| Feature Layer | 要素图层 | `GPFeatureLayer` | Input feature class or layer |
| Table | 表 | `GPTableView` | Input table |
| Raster Layer | 栅格图层 | `GPRasterLayer` | Input raster |
| Field | 字段 | `Field` | Field from input; needs `parameterDependencies` |
| String | 字符串 | `GPString` | Text value |
| Long | 长整型 | `GPLong` | Integer |
| Double | 双精度 | `GPDouble` | Float |
| Boolean | 布尔型 | `GPBoolean` | True/False |
| Workspace | 工作空间 | `DEWorkspace` | GDB or folder |
| Feature Class | 要素类 | `DEFeatureClass` | Output feature class |
| SQL Expression | SQL表达式 | `GPSQLExpression` | Where clause |
| Value Table | 值表 | `GPValueTable` | Multi-row table input |
| Composite Layer | 复合图层 | `GPComposite` | Non-standard |
| Linear Unit | 线性单位 | `GPLinearUnit` | Distance with unit |
| Spatial Reference | 空间参考 | `GPSpatialReference` | Coordinate system |

## Parameter Object — Complete API

### Constructor

```python
arcpy.Parameter(
    displayName="Label",     # Visible label (ASCII only for .pyt)
    name="param_name",       # Internal name used by parameterDependencies
    datatype="GPFeatureLayer",
    parameterType="Required",  # Required | Optional | Derived
    direction="Input",         # Input | Output
    multiValue=False,          # True = accepts list of values
    category="",               # Grouping label (ASCII only)
    symbology=None,            # Path to .lyr for symbology
)
```

### parameterType

| Value | Chinese UI | Behavior |
|-------|-----------|----------|
| `Required` | 必需 | Must have a value; tool shows red dot |
| `Optional` | 可选 | May be blank |
| `Derived` | 派生 | Hidden from dialog; output-only; populated by tool |

Derived parameters do NOT appear in the tool dialog. They exist to pass output to ModelBuilder chains. Set `schema.clone = True` on the source input parameter.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | str | Internal identifier; used by `parameterDependencies` |
| `displayName` | str | Visible label in tool dialog |
| `datatype` | str | Data type string (see table above) |
| `parameterType` | str | `Required` / `Optional` / `Derived` |
| `direction` | str | `Input` / `Output` |
| `value` | varies | Current value (native type: int for Long, str for String, etc.) |
| `valueAsText` | str | String representation of value (always safe to read) |
| `altered` | bool | True if user changed value from default |
| `enabled` | bool | True = parameter is interactive; False = grayed out |
| `hasBeenValidated` | bool | True after internal validation ran |
| `category` | str | Group label for collapsible sections |
| `schema` | object | For Derived outputs; set `schema.clone = True` |
| `filter` | object | Filter definition (see Filter Types below) |
| `message` | str | Tool execution status message (read-only) |
| `symbology` | str | Path to .lyr file for result symbology |
| `multiValue` | bool | True = accepts list |
| `parameterDependencies` | list | `[other_param.name]` — links Field to source layer |
| `columns` | object | For GPValueTable; defines column schema |

### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `setErrorMessage` | `(msg: str)` | Red error; blocks execution; clears previous message |
| `setWarningMessage` | `(msg: str)` | Yellow warning; allows execution; clears previous message |
| `setIDMessage` | `(msg: str)` | Informational (blue) message; clears previous message |
| `clearMessage` | `()` | Removes any error/warning/info message |
| `hasError` | `() -> bool` | True if parameter has an error message set |
| `hasWarning` | `() -> bool` | True if parameter has a warning message set |
| `isInputValueDerived` | `() -> bool` | True if value came from upstream (ModelBuilder chain) |

**Message behavior:** Setting any message replaces the previous one. Only one message active per parameter at a time.

**Note on `value` vs `valueAsText`:**
- `value` returns native type — `int` for Long, `str` for String, geometry object for Feature Layer. Can be `None`.
- `valueAsText` always returns `str`. Safer for string operations. Can be empty string `""` for blank parameters.
- For Long params with no value, `parameters[0].value` returns `0` (not None), but `valueAsText` returns `""`.

## Filter Types

### 1. ValueList

Constrains parameter to a fixed set of string options.

```python
p.filter.type = "ValueList"
p.filter.list = ["Option A", "Option B", "Option C"]
```

Used for: String parameters with predefined choices.

### 2. Range

Constrains numeric parameter to a min/max range.

```python
p.filter.type = "Range"
p.filter.list = [1, 20]  # [min, max]
```

Used for: Long, Double parameters.

### 3. FeatureClass

Constrains input layer to specific geometry types.

```python
p.filter.type = "FeatureClass"
p.filter.list = ["Point", "Polyline", "Polygon", "Multipoint", "Annotation"]
```

Used for: Feature Layer, Feature Class parameters.

### 4. File

Constrains to specific file extensions.

```python
p.filter.type = "File"
p.filter.list = ["lyr", "pdf", "png"]
```

Used for: File input parameters.

### 5. Field

Constrains to specific field types. Applied automatically when `datatype="Field"` with `parameterDependencies`.

```python
p.filter.type = "Field"
p.filter.list = ["Short", "Long", "Float", "Double", "Text", "Date", "OID", "Geometry", "BLOB", "Raster", "GUID"]
```

Used for: Field parameters.

### 6. Workspace

Constrains to workspace types.

```python
p.filter.type = "Workspace"
p.filter.list = ["FileSystem", "LocalDatabase", "RemoteDatabase"]
```

Used for: Workspace parameters.

## Field Dependencies

Field parameters MUST declare `parameterDependencies` to link to their source Feature Layer or Table parameter:

```python
p0 = arcpy.Parameter(
    displayName="Input Features",
    name="in_features",
    datatype="GPFeatureLayer",
    parameterType="Required",
    direction="Input",
)

p1 = arcpy.Parameter(
    displayName="Group Field",
    name="group_field",
    datatype="Field",
    parameterType="Required",
    direction="Input",
)
p1.parameterDependencies = [p0.name]  # links to "in_features"
```

Without this, the field dropdown will be empty.

## GPValueTable (Value Table)

A multi-row table parameter where each column has a defined data type.

```python
p = arcpy.Parameter(
    displayName="Field Map",
    name="field_map",
    datatype="GPValueTable",
    parameterType="Required",
    direction="Input",
)

# Define columns
p.columns = [
    ["GPFeatureLayer", "Input Features"],   # [datatype, heading]
    ["Field", "Source Field"],              # [datatype, heading]
    ["GPString", "Target Name"],            # [datatype, heading]
]
```

**Limitation:** .pyt does NOT support `GPValueTable` with `GPFeatureLayer` columns. Use .tbx for this combination.

## multiValue

Allows a parameter to accept multiple values (e.g., multiple fields, multiple layers).

```python
p = arcpy.Parameter(
    displayName="Fields to Process",
    name="fields",
    datatype="Field",
    parameterType="Required",
    direction="Input",
    multiValue=True,
)
p.parameterDependencies = [p0.name]
```

Access multi-values in execute:

```python
# valueAsText returns semicolon-separated string
field_list = parameters[1].valueAsText.split(";")

# value returns a list of native values
values = parameters[1].value  # list of field names
```

## Derived Output Parameters

For tools that modify input in-place (Add Field, Calculate Field, etc.), add a Derived output so ModelBuilder knows the output exists:

```python
param_in = arcpy.Parameter(
    displayName="Input Features",
    name="in_features",
    datatype="GPFeatureLayer",
    parameterType="Required",
    direction="Input",
)

param_out = arcpy.Parameter(
    displayName="Output Features",
    name="out_features",
    datatype="GPFeatureLayer",
    parameterType="Derived",
    direction="Output",
)
param_out.parameterDependencies = [param_in.name]
param_out.schema.clone = True  # copies schema from input
```

Derived parameters are hidden from the tool dialog but appear in ModelBuilder chains.

## category — Parameter Grouping

Group related parameters under collapsible sections:

```python
p0.category = "Input"       # Group: Input
p1.category = "Input"
p2.category = "Settings"    # Group: Settings
p3.category = "Settings"
```

Categories appear as collapsible sections in the tool dialog. Must be ASCII for .pyt.

## defaultEnvironmentName

Set default workspace for the tool (used for scratch data, output resolution, extent, etc.):

```python
p = arcpy.Parameter(
    displayName="Input Features",
    name="in_features",
    datatype="GPFeatureLayer",
    parameterType="Required",
    direction="Input",
)
p.defaultEnvironmentName = "workspace"
```

Common environment names: `workspace`, `scratchWorkspace`, `extent`, `cellSize`, `outputCoordinateSystem`, `mask`.

## symbology

Set result symbology from a layer file:

```python
p.symbology = r"C:\path\to\symbology.lyr"
```

## Validation — The Full Picture

### Method call order

For each parameter change, ArcGIS calls:

```
updateParameters(parameters)  →  internal validation  →  updateMessages(parameters)
```

### updateParameters — adjust parameter state

- Modify parameter properties (enabled, value, filter) in response to other parameter changes
- **Set default values here**, NOT in updateMessages
- Use `altered` to avoid overwriting user input:

```python
def updateParameters(self, parameters):
    if parameters[0].value and not parameters[1].altered:
        parameters[1].value = "computed_default"

    if parameters[3].valueAsText == "From Field":
        parameters[4].enabled = False
        parameters[5].enabled = True
    else:
        parameters[4].enabled = True
        parameters[5].enabled = False
```

### internal validation

ArcGIS runs its own validation after `updateParameters`. You cannot control or observe this directly. It sets `hasBeenValidated`.

### updateMessages — add warnings/errors

- Run AFTER internal validation
- **Do NOT set parameter values here** — values set here are NOT validated
- **MUST wrap in try-except** — uncaught exception = silent red X on tool
- Use `setErrorMessage` (blocks execution) or `setWarningMessage` (allows execution)

```python
def updateMessages(self, parameters):
    try:
        if parameters[3].valueAsText == "From Field" and not parameters[5].value:
            parameters[5].setErrorMessage("Prefix field required.")
        elif parameters[0].value and not parameters[1].value:
            parameters[1].setWarningMessage("Using all features (no grouping).")
    except Exception:
        pass
```

### Validation don'ts

1. **Don't set values in `updateMessages`** — values won't be validated by internal validation
2. **Don't use catalog-path methods** — `ListFields`, `ListFeatureClasses`, etc. crash when the dataset doesn't exist yet (ModelBuilder validation). Use `arcpy.Describe()` instead:

```python
# SAFE in validation:
desc = arcpy.Describe(parameters[0].value)
field_names = [f.name for f in desc.fields]  # works even during validation

# UNSAFE in validation:
arcpy.ListFields(parameters[0].value)  # may crash
```

3. **Don't throw unhandled exceptions** — always wrap `updateMessages` body in try-except
4. **Don't use Chinese in source** — violates GBK encoding constraint

## .tbx Script Tool Parameter Order

Parameters passed to the .py script follow the order in the .tbx tool properties table. Access them by index:

```python
in_features = arcpy.GetParameterAsText(0)    # 1st parameter
group_field = arcpy.GetParameterAsText(1)    # 2nd parameter
target_field = arcpy.GetParameterAsText(2)   # 3rd parameter
num_digits = int(arcpy.GetParameter(6))      # 7th parameter (Long)
```

- `GetParameterAsText()` — returns string (may be unicode for Chinese values)
- `GetParameter()` — returns native type (int for Long, bool for Boolean, etc.)
- Always wrap text results in `_to_uni()`

## .pyt Parameter Construction — Full Example

```python
def getParameterInfo(self):
    # Input features
    p0 = arcpy.Parameter(
        displayName="Input Features",
        name="in_features",
        datatype="GPFeatureLayer",
        parameterType="Required",
        direction="Input",
    )

    # Field (depends on p0)
    p1 = arcpy.Parameter(
        displayName="Group Field",
        name="group_field",
        datatype="Field",
        parameterType="Required",
        direction="Input",
    )
    p1.parameterDependencies = [p0.name]

    # String with ValueList filter
    p2 = arcpy.Parameter(
        displayName="Prefix Source",
        name="prefix_type",
        datatype="GPString",
        parameterType="Required",
        direction="Input",
    )
    p2.filter.type = "ValueList"
    p2.filter.list = ["Fixed", "From Field"]

    # Long with Range filter and default
    p3 = arcpy.Parameter(
        displayName="Number of Digits",
        name="num_digits",
        datatype="GPLong",
        parameterType="Required",
        direction="Input",
    )
    p3.value = 3
    p3.filter.type = "Range"
    p3.filter.list = [1, 20]

    # Derived output
    p4 = arcpy.Parameter(
        displayName="Output Features",
        name="out_features",
        datatype="GPFeatureLayer",
        parameterType="Derived",
        direction="Output",
    )
    p4.parameterDependencies = [p0.name]
    p4.schema.clone = True

    return [p0, p1, p2, p3, p4]
```

## Working with ValueList Parameters

ValueList values configured in the UI (Chinese or English) are returned exactly as entered:

```python
# If .tbx ValueList is "Fixed;From Field"
prefix_type = _to_uni(arcpy.GetParameterAsText(3))
if prefix_type == u"From Field":
    ...

# For Chinese ValueList "手动输入;从字段取值"
# Can't compare with Chinese literal in source (encoding issue)
# Use codepoint detection instead:
if prefix_type and len(prefix_type) > 0 and ord(prefix_type[0]) == 0x4ECE:
    # 0x4ECE = "从" (first char of "从字段取值")
    use_field_prefix = True
```

## Cursor Tokens

| Token | Returns | Notes |
|-------|---------|-------|
| `"OID@"` | int | Object ID |
| `"SHAPE@"` | Geometry object | Full geometry |
| `"SHAPE@XY"` | (x, y) tuple | Centroid for polygons, midpoint for lines |
| `"SHAPE@LENGTH"` | double | Length (lines/polygons) |
| `"SHAPE@AREA"` | double | Area (polygons) |
| `"SHAPE@WKT"` | str | Well-Known Text |
| `"SHAPE@JSON"` | str | Esri JSON |
| `"FieldName"` | varies | Named field value |

```python
# SearchCursor — field list + optional where clause
arcpy.da.SearchCursor(fc, ["OID@", "Field1", "SHAPE@XY"])
arcpy.da.SearchCursor(fc, ["*"], where_clause="GROUP = 'A'")

# UpdateCursor — requires fields to update
arcpy.da.UpdateCursor(fc, ["OID@", "TargetField"])

# InsertCursor — for creating new features
arcpy.da.InsertCursor(fc, ["Field1", "Field2", "SHAPE@XY"])
```

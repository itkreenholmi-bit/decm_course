# Superset SQL Snippets

This file collects copy-paste SQL snippets for common chart customizations in Superset.

Dataset used in examples:
- `mart.v_air_quality_hourly`

## Month Names In Logical Order (Space-Padded Label)

Use this as a calculated column when a chart/pivot only supports alphabetic sorting on labels.

```sql
CASE
WHEN month_name = 'January'   THEN '           Jan'
WHEN month_name = 'February'  THEN '          Feb'
WHEN month_name = 'March'     THEN '         Mar'
WHEN month_name = 'April'     THEN '        Apr'
WHEN month_name = 'May'       THEN '       May'
WHEN month_name = 'June'      THEN '      Jun'
WHEN month_name = 'July'      THEN '     Jul'
WHEN month_name = 'August'    THEN '    Aug'
WHEN month_name = 'September' THEN '   Sep'
WHEN month_name = 'October'   THEN '  Oct'
WHEN month_name = 'November'  THEN ' Nov'
WHEN month_name = 'December'  THEN 'Dec'
ELSE month_name
END
```

## Weekday Names In Logical Order (Space-Padded Label)

Use this as a calculated column when weekday labels would otherwise sort alphabetically.

```sql
CASE
WHEN day_name = 'Mon' THEN '      Mon'
WHEN day_name = 'Tue' THEN '     Tue'
WHEN day_name = 'Wed' THEN '    Wed'
WHEN day_name = 'Thu' THEN '   Thu'
WHEN day_name = 'Fri' THEN '  Fri'
WHEN day_name = 'Sat' THEN ' Sat'
WHEN day_name = 'Sun' THEN 'Sun'
ELSE day_name
END
```

## Wind Direction Metrics (8-Sector Radar)

Use these as custom metrics for charts where each metric represents one wind direction.

```sql
AVG(CASE WHEN wind_sector = 'N'  THEN ws10 ELSE NULL END)
AVG(CASE WHEN wind_sector = 'NE' THEN ws10 ELSE NULL END)
AVG(CASE WHEN wind_sector = 'E'  THEN ws10 ELSE NULL END)
AVG(CASE WHEN wind_sector = 'SE' THEN ws10 ELSE NULL END)
AVG(CASE WHEN wind_sector = 'S'  THEN ws10 ELSE NULL END)
AVG(CASE WHEN wind_sector = 'SW' THEN ws10 ELSE NULL END)
AVG(CASE WHEN wind_sector = 'W'  THEN ws10 ELSE NULL END)
AVG(CASE WHEN wind_sector = 'NW' THEN ws10 ELSE NULL END)
```


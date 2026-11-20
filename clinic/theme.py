"""StrokeScope's palette and type: a hospital laboratory report. White report sheets on a cool grey desk, a maroon
letterhead, monospaced results with H/L flags and reference intervals. Tier colours are status colours and always come
with a label and an icon."""

BG = "#eceef1"          # the desk the report sheets lie on
PANEL = "#ffffff"       # report sheet
LINE = "#d5d9df"
RULE = "#1d2330"        # heavy table rules
INK = "#1d2330"
MUTED = "#535b69"
FAINT = "#6e7685"
SHADE = "#f5f6f8"       # alternate table rows, reference columns

BRAND = "#7b2343"       # letterhead maroon: the product, the patient's marker, the model's series (9.6:1 on white)
BRAND_DARK = "#5c1a32"
BRAND_SOFT = "#f8eef2"
TEAL = "#0f7a6e"        # second series (lowers risk, found)
ORANGE = "#b8650a"      # third series

TIER = {"Routine": "#2b7a3d", "Check": "#a86400", "Priority": "#c62828"}
TIER_SOFT = {"Routine": "#eaf5ec", "Check": "#fdf3e1", "Priority": "#fdecec"}
TIER_ICON = {"Routine": "check_circle", "Check": "visibility", "Priority": "priority_high"}
TIER_TEXT = {
    "Routine": "Below the screening line. Routine care; re-screen when something changes.",
    "Check": "At or above the screening line. Offer a stroke risk check.",
    "Priority": "At or above the high-risk line. Check first.",
}
FLAG_HIGH, FLAG_LOW = "#c62828", "#1f5fa8"

RAISES = "#c62828"
LOWERS = "#0f7a6e"

SERIF = "'Libre Franklin', 'Segoe UI', sans-serif"   # headings (name kept for the charts module)
SANS = "'Libre Franklin', 'Segoe UI', sans-serif"
MONO = "'Roboto Mono', Consolas, monospace"

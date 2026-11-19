"""StrokeScope's palette and type: a light clinical report (paper background, white charts, indigo brand).
Tier colours are status colours and always come with a label and an icon."""

BG = "#f4f5f9"
PANEL = "#ffffff"
LINE = "#dde1ea"
INK = "#1b2140"
MUTED = "#5a6378"
FAINT = "#8a92a6"

BRAND = "#4f46e5"       # indigo: the product, the patient's marker, the model's series
BRAND_DARK = "#3730a3"
BRAND_SOFT = "#eef0ff"
TEAL = "#0f9b8e"        # second series (lowers risk, found)
ORANGE = "#d97706"      # third series

TIER = {"Routine": "#2f855a", "Check": "#b7791f", "Priority": "#c53030"}
TIER_SOFT = {"Routine": "#e9f5ee", "Check": "#fbf3e2", "Priority": "#fbeaea"}
TIER_ICON = {"Routine": "check_circle", "Check": "visibility", "Priority": "priority_high"}
TIER_TEXT = {
    "Routine": "Below the screening line. Routine care; re-screen when something changes.",
    "Check": "At or above the screening line. Offer a stroke risk check.",
    "Priority": "At or above the high-risk line. Check first.",
}

RAISES = "#c53030"
LOWERS = "#0f9b8e"

SERIF = "'Source Serif 4', Georgia, serif"
SANS = "'IBM Plex Sans', 'Segoe UI', sans-serif"
MONO = "'IBM Plex Mono', Consolas, monospace"

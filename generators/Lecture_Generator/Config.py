from reportlab.lib.units import inch

# OpenRouter model
OPENROUTER_MODEL = "z-ai/glm-4.5-air:free"

# Slide page size: 16:9 widescreen (10 x 5.625 inches)

SLIDE_WIDTH  = 10 * inch
SLIDE_HEIGHT = 5.625 * inch
SLIDE_SIZE   = (SLIDE_WIDTH, SLIDE_HEIGHT)

SLIDE_MARGIN_H = 0.55 * inch   # left / right
SLIDE_MARGIN_T = 0.45 * inch   # top
SLIDE_MARGIN_B = 0.35 * inch   # bottom

# Source-type label map
FILE_TYPE_SOURCE_LABELS = {
    "website": "website",
    "video":   "video",
    "pptx":    "presentation",
    "audio":   "audio",
    "pdf":     "pdf",
    "docx":    "docx",
    "image":   "image",   # user-supplied image: placed on the right side of a slide
}

# Image layout constants
# Fraction of the content-area width reserved for the right-hand image column.
# The text column gets (1 - IMAGE_COL_RATIO) of the width.
IMAGE_COL_RATIO = 0.38

# Horizontal gap (pts) between the text column and the image column.
IMAGE_COL_GAP = 14
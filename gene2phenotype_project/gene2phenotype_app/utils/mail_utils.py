from io import BytesIO

from django.contrib.staticfiles.finders import find
from PIL import Image

LOGO_CID = "g2p_logo"
_LOGO_STATIC_PATH = "gene2phenotype_app/G2P-ALL.png"

# Must match the width/height set on the <img> tag in the email templates.
LOGO_DISPLAY_PX = 72


def attach_g2p_logo(message):
    """
    Attach the G2P logo to an EmailMessage as an inline (CID) image.
    Templates reference it via <img src="cid:g2p_logo" ...>.
    Embedding the image avoids relying on a publicly reachable static URL,
    which email clients can't resolve anyway.
    """
    logo_path = find(_LOGO_STATIC_PATH)
    if not logo_path:
        return

    with Image.open(logo_path) as img:
        resized = img.convert("RGBA").resize(
            (LOGO_DISPLAY_PX, LOGO_DISPLAY_PX), Image.LANCZOS
        )
        buffer = BytesIO()
        resized.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()

    message.add_related(image_bytes, maintype="image", subtype="png", cid=f"<{LOGO_CID}>")

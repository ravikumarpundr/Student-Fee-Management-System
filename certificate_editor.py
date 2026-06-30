"""Certificate editor — launches the local web editor; PDF logic lives in certificate_pdf.py."""
from certificate_pdf import HAS_PYMUPDF
from certificate_web_server import open_certificate_web_editor

open_windows = []


def open_certificate_editor():
    """Open the certificate editor in the default browser (localhost)."""
    url = open_certificate_web_editor()
    return url


__all__ = [
    "open_certificate_editor",
    "open_windows",
    "HAS_PYMUPDF",
]

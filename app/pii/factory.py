from app.config import Settings
from app.pii.base import BasePIIFilter


def get_pii_filter(settings: Settings) -> BasePIIFilter:
    if settings.pii_filter == "presidio":
        from app.pii.presidio_filter import PresidioFilter
        return PresidioFilter()
    from app.pii.noop_filter import NoopFilter
    return NoopFilter()

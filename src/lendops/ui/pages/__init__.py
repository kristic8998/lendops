"""Page factories — the shell looks pages up here by module id."""

from __future__ import annotations

from .collecta_page import CollectaPage
from .home_page import HomePage
from .kyc_page import KycPage
from .policysim_page import PolicySimPage

PAGE_FACTORIES = {
    "home": HomePage,
    "collecta": CollectaPage,
    "policysim": PolicySimPage,
    "kyc": KycPage,
}

__all__ = ["PAGE_FACTORIES"]

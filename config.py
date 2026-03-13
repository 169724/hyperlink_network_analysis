"""Konfiguracja projektu analizy sieci hyperlinkowej."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

KATALOG_BAZOWY = Path(__file__).resolve().parent


@dataclass(slots=True, frozen=True)
class KonfiguracjaAnalizy:
    """Ustawienia sterujące pobieraniem stron, analizą i zapisem wyników."""

    plik_wejsciowy: Path = KATALOG_BAZOWY / "input_urls.txt"
    katalog_wyjsciowy: Path = KATALOG_BAZOWY / "output"

    tylko_ta_sama_domena: bool = True
    maksymalna_liczba_stron: int = 30
    maksymalna_liczba_linkow_na_strone: int | None = 200

    timeout_zadania: int = 10
    user_agent: str = "AnalizatorSieciHiperlinkowej/3.0 (projekt akademicki z GUI)"
    opoznienie_miedzy_zadaniami: float = 0.2
    weryfikuj_ssl: bool = True
    podazaj_za_przekierowaniami: bool = True

    top_n_pagerank: int = 10
    rozmiar_rysunku_grafu: tuple[int, int] = (14, 10)
    ziarno_losowe: int = 42


USTAWIENIA = KonfiguracjaAnalizy()

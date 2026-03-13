"""Moduł odpowiedzialny za budowę grafu skierowanego."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import networkx as nx
import pandas as pd

from config import KonfiguracjaAnalizy
from scraper import ZbieraczStron
from utils import czy_w_obrebie_domeny, normalizuj_url, pobierz_domene

CallbackLogu = Callable[[str], None]
CallbackPostepu = Callable[[int, int, str], None]


@dataclass(slots=True)
class ElementKolejki:
    """Element kolejki crawlera."""

    url: str
    domena_zakresu: str | None


@dataclass(slots=True)
class PodsumowanieZbierania:
    """Podsumowanie etapu pobierania stron i budowy grafu."""

    liczba_adresow_startowych: int
    liczba_zadan_http: int
    liczba_przeanalizowanych_stron_html: int
    liczba_odkrytych_wezlow: int
    liczba_odkrytych_krawedzi: int
    liczba_bledow_pobierania: int


def _loguj(callback_logu: CallbackLogu | None, wiadomosc: str) -> None:
    if callback_logu:
        callback_logu(wiadomosc)


def _raportuj_postep(
    callback_postepu: CallbackPostepu | None,
    aktualny_stan: int,
    maksymalny_stan: int,
    aktualny_url: str,
) -> None:
    if callback_postepu:
        callback_postepu(aktualny_stan, maksymalny_stan, aktualny_url)


def zbuduj_graf_hiperlinkow(
    adresy_startowe: list[str],
    zbieracz: ZbieraczStron,
    konfiguracja: KonfiguracjaAnalizy,
    callback_logu: CallbackLogu | None = None,
    callback_postepu: CallbackPostepu | None = None,
) -> tuple[nx.DiGraph, PodsumowanieZbierania]:
    """Buduje graf skierowany na podstawie hyperlinków znalezionych na stronach WWW."""
    graf = nx.DiGraph()

    kolejka: deque[ElementKolejki] = deque()
    adresy_w_kolejce: set[str] = set()
    odwiedzone_adresy: set[str] = set()

    znormalizowane_adresy_startowe: list[str] = []

    for surowy_url in adresy_startowe:
        znormalizowany = normalizuj_url(surowy_url, surowy_url)
        if znormalizowany is None or znormalizowany in adresy_w_kolejce:
            continue

        domena_zakresu = (
            pobierz_domene(znormalizowany) if konfiguracja.tylko_ta_sama_domena else None
        )
        kolejka.append(ElementKolejki(url=znormalizowany, domena_zakresu=domena_zakresu))
        adresy_w_kolejce.add(znormalizowany)
        znormalizowane_adresy_startowe.append(znormalizowany)
        graf.add_node(znormalizowany)

    liczba_zadan_http = 0
    liczba_przeanalizowanych_stron_html = 0
    liczba_bledow_pobierania = 0

    _loguj(
        callback_logu,
        f"Do kolejki dodano {len(znormalizowane_adresy_startowe)} adresów startowych.",
    )

    while kolejka and liczba_przeanalizowanych_stron_html < konfiguracja.maksymalna_liczba_stron:
        element = kolejka.popleft()
        aktualny_url = element.url

        if aktualny_url in odwiedzone_adresy:
            continue

        odwiedzone_adresy.add(aktualny_url)
        liczba_zadan_http += 1
        _loguj(callback_logu, f"[{liczba_zadan_http}] Pobieranie: {aktualny_url}")
        _raportuj_postep(
            callback_postepu,
            min(liczba_zadan_http, konfiguracja.maksymalna_liczba_stron),
            konfiguracja.maksymalna_liczba_stron,
            aktualny_url,
        )

        wynik_pobrania = zbieracz.pobierz_strone(aktualny_url)

        if wynik_pobrania.blad:
            liczba_bledow_pobierania += 1
            _loguj(callback_logu, f"  Błąd pobierania: {wynik_pobrania.blad}")
            continue

        url_zrodlowy = wynik_pobrania.finalny_url or aktualny_url
        graf.add_node(url_zrodlowy)

        if aktualny_url != url_zrodlowy and graf.has_node(aktualny_url):
            if graf.degree(aktualny_url) == 0:
                graf.remove_node(aktualny_url)

        if konfiguracja.tylko_ta_sama_domena and element.domena_zakresu:
            if not czy_w_obrebie_domeny(url_zrodlowy, element.domena_zakresu):
                _loguj(callback_logu, "  Pominięto po przekierowaniu poza domenę.")
                continue

        if not wynik_pobrania.html:
            _loguj(callback_logu, "  Pominięto zasób, który nie jest dokumentem HTML.")
            continue

        liczba_przeanalizowanych_stron_html += 1
        linki = zbieracz.wyodrebnij_linki(url_zrodlowy, wynik_pobrania.html)
        _loguj(callback_logu, f"  Znaleziono linków: {len(linki)}")

        for link in linki:
            if konfiguracja.tylko_ta_sama_domena and element.domena_zakresu:
                if not czy_w_obrebie_domeny(link, element.domena_zakresu):
                    continue

            graf.add_edge(url_zrodlowy, link)

            if link not in odwiedzone_adresy and link not in adresy_w_kolejce:
                kolejka.append(ElementKolejki(url=link, domena_zakresu=element.domena_zakresu))
                adresy_w_kolejce.add(link)

    podsumowanie = PodsumowanieZbierania(
        liczba_adresow_startowych=len(znormalizowane_adresy_startowe),
        liczba_zadan_http=liczba_zadan_http,
        liczba_przeanalizowanych_stron_html=liczba_przeanalizowanych_stron_html,
        liczba_odkrytych_wezlow=graf.number_of_nodes(),
        liczba_odkrytych_krawedzi=graf.number_of_edges(),
        liczba_bledow_pobierania=liczba_bledow_pobierania,
    )

    _loguj(
        callback_logu,
        (
            "Budowa grafu zakończona. "
            f"Węzły: {podsumowanie.liczba_odkrytych_wezlow}, "
            f"krawędzie: {podsumowanie.liczba_odkrytych_krawedzi}."
        ),
    )
    return graf, podsumowanie


def zapisz_krawedzie_do_csv(graf: nx.DiGraph, sciezka_wyjsciowa: Path) -> None:
    """Zapisuje listę krawędzi grafu do pliku CSV."""
    krawedzie = sorted(graf.edges())
    dataframe = pd.DataFrame(krawedzie, columns=["source", "target"])
    dataframe.to_csv(sciezka_wyjsciowa, index=False)

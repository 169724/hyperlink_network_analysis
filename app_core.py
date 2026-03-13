"""Wspólna logika aplikacji używana przez CLI i GUI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import networkx as nx
import pandas as pd

from analysis import (
    PodsumowanieSieci,
    analizuj_graf,
    zapisz_metryki_wezlow,
    zapisz_podsumowanie_sieci,
)
from config import KonfiguracjaAnalizy
from graph_builder import (
    PodsumowanieZbierania,
    zapisz_krawedzie_do_csv,
    zbuduj_graf_hiperlinkow,
)
from scraper import ZbieraczStron
from utils import skroc_url, utworz_katalog_wyjsciowy, wczytaj_url_z_pliku, wczytaj_url_z_tekstu
from visualization import generuj_wizualizacje

CallbackLogu = Callable[[str], None]
CallbackPostepu = Callable[[int, str], None]


@dataclass(slots=True)
class WynikAnalizy:
    """Kontener przechowujący główne wyniki działania programu."""

    graf: nx.DiGraph
    dataframe_metryk: pd.DataFrame
    podsumowanie_zbierania: PodsumowanieZbierania
    podsumowanie_sieci: PodsumowanieSieci
    katalog_wyjsciowy: Path
    konfiguracja: KonfiguracjaAnalizy
    pliki_wynikowe: dict[str, Path]


def _loguj(callback_logu: CallbackLogu | None, wiadomosc: str) -> None:
    if callback_logu:
        callback_logu(wiadomosc)


def _raportuj_postep(
    callback_postepu: CallbackPostepu | None,
    procent: int,
    opis: str,
) -> None:
    if callback_postepu:
        callback_postepu(max(0, min(100, procent)), opis)


def uruchom_pelna_analize(
    konfiguracja: KonfiguracjaAnalizy,
    adresy_startowe: list[str] | None = None,
    callback_logu: CallbackLogu | None = None,
    callback_postepu: CallbackPostepu | None = None,
) -> WynikAnalizy:
    """Uruchamia cały pipeline projektu i zapisuje wszystkie wyniki na dysk."""
    _raportuj_postep(callback_postepu, 0, "Przygotowanie analizy...")
    utworz_katalog_wyjsciowy(konfiguracja.katalog_wyjsciowy)
    _loguj(callback_logu, f"Tworzenie katalogu wynikowego: {konfiguracja.katalog_wyjsciowy}")

    if adresy_startowe is None:
        lista_startowa = wczytaj_url_z_pliku(konfiguracja.plik_wejsciowy)
    else:
        lista_startowa = wczytaj_url_z_tekstu("\n".join(adresy_startowe))

    if not lista_startowa:
        raise ValueError(
            "Brak poprawnych adresów URL do analizy. "
            "Uzupełnij listę adresów w GUI lub w pliku wejściowym."
        )

    _loguj(callback_logu, f"Wczytano {len(lista_startowa)} adresów startowych.")
    _loguj(
        callback_logu,
        "Tryb domeny: "
        + (
            "tylko strony z tej samej domeny"
            if konfiguracja.tylko_ta_sama_domena
            else "pełny zbiór odnośników"
        ),
    )
    _loguj(
        callback_logu,
        f"Maksymalna liczba stron do odwiedzenia: {konfiguracja.maksymalna_liczba_stron}",
    )

    _raportuj_postep(callback_postepu, 5, "Inicjalizacja scrapera...")
    zbieracz = ZbieraczStron(konfiguracja)

    def _postep_zbierania(aktualny_stan: int, maksymalny_stan: int, aktualny_url: str) -> None:
        if maksymalny_stan <= 0:
            procent = 10
        else:
            procent = 10 + int((aktualny_stan / maksymalny_stan) * 60)
        opis = f"Pobieranie i analiza strony: {skroc_url(aktualny_url, 90)}"
        _raportuj_postep(callback_postepu, procent, opis)

    try:
        _loguj(callback_logu, "Rozpoczynam pobieranie stron i budowę grafu...")
        _raportuj_postep(callback_postepu, 10, "Pobieranie stron i budowa grafu...")
        graf, podsumowanie_zbierania = zbuduj_graf_hiperlinkow(
            adresy_startowe=lista_startowa,
            zbieracz=zbieracz,
            konfiguracja=konfiguracja,
            callback_logu=callback_logu,
            callback_postepu=_postep_zbierania,
        )
    finally:
        zbieracz.zamknij()

    _loguj(callback_logu, "Obliczam metryki sieciowe...")
    _raportuj_postep(callback_postepu, 75, "Obliczanie metryk sieciowych...")
    dataframe_metryk, podsumowanie_sieci = analizuj_graf(graf)

    sciezka_krawedzi = konfiguracja.katalog_wyjsciowy / "edges.csv"
    sciezka_metryk = konfiguracja.katalog_wyjsciowy / "node_metrics.csv"
    sciezka_podsumowania = konfiguracja.katalog_wyjsciowy / "network_summary.txt"

    _loguj(callback_logu, "Zapisuję pliki CSV i podsumowanie tekstowe...")
    _raportuj_postep(callback_postepu, 85, "Zapisywanie wyników do plików...")
    zapisz_krawedzie_do_csv(graf, sciezka_krawedzi)
    zapisz_metryki_wezlow(dataframe_metryk, sciezka_metryk)
    zapisz_podsumowanie_sieci(
        podsumowanie_zbierania=podsumowanie_zbierania,
        podsumowanie_sieci=podsumowanie_sieci,
        sciezka_wyjsciowa=sciezka_podsumowania,
    )

    _loguj(callback_logu, "Generuję wizualizacje PNG...")
    _raportuj_postep(callback_postepu, 92, "Generowanie wykresów i grafu...")
    pliki_wynikowe = generuj_wizualizacje(
        graf=graf,
        dataframe_metryk=dataframe_metryk,
        katalog_wyjsciowy=konfiguracja.katalog_wyjsciowy,
        konfiguracja=konfiguracja,
    )
    pliki_wynikowe.update(
        {
            "krawedzie_csv": sciezka_krawedzi,
            "metryki_csv": sciezka_metryk,
            "podsumowanie_txt": sciezka_podsumowania,
        }
    )

    _loguj(callback_logu, "Analiza zakończona powodzeniem.")
    _raportuj_postep(callback_postepu, 100, "Analiza zakończona.")
    return WynikAnalizy(
        graf=graf,
        dataframe_metryk=dataframe_metryk,
        podsumowanie_zbierania=podsumowanie_zbierania,
        podsumowanie_sieci=podsumowanie_sieci,
        katalog_wyjsciowy=konfiguracja.katalog_wyjsciowy,
        konfiguracja=konfiguracja,
        pliki_wynikowe=pliki_wynikowe,
    )

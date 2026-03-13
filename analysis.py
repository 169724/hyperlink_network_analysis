"""Moduł odpowiedzialny za analizę sieci złożonej."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import networkx as nx
import pandas as pd

from graph_builder import PodsumowanieZbierania


@dataclass(slots=True)
class PodsumowanieSieci:
    """Podstawowe statystyki całej sieci hyperlinkowej."""

    liczba_wezlow: int
    liczba_krawedzi: int
    liczba_slabo_spojnych_skladowych: int
    rozmiar_najwiekszej_skladowej: int


def _mapa_zerowa(wezly: list[str]) -> dict[str, float]:
    """Tworzy słownik zerowych wartości metryk."""
    return {wezel: 0.0 for wezel in wezly}


def _pagerank_awaryjny(
    graf: nx.DiGraph,
    alpha: float = 0.85,
    maks_iteracji: int = 100,
    tolerancja: float = 1.0e-6,
) -> dict[str, float]:
    """Awaryjna implementacja PageRank w czystym Pythonie."""
    wezly = list(graf.nodes())
    liczba_wezlow = len(wezly)
    if liczba_wezlow == 0:
        return {}

    rangi = {wezel: 1.0 / liczba_wezlow for wezel in wezly}
    stopien_wyjscia = {wezel: graf.out_degree(wezel) for wezel in wezly}

    for _ in range(maks_iteracji):
        poprzednie_rangi = rangi.copy()
        suma_wiszaca = (
            alpha
            * sum(poprzednie_rangi[wezel] for wezel in wezly if stopien_wyjscia[wezel] == 0)
            / liczba_wezlow
        )

        for wezel in wezly:
            nowa_wartosc = (1.0 - alpha) / liczba_wezlow
            nowa_wartosc += suma_wiszaca

            for poprzednik in graf.predecessors(wezel):
                if stopien_wyjscia[poprzednik] > 0:
                    nowa_wartosc += alpha * (
                        poprzednie_rangi[poprzednik] / stopien_wyjscia[poprzednik]
                    )

            rangi[wezel] = nowa_wartosc

        blad = sum(abs(rangi[wezel] - poprzednie_rangi[wezel]) for wezel in wezly)
        if blad < liczba_wezlow * tolerancja:
            break

    suma_rang = sum(rangi.values())
    if suma_rang > 0:
        rangi = {wezel: wartosc / suma_rang for wezel, wartosc in rangi.items()}

    return rangi


def analizuj_graf(graf: nx.DiGraph) -> tuple[pd.DataFrame, PodsumowanieSieci]:
    """Oblicza podstawowe miary teorii sieci złożonych dla grafu skierowanego."""
    wezly = list(graf.nodes())

    kolumny = [
        "url",
        "in_degree",
        "out_degree",
        "total_degree",
        "degree_centrality",
        "betweenness_centrality",
        "closeness_centrality",
        "pagerank",
        "weak_component_id",
        "weak_component_size",
        "in_largest_component",
    ]

    if not wezly:
        pusty_dataframe = pd.DataFrame(columns=kolumny)
        podsumowanie = PodsumowanieSieci(
            liczba_wezlow=0,
            liczba_krawedzi=0,
            liczba_slabo_spojnych_skladowych=0,
            rozmiar_najwiekszej_skladowej=0,
        )
        return pusty_dataframe, podsumowanie

    stopien_wejsciowy = dict(graf.in_degree())
    stopien_wyjsciowy = dict(graf.out_degree())

    if graf.number_of_nodes() > 1:
        centralnosc_stopnia = nx.degree_centrality(graf)
    else:
        centralnosc_stopnia = _mapa_zerowa(wezly)

    if graf.number_of_nodes() > 1 and graf.number_of_edges() > 0:
        centralnosc_posrednictwa = nx.betweenness_centrality(graf, normalized=True)
        centralnosc_bliskosci = nx.closeness_centrality(graf.reverse())

        try:
            pagerank = nx.pagerank(graf, alpha=0.85)
        except ModuleNotFoundError:
            pagerank = _pagerank_awaryjny(graf, alpha=0.85)
    else:
        centralnosc_posrednictwa = _mapa_zerowa(wezly)
        centralnosc_bliskosci = _mapa_zerowa(wezly)
        wartosc_jednolita = 1.0 / max(len(wezly), 1)
        pagerank = {wezel: wartosc_jednolita for wezel in wezly}

    slabo_spojne_skladowe = list(nx.weakly_connected_components(graf))
    slabo_spojne_skladowe = sorted(slabo_spojne_skladowe, key=len, reverse=True)

    mapa_id_skladowej: dict[str, int] = {}
    mapa_rozmiaru_skladowej: dict[str, int] = {}

    najwieksza_skladowa = slabo_spojne_skladowe[0] if slabo_spojne_skladowe else set()

    for id_skladowej, wezly_skladowej in enumerate(slabo_spojne_skladowe, start=1):
        rozmiar_skladowej = len(wezly_skladowej)
        for wezel in wezly_skladowej:
            mapa_id_skladowej[wezel] = id_skladowej
            mapa_rozmiaru_skladowej[wezel] = rozmiar_skladowej

    rekordy: list[dict] = []
    for wezel in wezly:
        rekordy.append(
            {
                "url": wezel,
                "in_degree": stopien_wejsciowy.get(wezel, 0),
                "out_degree": stopien_wyjsciowy.get(wezel, 0),
                "total_degree": stopien_wejsciowy.get(wezel, 0) + stopien_wyjsciowy.get(wezel, 0),
                "degree_centrality": centralnosc_stopnia.get(wezel, 0.0),
                "betweenness_centrality": centralnosc_posrednictwa.get(wezel, 0.0),
                "closeness_centrality": centralnosc_bliskosci.get(wezel, 0.0),
                "pagerank": pagerank.get(wezel, 0.0),
                "weak_component_id": mapa_id_skladowej.get(wezel, 0),
                "weak_component_size": mapa_rozmiaru_skladowej.get(wezel, 0),
                "in_largest_component": wezel in najwieksza_skladowa,
            }
        )

    dataframe_metryk = pd.DataFrame(rekordy)
    dataframe_metryk = dataframe_metryk.sort_values(
        by=["pagerank", "total_degree", "url"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    podsumowanie = PodsumowanieSieci(
        liczba_wezlow=graf.number_of_nodes(),
        liczba_krawedzi=graf.number_of_edges(),
        liczba_slabo_spojnych_skladowych=len(slabo_spojne_skladowe),
        rozmiar_najwiekszej_skladowej=len(najwieksza_skladowa),
    )

    return dataframe_metryk, podsumowanie


def zapisz_metryki_wezlow(dataframe_metryk: pd.DataFrame, sciezka_wyjsciowa: Path) -> None:
    """Zapisuje metryki węzłów do pliku CSV."""
    dataframe_metryk.to_csv(sciezka_wyjsciowa, index=False, float_format="%.8f")


def zapisz_podsumowanie_sieci(
    podsumowanie_zbierania: PodsumowanieZbierania,
    podsumowanie_sieci: PodsumowanieSieci,
    sciezka_wyjsciowa: Path,
) -> None:
    """Zapisuje podsumowanie analizy do pliku tekstowego."""
    linie = [
        "Podsumowanie analizy sieci hyperlinkowej",
        "=" * 50,
        f"Liczba adresów startowych: {podsumowanie_zbierania.liczba_adresow_startowych}",
        f"Liczba żądań HTTP: {podsumowanie_zbierania.liczba_zadan_http}",
        (
            "Liczba przeanalizowanych stron HTML: "
            f"{podsumowanie_zbierania.liczba_przeanalizowanych_stron_html}"
        ),
        f"Liczba błędów pobierania: {podsumowanie_zbierania.liczba_bledow_pobierania}",
        f"Liczba odkrytych węzłów: {podsumowanie_zbierania.liczba_odkrytych_wezlow}",
        f"Liczba odkrytych krawędzi: {podsumowanie_zbierania.liczba_odkrytych_krawedzi}",
        "",
        f"Liczba węzłów w grafie: {podsumowanie_sieci.liczba_wezlow}",
        f"Liczba krawędzi w grafie: {podsumowanie_sieci.liczba_krawedzi}",
        (
            "Liczba słabo spójnych składowych: "
            f"{podsumowanie_sieci.liczba_slabo_spojnych_skladowych}"
        ),
        (
            "Rozmiar największej słabo spójnej składowej: "
            f"{podsumowanie_sieci.rozmiar_najwiekszej_skladowej}"
        ),
    ]
    sciezka_wyjsciowa.write_text("\n".join(linie), encoding="utf-8")

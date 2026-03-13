"""Moduł odpowiedzialny za tworzenie i zapis wizualizacji."""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import pandas as pd
from matplotlib.figure import Figure

from config import KonfiguracjaAnalizy
from utils import skroc_url


def _utworz_pusta_figure(komunikat: str, tytul: str) -> Figure:
    """Tworzy pustą figurę z komunikatem o braku danych."""
    figura = Figure(figsize=(10, 6), dpi=100)
    os = figura.add_subplot(111)
    os.text(0.5, 0.5, komunikat, ha="center", va="center", fontsize=12)
    os.set_title(tytul)
    os.axis("off")
    figura.tight_layout()
    return figura


def utworz_figure_grafu(
    graf: nx.DiGraph,
    dataframe_metryk: pd.DataFrame,
    konfiguracja: KonfiguracjaAnalizy,
) -> Figure:
    """Tworzy figurę przedstawiającą graf skierowany sieci hyperlinkowej."""
    if graf.number_of_nodes() == 0:
        return _utworz_pusta_figure(
            "Brak danych do wizualizacji grafu.",
            "Graf sieci hyperlinkowej",
        )

    figura = Figure(figsize=konfiguracja.rozmiar_rysunku_grafu, dpi=100)
    os = figura.add_subplot(111)

    mapa_pagerank = {}
    if not dataframe_metryk.empty:
        mapa_pagerank = dataframe_metryk.set_index("url")["pagerank"].to_dict()

    rozmiary_wezlow = [
        250 + mapa_pagerank.get(wezel, 0.0) * 12000
        for wezel in graf.nodes()
    ]
    uklad = nx.spring_layout(graf, seed=konfiguracja.ziarno_losowe)

    top_wezly = []
    if not dataframe_metryk.empty:
        top_wezly = dataframe_metryk.head(konfiguracja.top_n_pagerank)["url"].tolist()

    etykiety = {wezel: skroc_url(wezel, 45) for wezel in top_wezly if wezel in graf}

    nx.draw_networkx_nodes(graf, uklad, node_size=rozmiary_wezlow, alpha=0.85, ax=os)
    nx.draw_networkx_edges(
        graf,
        uklad,
        alpha=0.30,
        arrows=True,
        arrowsize=12,
        width=0.8,
        arrowstyle="->",
        ax=os,
    )
    nx.draw_networkx_labels(graf, uklad, labels=etykiety, font_size=8, ax=os)

    os.set_title("Graf skierowany sieci hyperlinkowej")
    os.axis("off")
    figura.tight_layout()
    return figura


def utworz_figure_top_pagerank(dataframe_metryk: pd.DataFrame, top_n: int) -> Figure:
    """Tworzy wykres słupkowy stron o najwyższym PageRank."""
    if dataframe_metryk.empty:
        return _utworz_pusta_figure(
            "Brak danych do wizualizacji PageRank.",
            "Top strony według PageRank",
        )

    top_dataframe = dataframe_metryk.head(top_n).copy().sort_values(by="pagerank", ascending=True)
    etykiety = [skroc_url(url, 70) for url in top_dataframe["url"]]

    figura = Figure(figsize=(12, 7), dpi=100)
    os = figura.add_subplot(111)
    os.barh(etykiety, top_dataframe["pagerank"])
    os.set_xlabel("PageRank")
    os.set_ylabel("URL")
    os.set_title(f"Top {min(top_n, len(top_dataframe))} stron według PageRank")
    figura.tight_layout()
    return figura


def utworz_figure_liniowego_rozkladu_stopni(dataframe_metryk: pd.DataFrame) -> Figure:
    """Tworzy liniowy wykres rozkładu stopni węzłów."""
    if dataframe_metryk.empty:
        return _utworz_pusta_figure(
            "Brak danych do wykresu rozkładu stopni.",
            "Liniowy wykres rozkładu stopni",
        )

    liczebnosci = dataframe_metryk["total_degree"].value_counts().sort_index()

    figura = Figure(figsize=(10, 6), dpi=100)
    os = figura.add_subplot(111)
    os.plot(liczebnosci.index.tolist(), liczebnosci.values.tolist(), marker="o")
    os.set_xlabel("Stopień węzła (in-degree + out-degree)")
    os.set_ylabel("Liczba węzłów")
    os.set_title("Liniowy wykres rozkładu stopni")
    os.grid(True, alpha=0.3)
    figura.tight_layout()
    return figura


def utworz_figury_wizualizacji(
    graf: nx.DiGraph,
    dataframe_metryk: pd.DataFrame,
    konfiguracja: KonfiguracjaAnalizy,
) -> dict[str, Figure]:
    """Tworzy komplet figur używanych przez GUI i zapis plików PNG."""
    return {
        "graf_sieci": utworz_figure_grafu(graf, dataframe_metryk, konfiguracja),
        "top_pagerank": utworz_figure_top_pagerank(dataframe_metryk, konfiguracja.top_n_pagerank),
        "rozklad_stopni": utworz_figure_liniowego_rozkladu_stopni(dataframe_metryk),
    }


def generuj_wizualizacje(
    graf: nx.DiGraph,
    dataframe_metryk: pd.DataFrame,
    katalog_wyjsciowy: Path,
    konfiguracja: KonfiguracjaAnalizy,
) -> dict[str, Path]:
    """Generuje i zapisuje wszystkie wymagane wizualizacje do plików PNG."""
    figury = utworz_figury_wizualizacji(graf, dataframe_metryk, konfiguracja)

    sciezki = {
        "graf_sieci": katalog_wyjsciowy / "network_graph.png",
        "top_pagerank": katalog_wyjsciowy / "top_pagerank.png",
        "rozklad_stopni": katalog_wyjsciowy / "degree_histogram.png",
    }

    for klucz, figura in figury.items():
        figura.savefig(sciezki[klucz], dpi=200)

    return sciezki

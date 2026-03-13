"""Funkcje pomocnicze używane w całym projekcie."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse

NIEPOPRAWNE_PREFIKSY = ("#", "mailto:", "javascript:", "tel:", "data:")


def normalizuj_url(bazowy_url: str, href: str) -> str | None:
    """
    Normalizuje adres URL.

    - zamienia ścieżki względne na pełne adresy,
    - usuwa fragment po znaku '#',
    - odrzuca nieobsługiwane schematy,
    - porządkuje host i ścieżkę.
    """
    if not href:
        return None

    href = href.strip()
    if not href:
        return None

    if href.lower().startswith(NIEPOPRAWNE_PREFIKSY):
        return None

    pelny_url = urljoin(bazowy_url, href)
    pelny_url, _ = urldefrag(pelny_url)

    parsowany = urlparse(pelny_url)
    schemat = parsowany.scheme.lower()

    if schemat not in {"http", "https"}:
        return None

    if not parsowany.hostname:
        return None

    try:
        port = parsowany.port
    except ValueError:
        return None

    host = parsowany.hostname.lower()

    netloc = host
    if port and not ((schemat == "http" and port == 80) or (schemat == "https" and port == 443)):
        netloc = f"{host}:{port}"

    sciezka = re.sub(r"/{2,}", "/", parsowany.path or "/")
    if sciezka != "/" and sciezka.endswith("/"):
        sciezka = sciezka[:-1]

    return urlunparse((schemat, netloc, sciezka, "", parsowany.query, ""))


def pobierz_domene(url: str) -> str:
    """Zwraca nazwę domeny bez prefiksu 'www.'."""
    parsowany = urlparse(url)
    host = (parsowany.hostname or "").lower()
    return host.removeprefix("www.")


def czy_w_obrebie_domeny(url: str, domena: str) -> bool:
    """Sprawdza, czy dany URL należy do wskazanej domeny."""
    return pobierz_domene(url) == domena.removeprefix("www.").lower()


def utworz_katalog_wyjsciowy(katalog_wyjsciowy: Path) -> None:
    """Tworzy katalog wyjściowy, jeśli jeszcze nie istnieje."""
    katalog_wyjsciowy.mkdir(parents=True, exist_ok=True)


def wczytaj_url_z_tekstu(tekst: str) -> list[str]:
    """
    Wczytuje i normalizuje adresy URL z przekazanego tekstu.

    Ignoruje puste linie oraz linie komentarzy rozpoczynające się od '#'.
    """
    adresy: list[str] = []
    widziane: set[str] = set()

    for linia in tekst.splitlines():
        surowy = linia.strip()

        if not surowy or surowy.startswith("#"):
            continue

        kandydat = surowy if "://" in surowy else f"https://{surowy}"
        znormalizowany = normalizuj_url(kandydat, kandydat)

        if znormalizowany and znormalizowany not in widziane:
            widziane.add(znormalizowany)
            adresy.append(znormalizowany)

    return adresy


def wczytaj_url_z_pliku(sciezka_pliku: Path) -> list[str]:
    """Wczytuje adresy URL z pliku tekstowego."""
    if not sciezka_pliku.exists():
        raise FileNotFoundError(f"Nie znaleziono pliku wejściowego: {sciezka_pliku}")

    tekst = sciezka_pliku.read_text(encoding="utf-8")
    return wczytaj_url_z_tekstu(tekst)


def zapisz_url_do_pliku(adresy_url: list[str], sciezka_pliku: Path) -> None:
    """Zapisuje listę adresów URL do pliku tekstowego."""
    sciezka_pliku.parent.mkdir(parents=True, exist_ok=True)
    tresc = "\n".join(adresy_url).strip()
    if tresc:
        tresc += "\n"
    sciezka_pliku.write_text(tresc, encoding="utf-8")


def skroc_url(url: str, maksymalna_dlugosc: int = 60) -> str:
    """Skraca długi URL do czytelnej postaci."""
    if len(url) <= maksymalna_dlugosc:
        return url
    return f"{url[: maksymalna_dlugosc - 3]}..."

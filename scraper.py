"""Moduł odpowiedzialny za pobieranie stron i ekstrakcję linków."""

from __future__ import annotations

import time
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import KonfiguracjaAnalizy
from utils import normalizuj_url


@dataclass(slots=True)
class WynikPobrania:
    """Wynik pojedynczego pobrania strony WWW."""

    zadany_url: str
    finalny_url: str
    html: str | None
    status_code: int | None
    blad: str | None = None


class ZbieraczStron:
    """Prosty i stabilny scraper stron WWW oparty o requests i BeautifulSoup."""

    def __init__(self, konfiguracja: KonfiguracjaAnalizy) -> None:
        self.konfiguracja = konfiguracja
        self.sesja = requests.Session()
        self.sesja.headers.update({"User-Agent": konfiguracja.user_agent})
        self._skonfiguruj_ponawianie_zadan()

    def _skonfiguruj_ponawianie_zadan(self) -> None:
        """Konfiguruje ponawianie żądań dla błędów tymczasowych."""
        strategia_ponawiania = Retry(
            total=2,
            connect=2,
            read=2,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset({"GET", "HEAD"}),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=strategia_ponawiania)
        self.sesja.mount("http://", adapter)
        self.sesja.mount("https://", adapter)

    def pobierz_strone(self, url: str) -> WynikPobrania:
        """Pobiera stronę WWW i zwraca wynik wraz z metadanymi."""
        try:
            if self.konfiguracja.opoznienie_miedzy_zadaniami > 0:
                time.sleep(self.konfiguracja.opoznienie_miedzy_zadaniami)

            odpowiedz = self.sesja.get(
                url,
                timeout=self.konfiguracja.timeout_zadania,
                allow_redirects=self.konfiguracja.podazaj_za_przekierowaniami,
                verify=self.konfiguracja.weryfikuj_ssl,
            )

            finalny_url = normalizuj_url(url, odpowiedz.url) or url
            typ_tresci = odpowiedz.headers.get("Content-Type", "").lower()

            if odpowiedz.status_code >= 400:
                return WynikPobrania(
                    zadany_url=url,
                    finalny_url=finalny_url,
                    html=None,
                    status_code=odpowiedz.status_code,
                    blad=f"HTTP {odpowiedz.status_code}",
                )

            if "text/html" not in typ_tresci:
                return WynikPobrania(
                    zadany_url=url,
                    finalny_url=finalny_url,
                    html=None,
                    status_code=odpowiedz.status_code,
                    blad=None,
                )

            return WynikPobrania(
                zadany_url=url,
                finalny_url=finalny_url,
                html=odpowiedz.text,
                status_code=odpowiedz.status_code,
                blad=None,
            )

        except requests.RequestException as exc:
            return WynikPobrania(
                zadany_url=url,
                finalny_url=url,
                html=None,
                status_code=None,
                blad=str(exc),
            )

    def wyodrebnij_linki(self, bazowy_url: str, html: str) -> list[str]:
        """Wyciąga i normalizuje linki z dokumentu HTML."""
        soup = BeautifulSoup(html, "html.parser")
        linki: set[str] = set()

        for znacznik in soup.find_all("a", href=True):
            href = znacznik.get("href", "").strip()
            znormalizowany = normalizuj_url(bazowy_url, href)
            if znormalizowany is None:
                continue

            linki.add(znormalizowany)

            if (
                self.konfiguracja.maksymalna_liczba_linkow_na_strone is not None
                and len(linki) >= self.konfiguracja.maksymalna_liczba_linkow_na_strone
            ):
                break

        return sorted(linki)

    def zamknij(self) -> None:
        """Zamyka sesję HTTP."""
        self.sesja.close()

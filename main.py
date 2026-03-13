"""Plik uruchomieniowy wersji konsolowej projektu."""

from __future__ import annotations

from app_core import WynikAnalizy, uruchom_pelna_analize
from config import USTAWIENIA
from utils import skroc_url


def wypisz_podsumowanie_w_konsoli(wynik: WynikAnalizy) -> None:
    """Wypisuje zwarte podsumowanie wyników analizy w konsoli."""
    podsumowanie_zbierania = wynik.podsumowanie_zbierania
    podsumowanie_sieci = wynik.podsumowanie_sieci
    dataframe_metryk = wynik.dataframe_metryk

    print("\n" + "=" * 72)
    print("ANALIZA SIECI HYPERLINKOWEJ ZAKOŃCZONA")
    print("=" * 72)
    print(f"Liczba adresów startowych: {podsumowanie_zbierania.liczba_adresow_startowych}")
    print(f"Liczba żądań HTTP:         {podsumowanie_zbierania.liczba_zadan_http}")
    print(
        "Liczba przeanalizowanych stron HTML: "
        f"{podsumowanie_zbierania.liczba_przeanalizowanych_stron_html}"
    )
    print(f"Liczba błędów połączenia:  {podsumowanie_zbierania.liczba_bledow_pobierania}")
    print(f"Liczba węzłów w grafie:    {podsumowanie_sieci.liczba_wezlow}")
    print(f"Liczba krawędzi w grafie:  {podsumowanie_sieci.liczba_krawedzi}")
    print(
        "Liczba słabo spójnych składowych: "
        f"{podsumowanie_sieci.liczba_slabo_spojnych_skladowych}"
    )
    print(
        "Rozmiar największej składowej: "
        f"{podsumowanie_sieci.rozmiar_najwiekszej_skladowej}"
    )

    if not dataframe_metryk.empty:
        print("\nTop 5 stron według PageRank:")
        for pozycja, (_, wiersz) in enumerate(dataframe_metryk.head(5).iterrows(), start=1):
            print(
                f"{pozycja:>2}. {skroc_url(wiersz['url'], 85)} "
                f"| PageRank = {wiersz['pagerank']:.6f}"
            )

    print("\nPliki wynikowe zapisano w katalogu:", wynik.katalog_wyjsciowy)
    print("=" * 72)


def main() -> None:
    """Uruchamia wersję konsolową aplikacji."""
    wynik = uruchom_pelna_analize(
        konfiguracja=USTAWIENIA,
        callback_logu=print,
    )
    wypisz_podsumowanie_w_konsoli(wynik)


if __name__ == "__main__":
    main()

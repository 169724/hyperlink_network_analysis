"""Graficzny interfejs projektu analizy sieci hyperlinkowej."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import traceback
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from app_core import WynikAnalizy, uruchom_pelna_analize
from config import KATALOG_BAZOWY, KonfiguracjaAnalizy, USTAWIENIA
from utils import wczytaj_url_z_tekstu, zapisz_url_do_pliku
from visualization import utworz_figury_wizualizacji


class InterfejsAnalizatoraHiperlinkow:
    """Desktopowe GUI oparte na tkinter."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Analizator sieci hyperlinkowej")
        self.root.geometry("1360x860")
        self.root.minsize(1080, 720)

        self.kolejka_zdarzen: queue.Queue[tuple[str, object]] = queue.Queue()
        self.watek_roboczy: threading.Thread | None = None
        self.ostatni_wynik: WynikAnalizy | None = None
        self.canvasy_wykresow: dict[str, FigureCanvasTkAgg] = {}
        self.ramki_wykresow: dict[str, ttk.Frame] = {}

        self._zbuduj_zmienne()
        self._zbuduj_uklad()
        self._wczytaj_adresy_z_ustawionego_pliku()
        self._pokaz_komunikaty_startowe()
        self._obsluz_kolejke_zdarzen()

    def _zbuduj_zmienne(self) -> None:
        domyslne = USTAWIENIA
        self.zmienna_pliku_wejsciowego = tk.StringVar(value=str(domyslne.plik_wejsciowy))
        self.zmienna_katalogu_wyjsciowego = tk.StringVar(value=str(domyslne.katalog_wyjsciowy))
        self.zmienna_tylko_ta_sama_domena = tk.BooleanVar(value=domyslne.tylko_ta_sama_domena)
        self.zmienna_maks_liczba_stron = tk.StringVar(value=str(domyslne.maksymalna_liczba_stron))
        self.zmienna_maks_liczba_linkow = tk.StringVar(
            value=""
            if domyslne.maksymalna_liczba_linkow_na_strone is None
            else str(domyslne.maksymalna_liczba_linkow_na_strone)
        )
        self.zmienna_timeout = tk.StringVar(value=str(domyslne.timeout_zadania))
        self.zmienna_opoznienia = tk.StringVar(value=str(domyslne.opoznienie_miedzy_zadaniami))
        self.zmienna_top_n = tk.StringVar(value=str(domyslne.top_n_pagerank))
        self.zmienna_weryfikacji_ssl = tk.BooleanVar(value=domyslne.weryfikuj_ssl)
        self.zmienna_przekierowan = tk.BooleanVar(value=domyslne.podazaj_za_przekierowaniami)

        self.zmienna_statusu = tk.StringVar(value="Gotowe do uruchomienia.")
        self.zmienna_opisu_postepu = tk.StringVar(value="Brak aktywnej analizy.")
        self.zmienna_postepu = tk.DoubleVar(value=0.0)

    def _zbuduj_uklad(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        naglowek = ttk.Frame(self.root, padding=(16, 16, 16, 8))
        naglowek.grid(row=0, column=0, sticky="ew")
        naglowek.columnconfigure(0, weight=1)

        ttk.Label(
            naglowek,
            text="Analiza struktury sieci hyperlinkowej",
            font=("Segoe UI", 18, "bold"),
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(
            naglowek,
            text=(
                "Interfejs do lokalnego scrapingu WWW, budowy grafu skierowanego, "
                "analizy metryk sieci złożonych i przeglądania wykresów."
            ),
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        paned = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        paned.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        panel_lewy = ttk.Frame(paned, padding=8)
        panel_prawy = ttk.Frame(paned, padding=8)
        panel_lewy.columnconfigure(0, weight=1)
        panel_lewy.rowconfigure(0, weight=1)
        panel_prawy.columnconfigure(0, weight=1)
        panel_prawy.rowconfigure(0, weight=1)

        paned.add(panel_lewy, weight=2)
        paned.add(panel_prawy, weight=3)

        self._zbuduj_lewy_panel(panel_lewy)
        self._zbuduj_prawy_panel(panel_prawy)

        stopka = ttk.Frame(self.root, padding=(16, 0, 16, 16))
        stopka.grid(row=2, column=0, sticky="ew")
        stopka.columnconfigure(0, weight=1)

        ttk.Label(stopka, textvariable=self.zmienna_statusu).grid(row=0, column=0, sticky="w")
        ttk.Label(stopka, textvariable=self.zmienna_opisu_postepu).grid(
            row=1, column=0, sticky="w", pady=(4, 4)
        )
        self.pasek_postepu = ttk.Progressbar(
            stopka,
            mode="determinate",
            maximum=100,
            variable=self.zmienna_postepu,
        )
        self.pasek_postepu.grid(row=2, column=0, sticky="ew")

    def _zbuduj_lewy_panel(self, rodzic: ttk.Frame) -> None:
        notebook = ttk.Notebook(rodzic)
        notebook.grid(row=0, column=0, sticky="nsew")

        karta_ustawien = ttk.Frame(notebook, padding=12)
        karta_adresow = ttk.Frame(notebook, padding=12)
        karta_ustawien.columnconfigure(1, weight=1)
        karta_adresow.columnconfigure(0, weight=1)
        karta_adresow.rowconfigure(2, weight=1)

        notebook.add(karta_ustawien, text="Ustawienia")
        notebook.add(karta_adresow, text="Adresy URL")

        self._zbuduj_formularz_ustawien(karta_ustawien)
        self._zbuduj_edytor_adresow(karta_adresow)

    def _zbuduj_formularz_ustawien(self, rodzic: ttk.Frame) -> None:
        wiersz = 0
        ttk.Label(rodzic, text="Plik wejściowy").grid(row=wiersz, column=0, sticky="w", pady=4)
        ttk.Entry(rodzic, textvariable=self.zmienna_pliku_wejsciowego).grid(
            row=wiersz, column=1, sticky="ew", padx=(8, 8)
        )
        ttk.Button(rodzic, text="Wybierz...", command=self._wybierz_plik_wejsciowy).grid(
            row=wiersz, column=2, sticky="ew"
        )

        wiersz += 1
        ttk.Label(rodzic, text="Katalog wynikowy").grid(row=wiersz, column=0, sticky="w", pady=4)
        ttk.Entry(rodzic, textvariable=self.zmienna_katalogu_wyjsciowego).grid(
            row=wiersz, column=1, sticky="ew", padx=(8, 8)
        )
        ttk.Button(rodzic, text="Wybierz...", command=self._wybierz_katalog_wyjsciowy).grid(
            row=wiersz, column=2, sticky="ew"
        )

        wiersz += 1
        ttk.Separator(rodzic).grid(row=wiersz, column=0, columnspan=3, sticky="ew", pady=10)

        wiersz += 1
        ttk.Checkbutton(
            rodzic,
            text="Analizuj tylko strony z tej samej domeny",
            variable=self.zmienna_tylko_ta_sama_domena,
        ).grid(row=wiersz, column=0, columnspan=3, sticky="w", pady=4)

        wiersz += 1
        ttk.Checkbutton(
            rodzic,
            text="Weryfikuj certyfikaty SSL",
            variable=self.zmienna_weryfikacji_ssl,
        ).grid(row=wiersz, column=0, columnspan=3, sticky="w", pady=4)

        wiersz += 1
        ttk.Checkbutton(
            rodzic,
            text="Podążaj za przekierowaniami HTTP",
            variable=self.zmienna_przekierowan,
        ).grid(row=wiersz, column=0, columnspan=3, sticky="w", pady=4)

        wiersz += 1
        ttk.Label(rodzic, text="Maksymalna liczba stron").grid(row=wiersz, column=0, sticky="w", pady=4)
        ttk.Entry(rodzic, textvariable=self.zmienna_maks_liczba_stron, width=12).grid(
            row=wiersz, column=1, sticky="w", padx=(8, 8)
        )

        wiersz += 1
        ttk.Label(rodzic, text="Maks. liczba linków na stronę").grid(
            row=wiersz, column=0, sticky="w", pady=4
        )
        ttk.Entry(rodzic, textvariable=self.zmienna_maks_liczba_linkow, width=12).grid(
            row=wiersz, column=1, sticky="w", padx=(8, 8)
        )
        ttk.Label(rodzic, text="(puste = bez limitu)").grid(row=wiersz, column=2, sticky="w")

        wiersz += 1
        ttk.Label(rodzic, text="Timeout żądania (s)").grid(row=wiersz, column=0, sticky="w", pady=4)
        ttk.Entry(rodzic, textvariable=self.zmienna_timeout, width=12).grid(
            row=wiersz, column=1, sticky="w", padx=(8, 8)
        )

        wiersz += 1
        ttk.Label(rodzic, text="Opóźnienie między żądaniami (s)").grid(
            row=wiersz, column=0, sticky="w", pady=4
        )
        ttk.Entry(rodzic, textvariable=self.zmienna_opoznienia, width=12).grid(
            row=wiersz, column=1, sticky="w", padx=(8, 8)
        )

        wiersz += 1
        ttk.Label(rodzic, text="Top N stron według PageRank").grid(
            row=wiersz, column=0, sticky="w", pady=4
        )
        ttk.Entry(rodzic, textvariable=self.zmienna_top_n, width=12).grid(
            row=wiersz, column=1, sticky="w", padx=(8, 8)
        )

        wiersz += 1
        ttk.Separator(rodzic).grid(row=wiersz, column=0, columnspan=3, sticky="ew", pady=10)

        wiersz += 1
        ramka_przyciskow = ttk.Frame(rodzic)
        ramka_przyciskow.grid(row=wiersz, column=0, columnspan=3, sticky="ew")
        for idx in range(3):
            ramka_przyciskow.columnconfigure(idx, weight=1)

        self.przycisk_uruchom = ttk.Button(
            ramka_przyciskow,
            text="Uruchom analizę",
            command=self._uruchom_analize,
        )
        self.przycisk_uruchom.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ttk.Button(
            ramka_przyciskow,
            text="Otwórz folder wyników",
            command=self._otworz_katalog_wyjsciowy,
        ).grid(row=0, column=1, sticky="ew", padx=6)

        ttk.Button(
            ramka_przyciskow,
            text="Przywróć domyślne",
            command=self._przywroc_ustawienia_domyslne,
        ).grid(row=0, column=2, sticky="ew", padx=(6, 0))

    def _zbuduj_edytor_adresow(self, rodzic: ttk.Frame) -> None:
        gorna_ramka = ttk.Frame(rodzic)
        gorna_ramka.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        for idx in range(4):
            gorna_ramka.columnconfigure(idx, weight=1)

        ttk.Button(
            gorna_ramka,
            text="Wczytaj z pliku",
            command=self._wczytaj_adresy_z_ustawionego_pliku,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(
            gorna_ramka,
            text="Zapisz do pliku",
            command=self._zapisz_adresy_do_ustawionego_pliku,
        ).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(
            gorna_ramka,
            text="Wyczyść listę",
            command=self._wyczysc_adresy,
        ).grid(row=0, column=2, sticky="ew", padx=6)
        ttk.Button(
            gorna_ramka,
            text="Dodaj przykład",
            command=self._wstaw_przykladowe_adresy,
        ).grid(row=0, column=3, sticky="ew", padx=(6, 0))

        ttk.Label(
            rodzic,
            text=(
                "Wpisuj lub wklej po jednym adresie URL w każdej linii. "
                "Komentarze zaczynające się od # są ignorowane."
            ),
        ).grid(row=1, column=0, sticky="nw", pady=(0, 6))

        self.pole_adresow = ScrolledText(rodzic, wrap=tk.WORD, font=("Consolas", 10))
        self.pole_adresow.grid(row=2, column=0, sticky="nsew")

    def _zbuduj_prawy_panel(self, rodzic: ttk.Frame) -> None:
        notebook = ttk.Notebook(rodzic)
        notebook.grid(row=0, column=0, sticky="nsew")

        karta_logu = ttk.Frame(notebook, padding=12)
        karta_logu.columnconfigure(0, weight=1)
        karta_logu.rowconfigure(1, weight=1)

        ttk.Label(karta_logu, text="Log działania programu", font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )
        self.pole_logu = ScrolledText(karta_logu, wrap=tk.WORD, font=("Consolas", 10), state=tk.DISABLED)
        self.pole_logu.grid(row=1, column=0, sticky="nsew")

        notebook.add(karta_logu, text="Log")

        for klucz, tytul in (
            ("graf_sieci", "Graf sieci"),
            ("top_pagerank", "Top PageRank"),
            ("rozklad_stopni", "Rozkład stopni"),
        ):
            karta = ttk.Frame(notebook, padding=8)
            karta.columnconfigure(0, weight=1)
            karta.rowconfigure(0, weight=1)
            notebook.add(karta, text=tytul)
            self.ramki_wykresow[klucz] = karta
            self._pokaz_placeholder_w_ramce(
                karta,
                "Wykres pojawi się tutaj po zakończeniu analizy.",
            )

    def _pokaz_placeholder_w_ramce(self, ramka: ttk.Frame, tresc: str) -> None:
        for widget in ramka.winfo_children():
            widget.destroy()
        ttk.Label(
            ramka,
            text=tresc,
            anchor="center",
            justify="center",
        ).grid(row=0, column=0, sticky="nsew")

    def _pokaz_komunikaty_startowe(self) -> None:
        self._dodaj_log("GUI uruchomione.")
        self._dodaj_log("Możesz edytować adresy URL bezpośrednio w zakładce 'Adresy URL'.")
        self._dodaj_log("Po analizie wykresy pojawią się w zakładkach po prawej stronie.")

    def _wybierz_plik_wejsciowy(self) -> None:
        sciezka = filedialog.askopenfilename(
            title="Wybierz plik z adresami URL",
            initialdir=str(KATALOG_BAZOWY),
            filetypes=[("Pliki tekstowe", "*.txt"), ("Wszystkie pliki", "*.*")],
        )
        if sciezka:
            self.zmienna_pliku_wejsciowego.set(sciezka)
            self._wczytaj_adresy_z_ustawionego_pliku()

    def _wybierz_katalog_wyjsciowy(self) -> None:
        sciezka = filedialog.askdirectory(
            title="Wybierz katalog wynikowy",
            initialdir=str(KATALOG_BAZOWY),
        )
        if sciezka:
            self.zmienna_katalogu_wyjsciowego.set(sciezka)

    def _wczytaj_adresy_z_ustawionego_pliku(self) -> None:
        sciezka = Path(self.zmienna_pliku_wejsciowego.get().strip())
        if not sciezka:
            return

        try:
            if sciezka.exists():
                tekst = sciezka.read_text(encoding="utf-8")
                self.pole_adresow.delete("1.0", tk.END)
                self.pole_adresow.insert("1.0", tekst)
                self.zmienna_statusu.set("Wczytano adresy URL z pliku.")
            else:
                self.pole_adresow.delete("1.0", tk.END)
                self.zmienna_statusu.set("Wybrany plik jeszcze nie istnieje.")
        except Exception as exc:
            messagebox.showerror("Błąd", f"Nie udało się wczytać pliku:\n{exc}")

    def _zapisz_adresy_do_ustawionego_pliku(self) -> None:
        try:
            adresy = self._pobierz_adresy_z_gui()
            sciezka = Path(self.zmienna_pliku_wejsciowego.get().strip())
            if not sciezka:
                raise ValueError("Wskaż plik wejściowy.")
            zapisz_url_do_pliku(adresy, sciezka)
            self.zmienna_statusu.set(f"Zapisano {len(adresy)} adresów do pliku.")
            self._dodaj_log(f"Zapisano adresy URL do pliku: {sciezka}")
        except Exception as exc:
            messagebox.showerror("Błąd zapisu", str(exc))

    def _wyczysc_adresy(self) -> None:
        self.pole_adresow.delete("1.0", tk.END)
        self.zmienna_statusu.set("Wyczyszczono listę adresów URL.")

    def _wstaw_przykladowe_adresy(self) -> None:
        przyklad = (
            "# Przykładowe adresy startowe\n"
            "https://www.python.org/\n"
            "https://www.python.org/about/\n"
            "https://www.python.org/downloads/\n"
        )
        self.pole_adresow.delete("1.0", tk.END)
        self.pole_adresow.insert("1.0", przyklad)
        self.zmienna_statusu.set("Wstawiono przykładowe adresy URL.")

    def _dodaj_log(self, wiadomosc: str) -> None:
        self.pole_logu.configure(state=tk.NORMAL)
        self.pole_logu.insert(tk.END, wiadomosc.rstrip() + "\n")
        self.pole_logu.see(tk.END)
        self.pole_logu.configure(state=tk.DISABLED)

    def _dodaj_do_kolejki_log(self, wiadomosc: str) -> None:
        self.kolejka_zdarzen.put(("log", wiadomosc))

    def _dodaj_do_kolejki_postep(self, procent: int, opis: str) -> None:
        self.kolejka_zdarzen.put(("postep", (procent, opis)))

    def _obsluz_kolejke_zdarzen(self) -> None:
        try:
            while True:
                typ, wartosc = self.kolejka_zdarzen.get_nowait()
                if typ == "log":
                    self._dodaj_log(str(wartosc))
                elif typ == "postep":
                    procent, opis = wartosc
                    self.zmienna_postepu.set(float(procent))
                    self.zmienna_opisu_postepu.set(str(opis))
        except queue.Empty:
            pass
        self.root.after(120, self._obsluz_kolejke_zdarzen)

    def _przywroc_ustawienia_domyslne(self) -> None:
        domyslne = USTAWIENIA
        self.zmienna_pliku_wejsciowego.set(str(domyslne.plik_wejsciowy))
        self.zmienna_katalogu_wyjsciowego.set(str(domyslne.katalog_wyjsciowy))
        self.zmienna_tylko_ta_sama_domena.set(domyslne.tylko_ta_sama_domena)
        self.zmienna_maks_liczba_stron.set(str(domyslne.maksymalna_liczba_stron))
        self.zmienna_maks_liczba_linkow.set(
            "" if domyslne.maksymalna_liczba_linkow_na_strone is None else str(domyslne.maksymalna_liczba_linkow_na_strone)
        )
        self.zmienna_timeout.set(str(domyslne.timeout_zadania))
        self.zmienna_opoznienia.set(str(domyslne.opoznienie_miedzy_zadaniami))
        self.zmienna_top_n.set(str(domyslne.top_n_pagerank))
        self.zmienna_weryfikacji_ssl.set(domyslne.weryfikuj_ssl)
        self.zmienna_przekierowan.set(domyslne.podazaj_za_przekierowaniami)
        self._wczytaj_adresy_z_ustawionego_pliku()
        self.zmienna_statusu.set("Przywrócono ustawienia domyślne.")
        self.zmienna_opisu_postepu.set("Brak aktywnej analizy.")
        self.zmienna_postepu.set(0.0)

    def _pobierz_adresy_z_gui(self) -> list[str]:
        tekst = self.pole_adresow.get("1.0", tk.END)
        adresy = wczytaj_url_z_tekstu(tekst)
        if not adresy:
            raise ValueError("Lista adresów URL jest pusta albo zawiera wyłącznie niepoprawne wpisy.")
        return adresy

    def _zbuduj_konfiguracje(self) -> KonfiguracjaAnalizy:
        plik_wejsciowy = Path(self.zmienna_pliku_wejsciowego.get().strip())
        katalog_wyjsciowy = Path(self.zmienna_katalogu_wyjsciowego.get().strip())

        if not plik_wejsciowy:
            raise ValueError("Wskaż plik wejściowy.")
        if not katalog_wyjsciowy:
            raise ValueError("Wskaż katalog wynikowy.")

        maksymalna_liczba_stron = int(self.zmienna_maks_liczba_stron.get().strip())
        if maksymalna_liczba_stron <= 0:
            raise ValueError("Maksymalna liczba stron musi być większa od zera.")

        tekst_limitu_linkow = self.zmienna_maks_liczba_linkow.get().strip()
        maksymalna_liczba_linkow_na_strone = None if not tekst_limitu_linkow else int(tekst_limitu_linkow)
        if (
            maksymalna_liczba_linkow_na_strone is not None
            and maksymalna_liczba_linkow_na_strone <= 0
        ):
            raise ValueError("Limit linków na stronę musi być większy od zera albo pusty.")

        timeout_zadania = int(self.zmienna_timeout.get().strip())
        if timeout_zadania <= 0:
            raise ValueError("Timeout musi być większy od zera.")

        opoznienie_miedzy_zadaniami = float(self.zmienna_opoznienia.get().strip())
        if opoznienie_miedzy_zadaniami < 0:
            raise ValueError("Opóźnienie nie może być ujemne.")

        top_n_pagerank = int(self.zmienna_top_n.get().strip())
        if top_n_pagerank <= 0:
            raise ValueError("Top N stron według PageRank musi być większe od zera.")

        return KonfiguracjaAnalizy(
            plik_wejsciowy=plik_wejsciowy,
            katalog_wyjsciowy=katalog_wyjsciowy,
            tylko_ta_sama_domena=self.zmienna_tylko_ta_sama_domena.get(),
            maksymalna_liczba_stron=maksymalna_liczba_stron,
            maksymalna_liczba_linkow_na_strone=maksymalna_liczba_linkow_na_strone,
            timeout_zadania=timeout_zadania,
            user_agent=USTAWIENIA.user_agent,
            opoznienie_miedzy_zadaniami=opoznienie_miedzy_zadaniami,
            weryfikuj_ssl=self.zmienna_weryfikacji_ssl.get(),
            podazaj_za_przekierowaniami=self.zmienna_przekierowan.get(),
            top_n_pagerank=top_n_pagerank,
            rozmiar_rysunku_grafu=USTAWIENIA.rozmiar_rysunku_grafu,
            ziarno_losowe=USTAWIENIA.ziarno_losowe,
        )

    def _uruchom_analize(self) -> None:
        if self.watek_roboczy and self.watek_roboczy.is_alive():
            messagebox.showwarning("Analiza w toku", "Poczekaj, aż aktualna analiza się zakończy.")
            return

        try:
            konfiguracja = self._zbuduj_konfiguracje()
            adresy = self._pobierz_adresy_z_gui()
            zapisz_url_do_pliku(adresy, konfiguracja.plik_wejsciowy)
        except Exception as exc:
            messagebox.showerror("Błędna konfiguracja", str(exc))
            return

        self._dodaj_log("-" * 72)
        self._dodaj_log("Start analizy z poziomu GUI.")
        self._dodaj_log(f"Plik wejściowy: {konfiguracja.plik_wejsciowy}")
        self._dodaj_log(f"Katalog wynikowy: {konfiguracja.katalog_wyjsciowy}")
        self._dodaj_log(f"Liczba adresów startowych: {len(adresy)}")
        self.zmienna_statusu.set("Analiza uruchomiona...")
        self.zmienna_opisu_postepu.set("Przygotowanie analizy...")
        self.zmienna_postepu.set(0.0)
        self.przycisk_uruchom.configure(state=tk.DISABLED)

        self.watek_roboczy = threading.Thread(
            target=self._worker_analizy,
            args=(konfiguracja, adresy),
            daemon=True,
        )
        self.watek_roboczy.start()

    def _worker_analizy(self, konfiguracja: KonfiguracjaAnalizy, adresy: list[str]) -> None:
        try:
            wynik = uruchom_pelna_analize(
                konfiguracja=konfiguracja,
                adresy_startowe=adresy,
                callback_logu=self._dodaj_do_kolejki_log,
                callback_postepu=self._dodaj_do_kolejki_postep,
            )
            self.ostatni_wynik = wynik
            self.root.after(0, self._po_udanej_analizie, wynik)
        except Exception as exc:
            sledzenie_bledu = traceback.format_exc()
            self._dodaj_do_kolejki_log("Wystąpił błąd podczas analizy.")
            self._dodaj_do_kolejki_log(sledzenie_bledu)
            self.root.after(0, self._po_bledzie_analizy, exc)

    def _po_udanej_analizie(self, wynik: WynikAnalizy) -> None:
        self.przycisk_uruchom.configure(state=tk.NORMAL)
        self.zmienna_statusu.set("Analiza zakończona powodzeniem.")
        self.zmienna_postepu.set(100.0)
        self.zmienna_opisu_postepu.set(
            f"Węzły: {wynik.podsumowanie_sieci.liczba_wezlow} | "
            f"Krawędzie: {wynik.podsumowanie_sieci.liczba_krawedzi} | "
            f"Składowe: {wynik.podsumowanie_sieci.liczba_slabo_spojnych_skladowych}"
        )
        self._wyswietl_wykresy(wynik)
        messagebox.showinfo(
            "Gotowe",
            (
                "Analiza zakończona.\n\n"
                f"Węzły: {wynik.podsumowanie_sieci.liczba_wezlow}\n"
                f"Krawędzie: {wynik.podsumowanie_sieci.liczba_krawedzi}\n"
                f"Wyniki zapisano w:\n{wynik.katalog_wyjsciowy}"
            ),
        )

    def _po_bledzie_analizy(self, exc: Exception) -> None:
        self.przycisk_uruchom.configure(state=tk.NORMAL)
        self.zmienna_statusu.set("Analiza zakończona błędem.")
        self.zmienna_opisu_postepu.set("Wystąpił błąd podczas analizy.")
        messagebox.showerror("Błąd", str(exc))

    def _wyswietl_wykresy(self, wynik: WynikAnalizy) -> None:
        figury = utworz_figury_wizualizacji(
            graf=wynik.graf,
            dataframe_metryk=wynik.dataframe_metryk,
            konfiguracja=wynik.konfiguracja,
        )

        for klucz, figura in figury.items():
            ramka = self.ramki_wykresow[klucz]
            for widget in ramka.winfo_children():
                widget.destroy()

            canvas = FigureCanvasTkAgg(figura, master=ramka)
            canvas.draw()
            widget_canvas = canvas.get_tk_widget()
            widget_canvas.grid(row=0, column=0, sticky="nsew")
            self.canvasy_wykresow[klucz] = canvas

    def _otworz_katalog_wyjsciowy(self) -> None:
        katalog = Path(self.zmienna_katalogu_wyjsciowego.get().strip())
        if not katalog.exists():
            messagebox.showwarning("Brak katalogu", "Katalog wynikowy jeszcze nie istnieje.")
            return

        try:
            if sys.platform.startswith("win"):
                os.startfile(katalog)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", str(katalog)], check=False)
            else:
                subprocess.run(["xdg-open", str(katalog)], check=False)
        except Exception as exc:
            messagebox.showerror("Błąd", f"Nie udało się otworzyć katalogu:\n{exc}")


def main() -> None:
    root = tk.Tk()

    try:
        styl = ttk.Style(root)
        dostepne_motywy = styl.theme_names()
        for kandydat in ("vista", "clam", "default"):
            if kandydat in dostepne_motywy:
                styl.theme_use(kandydat)
                break
    except Exception:
        pass

    InterfejsAnalizatoraHiperlinkow(root)
    root.mainloop()


if __name__ == "__main__":
    main()

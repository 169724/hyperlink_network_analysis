# Analiza struktury sieci stron internetowych na podstawie połączeń hyperlinkowych

Projekt w Pythonie do budowy i analizy skierowanego grafu stron WWW na podstawie linków hyperlinkowych.  
Wersja rozszerzona zawiera tryb konsolowy oraz rozbudowane GUI w `tkinter`.

## Co zostało dodane i zmienione

- pełne spolszczenie kodu i interfejsu,
- pasek ładowania podczas analizy,
- możliwość edytowania adresów URL bezpośrednio w GUI,
- wykresy wyświetlane w osobnych zakładkach GUI,
- liniowy wykres rozkładu stopni zamiast histogramu.

## Struktura projektu

```text
hyperlink_network_analysis/
├── main.py
├── gui.py
├── app_core.py
├── scraper.py
├── graph_builder.py
├── analysis.py
├── visualization.py
├── utils.py
├── config.py
├── requirements.txt
├── README.md
├── input_urls.txt
└── output/
    └── .gitkeep
```

## Instalacja

```bash
python -m pip install -r requirements.txt
```

Na Windows, gdy komenda `pip` nie działa:

```powershell
py -m pip install -r requirements.txt
```

## Uruchomienie GUI

```bash
python gui.py
```

## Uruchomienie wersji konsolowej

```bash
python main.py
```

## Jak działa GUI

### Zakładka „Ustawienia”
Pozwala ustawić:
- plik wejściowy,
- katalog wynikowy,
- ograniczenie do tej samej domeny,
- limit liczby stron,
- limit liczby linków na stronę,
- timeout,
- opóźnienie między żądaniami,
- liczbę top stron według PageRank.

### Zakładka „Adresy URL”
Pozwala:
- edytować adresy ręcznie,
- wkleić wiele adresów naraz,
- wczytać adresy z pliku,
- zapisać adresy do pliku,
- wyczyścić listę,
- wstawić przykładowe adresy.

### Zakładki z wykresami
Po zakończeniu analizy GUI pokazuje:
- graf sieci,
- wykres top stron według PageRank,
- liniowy wykres rozkładu stopni.

## Wyniki zapisywane do katalogu output

- `edges.csv`
- `node_metrics.csv`
- `network_summary.txt`
- `network_graph.png`
- `top_pagerank.png`
- `degree_histogram.png`

## Uwaga

Plik `degree_histogram.png` zachował swoją historyczną nazwę, ale zawiera już wykres liniowy rozkładu stopni, a nie histogram.

## Możliwe dalsze rozszerzenia

- analiza wielu domen jednocześnie,
- filtrowanie linków po wzorcach,
- analiza odporności sieci,
- wykrywanie społeczności,
- eksport dodatkowych raportów.

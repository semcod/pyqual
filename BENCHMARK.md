# Benchmark — opis działania i użycie

Framework benchmarkowy w `benchmark.py` mierzy wydajność prefact oraz dowolnej innej biblioteki Python. Obejmuje cztery kategorie pomiarów: czas startu, czas unit testów, przepustowość skanowania i wydajność in-process.

---

## Szybki start

```bash
# Wszystkie zestawy
python3 benchmark.py

# Tylko jeden zestaw
python3 benchmark.py --suite startup
python3 benchmark.py --suite tests
python3 benchmark.py --suite scan
python3 benchmark.py --suite throughput

# Wyjście JSON (do dalszej analizy)
python3 benchmark.py --json

# Tekst bez kolorów (CI, logi)
python3 benchmark.py --plain

# Globalny próg czasu (FAIL jeśli przekroczony)
python3 benchmark.py --threshold 5.0
```

---

## Zestawy (suites)

### `startup` — czas startu i importu
Mierzy jak szybko biblioteka jest dostępna po uruchomieniu procesu.

| Sonda | Co mierzy |
|---|---|
| `ImportProbe("prefact")` | Czas `import prefact` w świeżym procesie |
| `ImportProbe("prefact.engine")` | Czas importu konkretnego modułu |
| `CLIProbe(["prefact", "--help"])` | Czas odpowiedzi CLI |

Każda sonda uruchamia pomiar **3 razy** i bierze najlepszy wynik (best-of-3), eliminując szum systemowy.

### `tests` — czas unit testów
Uruchamia pytest dla całego katalogu `tests/` oraz każdego pliku testowego osobno. Pozwala wykryć który plik testowy dominuje czas całego suite'a.

```
full test suite      4.3 s   PASS
pytest test_engine.py  4.4 s   PASS   ← dominuje
pytest test_config.py  0.9 s   PASS
```

### `scan` — przepustowość skanowania plików
Tworzy tymczasowe pliki Python z celowo wprowadzonymi problemami (relative imports, duplicate imports) i mierzy czas pełnego przebiegu `engine.run()`.

| Konfiguracja | Przykładowy próg |
|---|---|
| 50 plików × 1 KB | 10 s |
| 100 plików × 1 KB | 20 s |
| 200 plików × 5 KB | 40 s |

### `throughput` — wydajność in-process
Wywołuje `scanner.scan()` wielokrotnie w tym samym procesie (10 iteracji × 20 plików) i oblicza **operacje/sekundę** oraz **średni czas/operację** w ms.

---

## Architektura

```
benchmark.py
├── BenchmarkResult        – wynik pojedynczego pomiaru (czas, status, extra)
├── BenchmarkProbe (ABC)   – abstrakcyjna sonda
│   ├── ImportProbe        – czas importu modułu (subprocess)
│   ├── CLIProbe           – czas komendy CLI (subprocess)
│   ├── UnitTestProbe      – czas pytest (subprocess)
│   ├── ThroughputProbe    – wywołania/s dowolnej funkcji (in-process)
│   └── ScanProbe          – przepustowość prefact engine (subprocess + temp files)
├── BenchmarkSuite         – kolekcja sond + runner
└── BenchmarkReporter      – wyświetlanie: rich table / plain text / JSON
```

### Statusy wyników

| Status | Znaczenie |
|---|---|
| `OK` | Sonda przebiegła, brak progu |
| `PASS` | Czas ≤ próg (`--threshold`) |
| `FAIL` | Czas > próg |
| `ERROR` | Wyjątek lub brakujące narzędzie |

---

## Użycie z dowolną biblioteką

`benchmark.py` zawiera helper `benchmark_library()`, który można zaimportować do własnego skryptu:

```python
from benchmark import benchmark_library, BenchmarkReporter

# Pomiar dowolnej biblioteki
suite = benchmark_library(
    module="requests",
    cli_commands=[
        ["python3", "-c", "import requests; print(requests.__version__)"],
    ],
    test_path=Path("tests/"),
    threshold_import=1.0,
    threshold_cli=2.0,
    threshold_tests=30.0,
)

results = suite.run()
BenchmarkReporter(results).print()
```

Lub własne sondy:

```python
from benchmark import ThroughputProbe, CLIProbe, ImportProbe, BenchmarkSuite, BenchmarkReporter

suite = BenchmarkSuite("moja-biblioteka")

# Import
suite.add(ImportProbe("django", threshold=3.0))

# CLI
suite.add(CLIProbe(["django-admin", "version"], threshold=2.0))

# Własna funkcja
import json, pathlib
data = pathlib.Path("data.json").read_text()
suite.add(ThroughputProbe(
    label="json.loads duży plik",
    fn=lambda: json.loads(data),
    n=10_000,
    threshold_ops=5_000,  # minimum 5000 ops/s aby PASS
))

results = suite.run()
BenchmarkReporter(results).print()
```

---

## Interpretacja wyników

### Czas startu (`startup`)

```
import prefact          29 ms   PASS   ← dobry wynik
import prefact.engine  228 ms   PASS   ← dopuszczalny
```

Duże wartości (>1 s) wskazują na zbyt wiele importów przy starcie lub powolną inicjalizację pluginów.

### Czas testów (`tests`)

Jeśli jeden plik testowy zajmuje tyle co cały suite, prawdopodobnie:
- tworzy dużo plików tymczasowych
- używa powolnych fixturów (`scope="function"` zamiast `scope="session"`)
- wywołuje subprocess dla każdego testu

### Przepustowość skanowania (`scan`)

Niska liczba `files/sec` wskazuje na:

| Problem | Symptom | Naprawa |
|---|---|---|
| Wiele subprocesów per plik | ruff/mypy/isort × N reguł | Batching (zaimplementowane) |
| Brak równoległości | 1 wątek na wszystkie pliki | ThreadPoolExecutor (zaimplementowane) |
| Powtórne parsowanie AST | każda reguła parsuje od nowa | AST cache (planowane) |
| Duże pliki | pliki >100KB ładowane do RAM | filtr rozmiaru |

---

## Wykryte i naprawione bottlenecki

### Problem 1 — Wielokrotne wywołania `ruff` per plik

**Przed:** każda reguła ruff-based spawowała osobny subprocess
```
RuffWildcardImports  →  ruff check file.py --select F403
RuffUnusedImports    →  ruff check file.py --select F401
RuffSortedImports    →  ruff check file.py --select I001,I002
RuffPrintStatements  →  ruff check file.py --select T201
RuffDuplicateImports →  ruff check file.py --select F811
# = 5 procesów na każdy plik
```

**Po** (`src/prefact/rules/ruff_based.py`):
```
RuffHelper._run_ruff_all(file.py)  →  ruff check file.py --select F401,F403,...
# = 1 proces na każdy plik, wyniki cache'owane i filtrowane per reguła
```

**Wynik:** ~5× mniej wywołań subprocess.

### Problem 2 — Sekwencyjne skanowanie plików

**Przed** (`scanner.py`):
```python
for path, source in sources.items():
    for rule in self._rules:
        issues.extend(rule.scan_file(path, source))
```

**Po** (`scanner.py`):
```python
with ThreadPoolExecutor(max_workers=min(cpu_count, 8)) as executor:
    futures = {executor.submit(self._scan_single, path, source): path ...}
```

**Wynik:** pliki skanowane równolegle — na 8-rdzeniowym CPU teoretycznie 8× szybciej.

---

## Uruchamianie w CI

```yaml
# .github/workflows/benchmark.yml
- name: Performance benchmark
  run: python3 benchmark.py --plain --threshold 30.0
  # Zwraca exit code 1 jeśli jakikolwiek próg przekroczony
```

```bash
# Lokalne porównanie przed/po zmianach
python3 benchmark.py --json > before.json
# ... zmiany w kodzie ...
python3 benchmark.py --json > after.json
```

---

## Wymagania

| Pakiet | Wymagany | Cel |
|---|---|---|
| `rich` | opcjonalny | kolorowa tabela (fallback: plain text) |
| `pytest` | opcjonalny | sonda `UnitTestProbe` |
| `ruff` | opcjonalny | sonda `ScanProbe` z regułami ruff |
| `prefact` | wymagany dla `ScanProbe` | skanowanie plików |

Wszystkie sondy obsługują brakujące narzędzia — zwracają status `ERROR` zamiast rzucać wyjątek.

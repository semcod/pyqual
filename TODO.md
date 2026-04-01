# GitHub Issue #10

- [x] #10: Refactor: Extract magic numbers in pyqual/constants.py

### Issue Body
## Problem

Plik `pyqual/constants.py` zawiera magiczne liczby (np. timeout=30, port=8000) które powinny być zdefiniowane jako stałe.

## Zadanie

1. Znajdź wszystkie magiczne liczby w `pyqual/constants.py`
2. Zamień je na nazwane stałe
3. Upewnij się że kod nadal działa

## Przykład

```python
# Zamiast:
timeout = 30

# Użyj:
DEFAULT_TIMEOUT = 30
timeout = DEFAULT_TIMEOUT
```

---
*Auto-fix przez pyqual*

---
*Auto-generated from GitHub issue event*

# GitHub Issue #9

- [x] #9: Fix: Remove unused imports in pyqual/tools.py

### Issue Body
## Problem

Plik  zawiera nieużywane importy na górze pliku. Należy je usunąć aby poprawić czytelność kodu.

## Zadanie

1. Zidentyfikuj nieużywane importy w 
2. Usuń nieużywane importy
3. Upewnij się że kod nadal działa poprawnie

## Oczekiwany wynik

Czystszy kod bez zbędnych importów.

---
*To zadanie zostanie przetworzone automatycznie przez pyqual*


---
*Auto-generated from GitHub issue event*

# GitHub Issue #7

- [x] #7: Test

### Issue Body
Body pyqual-fix

---
*Auto-generated from GitHub issue event*

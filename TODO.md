# GitHub Issue #13

- [x] #13: Test: Verify GitHub Actions auto-processing

### Issue Body
## Test

Ten issue testuje czy GitHub Actions automatycznie:
1. Przetwarza issue po utworzeniu
2. Uruchamia pyqual run
3. Dodaje komentarz z wynikami
4. Zamyka issue jeśli wszystkie gate przechodzą

## Oczekiwany flow

```
Issue created with label pyqual-fix
  ↓
Workflow triggers (issues: opened)
  ↓
pyqual run --config pyqual.yaml
  ↓
Post comment with completion %
  ↓
Close issue if all gates pass
```

---
*Test auto-close functionality*

---
*Auto-generated from GitHub issue event*

# GitHub Issue #12

- [x] #12: [TEST] GitHub Actions Integration Test

### Issue Body
## Test Issue
    
This issue was created automatically by test script.

### Purpose
Verify GitHub Actions integration works correctly.

### Checklist
- [ ] Issue created
- [ ] Can be fetched by pyqual
- [ ] Comments can be posted

---
*Auto-generated test*

---
*Auto-generated from GitHub issue event*

# GitHub Issue #11

- [x] #11: Add GitHub Actions integration documentation to README

### Issue Body
## Problem

README.md nie zawiera dokumentacji nowej funkcji GitHub Actions integracji. Użytkownicy nie wiedzą jak używać automatycznego przetwarzania issue przez pyqual.

## Zadanie

Dodaj do README.md sekcję opisującą:
1. Jak działa automatyczne przetwarzanie issue
2. Wymagane labelki (np. `pyqual-fix`)
3. Konfiguracja workflow
4. Przykład użycia

## Oczekiwany wynik

Zaktualizowany README.md z nową sekcją "GitHub Actions Integration".

---
*Auto-fix przez pyqual*

---
*Auto-generated from GitHub issue event*

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

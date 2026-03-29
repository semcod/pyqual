---
title: "devloop — deklaratywne pętle jakości dla developmentu z AI"
slug: devloop-declarative-quality-gates
date: 2026-03-29
category: Projekty
tags: [devloop, pipeline, CI/CD, quality gates, metryki, Python, PyPI]
excerpt: "Jeden plik YAML, jedno polecenie. Pipeline iteruje dopóki Twój kod nie spełni progów jakości — CC, coverage, vallm pass rate. Developer projektuje reguły, AI pracuje."
---

# devloop — deklaratywne pętle jakości dla developmentu z AI

## Problem

Masz Copilota, Claude'a, GPT-4o. Generują kod. Ale kto sprawdza, czy ten kod spełnia Twoje standardy jakości? I kto automatycznie iteruje, jeśli nie spełnia?

Dziś to wygląda tak: LLM generuje → developer czyta → poprawia ręcznie → wkleja z powrotem. Powtarzalne, nieefektywne, nieskalowalne.

## Rozwiązanie

devloop zamyka tę pętlę: definiujesz metryki i progi w jednym pliku YAML → pipeline uruchamia narzędzia → sprawdza quality gates → jeśli nie przechodzą, LLM naprawia → re-check → powtarza aż do sukcesu.

```bash
pip install devloop
devloop init
devloop run
```

## Jeden plik, cały pipeline

```yaml
pipeline:
  name: quality-loop

  metrics:
    cc_max: 15           # złożoność cyklomatyczna ≤ 15
    vallm_pass_min: 90   # walidacja vallm ≥ 90%
    coverage_min: 80     # pokrycie testami ≥ 80%

  stages:
    - name: analyze
      run: code2llm ./ -f toon,evolution
    - name: validate
      run: vallm batch ./ --recursive
    - name: fix
      run: echo "Twój LLM fixer tutaj"
      when: metrics_fail
    - name: test
      run: pytest --cov

  loop:
    max_iterations: 3
    on_fail: report
```

Developer nie pisze promptów. Definiuje progi i pozwala narzędziom działać.

## Metryki paczki

557 linii kodu źródłowego. 5 plików. 10 testów, 100% pass. CC̄ poniżej 2.5. To jest paczka, która praktykuje to, co głosi — utrzymuje własne standardy jakości.

Dla porównania: algitex, który robił „wszystko", ma 29,448 linii i vallm pass 42.8%. devloop robi jedną rzecz dobrze.

## Dlaczego osobna paczka, nie algitex?

algitex próbuje robić wszystko: analiza, fixy, TODO processing, NLP, benchmarki, dashboardy, 34 przykłady. Efekt: 64 critical issues, 3 god modules, vallm pass poniżej 50%.

devloop robi jedną rzecz: deklaratywne pętle jakości. algitex może importować devloop jako zależność. Oba stają się lepsze.

## Integracja z ekosystemem

devloop czyta metryki z narzędzi, które już masz:

- `analysis_toon.yaml` z code2llm → CC̄, critical count
- `validation_toon.yaml` z vallm → pass rate
- `.devloop/coverage.json` z pytest → coverage

Nie wymaga żadnego z nich do działania — stages są dowolnymi komendami shell.

---

*PyPI: pip install devloop | GitHub: github.com/semcod/devloop | Licencja: Apache 2.0*

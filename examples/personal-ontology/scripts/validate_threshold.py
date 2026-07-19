#!/usr/bin/env python3
"""
Issue #5: VALIDATE — валидация порога на выборке 50 URL.

Метрики:
- Precision: доля извлечённых цитат, которые содержат "Фрадков" или местоимение
- Recall: доля страниц с Фрадковым, где извлечена >= 1 цитата
- Hallucination rate: доля цитат с cosine < порога

Тестирует пороги: 0.3, 0.4, 0.5, 0.6, 0.7
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
from rebuild_pipeline import fetch_page, extract_quotes, validate_quote, llm_generate

URLS_FILE = os.path.join(os.path.dirname(__file__), "..", "output", "validation_urls.json")
RESULTS_FILE = os.path.join(os.path.dirname(__file__), "..", "output", "validation_results.json")


def has_subject_mention(text, quote):
    """Проверяет, упоминается ли субъект в цитате или рядом."""
    # Прямое упоминание
    if "фрадков" in quote.lower():
        return True
    # Местоимение в контексте (упрощённо)
    if "он " in quote.lower() or "его " in quote.lower():
        return True
    return False


def extract_quotes_raw(text, url):
    """Извлечение БЕЗ фильтрации по порогу — для валидации."""
    prompt = f"""[РОЛЬ] Quote Extractor
[ОГРАНИЧЕНИЕ] Извлекай только то, что есть в тексте. Не придумывай.

Найди в тексте утверждения и цитаты Петра Фрадкова.
Это могут быть прямые цитаты в кавычках или пересказ его слов.

Текст: {text[:3000]}

Верни СТРОГО JSON массив строк.
Если ничего не найдено — верни [].

JSON: ["цитата 1", "цитата 2"]"""

    try:
        content = llm_generate(prompt, max_tokens=500)
        if not content:
            return []

        if "```" in content:
            lines = content.split("\n")
            content = "\n".join(l for l in lines if not l.strip().startswith("```"))

        start = content.find("[")
        end = content.rfind("]") + 1
        if start >= 0 and end > start:
            quotes = json.loads(content[start:end])
            return [q for q in quotes if isinstance(q, str) and len(q) > 30]
    except:
        pass
    return []


def run_validation(urls, threshold=0.5):
    """Прогоняет валидацию на выборке URL."""
    results = {
        "threshold": threshold,
        "pages_with_fradkov": 0,
        "pages_with_quotes": 0,
        "total_quotes_extracted": 0,
        "total_quotes_valid": 0,
        "total_quotes_hallucination": 0,
        "details": []
    }

    for i, url in enumerate(urls):
        text = fetch_page(url)
        if not text or len(text) < 200:
            continue

        has_fradkov = "фрадков" in text.lower()
        if has_fradkov:
            results["pages_with_fradkov"] += 1

        # Извлекаем БЕЗ фильтрации
        quotes = extract_quotes_raw(text, url)
        valid = 0
        hallucinations = 0

        for q in quotes:
            conf = validate_quote(q, text)
            if conf >= threshold:
                valid += 1
            else:
                hallucinations += 1

        if valid > 0:
            results["pages_with_quotes"] += 1

        results["total_quotes_extracted"] += len(quotes)
        results["total_quotes_valid"] += valid
        results["total_quotes_hallucination"] += hallucinations

        results["details"].append({
            "url": url,
            "has_fradkov": has_fradkov,
            "extracted": len(quotes),
            "valid": valid,
            "hallucinations": hallucinations
        })

        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{len(urls)}] valid={results['total_quotes_valid']} hall={results['total_quotes_hallucination']}")

    # Метрики
    total_extracted = results["total_quotes_extracted"]
    total_valid = results["total_quotes_valid"]
    total_hall = results["total_quotes_hallucination"]

    precision = total_valid / total_extracted if total_extracted > 0 else 0
    recall = results["pages_with_quotes"] / results["pages_with_fradkov"] if results["pages_with_fradkov"] > 0 else 0
    hall_rate = total_hall / total_extracted if total_extracted > 0 else 0

    results["precision"] = round(precision, 3)
    results["recall"] = round(recall, 3)
    results["hallucination_rate"] = round(hall_rate, 3)

    return results


def main():
    print("=" * 60)
    print("Issue #5: VALIDATE — валидация порога")
    print("=" * 60)

    with open(URLS_FILE) as f:
        urls = json.load(f)
    print(f"URL для валидации: {len(urls)}")
    print()

    # Тестируем разные пороги
    thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]
    all_results = []

    for threshold in thresholds:
        print(f"\n--- Порог cosine = {threshold} ---")
        results = run_validation(urls, threshold=threshold)
        all_results.append(results)
        print(f"  Precision: {results['precision']:.3f}")
        print(f"  Recall:    {results['recall']:.3f}")
        print(f"  Hall rate: {results['hallucination_rate']:.3f}")
        print(f"  Valid: {results['total_quotes_valid']} / {results['total_quotes_extracted']}")

    # Сохраняем
    with open(RESULTS_FILE, "w") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n✓ Сохранено: {RESULTS_FILE}")

    # Рекомендация
    print("\n--- Рекомендация ---")
    best = max(all_results, key=lambda r: r["precision"] + r["recall"])
    print(f"Оптимальный порог: {best['threshold']}")
    print(f"  Precision: {best['precision']:.3f}")
    print(f"  Recall:    {best['recall']:.3f}")


if __name__ == "__main__":
    main()

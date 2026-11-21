
import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
import statistics

URL = "https://www.walmart.com/ip/Great-Value-Large-White-Eggs-18-Count/172844767?classType=REGULAR&athbdg=L1200&from=/search"
TRIALS = 30

results = []

with requests.Session() as session:
    for i in range(TRIALS):
        start_total = time.perf_counter()

        try:
            # Measure HTTP request and HTML download
            start_request = time.perf_counter()
            response = session.get(URL, timeout=15)
            response.raise_for_status()
            html = response.text
            request_time = time.perf_counter() - start_request

            # Measure HTML parsing and extraction
            start_parse = time.perf_counter()
            soup = BeautifulSoup(html, "html.parser")

            # Replace with actual product price selector
            price_element = soup.select_one(".price")
            price = (
                price_element.get_text(strip=True)
                if price_element else None
            )

            parse_time = time.perf_counter() - start_parse
            total_time = time.perf_counter() - start_total

            results.append({
                "trial": i + 1,
                "request_s": request_time,
                "parse_s": parse_time,
                "total_s": total_time,
                "success": price is not None,
                "price": price
            })

        except requests.RequestException as exc:
            results.append({
                "trial": i + 1,
                "request_s": None,
                "parse_s": None,
                "total_s": time.perf_counter() - start_total,
                "success": False,
                "price": None
            })
            print(f"Trial {i + 1} failed: {exc}")

        # Avoid rapid repeated requests
        time.sleep(2)

df = pd.DataFrame(results)
df.to_csv("scraping_benchmark.csv", index=False)

print(df[["request_s", "parse_s", "total_s"]].describe())
print(f"Success rate: {df['success'].mean():.1%}")
print(f"P95 total: {df['total_s'].quantile(.95):.3f} s")

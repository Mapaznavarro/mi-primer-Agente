import json
import os
import re
import sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen

PRODUCT_URL = "https://www.jumbo.cl/tomate-cocktail-frutas-y-verduras-jumbo-variedades/p"
STATE_PATH = "state.json"

# Si defines ISSUE_NUMBER, actualiza ese Issue (modo "Issue fijo").
# Si no lo defines, crea un Issue nuevo cada vez que detecta un cambio.
ISSUE_NUMBER = os.getenv("ISSUE_NUMBER")  # e.g. "1"
REPO = os.getenv("GITHUB_REPOSITORY")     # "owner/repo"
TOKEN = os.getenv("GITHUB_TOKEN")

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)

def fetch_html(url: str) -> str:
    req = Request(url, headers={"User-Agent": UA, "Accept-Language": "es-CL,es;q=0.9,en;q=0.8"})
    with urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")

def extract_price_clp(html: str) -> int:
    # 1) JSON-ish: "price": "12990"
    m = re.search(r'"price"\s*:\s*"?(?P<p>\d+(?:[.,]\d+)?)"?', html)
    if m:
        raw = m.group("p").replace(".", "").replace(",", ".")
        return int(float(raw))

    # 2) Visual: $12.990
    m = re.search(r"\$\s*(\d{1,3}(?:\.\d{3})+|\d+)", html)
    if m:
        return int(m.group(1).replace(".", ""))

    # 3) meta itemprop price
    m = re.search(r'itemprop\s*=\s*"price"[^>]*content\s*=\s*"(?P<p>\d+)"', html)
    if m:
        return int(m.group("p"))

    raise RuntimeError("No pude extraer el precio del HTML (posible render con JS o cambio de estructura).")

def load_state() -> dict:
    if not os.path.exists(STATE_PATH):
        return {}
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(state: dict) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def gh_request(method: str, url: str, payload: dict | None = None) -> dict:
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN no está definido (en Actions viene por defecto).")

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "tomato-price-agent",
        },
    )
    with urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}

def notify(title: str, body: str) -> None:
    if not REPO:
        raise RuntimeError("GITHUB_REPOSITORY no está definido.")
    api = "https://api.github.com"

    if ISSUE_NUMBER:
        gh_request("PATCH", f"{api}/repos/{REPO}/issues/{ISSUE_NUMBER}", {"title": title, "body": body})
    else:
        gh_request("POST", f"{api}/repos/{REPO}/issues", {"title": title, "body": body})

def main() -> int:
    html = fetch_html(PRODUCT_URL)
    price = extract_price_clp(html)

    now = datetime.now(timezone.utc).isoformat()
    state = load_state()

    last_price = state.get("last_price")
    last_seen = state.get("last_seen")

    changed = (last_price is None) or (int(last_price) != int(price))

    state["last_price"] = int(price)
    state["last_seen"] = now
    save_state(state)

    if changed:
        title = "Cambio de precio: Tomate cherry/cocktail (Jumbo.cl)"
        body = "\n".join([
            f"- URL: {PRODUCT_URL}",
            f"- Precio actual: ${price} CLP",
            f"- Precio anterior: {('$' + str(last_price) + ' CLP') if last_price is not None else '(sin registro)'}",
            f"- Timestamp (UTC): {now}",
            f"- Timestamp anterior (UTC): {last_seen if last_seen else '(sin registro)'}",
        ])
        notify(title, body)
        print(f"Notificado. Nuevo precio: {price}")
    else:
        print(f"Sin cambio. Precio: {price}")

    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise

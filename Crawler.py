

import os, re, json
from bs4 import BeautifulSoup
import requests
import matplotlib.pyplot as plt
from PIL import Image
from io import BytesIO
import textwrap

# ---------------------------
# Helpers: parse local HTMLs
# ---------------------------
def read_file_if_exists(fname):
    if os.path.exists(fname):
        with open(fname, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    return None

def parse_amazon_html(html):
    """Attempt to extract title, price, image, url from an Amazon search page HTML (local)."""
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")

    # Find first search result by data-asin attribute
    item = soup.find(lambda tag: tag.name == "div" and tag.get("data-asin"))
    if not item:
        item = soup.find("div", {"data-component-type": "s-search-result"})
    if not item:
        return None

    # title
    title = None
    h2 = item.find("h2")
    if h2:
        title = h2.get_text(strip=True)
    if not title:
        span = item.find("span", class_=re.compile(r"a-size-.*title|a-text-normal"))
        title = span.get_text(strip=True) if span else None

    # price: try offscreen span or a-price-whole
    price = None
    price_tag = item.find("span", {"class": re.compile(r"a-price-whole|a-offscreen")})
    if price_tag:
        txt = price_tag.get_text()
        m = re.search(r'[\d,]+', txt)
        if m:
            price = float(m.group(0).replace(',', ''))

    # image
    img = None
    img_tag = item.find("img")
    if img_tag:
        img = img_tag.get("src") or img_tag.get("data-src")

    # link
    link = None
    a = item.find("a", href=True)
    if a:
        href = a["href"]
        if href.startswith("/"):
            link = "https://www.amazon.in" + href
        else:
            link = href

    return {"store":"Amazon", "title": title or "Not Available", "price": price, "url": link, "image": img}

def parse_flipkart_html(html):
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")

    # Flipkart search results often include elements with data-id
    item = soup.find(attrs={"data-id": True})
    if not item:
        # fallback: product cards with class _1AtVbE (older)
        item = soup.find("a", class_=re.compile(r"_1fQZEK|s1Q9rs|_2rpwqI"))
        if item:
            # get parent container
            parent = item.find_parent()
            item = parent or item

    if not item:
        return None

    title = None
    title_tag = item.find("a", class_=re.compile(r"s1Q9rs|_2rpwqI|_1fQZEK"))
    if title_tag:
        title = title_tag.get_text(strip=True)
    else:
        title = item.get_text(strip=True).split("\n")[0]

    price = None
    price_tag = item.find("div", class_=re.compile(r"_30jeq3|_25b18c|_1vC4OE"))
    if price_tag:
        m = re.search(r'[\d,]+', price_tag.get_text())
        if m:
            price = float(m.group(0).replace(',', ''))

    img = None
    img_tag = item.find("img")
    if img_tag:
        img = img_tag.get("src") or img_tag.get("data-src")

    link = None
    a = item.find("a", href=True)
    if a:
        href = a["href"]
        if href.startswith("/"):
            link = "https://www.flipkart.com" + href
        else:
            link = href

    return {"store":"Flipkart", "title": title or "Not Available", "price": price, "url": link, "image": img}

def parse_myntra_html(html):
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    # Myntra product base
    product = soup.find("li", class_=lambda x: x and "product-base" in x)
    if not product:
        product = soup.find("div", {"data-track": "product"})
    if not product:
        # fallback to first product link
        product = soup.find("a", href=re.compile(r"/product/"))
    if not product:
        return None

    title_tag = product.find("h3", class_=re.compile(r"product-brand"))
    title = title_tag.get_text(strip=True) if title_tag else (product.get_text(strip=True).split("\n")[0] if product else None)

    price = None
    p = product.find("span", class_=re.compile(r"product-discountedPrice|price"))
    if p:
        m = re.search(r'[\d,]+', p.get_text())
        if m:
            price = float(m.group(0).replace(',', ''))

    img = None
    img_tag = product.find("img")
    if img_tag:
        img = img_tag.get("src") or img_tag.get("data-src")

    link = None
    a = product.find("a", href=True)
    if a:
        href = a["href"]
        link = "https://www.myntra.com" + href if href.startswith("/") else href

    return {"store":"Myntra", "title": title or "Not Available", "price": price, "url": link, "image": img}

def parse_meesho_html(html):
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("div", class_=lambda x: x and "Card" in x) or soup.find("div", {"data-testid":"product-card"})
    if not card:
        card = soup.find("div", {"role":"article"}) or soup.find("a", href=re.compile(r"/product/"))
    if not card:
        return None

    title_tag = card.find(["p","h3"])
    title = title_tag.get_text(strip=True) if title_tag else (card.get_text(strip=True).split("\n")[0] if card else None)

    price = None
    p = card.find(lambda tag: tag.name in ["h5","span","p"] and '₹' in tag.get_text() if tag.get_text() else False)
    if p:
        m = re.search(r'[\d,]+', p.get_text())
        if m:
            price = float(m.group(0).replace(',', ''))

    img = None
    img_tag = card.find("img")
    if img_tag:
        img = img_tag.get("src") or img_tag.get("data-src")

    link = None
    a = card.find("a", href=True)
    if a:
        href = a["href"]
        link = "https://www.meesho.com" + href if href.startswith("/") else href

    return {"store":"Meesho", "title": title or "Not Available", "price": price, "url": link, "image": img}

# -----------------------------------
# Mock fallback (presentation-safe)
# -----------------------------------
def mock_for(product):
    p = product.strip().lower()
    samples = {
        "iphone 15": {
            "Amazon": {"title":"Apple iPhone 15 (128GB)","price":79999,"url":"https://amazon.example/iphone15","image":None},
            "Flipkart": {"title":"Apple iPhone 15 (128GB)","price":59900,"url":"https://flipkart.example/iphone15","image":None},
            "Myntra": {"title":"Apple iPhone 15 - Not Sold","price":None,"url":None,"image":None},
            "Meesho": {"title":"Apple iPhone 15 - Not Sold","price":None,"url":None,"image":None},
        },
        "kurti": {
            "Amazon": {"title":"Kurti Cotton","price":699,"url":"https://amazon.example/kurti","image":None},
            "Flipkart": {"title":"Veemora Kurti","price":500,"url":"https://flipkart.example/kurti","image":None},
            "Myntra": {"title":"Women Kurti","price":749,"url":"https://myntra.example/kurti","image":None},
            "Meesho": {"title":"Kurti - Meesho Seller","price":450,"url":"https://meesho.example/kurti","image":None},
        }
    }
    default = {
        "Amazon":{"title":f"{product} - Amazon","price":None,"url":None,"image":None},
        "Flipkart":{"title":f"{product} - Flipkart","price":None,"url":None,"image":None},
        "Myntra":{"title":f"{product} - Myntra","price":None,"url":None,"image":None},
        "Meesho":{"title":f"{product} - Meesho","price":None,"url":None,"image":None},
    }
    return samples.get(p, default)

# --------------------------
# Compose results & display
# --------------------------
def build_results(product):
    # Try reading local html files
    am_html = read_file_if_exists("amazon.html")
    fk_html = read_file_if_exists("flipkart.html")
    my_html = read_file_if_exists("myntra.html")
    me_html = read_file_if_exists("meesho.html")

    am = parse_amazon_html(am_html)
    fk = parse_flipkart_html(fk_html)
    my = parse_myntra_html(my_html)
    me = parse_meesho_html(me_html)

    # If none found for a site, use mock sample for that site
    fallback = mock_for(product)
    results = {}
    results["Amazon"] = am if am else {"store":"Amazon", **fallback["Amazon"]}
    results["Flipkart"] = fk if fk else {"store":"Flipkart", **fallback["Flipkart"]}
    results["Myntra"] = my if my else {"store":"Myntra", **fallback["Myntra"]}
    results["Meesho"] = me if me else {"store":"Meesho", **fallback["Meesho"]}

    return results

def fetch_image_for_display(img_url):
    """Return PIL Image or None. If the URL is relative/local, ignore for now."""
    if not img_url:
        return None
    try:
        if img_url.startswith("data:"):
            # skip inline base64 images for simplicity
            return None
        if img_url.startswith("//"):
            img_url = "https:" + img_url
        if img_url.startswith("/"):
            # relative path — cannot fetch without site context
            return None
        resp = requests.get(img_url, timeout=8)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content))
    except Exception:
        return None

def show_comparison(product, results):
    # Prepare plot data
    stores = []
    prices = []
    for s in ["Amazon","Flipkart","Myntra","Meesho"]:
        p = results[s].get("price")
        if p is not None:
            stores.append(s)
            prices.append(p)

    # Create figure with 2 rows: bar chart + details row
    fig = plt.figure(figsize=(10, 6))
    gs = fig.add_gridspec(3, 4, height_ratios=[3, 0.1, 1])  # top spans columns
    ax_bar = fig.add_subplot(gs[0, :])  # bar chart across top
    ax_bar.clear()

    if stores:
        colors_map = {"Amazon":"#FF9900","Flipkart":"#34a853","Myntra":"#f06292","Meesho":"#00bcd4"}
        colors = [colors_map.get(s, "#999999") for s in stores]
        ax_bar.bar(stores, prices, color=colors)
        ax_bar.set_title(f"Price Comparison — {product}", fontsize=14, fontweight='bold')
        ax_bar.set_ylabel("Price (₹)")
        ax_bar.grid(axis='y', linestyle='--', alpha=0.3)
        # labels
        for i, v in enumerate(prices):
            ax_bar.text(i, v + max(50, v*0.02), f"₹{int(v)}", ha='center', fontweight='bold')
    else:
        ax_bar.text(0.5, 0.5, "No price data available", ha='center', va='center', fontsize=14)

    # Hide axes for the small spacer row
    ax_spacer = fig.add_subplot(gs[1, :])
    ax_spacer.axis('off')

    # Details row: show each store in a column with thumbnail and text
    for i, store in enumerate(["Amazon","Flipkart","Myntra","Meesho"]):
        ax = fig.add_subplot(gs[2, i])
        ax.axis('off')
        info = results[store]
        title = info.get("title") or "Not Available"
        price = info.get("price")
        url = info.get("url") or "N/A"
        img = fetch_image_for_display(info.get("image"))

        # If image exists, show scaled thumbnail
        if img:
            # resize thumbnail to fit
            img.thumbnail((160, 120))
            ax.imshow(img)
            ax.text(0.5, -0.12, textwrap.shorten(title, width=40), ha='center', va='top', transform=ax.transAxes, fontsize=9)
            ax.text(0.5, -0.25, f"{'₹'+str(int(price)) if price else 'Not Available'}", ha='center', va='top', transform=ax.transAxes, fontsize=9, fontweight='bold')
            ax.text(0.5, -0.38, textwrap.shorten(url, width=40), ha='center', va='top', transform=ax.transAxes, fontsize=7)
        else:
            # show placeholder text
            ax.text(0.5, 0.6, store, ha='center', va='center', fontsize=12, fontweight='bold')
            ax.text(0.5, 0.35, textwrap.shorten(title, width=40), ha='center', va='center', fontsize=9)
            ax.text(0.5, 0.15, f"{'₹'+str(int(price)) if price else 'Not Available'}", ha='center', va='center', fontsize=9, fontweight='bold')
            ax.text(0.5, -0.05, textwrap.shorten(url, width=40), ha='center', va='center', fontsize=7)

    plt.tight_layout()
    plt.show()

    # Also print details in terminal
    print("\n---------------- PRODUCT DETAILS ----------------")
    for s in ["Amazon","Flipkart","Myntra","Meesho"]:
        info = results[s]
        print(f"\n🛒 {s}")
        print(f"Name : {info.get('title')}")
        print(f"Price: {'₹'+str(int(info.get('price'))) if info.get('price') else 'Not Available'}")
        print(f"Link : {info.get('url') or 'N/A'}")

# -------------
# Main program
# -------------
if __name__ == "__main__":
    print("🛍️ Product  Price Comparison: ")
    prod = input("Enter product name: ").strip()
    if not prod:
        print("Please enter a product name and re-run.")
        exit(1)
    results = build_results(prod)
    show_comparison(prod, results)

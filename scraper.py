import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

def _fetch(url, timeout=15):
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp

def _extract_og(soup, prop):
    tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
    return tag["content"].strip() if tag and tag.has_attr("content") else None

def parse_purepeople_home(url, max_items=15):
    """
    Raspador do Purepeople.
    - Pega links de notícias na home
    - Entra em cada artigo e extrai título, imagem, descrição e, se rolar, vídeo (só MP4)
    """
    out = []
    r = _fetch(url)
    s = BeautifulSoup(r.text, "lxml")

    # Links principais: "/noticia", "/famosos", "/musica", "/televisao"
    for a in s.select('a[href^="/"]'):
        href = a.get("href", "")
        if not href or href == "/":
            continue
        if "/noticia" in href or "/famosos" in href or "/musica" in href or "/televisao" in href:
            article_url = urljoin(url, href)
            title = a.get_text(strip=True)
            if title and len(title) > 25:  # evitar títulos curtos tipo "Ver mais"
                out.append({"title": title, "url": article_url})
        if len(out) >= max_items:
            break

    enriched = []
    for it in out:
        try:
            ar = _fetch(it["url"])
            asoup = BeautifulSoup(ar.text, "lxml")
            title = _extract_og(asoup, "og:title") or it["title"]
            image = _extract_og(asoup, "og:image")
            video = _extract_og(asoup, "og:video")
            desc = _extract_og(asoup, "og:description") or ""
            enriched.append({
                "title": title,
                "url": it["url"],
                "image_url": image,
                "video_url": video if (video and video.lower().endswith(".mp4")) else None,
                "summary": desc
            })
        except Exception as e:
            print(f"⚠️ Falha enriquecendo artigo: {it.get('url')} -> {e}")
    return enriched

def collect_news_items(sites, max_items=10):
    """
    Coleta notícias de uma lista de sites.
    Hoje só Purepeople tem parser dedicado.
    Se for outro site, tenta extrair direto via OG tags.
    """
    items = []
    for site in sites:
        if "purepeople.com.br" in site:
            items.extend(parse_purepeople_home(site, max_items=max_items))
        else:
            try:
                r = _fetch(site)
                s = BeautifulSoup(r.text, "lxml")
                title = _extract_og(s, "og:title")
                image = _extract_og(s, "og:image")
                video = _extract_og(s, "og:video")
                desc = _extract_og(s, "og:description")
                if title and image:
                    items.append({
                        "title": title,
                        "url": site,
                        "image_url": image,
                        "video_url": video if (video and video.lower().endswith('.mp4')) else None,
                        "summary": desc
                    })
            except Exception as e:
                print(f"⚠️ Falha ao coletar de {site}: {e}")

    # Remover duplicados por URL
    seen = set()
    deduped = []
    for it in items:
        if it["url"] in seen:
            continue
        deduped.append(it)
        seen.add(it["url"])
    return deduped[:max_items]

def get_latest_posts():
    """
    Função principal que o main.py espera.
    Retorna uma lista de posts.
    """
    sites_to_scrape = [
        "https://www.purepeople.com.br/famosos"
    ]
    scraped_items = collect_news_items(sites_to_scrape)
    formatted_posts = []
    for item in scraped_items:
        formatted_posts.append({
            "id": item.get("url"),
            "title": item.get("title"),
            "text": item.get("summary"),
            "image": item.get("image_url"),
            "video": item.get("video_url")   # 🔥 AGORA PASSA PRO MAIN.PY
        })
    return formatted_posts

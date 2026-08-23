#!/usr/bin/env python3
"""
Rastreia (crawl) um site inteiro a partir de uma URL inicial e tira um
screenshot (print) de cada página encontrada, usando Playwright.

Instalação
----------
  pip install playwright
  playwright install chromium

Uso básico
----------
  python screenshot_site.py https://exemplo.com

Opções
------
  -o, --output       Pasta de saída para os screenshots (padrão: screenshots)
  -m, --max-pages    Número máximo de páginas a visitar (padrão: 50)
  -d, --depth        Profundidade máxima de navegação a partir da URL inicial
  --all-domains      Permite seguir links para outros domínios (padrão: só o mesmo domínio)
  --no-headless      Mostra a janela do navegador em vez de rodar oculto
  --viewport-only    Tira o print só da área visível (padrão: página inteira)
  --scroll-to-bottom Faz scroll até o final da página antes do screenshot
  --delay            Delay em segundos entre uma página e outra (padrão: 1.0)
  --width / --height Dimensões da viewport (padrão: 1366x768)
  --login            Habilita sessão autenticada usando um perfil persistente
                      do Chromium (cookies, localStorage, IndexedDB etc).
                      Sempre abre o navegador visível, carrega a URL e espera
                      você pressionar ENTER no terminal antes de seguir com o
                      crawl — o comportamento é o mesmo em toda execução,
                      não só na primeira. O perfil salvo faz com que, se você
                      já tiver logado antes, a página já apareça autenticada.
  --profile-dir      Pasta onde o perfil persistente do navegador é salvo
                      (padrão: .browser-profile)
  --relogin          Apaga o perfil salvo e força um novo login manual
                      (útil quando a sessão expirou)

Exemplo
-------
  python screenshot_site.py https://meusite.com.br -o prints -m 30 -d 2

  # Com --login: sempre abre o navegador, espera você confirmar (ENTER) e
  # então roda o crawl. Se você já tiver logado antes, a sessão salva no
  # perfil já aparece pronta, mas o fluxo é sempre o mesmo.
  python screenshot_site.py https://meusite.com.br --login
"""

import argparse
import asyncio
import os
import re
import shutil
from collections import deque
from urllib.parse import urldefrag, urlparse

from playwright.async_api import async_playwright


def sanitize_filename(url: str) -> str:
  """Converte uma URL em um nome de arquivo seguro para o sistema de arquivos."""
  parsed = urlparse(url)
  path = parsed.path.strip("/") or "home"
  name = f"{parsed.netloc}_{path}"
  if parsed.query:
    name += f"_{parsed.query}"
  name = re.sub(r"[^a-zA-Z0-9_\-]", "_", name)
  return name[:150]  # evita nomes de arquivo excessivamente longos


def is_same_domain(base_url: str, target_url: str) -> bool:
  """Verifica se duas URLs pertencem ao mesmo domínio."""
  return urlparse(base_url).netloc == urlparse(target_url).netloc


async def get_links(page) -> set:
  """Extrai todos os links <a href> válidos (http/https) da página atual."""
  hrefs = await page.eval_on_selector_all(
    "a[href]", "elements => elements.map(el => el.href)"
  )
  links = set()
  for href in hrefs:
    href, _ = urldefrag(href)  # remove o fragmento (#âncora)
    if href.startswith(("http://", "https://")):
      links.add(href)
  return links


async def scroll_to_bottom(page, pause: float = 0.5, max_scrolls: int = 50) -> None:
  """Faz scroll incremental até o final da página para acionar lazy loading."""
  previous_height = 0
  for _ in range(max_scrolls):
    current_height = await page.evaluate("document.body.scrollHeight")
    if current_height == previous_height:
      break
    previous_height = current_height
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(pause)
  # Volta ao topo para o screenshot começar do início
  await page.evaluate("window.scrollTo(0, 0)")
  await asyncio.sleep(0.2)


async def crawl_and_screenshot(
  start_url: str,
  output_dir: str = "screenshots",
  max_pages: int = 50,
  max_depth: int | None = None,
  same_domain_only: bool = True,
  headless: bool = True,
  full_page: bool = True,
  scroll_before_print: bool = False,
  delay: float = 1.0,
  viewport_width: int = 1366,
  viewport_height: int = 768,
  login: bool = False,
  profile_dir: str = ".browser-profile",
) -> None:
  os.makedirs(output_dir, exist_ok=True)

  visited: set[str] = set()
  queue: deque[tuple[str, int]] = deque([(start_url, 0)])
  errors: list[tuple[str, str]] = []
  saved = 0

  async with async_playwright() as p:
    browser = None  # só é usado no modo sem --login (contexto "solto")

    if login:
      context = await p.chromium.launch_persistent_context(
        profile_dir,
        headless=False,
        viewport={"width": viewport_width, "height": viewport_height},
      )
      page = context.pages[0] if context.pages else await context.new_page()

      print("\n=== Modo de login ===")
      print(f"Abrindo o navegador em: {start_url}")
      print("Confira se está logado (ou faça o login agora, se precisar).")
      print("Quando estiver pronto, volte para este terminal e pressione "
            "ENTER para seguir com o crawl.\n")
      try:
        await page.goto(start_url, wait_until="networkidle", timeout=30000)
      except Exception as e:
        print(f"Aviso: não foi possível carregar {start_url} automaticamente: {e}")
        print("Você ainda pode navegar manualmente até a página desejada.")

      await asyncio.get_event_loop().run_in_executor(
        None, input, "Pressione ENTER aqui para continuar... "
      )
      print(f"Perfil salvo em: {profile_dir}\n")
    else:
      browser = await p.chromium.launch(headless=headless)
      context = await browser.new_context(
        viewport={"width": viewport_width, "height": viewport_height}
      )
      page = await context.new_page()

    while queue and saved < max_pages:
      url, depth = queue.popleft()

      if url in visited:
        continue
      if max_depth is not None and depth > max_depth:
        continue

      visited.add(url)

      print(f"[{saved + 1}/{max_pages}] Visitando: {url}")

      try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
      except Exception as e:
        print(f"  Erro ao carregar {url}: {e}")
        errors.append((url, str(e)))
        continue

      # Scroll até o final para acionar lazy loading, se solicitado
      if scroll_before_print:
        try:
          print("  Fazendo scroll até o final da página...")
          await scroll_to_bottom(page)
        except Exception as e:
          print(f"  Aviso: erro durante scroll: {e}")

      filename = f"{sanitize_filename(url)}.png"
      filepath = os.path.join(output_dir, filename)

      try:
        await page.screenshot(path=filepath, full_page=full_page)
        print(f"  Screenshot salvo em: {filepath}")
        saved += 1
      except Exception as e:
        print(f"  Erro ao tirar screenshot de {url}: {e}")
        errors.append((url, str(e)))
        continue

      # Descobre novos links para continuar o rastreamento
      try:
        links = await get_links(page)
      except Exception as e:
        print(f"  Erro ao extrair links de {url}: {e}")
        links = set()

      for link in links:
        if same_domain_only and not is_same_domain(start_url, link):
          continue
        if link not in visited:
          queue.append((link, depth + 1))

      await asyncio.sleep(delay)

    if browser is not None:
      await browser.close()
    else:
      await context.close()

  print("\n=== Resumo ===")
  print(f"Páginas visitadas: {len(visited)}")
  print(f"Screenshots salvos: {saved}")
  if errors:
    print(f"Erros ({len(errors)}):")
    for url, err in errors:
      print(f"  - {url}: {err}")


def main() -> None:
  parser = argparse.ArgumentParser(
    description="Tira screenshots de todas as páginas de um site a partir de uma URL, usando Playwright."
  )
  parser.add_argument("url", help="URL inicial do site (ex: https://exemplo.com)")
  parser.add_argument("-o", "--output", default="screenshots", help="Pasta de saída")
  parser.add_argument(
    "-m", "--max-pages", type=int, default=50, help="Número máximo de páginas"
  )
  parser.add_argument(
    "-d", "--depth", type=int, default=None, help="Profundidade máxima de navegação"
  )
  parser.add_argument(
    "--all-domains",
    action="store_true",
    help="Permite navegar para outros domínios também",
  )
  parser.add_argument(
    "--no-headless",
    action="store_true",
    help="Mostra o navegador (modo não headless)",
  )
  parser.add_argument(
    "--viewport-only",
    action="store_true",
    help="Screenshot só da área visível (não a página inteira)",
  )
  parser.add_argument(
    "--scroll-to-bottom",
    action="store_true",
    help="Faz scroll até o final da página antes de tirar o screenshot (útil para lazy loading)",
  )
  parser.add_argument(
    "--delay", type=float, default=1.0, help="Delay entre páginas, em segundos"
  )
  parser.add_argument("--width", type=int, default=1366, help="Largura da viewport")
  parser.add_argument("--height", type=int, default=768, help="Altura da viewport")
  parser.add_argument(
    "--login",
    action="store_true",
    help=(
      "Habilita sessão autenticada com perfil persistente do Chromium. "
      "Sempre abre o navegador visível e espera você confirmar (ENTER) antes "
      "de seguir com o crawl — mesmo comportamento em toda execução, não só "
      "na primeira."
    ),
  )
  parser.add_argument(
    "--profile-dir",
    default=".browser-profile",
    help="Pasta onde o perfil persistente do navegador é salvo (padrão: .browser-profile)",
  )
  parser.add_argument(
    "--relogin",
    action="store_true",
    help="Apaga o perfil salvo e força um novo login manual (ex: sessão expirada)",
  )

  args = parser.parse_args()

  if args.relogin and os.path.isdir(args.profile_dir):
    shutil.rmtree(args.profile_dir)

  asyncio.run(
    crawl_and_screenshot(
      start_url=args.url,
      output_dir=args.output,
      max_pages=args.max_pages,
      max_depth=args.depth,
      same_domain_only=not args.all_domains,
      headless=not args.no_headless,
      full_page=not args.viewport_only,
      scroll_before_print=args.scroll_to_bottom,
      delay=args.delay,
      viewport_width=args.width,
      viewport_height=args.height,
      login=args.login,
      profile_dir=args.profile_dir,
    )
  )


if __name__ == "__main__":
  main()

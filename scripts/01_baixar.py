"""Baixa do TSE os arquivos usados no projeto para dados/brutos/.

Fontes (Portal de Dados Abertos do TSE):
- 2022 e 2026: boletim de urna (bweb), com a hora de recebimento de cada urna.
- 2010, 2014 e 2018: votação por seção (votacao_secao), sem hora.
- 2018: detalhe da votação por seção, com a hora da primeira totalização de cada urna.
- Todos os anos: votação por município e zona, usada só para conferir os totais.
- 2026: locais de votação, usados para posicionar os municípios no mapa.

A tabela oficial do 2º turno de 2014 fica em dados/oficiais/; a página original do TSE
saiu do ar e a cópia veio do arquivo da internet (endereço em scripts/marcos.py).

Os endereços vêm do catálogo do portal e ficam gravados em dados/brutos/manifesto.json.
Arquivo já baixado com o tamanho certo não é baixado de novo.
"""
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BRUTOS = RAIZ / "dados" / "brutos"
CATALOGO = "https://dadosabertos.tse.jus.br/api/3/action/package_show?id="
ODSELE = "https://cdn.tse.jus.br/estatistica/sead/odsele"
TENTATIVAS = 5


def recursos(pacote):
    with urllib.request.urlopen(CATALOGO + pacote, timeout=90) as r:
        return [x["url"] for x in json.load(r)["result"]["resources"]]


def montar_lista():
    arquivos = []
    for ano in (2022, 2026):
        # No catálogo de 2026 o boletim do 2º turno de Roraima aponta para o .sha512;
        # tirar o sufixo recupera o .zip certo, e o dict elimina as repetições.
        urls = {u.removesuffix(".sha512"): None for u in recursos(f"resultados-{ano}-boletim-de-urna")}
        arquivos += [(f"bweb/{ano}", u) for u in urls if u.lower().endswith(".zip")]
    for ano in (2010, 2014, 2018):
        for url in recursos(f"resultados-{ano}"):
            # O voto para presidente fica no arquivo nacional, que já inclui exterior e
            # voto em trânsito; os estaduais não têm esse cargo.
            if "/votacao_secao/" in url and url.endswith("_BR.zip"):
                arquivos.append((f"secao/{ano}", url))
    for ano in (2010, 2014, 2018, 2022, 2026):
        arquivos.append(("conferencia", f"{ODSELE}/votacao_candidato_munzona/votacao_candidato_munzona_{ano}.zip"))
    arquivos.append(("detalhe", f"{ODSELE}/detalhe_votacao_secao/detalhe_votacao_secao_2018.zip"))
    arquivos.append(("locais", f"{ODSELE}/eleitorado_locais_votacao/eleitorado_local_votacao_2026.zip"))
    return arquivos


def baixar(pasta, url):
    destino = BRUTOS / pasta / url.rsplit("/", 1)[1]
    destino.parent.mkdir(parents=True, exist_ok=True)
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                tamanho = int(r.headers.get("Content-Length") or 0)
                if destino.exists() and destino.stat().st_size == tamanho:
                    return destino, tamanho, "ja tinha"
                parcial = destino.with_suffix(".parcial")
                with open(parcial, "wb") as f:
                    while bloco := r.read(1 << 20):
                        f.write(bloco)
            if tamanho and parcial.stat().st_size != tamanho:
                raise OSError(f"tamanho {parcial.stat().st_size} != {tamanho}")
            parcial.replace(destino)
            return destino, tamanho, "baixado"
        except Exception as erro:
            if tentativa == TENTATIVAS:
                raise RuntimeError(f"{url}: {erro}") from erro
            time.sleep(5 * tentativa)


def main():
    BRUTOS.mkdir(parents=True, exist_ok=True)
    lista = montar_lista()
    (BRUTOS / "manifesto.json").write_text(
        json.dumps([{"pasta": p, "url": u} for p, u in lista], indent=1), encoding="utf-8"
    )
    print(f"{len(lista)} arquivos no manifesto", flush=True)
    falhas, total = [], 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        tarefas = {pool.submit(baixar, p, u): u for p, u in lista}
        for i, t in enumerate(as_completed(tarefas), 1):
            try:
                destino, tamanho, estado = t.result()
                total += tamanho
                print(f"[{i}/{len(lista)}] {estado} {destino.name} {tamanho / 1e6:.1f} MB", flush=True)
            except Exception as erro:
                falhas.append(str(erro))
                print(f"[{i}/{len(lista)}] FALHOU {erro}", flush=True)
    print(f"total {total / 1e9:.2f} GB, {len(falhas)} falhas", flush=True)
    for f in falhas:
        print("FALHA", f, flush=True)
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()

"""Confere a soma das urnas com o TSE e os números recalculados com os do vídeo.

Cada item do vídeo é comparado na mesma precisão em que o vídeo o mostra: o que
continuar diferente depois de arredondar igual entra como divergência na tela.
Grava site/dados/conferencia.json.
"""
import bisect
import json
import math
from pathlib import Path

import numpy as np
import polars as pl

from marcos import MARCOS

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "dados" / "processados"
SITE = RAIZ / "site" / "dados"

UF_REGIAO = {
    uf: r for r, ufs in {
        "Norte": "AC AM AP PA RO RR TO", "Nordeste": "AL BA CE MA PB PE PI RN SE",
        "Centro-Oeste": "DF GO MS MT", "Sudeste": "ES MG RJ SP", "Sul": "PR RS SC",
    }.items() for uf in ufs.split()
}


def comparar():
    oficial = pl.read_parquet(PROC / "conferencia_oficial.parquet")
    linhas = []
    for arquivo in sorted(PROC.glob("urnas_*.parquet")):
        u = pl.read_parquet(arquivo)
        linhas.append(
            u.filter(pl.col("nr") < 95).group_by("ano", "turno", "nr").agg(pl.col("votos").sum().alias("urnas"))
        )
    return (
        pl.concat(linhas)
        .join(oficial.select("ano", "turno", "nr", pl.col("votos").alias("oficial")), on=["ano", "turno", "nr"], how="full", coalesce=True)
        .with_columns((pl.col("urnas").fill_null(0) - pl.col("oficial").fill_null(0)).alias("dif"))
        .sort("ano", "turno", "urnas", descending=[False, False, True])
    )


def br(v, c=1):
    return f"{v:.{c}f}".replace(".", ",")


class Apuracao:
    """As urnas do 2º turno de 2026 na ordem real de chegada."""

    def __init__(self):
        chave = ["uf", "cd_mun", "zona", "secao"]
        u = (
            pl.read_parquet(PROC / "urnas_2026_2t.parquet")
            .group_by(chave)
            .agg(
                pl.col("recebido").min(),
                pl.col("votos").filter(pl.col("nr") == 13).sum().alias("lula"),
                pl.col("votos").filter(pl.col("nr") == 22).sum().alias("flavio"),
            )
            .with_columns((pl.col("lula") + pl.col("flavio")).alias("validos"))
            .filter(pl.col("validos") > 0)
            .sort("recebido", *chave)
        )
        self.n = u.height
        self.hora = u["recebido"].dt.strftime("%Hh%M").to_list()
        self.lula = u["lula"].to_numpy().astype(np.int64)
        self.flavio = u["flavio"].to_numpy().astype(np.int64)
        self.validos = u["validos"].to_numpy().astype(np.int64)
        self.regiao = np.array([UF_REGIAO.get(x, "") for x in u["uf"].to_list()])
        self.ac_lula = np.cumsum(self.lula)
        self.ac_validos = np.cumsum(self.validos)

    def indice(self, pct):
        return min(self.n - 1, math.ceil(pct / 100 * self.n) - 1)

    def lula_pct(self, pct):
        i = self.indice(pct)
        return self.ac_lula[i] / self.ac_validos[i] * 100

    def apurado(self, regiao, pct):
        m = self.regiao == regiao
        return self.validos[: self.indice(pct) + 1][m[: self.indice(pct) + 1]].sum() / self.validos[m].sum() * 100

    def trocas_sem_filtro(self):
        """Percentual de urnas em cada troca de liderança, sem nenhum filtro."""
        s = np.sign(np.cumsum(self.lula - self.flavio))
        i = np.nonzero(s)[0]
        s = s[i]
        return ((i[1:][s[1:] != s[:-1]] + 1) / self.n * 100).tolist()


def item(linhas, nome, video, calculado, igual, diferenca=""):
    linhas.append({"item": nome, "video": video, "calculado": calculado, "igual": bool(igual), "diferenca": diferenca})


def numero(linhas, nome, video, valor_video, valor, casas, sufixo="%", prefixo="", unidade="ponto"):
    """Compara arredondando o dado recalculado para as casas que o vídeo mostra."""
    igual = round(valor, casas) == round(valor_video, casas)
    dif = valor - valor_video
    plural = "s" if unidade == "ponto" and abs(dif) >= 2 else ""
    texto = "" if igual else f"{'+' if dif > 0 else '−'}{br(abs(dif), max(casas, 1))} {unidade}{plural}"
    item(linhas, nome, video, f"{prefixo}{br(valor, casas + 1)}{sufixo}", igual, texto)


def minutos(hora):
    h, m = hora.split("h")
    return int(h) * 60 + int(m)


def hora(linhas, ap, pct):
    calc, vid = ap.hora[ap.indice(pct[0])], pct[1]
    dif = minutos(calc) - minutos(vid)
    texto = "" if dif == 0 else f"{'+' if dif > 0 else '−'}{abs(dif)} min"
    item(linhas, f"Hora em que {br(pct[0])}% das urnas tinham chegado", vid, calc, dif == 0, texto)


def com_video():
    d = json.loads((SITE / "turno_2026_2.json").read_text(encoding="utf-8"))
    ap = Apuracao()
    nome = {d["a"]["nr"]: "a", d["b"]["nr"]: "b"}
    lula, flavio = nome[13], nome[22]
    c, v, s = d["curva"], d["viradas"], d["sorteios_ordem"]
    reg = {r["nome"]: r for r in d["regioes"]}
    linhas = []

    numero(linhas, "Lula no resultado final", "51,8%", 51.8, d[lula]["pct"], 1)
    numero(linhas, "Flávio no resultado final", "48,2%", 48.2, d[flavio]["pct"], 1)
    item(linhas, "Hora da última urna", "23h21", ap.hora[-1], ap.hora[-1] == "23h21",
         "" if ap.hora[-1] == "23h21" else f"{minutos(ap.hora[-1]) - minutos('23h21')} min")
    item(linhas, "Quem abre na frente", "Lula", f"Lula, {br(ap.lula_pct(1))}% com 1% das urnas", ap.lula_pct(1) > 50)
    numero(linhas, "Lula com 4,4% das urnas", "51,2%", 51.2, ap.lula_pct(4.4), 1)
    numero(linhas, "Flávio com 4,4% das urnas", "48,8%", 48.8, 100 - ap.lula_pct(4.4), 1)
    i_pico = max((i for i, x in enumerate(c["x"]) if x >= 10), key=lambda i: c[flavio][i])
    numero(linhas, "Maior percentual de Flávio depois de virar", "50,5%", 50.5, c[flavio][i_pico], 1)

    for pct in ((4.4, "19h26"), (6.0, "19h30"), (13.6, "19h44"), (45.1, "20h22"), (45.6, "20h22"), (50.1, "20h26"), (94.1, "21h05")):
        hora(linhas, ap, pct)

    if len(v) >= 2:
        item(linhas, "Hora em que Flávio passa à frente", "19h44", v[0]["hora"], v[0]["hora"] == "19h44",
             "" if v[0]["hora"] == "19h44" else f"{minutos(v[0]['hora']) - minutos('19h44')} min")
        numero(linhas, "Urnas apuradas quando Flávio passa à frente", "13,6%", 13.6, v[0]["pct"], 1, unidade="ponto")
        item(linhas, "Hora em que Lula volta à frente", "20h23", v[1]["hora"], v[1]["hora"] == "20h23",
             "" if v[1]["hora"] == "20h23" else f"{minutos(v[1]['hora']) - minutos('20h23')} min")
        numero(linhas, "Urnas apuradas quando Lula volta à frente", "47%", 47, v[1]["pct"], 0)

    sem_filtro = ap.trocas_sem_filtro()
    brutas = len(sem_filtro)
    antes = sum(x < 1 for x in sem_filtro)
    print("trocas sem filtro", [round(x, 3) for x in sem_filtro])
    item(linhas, "Trocas de liderança, com a regra desta tela", "2", str(len(v)), len(v) == 2)
    item(
        linhas, "Trocas de liderança, contando urna a urna, desde a primeira", "2", str(brutas), brutas == 2,
        f"{antes} trocas antes de 1% das urnas e {brutas - antes} em vai e volta de poucas urnas em torno das 2 viradas",
    )

    for pct, valores in (
        (6.0, {"Sul": 10, "Centro-Oeste": 12, "Norte": 20, "Nordeste": 4, "Sudeste": 2}),
        (50.1, {"Sul": 75, "Centro-Oeste": 74, "Norte": 82, "Nordeste": 49, "Sudeste": 30}),
        (94.1, {"Sul": 99, "Centro-Oeste": 99, "Norte": 99, "Nordeste": 96, "Sudeste": 89}),
    ):
        for regiao, valor in valores.items():
            numero(linhas, f"{regiao}: votos já apurados com {br(pct)}% das urnas", f"{valor}%", valor, ap.apurado(regiao, pct), 0)

    numero(linhas, "Flávio no Sul", "cerca de 60%", 60, reg["Sul"][flavio], 0)
    numero(linhas, "Flávio no Centro-Oeste", "cerca de 60%", 60, reg["Centro-Oeste"][flavio], 0)
    numero(linhas, "Lula no Nordeste", "69%", 69, reg["Nordeste"][lula], 0)

    item(
        linhas, "Trocas de liderança em ordem sorteada", "nenhuma",
        f"{br(s['pct_sem_virada'])}% dos sorteios sem troca; no máximo {s['viradas_max']}",
        s["pct_sem_virada"] == 100,
        "" if s["pct_sem_virada"] == 100 else f"{br(100 - s['pct_sem_virada'])}% dos {s['n']:,} sorteios têm troca".replace(",", "."),
    )
    for a, valor in zip(d["amostras"], (9.8, 3.3, 0.9, 0.3)):
        numero(linhas, f"Margem de erro com {a['n']:,} urnas".replace(",", "."), f"±{br(valor)}", valor, a["erro_95"], 1, sufixo="", prefixo="±")
    mil = next(a for a in d["amostras"] if a["n"] == 1000)
    item(linhas, "Com 1.000 urnas o erro fica abaixo de um ponto", "sim", f"±{br(mil['erro_95'], 2)}", mil["erro_95"] < 1,
         "" if mil["erro_95"] < 1 else "95% dos sorteios ficam até esse valor, um pouco acima de 1 ponto")
    numero(linhas, "1.000 urnas como parte do total", "0,2%", 0.2, mil["pct_das_urnas"], 1)
    return linhas


def com_marcos():
    """Cada registro da época ao lado da curva da tela no mesmo ponto."""
    saida = []
    for m in MARCOS:
        d = json.loads((SITE / f"turno_{m['ano']}_{m['turno']}.json").read_text(encoding="utf-8"))
        c = d["curva"]
        chave = {d["a"]["nr"]: "a", d["b"]["nr"]: "b"}
        if m["base"] == "hora":
            i = c["hora"].index(m["hora"]) if m["hora"] in c["hora"] else None
        else:
            i = min(bisect.bisect_left(c["x"], m["urnas"]), len(c["x"]) - 1)
        saida.append({
            **{k: v for k, v in m.items() if k != "valores"},
            "valores": {str(k): v for k, v in m["valores"].items()},
            "ordem": d["ordem"],
            "x": c["x"][i] if i is not None else None,
            "hora_curva": c["hora"][i] if i is not None and "hora" in c else None,
            "curva": {str(nr): c[k][i] for nr, k in chave.items()} if i is not None else {},
        })
    return saida


def main():
    t = comparar()
    print(t.group_by("ano", "turno").agg(pl.col("dif").abs().sum()).sort("ano", "turno"))
    print(t.filter(pl.col("dif") != 0))
    resumo = (
        t.filter(pl.col("oficial").is_not_null())
        .sort("ano", "turno", "oficial", descending=[False, False, True])
        .group_by("ano", "turno", maintain_order=True)
        .head(2)
    )
    conferencia = {
        "video": com_video(),
        "oficial": resumo.select("ano", "turno", "nr", "urnas", "oficial").to_dicts(),
        "marcos": com_marcos(),
    }
    (SITE / "conferencia.json").write_text(json.dumps(conferencia, ensure_ascii=False, indent=1), encoding="utf-8")
    for x in conferencia["video"]:
        print(f"{'IGUAL' if x['igual'] else 'DIFERE'} {x['item']:<62} video {x['video']:<14} dados {x['calculado']:<34} {x['diferenca']}")
    for x in conferencia["marcos"]:
        print(x["ano"], x["turno"], x["fonte"], x["hora"], "urnas", x["urnas"], x["valores"], "| curva", x["x"], x["hora_curva"], x["curva"])


if __name__ == "__main__":
    main()

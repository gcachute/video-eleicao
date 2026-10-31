"""Aplica o sistema do vídeo aos 10 turnos e grava site/dados/.

Para cada turno:
1. Curva na ordem de chegada. É real em 2018, 2022 e 2026, com a hora de cada
   urna. No 2º turno de 2014 vem da tabela oficial de parciais do TSE, que não
   tem urnas. Em 2010 e no 1º turno de 2014 a ordem é estimada, emprestando a
   chegada de 2018 município a município, e o mesmo vale para o mapa de 2014.
2. As mesmas urnas em ordem sorteada, muitas vezes.
3. Quantas urnas sorteadas bastam: amostras de 10, 100, 1.000 e 10.000 urnas.
4. Chegada por região e resultado por município.
"""
import datetime
import json
from pathlib import Path

import numpy as np
import polars as pl

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "dados" / "processados"
SITE = RAIZ / "site" / "dados"

TURNOS = [(a, t) for a in (2010, 2014, 2018, 2022, 2026) for t in (1, 2)]
ANOS_COM_HORA = (2018, 2022, 2026)
DOADOR = 2018
DIAS = {
    (2018, 1): datetime.date(2018, 10, 7), (2018, 2): datetime.date(2018, 10, 28),
    (2022, 1): datetime.date(2022, 10, 2), (2022, 2): datetime.date(2022, 10, 30),
    (2026, 1): datetime.date(2026, 10, 4), (2026, 2): datetime.date(2026, 10, 25),
}
SEMENTE = 20261025
SORTEIOS_ORDEM = 2000
SORTEIOS_AMOSTRA = 5000
TAMANHOS = (10, 100, 1000, 10000)
PONTOS_POR_TAMANHO = 300
# Uma troca de liderança só conta a partir de 1% das urnas e se durar ao menos 0,1%
# das urnas. Sem isso, cada virada vira um vai e volta de poucas urnas.
INICIO_VIRADA = 0.01
DURACAO_VIRADA = 0.001
PASSOS = np.linspace(0.0005, 1, 800)

REGIOES = {
    "Norte": "AC AM AP PA RO RR TO",
    "Nordeste": "AL BA CE MA PB PE PI RN SE",
    "Centro-Oeste": "DF GO MS MT",
    "Sudeste": "ES MG RJ SP",
    "Sul": "PR RS SC",
    "Exterior": "ZZ",
    "Em trânsito": "VT",
}
UF_REGIAO = {uf: r for r, ufs in REGIOES.items() for uf in ufs.split()}
ORDEM_REGIOES = ["Sul", "Centro-Oeste", "Norte", "Nordeste", "Sudeste", "Exterior", "Em trânsito"]


def carregar(ano, turno):
    linhas = pl.read_parquet(PROC / f"urnas_{ano}_{turno}t.parquet")
    # Válido é o voto em candidato da lista oficial; fica de fora, por exemplo, o
    # número 28 no 1º turno de 2026, que está nas urnas e não está na totalização.
    oficiais = (
        pl.read_parquet(PROC / "conferencia_oficial.parquet")
        .filter((pl.col("ano") == ano) & (pl.col("turno") == turno))["nr"].to_list()
    )
    valido = pl.col("nr").is_in(oficiais)
    chave = ["uf", "cd_mun", "zona", "secao"]
    urnas = linhas.group_by(chave).agg(
        pl.col("nm_mun").first(),
        pl.col("recebido").min(),
        pl.col("votos").filter(valido).sum().alias("validos"),
        pl.col("votos").sum().alias("total"),
    )
    urnas = urnas.filter(pl.col("total") > 0).sort(chave)
    if ano == 2018:
        horas = pl.read_parquet(PROC / "horas_2018.parquet").filter(pl.col("turno") == turno).drop("turno")
        urnas = urnas.drop("recebido").join(horas.rename({"hora": "recebido"}), on=chave, how="left").sort(chave)
    candidatos = (
        linhas.filter(valido)
        .group_by("nr")
        .agg(pl.col("nome").first(), pl.col("votos").sum())
        .sort("votos", descending=True)
    )
    return linhas, urnas, candidatos


def votos_por_urna(linhas, urnas, nr):
    chave = ["uf", "cd_mun", "zona", "secao"]
    v = linhas.filter(pl.col("nr") == nr).select(*chave, pl.col("votos").alias("v"))
    return urnas.select(chave).join(v, on=chave, how="left")["v"].fill_null(0).to_numpy().astype(np.int64)


def sinais(dif):
    """Sinal da diferença, repetindo o último quando há empate."""
    s = np.sign(dif)
    if (s == 0).any():
        s = s[np.maximum.accumulate(np.where(s != 0, np.arange(len(s)), 0))]
    return s


def viradas(dif, n):
    """Índices em que a liderança muda de forma sustentada."""
    desde = int(n * INICIO_VIRADA)
    duracao = max(int(n * DURACAO_VIRADA), 1)
    s = sinais(dif[desde:])
    mudancas = np.nonzero(s[1:] != s[:-1])[0] + 1
    if len(mudancas) == 0:
        return []
    inicios = np.concatenate(([0], mudancas))
    tamanhos = np.diff(np.concatenate((inicios, [len(s)])))
    lider = None
    trocas = []
    for inicio, tamanho in zip(inicios, tamanhos):
        if tamanho < duracao:
            continue
        if lider is None:
            lider = s[inicio]
        elif s[inicio] != lider:
            lider = s[inicio]
            trocas.append(int(inicio) + desde)
    return trocas


def amostras_da_curva(n):
    return np.unique(np.maximum((PASSOS * n).astype(np.int64), 1)) - 1


def curva(ordem, a, b, validos, recebido=None, dia=None):
    aa, bb, vv = np.cumsum(a[ordem]), np.cumsum(b[ordem]), np.cumsum(validos[ordem])
    n = len(ordem)
    idx = amostras_da_curva(n)
    com_voto = vv[idx] > 0
    idx = idx[com_voto]
    saida = {
        "x": np.round((idx + 1) / n * 100, 3).tolist(),
        "a": np.round(aa[idx] / vv[idx] * 100, 3).tolist(),
        "b": np.round(bb[idx] / vv[idx] * 100, 3).tolist(),
    }
    if recebido is not None:
        saida["hora"] = [formatar_hora(t, dia) for t in recebido[ordem][idx]]
    return saida


def formatar_hora(t, dia=None):
    """Hora e minuto; fora do dia da eleição, a data."""
    t = np.datetime64(t, "s").astype(object)
    if t is None:
        return ""
    return f"{t.day:02d}/{t.month:02d}" if dia and t.date() != dia else f"{t.hour:02d}h{t.minute:02d}"


def parciais_oficiais_2014():
    """Parciais do TSE: o eixo é o percentual dos votos válidos, pois não há contagem de urnas."""
    t = pl.read_csv(RAIZ / "dados" / "oficiais" / "parciais_2014_2t.csv")
    dilma, aecio, val = (t[c].to_numpy().astype(np.float64) for c in ("dilma", "aecio", "validos"))
    return {
        "x": np.round(val / val[-1] * 100, 3).tolist(),
        "a": np.round(dilma / val * 100, 3).tolist(),
        "b": np.round(aecio / val * 100, 3).tolist(),
        "hora": [h.replace(":", "h") for h in t["hora"].to_list()],
    }


def ordem_real(urnas, rng):
    """Ordena pela hora de chegada; empates de um mesmo segundo são sorteados."""
    t = urnas["recebido"].dt.epoch("s").to_numpy()
    sem_hora = ~np.isfinite(t.astype(np.float64))
    t = np.where(sem_hora, np.nan, t.astype(np.float64))
    return np.lexsort((rng.random(len(t)), t)), int(sem_hora.sum())


def chegada_do_doador(urnas_doador):
    """Para cada município, a posição (0 a 1) em que suas urnas chegaram no doador."""
    com_hora = urnas_doador.filter(pl.col("recebido").is_not_null()).sort("recebido")
    posicao = np.arange(com_hora.height) / com_hora.height
    tabela = com_hora.select("uf", "cd_mun").with_columns(pl.Series("p", posicao))
    return {
        "mun": {(u, c): np.sort(g["p"].to_numpy()) for (u, c), g in tabela.group_by(["uf", "cd_mun"])},
        "uf": {u[0]: np.sort(g["p"].to_numpy()) for u, g in tabela.group_by(["uf"])},
        "geral": np.sort(posicao),
    }


def ordem_emprestada(urnas, doador, rng):
    """Cada urna sorteia um instante de chegada entre os do seu município no doador."""
    n = urnas.height
    p = np.zeros(n)
    fonte = {"municipio": 0, "estado": 0, "geral": 0}
    grupos = urnas.with_row_index("i").group_by(["uf", "cd_mun"]).agg(pl.col("i"))
    for uf, cd, indices in grupos.iter_rows():
        base = doador["mun"].get((uf, cd))
        chave = "municipio"
        if base is None:
            base = doador["uf"].get(uf)
            chave = "estado"
        if base is None:
            base = doador["geral"]
            chave = "geral"
        indices = np.array(indices)
        p[indices] = rng.choice(base, size=len(indices))
        fonte[chave] += len(indices)
    return np.lexsort((rng.random(n), p)), fonte


def sortear_ordens(a, b, validos, rng):
    n = len(a)
    idx = amostras_da_curva(n)
    pct_a = np.empty((SORTEIOS_ORDEM, len(idx)), dtype=np.float32)
    pct_b = np.empty((SORTEIOS_ORDEM, len(idx)), dtype=np.float32)
    contagens = []
    exemplo = None
    for s in range(SORTEIOS_ORDEM):
        o = rng.permutation(n)
        aa, bb, vv = np.cumsum(a[o]), np.cumsum(b[o]), np.cumsum(validos[o])
        contagens.append(len(viradas(aa - bb, n)))
        pct_a[s] = aa[idx] / np.maximum(vv[idx], 1) * 100
        pct_b[s] = bb[idx] / np.maximum(vv[idx], 1) * 100
        if s == 0:
            exemplo = o
    faixa = {
        "x": np.round((idx + 1) / n * 100, 3).tolist(),
        "a_min": np.round(np.percentile(pct_a, 2.5, axis=0), 3).tolist(),
        "a_max": np.round(np.percentile(pct_a, 97.5, axis=0), 3).tolist(),
        "b_min": np.round(np.percentile(pct_b, 2.5, axis=0), 3).tolist(),
        "b_max": np.round(np.percentile(pct_b, 97.5, axis=0), 3).tolist(),
    }
    return faixa, exemplo, np.array(contagens)


def simular_amostras(a, b, validos, final_a, rng):
    saida = []
    n = len(a)
    for tamanho in TAMANHOS:
        estimativas = np.empty(SORTEIOS_AMOSTRA)
        acertos = 0
        for s in range(SORTEIOS_AMOSTRA):
            i = rng.choice(n, tamanho, replace=False, shuffle=False)
            va, vb, vv = a[i].sum(), b[i].sum(), validos[i].sum()
            estimativas[s] = va / max(vv, 1) * 100
            acertos += va > vb
        erro = np.abs(estimativas - final_a)
        saida.append({
            "n": tamanho,
            "pct_das_urnas": round(tamanho / n * 100, 3),
            "erro_95": round(float(np.percentile(erro, 95)), 3),
            "desvio": round(float(estimativas.std()), 3),
            "acerta_lider": round(acertos / SORTEIOS_AMOSTRA * 100, 2),
            "pontos": np.round(estimativas[: PONTOS_POR_TAMANHO], 2).tolist(),
        })
    return saida


def por_regiao(urnas, ordem, a, b, validos):
    reg = np.array([UF_REGIAO.get(u, "Exterior") for u in urnas["uf"].to_list()])
    n = len(ordem)
    marcos = np.linspace(0, 1, 101)
    saida = []
    for nome in ORDEM_REGIOES:
        m = reg == nome
        if not m.any():
            continue
        na_ordem = m[ordem]
        acumulado = np.cumsum(validos[ordem] * na_ordem) / validos[m].sum() * 100
        idx = np.maximum((marcos * n).astype(int) - 1, 0)
        pos = np.nonzero(na_ordem)[0]
        saida.append({
            "nome": nome,
            "urnas": int(m.sum()),
            "validos": int(validos[m].sum()),
            "a": round(float(a[m].sum() / validos[m].sum() * 100), 2),
            "b": round(float(b[m].sum() / validos[m].sum() * 100), 2),
            "chegada_mediana": round(float(np.median(pos) / n * 100), 1),
            "apurado": np.round(acumulado[idx], 1).tolist(),
        })
    return saida


def por_municipio(urnas, ordem, a, b, coordenadas):
    n = len(ordem)
    pos = np.empty(n)
    pos[ordem] = np.arange(n) / n * 100
    t = urnas.select("uf", "cd_mun", "nm_mun").with_columns(
        pl.Series("a", a), pl.Series("b", b), pl.Series("pos", pos)
    )
    g = t.group_by("uf", "cd_mun").agg(
        pl.col("nm_mun").first(), pl.col("a").sum(), pl.col("b").sum(), pl.col("pos").median()
    )
    g = g.join(coordenadas, on=["uf", "cd_mun"], how="inner").sort("uf", "cd_mun")
    return [
        [round(la, 3), round(lo, 3), va, vb, round(p, 1), f"{nome.title()} ({uf})"]
        for la, lo, va, vb, p, nome, uf in g.select("lat", "lon", "a", "b", "pos", "nm_mun", "uf").iter_rows()
    ]


def analisar(ano, turno, doadores, coordenadas):
    rng = np.random.default_rng([SEMENTE, ano, turno])
    linhas, urnas, candidatos = carregar(ano, turno)
    primeiros = candidatos.head(2)
    nr_a, nr_b = primeiros["nr"].to_list()
    a = votos_por_urna(linhas, urnas, nr_a)
    b = votos_por_urna(linhas, urnas, nr_b)
    validos = urnas["validos"].to_numpy().astype(np.int64)
    total_validos = int(validos.sum())
    final_a = a.sum() / total_validos * 100
    final_b = b.sum() / total_validos * 100

    tem_hora = ano in ANOS_COM_HORA
    fonte_ordem = None
    sem_hora = 0
    if tem_hora:
        ordem, sem_hora = ordem_real(urnas, rng)
    else:
        ordem, fonte_ordem = ordem_emprestada(urnas, doadores[turno], rng)

    recebido = urnas["recebido"].to_numpy() if tem_hora else None
    dia = DIAS.get((ano, turno))
    curva_chegada = curva(ordem, a, b, validos, recebido, dia)
    n = len(ordem)
    dif = np.cumsum(a[ordem] - b[ordem])
    trocas = viradas(dif, n)

    # A maior distância entre a parcial e o resultado final, a partir de 1% das urnas.
    cum_v = np.cumsum(validos[ordem])
    cum_a = np.cumsum(a[ordem])
    desde = n // 100
    distancia = np.abs(cum_a[desde:] / cum_v[desde:] * 100 - final_a)

    oficial = (ano, turno) == (2014, 2)
    if oficial:
        curva_chegada = parciais_oficiais_2014()
        x_of = np.array(curva_chegada["x"])
        a_of, b_of = np.array(curva_chegada["a"]), np.array(curva_chegada["b"])
        distancia = np.abs(a_of[x_of >= 1] - final_a)
        sinal = np.sign(a_of - b_of)
        mudou = np.nonzero((sinal[1:] != sinal[:-1]) & (x_of[1:] >= 1))[0] + 1

    faixa, exemplo, voltas = sortear_ordens(a, b, validos, rng)
    distancia_sorteada = np.abs(np.cumsum(a[exemplo])[desde:] / np.cumsum(validos[exemplo])[desde:] * 100 - final_a)

    return {
        "ano": ano,
        "turno": turno,
        "ordem": "oficial" if oficial else "real" if tem_hora else "estimada",
        "mapa_estimado": not tem_hora,
        "urnas": n,
        "urnas_sem_hora": sem_hora,
        "votos_validos": total_validos,
        "fonte_ordem": fonte_ordem,
        "candidatos": [
            {"nr": nr, "nome": nome, "votos": int(v), "pct": round(v / total_validos * 100, 3)}
            for nr, nome, v in candidatos.head(6).iter_rows()
        ],
        "a": {"nr": nr_a, "nome": primeiros["nome"][0], "pct": round(float(final_a), 3)},
        "b": {"nr": nr_b, "nome": primeiros["nome"][1], "pct": round(float(final_b), 3)},
        "curva": curva_chegada,
        "sorteada": {"faixa": faixa, "exemplo": curva(exemplo, a, b, validos)},
        "viradas": [
            {
                "urnas": int(i + 1),
                "pct": round((i + 1) / n * 100, 3),
                "hora": formatar_hora(recebido[ordem[i]], dia) if tem_hora else None,
                "lider": "a" if dif[i] > 0 else "b",
            }
            for i in trocas
        ] if not oficial else [
            {"urnas": None, "pct": float(x_of[i]), "hora": curva_chegada["hora"][i], "lider": "a" if sinal[i] > 0 else "b"}
            for i in mudou
        ],
        "distancia_max": round(float(distancia.max()), 3),
        "distancia_max_sorteada": round(float(distancia_sorteada.max()), 3),
        "sorteios_ordem": {
            "n": SORTEIOS_ORDEM,
            "viradas_media": round(float(voltas.mean()), 3),
            "viradas_max": int(voltas.max()),
            "pct_sem_virada": round(float((voltas == 0).mean() * 100), 1),
        },
        "amostras": simular_amostras(a, b, validos, final_a, rng),
        "regioes": por_regiao(urnas, ordem, a, b, validos),
        "municipios": por_municipio(urnas, ordem, a, b, coordenadas),
    }


def validar_emprestimo(doadores):
    """Testa o método em dois casos em que a curva verdadeira é conhecida."""
    resultado = []
    for ano, turno in ((2026, 2), (2014, 2)):
        rng = np.random.default_rng([SEMENTE, 1, ano, turno])
        linhas, urnas, candidatos = carregar(ano, turno)
        nr_a, nr_b = candidatos.head(2)["nr"].to_list()
        a = votos_por_urna(linhas, urnas, nr_a)
        b = votos_por_urna(linhas, urnas, nr_b)
        validos = urnas["validos"].to_numpy().astype(np.int64)
        estimada, _ = ordem_emprestada(urnas, doadores[turno], rng)
        v_est = np.cumsum(validos[estimada])
        x_est = v_est / v_est[-1] * 100
        y_est = np.cumsum(a[estimada]) / v_est * 100
        if ano == 2014:
            verdadeira = parciais_oficiais_2014()
            sinal = np.sign(np.array(verdadeira["a"]) - np.array(verdadeira["b"]))
            pontos = np.nonzero(sinal[1:] != sinal[:-1])[0] + 1
            viradas_real = [round(verdadeira["x"][i], 1) for i in pontos if verdadeira["x"][i] >= 1]
        else:
            real, _ = ordem_real(urnas, rng)
            v_real = np.cumsum(validos[real])
            idx = amostras_da_curva(len(real))
            verdadeira = {
                "x": np.round(v_real[idx] / v_real[-1] * 100, 3).tolist(),
                "a": np.round(np.cumsum(a[real])[idx] / v_real[idx] * 100, 3).tolist(),
            }
            viradas_real = [
                round(float(v_real[i] / v_real[-1] * 100), 1)
                for i in viradas(np.cumsum(a[real] - b[real]), len(real))
            ]
        x = np.array(verdadeira["x"])
        y = np.array(verdadeira["a"])
        pontos_est = np.interp(x, x_est, y_est)
        de_1pc = x >= 1
        resultado.append({
            "ano": ano,
            "turno": turno,
            "nr": nr_a,
            "erro_medio": round(float(np.mean(np.abs(pontos_est - y)[de_1pc])), 3),
            "erro_max": round(float(np.max(np.abs(pontos_est - y)[de_1pc])), 3),
            "viradas_real": viradas_real,
            "viradas_estimada": [
                round(float(x_est[i]), 1) for i in viradas(np.cumsum(a[estimada] - b[estimada]), len(estimada))
            ],
            "real": {"x": verdadeira["x"], "a": verdadeira["a"]},
            "estimada": {"x": verdadeira["x"], "a": np.round(pontos_est, 3).tolist()},
        })
    return resultado


def main():
    SITE.mkdir(parents=True, exist_ok=True)
    coordenadas = pl.read_parquet(PROC / "municipios.parquet")
    doadores = {}
    for turno in (1, 2):
        _, urnas_doador, _ = carregar(DOADOR, turno)
        doadores[turno] = chegada_do_doador(urnas_doador)
    resumo = []
    for ano, turno in TURNOS:
        r = analisar(ano, turno, doadores, coordenadas)
        (SITE / f"turno_{ano}_{turno}.json").write_text(
            json.dumps(r, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )
        resumo.append({k: r[k] for k in (
            "ano", "turno", "ordem", "urnas", "urnas_sem_hora", "votos_validos", "a", "b", "viradas",
            "distancia_max", "distancia_max_sorteada", "sorteios_ordem",
        )} | {
            "amostras": [{k: v for k, v in x.items() if k != "pontos"} for x in r["amostras"]],
            "mini": {k: r["curva"][k][::8] + r["curva"][k][-1:] for k in ("x", "a", "b")},
        })
        print(ano, turno, r["ordem"], r["urnas"], r["a"], r["b"], "viradas", len(r["viradas"]), flush=True)
    teste = validar_emprestimo(doadores)
    (SITE / "resumo.json").write_text(
        json.dumps({"turnos": resumo, "teste_emprestimo": teste}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

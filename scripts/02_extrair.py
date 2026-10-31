"""Separa o voto para presidente, urna por urna, em dados/processados/.

Saída: um arquivo por turno (urnas_<ano>_<turno>t.parquet), com uma linha por
urna e candidato, mais conferencia_oficial.parquet, municipios.parquet e
horas_2018.parquet. Grava também dados/oficiais/parciais_2014_2t.csv.

Com o argumento "complementos", refaz só os horários de 2018 e as parciais de 2014.
"""
import io
import re
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import polars as pl
from pypdf import PdfReader

RAIZ = Path(__file__).resolve().parent.parent
BRUTOS = RAIZ / "dados" / "brutos"
SAIDA = RAIZ / "dados" / "processados"
PARTES = SAIDA / "partes"
LINHAS_POR_LOTE = 400_000

COLUNAS_RENOMEAR = {
    "SG_ UF": "SG_UF",
    "DS_CARGO_PERGUNTA": "DS_CARGO",
    "DT_BU_RECEBIDO": "RECEBIDO",
}


def lotes_de_presidente(arquivo):
    """Percorre o maior CSV do zip e entrega as linhas de presidente em lotes."""
    with zipfile.ZipFile(arquivo) as z:
        info = max(
            (i for i in z.infolist() if i.filename.lower().endswith((".csv", ".txt"))),
            key=lambda i: i.file_size,
        )
        with z.open(info) as f:
            cabecalho = f.readline()
            lote = []
            for linha in f:
                if b'RESIDENTE"' in linha or b'residente"' in linha:
                    lote.append(linha)
                    if len(lote) >= LINHAS_POR_LOTE:
                        yield cabecalho, lote
                        lote = []
            if lote:
                yield cabecalho, lote


def ler_lote(cabecalho, lote):
    bruto = (cabecalho + b"".join(lote)).decode("latin-1").encode("utf-8")
    tabela = pl.read_csv(
        io.BytesIO(bruto),
        separator=";",
        infer_schema_length=0,
        truncate_ragged_lines=True,
    )
    return tabela.rename({k: v for k, v in COLUNAS_RENOMEAR.items() if k in tabela.columns})


def normalizar(tabela, ano):
    faltando = {"RECEBIDO"} - set(tabela.columns)
    for coluna in faltando:
        tabela = tabela.with_columns(pl.lit(None, dtype=pl.String).alias(coluna))
    tabela = tabela.filter(pl.col("DS_CARGO").str.to_uppercase() == "PRESIDENTE")
    return tabela.select(
        pl.lit(ano).alias("ano"),
        pl.col("NR_TURNO").cast(pl.Int8).alias("turno"),
        pl.col("SG_UF").alias("uf"),
        pl.col("CD_MUNICIPIO").cast(pl.Int32).alias("cd_mun"),
        pl.col("NM_MUNICIPIO").alias("nm_mun"),
        pl.col("NR_ZONA").cast(pl.Int32).alias("zona"),
        pl.col("NR_SECAO").cast(pl.Int32).alias("secao"),
        pl.col("NR_VOTAVEL").cast(pl.Int32).alias("nr"),
        pl.col("NM_VOTAVEL").alias("nome"),
        pl.col("QT_VOTOS").cast(pl.Int32).alias("votos"),
        pl.coalesce(
            pl.col("RECEBIDO").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False),
            pl.col("RECEBIDO").str.to_datetime("%d/%m/%Y %H:%M:%S", strict=False),
        ).alias("recebido"),
    )


def processar(args):
    arquivo, ano = args
    destino = PARTES / f"{ano}_{arquivo.stem}.parquet"
    if destino.exists():
        return destino.name, pl.scan_parquet(destino).select(pl.len()).collect().item()
    partes = [normalizar(ler_lote(c, l), ano) for c, l in lotes_de_presidente(arquivo)]
    pl.concat(partes).write_parquet(destino)
    return destino.name, sum(p.height for p in partes)


def turnos_com_cabecalho():
    tarefas = []
    for ano in (2010, 2014, 2018):
        tarefas += [(p, ano) for p in sorted((BRUTOS / "secao" / str(ano)).glob("*_BR.zip"))]
    for ano in (2022, 2026):
        tarefas += [(p, ano) for p in sorted((BRUTOS / "bweb" / str(ano)).glob("*.zip"))]
    return tarefas


def conferencia_oficial():
    partes = []
    for arquivo in sorted((BRUTOS / "conferencia").glob("votacao_candidato_munzona_*.zip")):
        ano = int(re.search(r"(\d{4})", arquivo.name).group(1))
        with zipfile.ZipFile(arquivo) as z:
            nome = next(n for n in z.namelist() if n.upper().endswith("_BR.CSV"))
            bruto = z.read(nome).decode("latin-1").encode("utf-8")
        t = pl.read_csv(io.BytesIO(bruto), separator=";", infer_schema_length=0)
        coluna_votos = "QT_VOTOS_NOMINAIS_VALIDOS" if "QT_VOTOS_NOMINAIS_VALIDOS" in t.columns else "QT_VOTOS_NOMINAIS"
        t = t.filter(pl.col("DS_CARGO").str.to_uppercase() == "PRESIDENTE")
        partes.append(
            t.group_by(pl.col("NR_TURNO").cast(pl.Int8).alias("turno"), pl.col("NR_CANDIDATO").cast(pl.Int32).alias("nr"))
            .agg(pl.col("NM_URNA_CANDIDATO").first().alias("nome"), pl.col(coluna_votos).cast(pl.Int64).sum().alias("votos"))
            .with_columns(pl.lit(ano).alias("ano"))
        )
    pl.concat(partes).sort("ano", "turno", "votos", descending=[False, False, True]).write_parquet(
        SAIDA / "conferencia_oficial.parquet"
    )


def municipios():
    arquivo = next((BRUTOS / "locais").glob("*.zip"))
    partes = []
    with zipfile.ZipFile(arquivo) as z:
        for nome in z.namelist():
            if not nome.lower().endswith(".csv") or nome.upper().endswith("_BRASIL.CSV"):
                continue
            bruto = z.read(nome).decode("latin-1").encode("utf-8")
            t = pl.read_csv(io.BytesIO(bruto), separator=";", infer_schema_length=0)
            partes.append(t.select(
                pl.col("SG_UF").alias("uf"),
                pl.col("CD_MUNICIPIO").cast(pl.Int32).alias("cd_mun"),
                pl.col("NR_LATITUDE").str.replace(",", ".").cast(pl.Float64, strict=False).alias("lat"),
                pl.col("NR_LONGITUDE").str.replace(",", ".").cast(pl.Float64, strict=False).alias("lon"),
            ))
    t = pl.concat(partes).filter(pl.col("lat").is_between(-34.5, 6) & pl.col("lon").is_between(-74.5, -28))
    t.group_by("uf", "cd_mun").agg(pl.col("lat").median(), pl.col("lon").median()).write_parquet(
        SAIDA / "municipios.parquet"
    )


def horas_2018():
    """Hora da primeira totalização de cada urna: às 19h18 do 2º turno dá os 94,44% do TSE."""
    arquivo = BRUTOS / "detalhe" / "detalhe_votacao_secao_2018.zip"
    partes = [
        ler_lote(c, l)
        .filter(pl.col("DS_CARGO").str.to_uppercase() == "PRESIDENTE")
        .select(
            pl.col("NR_TURNO").cast(pl.Int8).alias("turno"),
            pl.col("SG_UF").alias("uf"),
            pl.col("CD_MUNICIPIO").cast(pl.Int32).alias("cd_mun"),
            pl.col("NR_ZONA").cast(pl.Int32).alias("zona"),
            pl.col("NR_SECAO").cast(pl.Int32).alias("secao"),
            pl.col("DT_PRIM_TOT_PARCIAL_HOR_TSE").str.to_datetime("%d/%m/%Y %H:%M:%S", strict=False).alias("hora"),
        )
        for c, l in lotes_de_presidente(arquivo)
    ]
    pl.concat(partes).unique(["turno", "uf", "cd_mun", "zona", "secao"]).write_parquet(SAIDA / "horas_2018.parquet")


def parciais_2014():
    """Transcreve a tabela oficial do TSE, parcial por parcial."""
    pasta = RAIZ / "dados" / "oficiais"
    pdf = PdfReader(pasta / "tse_evolucao_totalizacao_presidente_2t_2014.pdf")
    texto = "\n".join(pagina.extract_text() for pagina in pdf.pages)
    linhas = re.findall(r"(\d\d/\d\d/\d{4}) (\d\d:\d\d) ([\d.]+)\s+[\d,]+% ([\d.]+)\s+[\d,]+% ([\d.]+)", texto)
    numero = lambda v: int(v.replace(".", ""))
    pl.DataFrame({
        "data": [x[0] for x in linhas],
        "hora": [x[1] for x in linhas],
        "dilma": [numero(x[2]) for x in linhas],
        "aecio": [numero(x[3]) for x in linhas],
        "validos": [numero(x[4]) for x in linhas],
    }).write_csv(pasta / "parciais_2014_2t.csv")
    print(len(linhas), "parciais de 2014", flush=True)


def main():
    if "complementos" in sys.argv:
        horas_2018()
        parciais_2014()
        return
    PARTES.mkdir(parents=True, exist_ok=True)
    tarefas = turnos_com_cabecalho()
    print(len(tarefas), "arquivos", flush=True)
    with ProcessPoolExecutor(max_workers=6) as pool:
        for i, (nome, linhas) in enumerate(pool.map(processar, tarefas), 1):
            print(f"[{i}/{len(tarefas)}] {nome}: {linhas} linhas", flush=True)
    for ano in (2010, 2014, 2018, 2022, 2026):
        for turno in (1, 2):
            grupo = (
                pl.scan_parquet(PARTES / f"{ano}_*.parquet")
                .filter(pl.col("turno") == turno)
                .group_by("ano", "turno", "uf", "cd_mun", "nm_mun", "zona", "secao", "nr")
                .agg(pl.col("nome").first(), pl.col("votos").sum(), pl.col("recebido").min())
                .collect()
            )
            grupo.write_parquet(SAIDA / f"urnas_{ano}_{turno}t.parquet")
            print(ano, turno, grupo.height, "linhas", grupo["votos"].sum(), "votos", flush=True)
    conferencia_oficial()
    municipios()
    horas_2018()
    parciais_2014()


if __name__ == "__main__":
    main()

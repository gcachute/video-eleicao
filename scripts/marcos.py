"""Registros da época, conferidos na fonte: parciais com hora ou percentual de urnas.

base "hora": compara com a curva no mesmo horário; base "urnas": no mesmo percentual.
tipo "contagem": a hora é a da parcial; tipo "publicacao": a hora é a da matéria.
"""
TSE_PDF = (
    "https://web.archive.org/web/20210731123238/https://www.tse.jus.br/imprensa/noticias-tse/arquivos/"
    "evolucao-da-totalizacao-para-presidente-no-2o-turno-de-2014/at_download/file"
)
TSE_NOTA = (
    "https://www.tse.jus.br/comunicacao/noticias/2021/Julho/"
    "fato-ou-boato-e-falsa-a-planilha-que-mostra-inversoes-entre-aecio-neves-e-dilma-rousseff-no-2o-turno-de-2014"
)

MARCOS = [
    {"ano": 2010, "turno": 1, "hora": "21h32", "tipo": "publicacao", "base": "urnas", "urnas": 99.89, "valores": {13: 46.89, 45: 32.62},
     "fonte": "Agência Brasil", "data": "03/10/2010", "oficial": False,
     "url": "https://memoria.ebc.com.br/agenciabrasil/noticia/2010-10-03/dilma-e-serra-decidem-eleicao-presidencial-no-segundo-turno"},
    {"ano": 2010, "turno": 2, "hora": "18h59", "tipo": "publicacao", "base": "urnas", "urnas": 90.3, "valores": {13: 55.26, 45: 44.74},
     "fonte": "Agência Brasil", "data": "31/10/2010", "oficial": False,
     "nota": "Sul, Sudeste e Centro-Oeste com mais de 90% das urnas; Norte e Nordeste com mais de 75%",
     "url": "https://memoria.ebc.com.br/agenciabrasil/noticia/2010-10-31/com-90-das-urnas-apuradas-dilma-tem-55-dos-votos-e-serra-44"},
    {"ano": 2014, "turno": 1, "hora": None, "tipo": "publicacao", "base": "urnas", "urnas": 94, "valores": {13: 41.08, 45: 34.20},
     "fonte": "Diario de Cuyo", "data": "05/10/2014", "oficial": False,
     "url": "https://diariodecuyo.com.ar/mundo/Dilma-y-Neves-se-disputaran-la-presidencia-de-Brasil-en-el-ballotage-20141005-0002.html"},
    {"ano": 2014, "turno": 1, "hora": "20h59", "tipo": "publicacao", "base": "urnas", "urnas": 96, "valores": {13: 41.23, 45: 33.96},
     "fonte": "Agência Brasil", "data": "05/10/2014", "oficial": False,
     "url": "https://agenciabrasil.ebc.com.br/politica/noticia/2014-10/dilma-ganha-no-norte-e-nordeste-aecio-fica-na-frente-nas-outras-regioes"},
    {"ano": 2014, "turno": 2, "hora": "17h05", "tipo": "contagem", "base": "hora", "urnas": None, "valores": {13: 32.3, 45: 67.7},
     "fonte": "CNN Brasil", "data": "2021", "oficial": False,
     "url": "https://www.cnnbrasil.com.br/politica/parciais-nao-mostram-inversoes-entre-dilma-e-aecio-apontadas-por-bolsonaro/"},
    {"ano": 2014, "turno": 2, "hora": "18h32", "tipo": "contagem", "base": "hora", "urnas": None, "valores": {13: 44.56, 45: 55.4},
     "fonte": "O Tempo", "data": "02/10/2022", "oficial": False,
     "url": "https://www.otempo.com.br/eleicoes/em-2014-dilma-virou-resultado-das-eleicoes-sobre-aecio-neves-as-19h32-1.2743860"},
    {"ano": 2014, "turno": 2, "hora": "19h32", "tipo": "contagem", "base": "hora", "urnas": None, "valores": {13: 50.05},
     "fonte": "TSE, tabela oficial", "data": "29/07/2021", "oficial": True, "nota": "única troca de liderança da noite", "url": TSE_NOTA},
    {"ano": 2014, "turno": 2, "hora": "19h32", "tipo": "contagem", "base": "hora", "urnas": 88.9, "valores": {},
     "fonte": "Diário do Nordeste", "data": "26/10/2014", "oficial": False, "nota": "Dilma passa Aécio com 88,9% dos votos apurados",
     "url": "https://diariodonordeste.verdesmares.com.br/ultima-hora/pais/dilma-so-ultrapassou-aecio-com-88-9-dos-votos-apurados-1.1136216"},
    {"ano": 2014, "turno": 2, "hora": "20h00", "tipo": "contagem", "base": "hora", "urnas": 95, "valores": {},
     "fonte": "Bahia Notícias", "data": "2014", "oficial": False,
     "url": "https://www.bahianoticias.com.br/noticia/162414-aecio-liderou-disputa-por-presidencia-ate-quase-90-da-apuracao"},
    {"ano": 2014, "turno": 2, "hora": "20h14", "tipo": "publicacao", "base": "urnas", "urnas": 96.29, "valores": {13: 51.18, 45: 48.82},
     "fonte": "Agência Brasil", "data": "26/10/2014", "oficial": False,
     "url": "https://agenciabrasil.ebc.com.br/politica/noticia/2014-10/com-96-das-urnas-apuradas-eleicao-para-presidente-segue-indefinida"},
    {"ano": 2014, "turno": 2, "hora": "20h27", "tipo": "contagem", "base": "hora", "urnas": 98, "valores": {13: 51.45},
     "fonte": "Bahia Notícias", "data": "2014", "oficial": False,
     "url": "https://www.bahianoticias.com.br/noticia/162414-aecio-liderou-disputa-por-presidencia-ate-quase-90-da-apuracao"},
    {"ano": 2018, "turno": 1, "hora": "20h30", "tipo": "contagem", "base": "urnas", "urnas": 92.5, "valores": {17: 47.0, 13: 27.9},
     "fonte": "TSE no X", "data": "07/10/2018", "oficial": True, "url": "https://x.com/TSEjusbr/status/1049078659750014977"},
    {"ano": 2018, "turno": 1, "hora": "20h56", "tipo": "publicacao", "base": "urnas", "urnas": 96, "valores": {17: 46.70, 13: 28.37},
     "fonte": "Banda B", "data": "07/10/2018", "oficial": False,
     "url": "https://www.bandab.com.br/politica/com-68-de-secoes-apuradas-bolsonaro-tem-4842-e-haddad-2656/"},
    {"ano": 2018, "turno": 2, "hora": "19h18", "tipo": "contagem", "base": "urnas", "urnas": 94.44, "valores": {},
     "fonte": "TSE, ministra Rosa Weber, via Agência Brasil", "data": "28/10/2018", "oficial": True,
     "nota": "momento em que o resultado foi definido",
     "url": "https://agenciabrasil.ebc.com.br/politica/noticia/2018-10/com-100-das-urnas-apuradas-bolsonaro-teve-577-milhoes-de-votos"},
]

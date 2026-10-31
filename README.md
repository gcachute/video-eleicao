# A ordem das urnas

Recalcula, com dados do TSE, o sistema de um vídeo do perfil Ciência Visual sobre a apuração do 2º turno de 2026, e o aplica aos 10 turnos das eleições para presidente de 2010, 2014, 2018, 2022 e 2026.

Site: https://gcachute.github.io/video-eleicao/

O sistema tem três partes: a curva da parcial na ordem de chegada das urnas, a mesma curva em ordem sorteada, e quantas urnas sorteadas bastam para chegar perto do resultado final.

## Rodar

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe scripts/01_baixar.py
.venv/Scripts/python.exe scripts/02_extrair.py
.venv/Scripts/python.exe scripts/03_analisar.py
.venv/Scripts/python.exe scripts/04_conferir.py
python -m http.server 3200 --bind 127.0.0.1 --directory site
```

A tela local fica em http://localhost:3200. O download tem cerca de 9 GB, e só `dados/oficiais/` vai para o repositório. Cada envio para a `main` que altera `site/` publica o site.

## O que cada script faz

| Script | Faz |
|---|---|
| `01_baixar.py` | Baixa do TSE os boletins de urna, a votação por seção, os totais oficiais e os locais de votação |
| `02_extrair.py` | Separa o voto para presidente, urna por urna |
| `03_analisar.py` | Calcula curvas, sorteios, amostras, regiões e municípios, e grava `site/dados/` |
| `04_conferir.py` | Compara a soma das urnas com o TSE, os números com os do vídeo e a curva com os registros da época |

## Sobre os dados

- **Hora de cada urna existe em 2018, 2022 e 2026.** Em 2022 e 2026 vem do boletim de urna. Em 2018 vem do arquivo Detalhe da apuração por seção, no campo da primeira totalização: às 19h18 do 2º turno ele soma 94,44% das urnas, o número anunciado pelo TSE naquela noite.
- **2º turno de 2014: tabela oficial.** São 333 parciais publicadas pelo TSE em 2021, com votos e sem urnas. A página original saiu do ar; a cópia veio do arquivo da internet e está em `dados/oficiais/`, junto com a transcrição em CSV.
- **2010 e 1º turno de 2014: ordem estimada.** Não há hora por urna nem tabela de parciais, então a ordem é emprestada de 2018, município a município. A tela não mostra trocas de liderança nem distância do final nesses turnos. Contra a tabela de 2014 a estimativa erra 2,4 pontos em média e coloca a virada em 33% a 40% dos votos, quando a real foi em 89,6%.
- **Registros da época.** `scripts/marcos.py` guarda os números publicados nas noites de eleição, com a fonte de cada um, e a tela os mostra ao lado da curva.
- **Presidente fica no arquivo `_BR`.** Em 2010, 2014 e 2018 os arquivos estaduais de votação por seção não têm esse cargo, e o nacional já inclui exterior e voto em trânsito.
- **Catálogo do TSE com erro.** Em 2026 o boletim do 2º turno de Roraima aponta para o `.sha512`; o `01_baixar.py` recupera o `.zip`.
- **Número 28 no 1º turno de 2026.** Tem 5.246 votos nas urnas e não consta da totalização oficial; não entra como voto válido.
- **Troca de liderança.** Conta a partir de 1% das urnas e quando a nova posição dura ao menos 0,1% das urnas, com a mesma regra na ordem real e na sorteada.

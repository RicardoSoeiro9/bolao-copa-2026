# 🏆 Bolão Copa 2026

Dashboard em [Streamlit](https://streamlit.io/) para o bolão da Copa do Mundo de 2026.
Cruza os palpites dos participantes (placar de cada jogo da fase de grupos + previsões
finais de campeão/vice/3º/4º/artilheiro) com os resultados reais, buscados em tempo
quase real na API [football-data.org](https://www.football-data.org/).

> Projeto independente do "Bolão GRAMMER" — dados e repositório próprios.

## Estrutura

| Arquivo | Função |
|---|---|
| `app.py` | Interface Streamlit (Ranking, Jogos, Grupos, Participante, Regras). |
| `bolao.py` | Leitura dos CSVs e motor de pontuação (jogos + previsões finais). |
| `dados_copa.py` | Integração com a API football-data.org e bandeiras das seleções. |
| `jogos.csv` | Gabarito dos jogos da fase de grupos (grupo, casa, fora). |
| `palpites.csv` | Palpite de placar de cada participante por jogo. |
| `participantes.csv` | Previsões finais de cada participante (campeão/vice/3º/4º/artilheiro). |
| `regras_pontuacao.md` | Regras oficiais (exibidas na aba Regras). |

> As fotos originais dos formulários (`Formularios/`) **não** são versionadas — contêm
> nomes/assinaturas e o repositório é público.

## Pontuação

- **Por jogo (fase de grupos):** placar exato 10 · acertar vencedor 5 · acertar empate 7.
- **Previsões finais:** campeão 30 · vice 20 · artilheiro 20 · 3º 10 · 4º 10.
- **Desempate:** mais placares exatos → acerto do campeão → acerto do artilheiro →
  maior pontuação no grupo do Brasil → divisão do prêmio.
- **Premiação:** 70% / 20% / 10% do arrecadado (R$ 30 por participante).

## Rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

O app funciona sem chave de API (mostra os palpites, sem placares reais). Para os
resultados ao vivo, crie a chave gratuita em
<https://www.football-data.org/client/register> e configure:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edite .streamlit/secrets.toml e cole sua FOOTBALL_DATA_API_KEY
```

(Alternativamente, defina a variável de ambiente `FOOTBALL_DATA_API_KEY`.)

## Deploy no Streamlit Community Cloud

1. Crie um repositório **novo** no GitHub e faça o push deste projeto:
   ```bash
   git remote add origin https://github.com/<seu-usuario>/<seu-repo>.git
   git push -u origin master
   ```
2. Acesse <https://share.streamlit.io> e clique em **New app**.
3. Selecione o repositório, branch `master` e arquivo `app.py`.
4. Em **Advanced settings → Secrets**, adicione:
   ```toml
   FOOTBALL_DATA_API_KEY = "sua-chave-aqui"
   ```
5. **Deploy**. O app fica público; os placares se atualizam sozinhos a cada 2 minutos
   (limite do plano gratuito da API).

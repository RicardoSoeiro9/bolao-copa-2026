"""Integração com a API football-data.org (Copa do Mundo 2026, código WC).

Plano gratuito: 10 requisições/minuto. O cache do Streamlit mantém o app bem abaixo
desse limite mesmo com vários usuários simultâneos.

Reaproveitado do "Bolão GRAMMER", com o acréscimo de `obter_resultado_final`, que
deriva campeão / vice / 3º / 4º das partidas de mata-mata e o artilheiro do endpoint
`scorers` — usado para pontuar as previsões finais do bolão.
"""

import os
import unicodedata

import pandas as pd
import requests
import streamlit as st

API_BASE = "https://api.football-data.org/v4/competitions/WC"
TTL_SEGUNDOS = 120

# Nome em PT -> aliases possíveis na API (em inglês, sem acento, minúsculo).
# A API pode variar a grafia (ex: Turkey/Türkiye), então cada time tem mais de um alias.
TIMES_ALIASES = {
    "México": ["mexico"],
    "África do Sul": ["south africa"],
    "Coreia do Sul": ["south korea", "korea republic", "korea"],
    "Rep. Checa": ["czechia", "czech republic"],
    "Canadá": ["canada"],
    "Bósnia e Herzeg.": ["bosnia and herzegovina", "bosnia-herzegovina", "bosnia"],
    "Catar": ["qatar"],
    "Suiça": ["switzerland"],
    "Brasil": ["brazil"],
    "Marrocos": ["morocco"],
    "Haiti": ["haiti"],
    "Escócia": ["scotland"],
    "EUA": ["united states", "usa", "united states of america"],
    "Paraguai": ["paraguay"],
    "Austrália": ["australia"],
    "Turquia": ["turkey", "turkiye"],
    "Alemanha": ["germany"],
    "Curaçao": ["curacao"],
    "Costa do Marfim": ["ivory coast", "cote d'ivoire", "cote divoire"],
    "Equador": ["ecuador"],
    "Holanda": ["netherlands", "holland"],
    "Japão": ["japan"],
    "Suécia": ["sweden"],
    "Tunísia": ["tunisia"],
    "Bélgica": ["belgium"],
    "Egito": ["egypt"],
    "Irã": ["iran", "ir iran"],
    "Nova Zelandia": ["new zealand"],
    "Espanha": ["spain"],
    "Cabo Verde": ["cape verde", "cabo verde", "cape verde islands"],
    "Arábia Saudita": ["saudi arabia"],
    "Uruguai": ["uruguay"],
    "França": ["france"],
    "Senegal": ["senegal"],
    "Iraque": ["iraq"],
    "Noruega": ["norway"],
    "Argentina": ["argentina"],
    "Argélia": ["algeria"],
    "Austria": ["austria"],
    "Jordânia": ["jordan"],
    "Portugal": ["portugal"],
    "Congo DR": ["dr congo", "congo dr", "democratic republic of the congo"],
    "Uzbequistão": ["uzbekistan"],
    "Colômbia": ["colombia"],
    "Inglaterra": ["england"],
    "Croácia": ["croatia"],
    "Gana": ["ghana"],
    "Panamá": ["panama"],
}

BANDEIRAS = {
    "México": "🇲🇽", "África do Sul": "🇿🇦", "Coreia do Sul": "🇰🇷", "Rep. Checa": "🇨🇿",
    "Canadá": "🇨🇦", "Bósnia e Herzeg.": "🇧🇦", "Catar": "🇶🇦", "Suiça": "🇨🇭",
    "Brasil": "🇧🇷", "Marrocos": "🇲🇦", "Haiti": "🇭🇹", "Escócia": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "EUA": "🇺🇸", "Paraguai": "🇵🇾", "Austrália": "🇦🇺", "Turquia": "🇹🇷",
    "Alemanha": "🇩🇪", "Curaçao": "🇨🇼", "Costa do Marfim": "🇨🇮", "Equador": "🇪🇨",
    "Holanda": "🇳🇱", "Japão": "🇯🇵", "Suécia": "🇸🇪", "Tunísia": "🇹🇳",
    "Bélgica": "🇧🇪", "Egito": "🇪🇬", "Irã": "🇮🇷", "Nova Zelandia": "🇳🇿",
    "Espanha": "🇪🇸", "Cabo Verde": "🇨🇻", "Arábia Saudita": "🇸🇦", "Uruguai": "🇺🇾",
    "França": "🇫🇷", "Senegal": "🇸🇳", "Iraque": "🇮🇶", "Noruega": "🇳🇴",
    "Argentina": "🇦🇷", "Argélia": "🇩🇿", "Austria": "🇦🇹", "Jordânia": "🇯🇴",
    "Portugal": "🇵🇹", "Congo DR": "🇨🇩", "Uzbequistão": "🇺🇿", "Colômbia": "🇨🇴",
    "Inglaterra": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Croácia": "🇭🇷", "Gana": "🇬🇭", "Panamá": "🇵🇦",
}

# Código ISO usado pelo flagcdn.com — emojis de bandeira não renderizam no Windows
CODIGOS_ISO = {
    "México": "mx", "África do Sul": "za", "Coreia do Sul": "kr", "Rep. Checa": "cz",
    "Canadá": "ca", "Bósnia e Herzeg.": "ba", "Catar": "qa", "Suiça": "ch",
    "Brasil": "br", "Marrocos": "ma", "Haiti": "ht", "Escócia": "gb-sct",
    "EUA": "us", "Paraguai": "py", "Austrália": "au", "Turquia": "tr",
    "Alemanha": "de", "Curaçao": "cw", "Costa do Marfim": "ci", "Equador": "ec",
    "Holanda": "nl", "Japão": "jp", "Suécia": "se", "Tunísia": "tn",
    "Bélgica": "be", "Egito": "eg", "Irã": "ir", "Nova Zelandia": "nz",
    "Espanha": "es", "Cabo Verde": "cv", "Arábia Saudita": "sa", "Uruguai": "uy",
    "França": "fr", "Senegal": "sn", "Iraque": "iq", "Noruega": "no",
    "Argentina": "ar", "Argélia": "dz", "Austria": "at", "Jordânia": "jo",
    "Portugal": "pt", "Congo DR": "cd", "Uzbequistão": "uz", "Colômbia": "co",
    "Inglaterra": "gb-eng", "Croácia": "hr", "Gana": "gh", "Panamá": "pa",
}


def bandeira_html(time: str, altura: int = 15) -> str:
    """Tag <img> com a bandeira do país (para os cards em HTML)."""
    codigo = CODIGOS_ISO.get(time)
    if not codigo:
        return ""
    return (
        f'<img src="https://flagcdn.com/h24/{codigo}.png" height="{altura}" '
        f'style="vertical-align:-2px;border-radius:2px" alt="{time}">'
    )


STATUS_COM_PLACAR = {"IN_PLAY", "PAUSED", "FINISHED"}
STATUS_AO_VIVO = {"IN_PLAY", "PAUSED"}


def _normalizar(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return sem_acento.lower().strip()


_ALIAS_PARA_PT = {
    _normalizar(alias): nome_pt
    for nome_pt, aliases in TIMES_ALIASES.items()
    for alias in aliases
}


def nome_api_para_planilha(nome_api: str) -> str | None:
    return _ALIAS_PARA_PT.get(_normalizar(nome_api))


def obter_api_key() -> str | None:
    try:
        chave = st.secrets.get("FOOTBALL_DATA_API_KEY")
    except FileNotFoundError:
        chave = None
    return chave or os.environ.get("FOOTBALL_DATA_API_KEY")


def _requisitar(caminho: str, chave: str) -> dict:
    resposta = requests.get(
        f"{API_BASE}/{caminho}", headers={"X-Auth-Token": chave}, timeout=20
    )
    resposta.raise_for_status()
    return resposta.json()


@st.cache_data(ttl=TTL_SEGUNDOS, show_spinner="Buscando resultados da Copa...")
def obter_jogos(chave: str) -> pd.DataFrame:
    """Jogos da fase de grupos com placar real e status, nomes já em PT (do gabarito)."""
    dados = _requisitar("matches?stage=GROUP_STAGE", chave)
    jogos = []
    for partida in dados.get("matches", []):
        casa_api = partida["homeTeam"].get("name") or ""
        fora_api = partida["awayTeam"].get("name") or ""
        placar = partida.get("score", {}).get("fullTime", {})
        jogos.append(
            {
                "casa": nome_api_para_planilha(casa_api) or casa_api,
                "fora": nome_api_para_planilha(fora_api) or fora_api,
                "gols_casa": placar.get("home"),
                "gols_fora": placar.get("away"),
                "status": partida.get("status", "SCHEDULED"),
                "data_utc": partida.get("utcDate"),
                "grupo": (partida.get("group") or "").replace("GROUP_", "Grupo "),
                "minuto": partida.get("minute"),
            }
        )
    return pd.DataFrame(jogos)


@st.cache_data(ttl=TTL_SEGUNDOS, show_spinner="Buscando classificação dos grupos...")
def obter_classificacao(chave: str) -> pd.DataFrame:
    """Classificação real dos grupos; uma linha por (grupo, time), nomes em PT."""
    dados = _requisitar("standings", chave)
    linhas = []
    for tabela in dados.get("standings", []):
        if tabela.get("type") != "TOTAL":
            continue
        grupo = (tabela.get("group") or "").replace("GROUP_", "Grupo ")
        for item in tabela.get("table", []):
            nome_api = item["team"].get("name") or ""
            linhas.append(
                {
                    "grupo": grupo,
                    "posicao": item.get("position"),
                    "time": nome_api_para_planilha(nome_api) or nome_api,
                    "pontos": item.get("points"),
                    "jogos": item.get("playedGames"),
                    "vitorias": item.get("won"),
                    "empates": item.get("draw"),
                    "derrotas": item.get("lost"),
                    "saldo": item.get("goalDifference"),
                }
            )
    return pd.DataFrame(linhas)


# Estágios de mata-mata como a football-data.org costuma nomear na competição WC.
_ESTAGIO_FINAL = "FINAL"
_ESTAGIO_TERCEIRO = "THIRD_PLACE"


def _vencedor_perdedor(partida: dict) -> tuple[str | None, str | None]:
    """Devolve (vencedor_pt, perdedor_pt) de uma partida ENCERRADA; senão (None, None)."""
    if partida.get("status") != "FINISHED":
        return None, None
    casa = partida["homeTeam"].get("name") or ""
    fora = partida["awayTeam"].get("name") or ""
    casa_pt = nome_api_para_planilha(casa) or casa
    fora_pt = nome_api_para_planilha(fora) or fora
    vencedor_api = partida.get("score", {}).get("winner")  # HOME_TEAM / AWAY_TEAM / DRAW
    if vencedor_api == "HOME_TEAM":
        return casa_pt, fora_pt
    if vencedor_api == "AWAY_TEAM":
        return fora_pt, casa_pt
    return None, None


@st.cache_data(ttl=TTL_SEGUNDOS, show_spinner="Buscando resultado final da Copa...")
def obter_resultado_final(chave: str) -> dict:
    """Deriva campeão / vice / 3º / 4º (mata-mata) e o artilheiro (scorers).

    Cada chave pode ser None enquanto o jogo correspondente não terminou.
    Nomes de seleção em PT; artilheiro como veio da API (texto livre).
    """
    resultado = {
        "campeao": None,
        "vice": None,
        "terceiro": None,
        "quarto": None,
        "artilheiro": None,
    }

    try:
        dados = _requisitar("matches?stage=FINAL,THIRD_PLACE", chave)
    except requests.RequestException:
        dados = {}
    for partida in dados.get("matches", []):
        estagio = partida.get("stage")
        vencedor, perdedor = _vencedor_perdedor(partida)
        if vencedor is None:
            continue
        if estagio == _ESTAGIO_FINAL:
            resultado["campeao"], resultado["vice"] = vencedor, perdedor
        elif estagio == _ESTAGIO_TERCEIRO:
            resultado["terceiro"], resultado["quarto"] = vencedor, perdedor

    try:
        scorers = _requisitar("scorers?limit=1", chave)
        artilheiros = scorers.get("scorers", [])
        if artilheiros:
            resultado["artilheiro"] = artilheiros[0]["player"].get("name")
    except requests.RequestException:
        pass

    return resultado

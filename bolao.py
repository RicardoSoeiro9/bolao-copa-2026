"""Leitura dos palpites (CSV) e motor de pontuação do Bolão Copa 2026.

Regras (de regras_pontuacao.md):
- Por jogo (fase de grupos): placar exato 10, acertar vencedor 5, acertar empate 7.
- Previsões finais: campeão 30, vice 20, artilheiro 20, 3º 10, 4º 10.
- Desempate: mais placares exatos > acerto do campeão > acerto do artilheiro >
  maior pontuação no grupo do Brasil > divisão do prêmio (ordem alfabética como
  critério determinístico final).

Os palpites por jogo vêm de `palpites.csv` (extraídos dos formulários preenchidos à
mão) e as previsões finais de `participantes.csv`.
"""

import re
from pathlib import Path

import pandas as pd
import streamlit as st

from dados_copa import _normalizar

PASTA = Path(__file__).parent
ARQUIVO_JOGOS = PASTA / "jogos.csv"
ARQUIVO_PALPITES = PASTA / "palpites.csv"
ARQUIVO_PARTICIPANTES = PASTA / "participantes.csv"

ARQUIVO_JOGOS_MATA = PASTA / "jogos_mata.csv"
ARQUIVO_PALPITES_MATA = PASTA / "palpites_mata.csv"
ARQUIVO_PARTICIPANTES_MATA = PASTA / "participantes_mata.csv"

PONTOS_PLACAR_EXATO = 10
PONTOS_VENCEDOR = 5
PONTOS_EMPATE = 7

PONTOS_CAMPEAO = 30
PONTOS_VICE = 20
PONTOS_ARTILHEIRO = 20
PONTOS_TERCEIRO = 10
PONTOS_QUARTO = 10

# Bolão do mata-mata: por jogo, máx. 3 pts (vencedor/empate + gols A + gols B);
# pontos extra pelos palpites de pódio. Ver regras_pontuacao_mata.md.
PONTOS_MATA_RESULTADO = 1
PONTOS_MATA_GOLS_CASA = 1
PONTOS_MATA_GOLS_FORA = 1

PONTOS_MATA_CAMPEAO = 10
PONTOS_MATA_VICE = 6
PONTOS_MATA_TERCEIRO = 4
PONTOS_MATA_QUARTO = 2


@st.cache_data(show_spinner="Lendo gabarito de jogos...")
def carregar_jogos_gabarito() -> pd.DataFrame:
    """Lê jogos.csv: os jogos oficiais da fase de grupos (grupo, casa, fora)."""
    df = pd.read_csv(ARQUIVO_JOGOS, dtype=str)
    for col in ("grupo", "casa", "fora"):
        df[col] = df[col].str.strip()
    return df


@st.cache_data(show_spinner="Lendo palpites dos participantes...")
def carregar_palpites() -> pd.DataFrame:
    """Lê palpites.csv (uma linha por participante/jogo)."""
    df = pd.read_csv(ARQUIVO_PALPITES, dtype=str)
    for col in ("participante", "grupo", "casa", "fora"):
        df[col] = df[col].str.strip()
    for col in ("palpite_casa", "palpite_fora"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(show_spinner="Lendo previsões finais...")
def carregar_participantes() -> pd.DataFrame:
    """Lê participantes.csv (palpites de campeão/vice/3º/4º/artilheiro)."""
    df = pd.read_csv(ARQUIVO_PARTICIPANTES, dtype=str)
    return df.apply(lambda c: c.str.strip() if c.dtype == "object" else c)


@st.cache_data(show_spinner="Lendo gabarito do mata-mata...")
def carregar_jogos_mata() -> pd.DataFrame:
    """Lê jogos_mata.csv: a numeração oficial dos jogos do mata-mata (jogo, fase, ...)."""
    df = pd.read_csv(ARQUIVO_JOGOS_MATA, dtype=str)
    for col in df.columns:
        df[col] = df[col].str.strip()
    df["jogo"] = pd.to_numeric(df["jogo"], errors="coerce")
    return df


@st.cache_data(show_spinner="Lendo palpites do mata-mata...")
def carregar_palpites_mata() -> pd.DataFrame:
    """Lê palpites_mata.csv (uma linha por participante/jogo do mata-mata)."""
    df = pd.read_csv(ARQUIVO_PALPITES_MATA, dtype=str)
    if "participante" in df.columns:
        df["participante"] = df["participante"].str.strip()
    for col in ("jogo", "palpite_casa", "palpite_fora"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(show_spinner="Lendo previsões de pódio do mata-mata...")
def carregar_participantes_mata() -> pd.DataFrame:
    """Lê participantes_mata.csv (palpites de campeão/vice/3º/4º do mata-mata)."""
    df = pd.read_csv(ARQUIVO_PARTICIPANTES_MATA, dtype=str)
    return df.apply(lambda c: c.str.strip() if c.dtype == "object" else c)


def pontuar(
    palpite_casa: int,
    palpite_fora: int,
    real_casa: int,
    real_fora: int,
) -> tuple[float, str]:
    """Retorna (pontos, tipo) de um palpite de jogo contra o resultado real.

    tipo: 'placar_exato' | 'vencedor' | 'empate' | 'errou'
    """
    if palpite_casa == real_casa and palpite_fora == real_fora:
        return PONTOS_PLACAR_EXATO, "placar_exato"

    sinal_palpite = (palpite_casa > palpite_fora) - (palpite_casa < palpite_fora)
    sinal_real = (real_casa > real_fora) - (real_casa < real_fora)
    if sinal_palpite == sinal_real:
        if sinal_real == 0:
            return PONTOS_EMPATE, "empate"
        return PONTOS_VENCEDOR, "vencedor"

    return 0.0, "errou"


def avaliar_palpites(palpites: pd.DataFrame, jogos_reais: pd.DataFrame) -> pd.DataFrame:
    """Cruza palpites com resultados reais (jogo a jogo).

    Só pontua jogos com placar disponível (em andamento ou encerrados).
    Acrescenta colunas: gols_casa, gols_fora, status, data_utc, pontos, tipo.
    """
    cols = ["casa", "fora", "gols_casa", "gols_fora", "status"]
    if "data_utc" in jogos_reais.columns:
        cols.append("data_utc")
    avaliado = palpites.merge(jogos_reais[cols], on=["casa", "fora"], how="left")

    def _avaliar(row):
        if (
            pd.isna(row["gols_casa"])
            or pd.isna(row["gols_fora"])
            or pd.isna(row["palpite_casa"])
            or pd.isna(row["palpite_fora"])
        ):
            return pd.Series({"pontos": 0.0, "tipo": "pendente"})
        pontos, tipo = pontuar(
            int(row["palpite_casa"]),
            int(row["palpite_fora"]),
            int(row["gols_casa"]),
            int(row["gols_fora"]),
        )
        return pd.Series({"pontos": pontos, "tipo": tipo})

    avaliado[["pontos", "tipo"]] = avaliado.apply(_avaliar, axis=1)
    return avaliado


def pontuar_mata(
    palpite_casa: int,
    palpite_fora: int,
    real_casa: int,
    real_fora: int,
) -> tuple[int, str]:
    """Pontua um jogo do mata-mata (máx. 3): vencedor/empate + gols A + gols B.

    Usa o placar do fim da prorrogação (sem pênaltis). tipo: 'exato' (3) |
    'parcial' (1–2) | 'errou' (0).
    """
    sinal_palpite = (palpite_casa > palpite_fora) - (palpite_casa < palpite_fora)
    sinal_real = (real_casa > real_fora) - (real_casa < real_fora)

    pontos = 0
    if sinal_palpite == sinal_real:
        pontos += PONTOS_MATA_RESULTADO
    if palpite_casa == real_casa:
        pontos += PONTOS_MATA_GOLS_CASA
    if palpite_fora == real_fora:
        pontos += PONTOS_MATA_GOLS_FORA

    if pontos == 3:
        tipo = "exato"
    elif pontos == 0:
        tipo = "errou"
    else:
        tipo = "parcial"
    return pontos, tipo


def avaliar_palpites_mata(palpites: pd.DataFrame, jogos_reais: pd.DataFrame) -> pd.DataFrame:
    """Cruza palpites do mata-mata com os jogos reais pelo NÚMERO do jogo.

    Os times de cada fase dependem da classificação, então o casamento é por `jogo`,
    não por par de seleções. Só pontua jogos com placar disponível.
    """
    cols = ["jogo", "casa", "fora", "gols_casa", "gols_fora", "status", "fase"]
    if "data_utc" in jogos_reais.columns:
        cols.append("data_utc")
    cols = [c for c in cols if c in jogos_reais.columns]
    avaliado = palpites.merge(jogos_reais[cols], on="jogo", how="left")

    def _avaliar(row):
        if (
            pd.isna(row.get("gols_casa"))
            or pd.isna(row.get("gols_fora"))
            or pd.isna(row.get("palpite_casa"))
            or pd.isna(row.get("palpite_fora"))
        ):
            return pd.Series({"pontos": 0, "tipo": "pendente"})
        pontos, tipo = pontuar_mata(
            int(row["palpite_casa"]),
            int(row["palpite_fora"]),
            int(row["gols_casa"]),
            int(row["gols_fora"]),
        )
        return pd.Series({"pontos": pontos, "tipo": tipo})

    avaliado[["pontos", "tipo"]] = avaliado.apply(_avaliar, axis=1)
    return avaliado


def _mesma_selecao(a: str | None, b: str | None) -> bool:
    """Compara nomes de seleção ignorando acento/caixa (ex.: 'FRANCA' == 'França')."""
    if not a or not b:
        return False
    return _normalizar(a) == _normalizar(b)


def _canon_artilheiro(nome: str | None) -> str:
    """Reduz um nome de jogador ao sobrenome normalizado para comparar variações.

    'KYLIAN MBAPPE (FRANCA)' / 'K. MBAPPE' / 'MBAPPE' / 'Kylian Mbappé' -> 'mbappe'.
    """
    if not nome:
        return ""
    sem_parenteses = re.sub(r"\(.*?\)", " ", nome)
    palavras = [
        p for p in re.split(r"[\s.]+", _normalizar(sem_parenteses))
        if len(p) > 1  # descarta iniciais ('k', 'h')
    ]
    return palavras[-1] if palavras else ""


def _mesmo_artilheiro(a: str | None, b: str | None) -> bool:
    ca, cb = _canon_artilheiro(a), _canon_artilheiro(b)
    return bool(ca) and ca == cb


def pontuar_final(palpite: pd.Series, resultado: dict) -> dict:
    """Pontua as 5 previsões finais de um participante.

    Retorna dict com pontos por item, total, e flags de acerto p/ desempate.
    """
    acerto_campeao = _mesma_selecao(palpite.get("campeao"), resultado.get("campeao"))
    acerto_vice = _mesma_selecao(palpite.get("vice_campeao"), resultado.get("vice"))
    acerto_terceiro = _mesma_selecao(
        palpite.get("terceiro_lugar"), resultado.get("terceiro")
    )
    acerto_quarto = _mesma_selecao(palpite.get("quarto_lugar"), resultado.get("quarto"))
    acerto_artilheiro = _mesmo_artilheiro(
        palpite.get("artilheiro"), resultado.get("artilheiro")
    )

    pontos = (
        PONTOS_CAMPEAO * acerto_campeao
        + PONTOS_VICE * acerto_vice
        + PONTOS_TERCEIRO * acerto_terceiro
        + PONTOS_QUARTO * acerto_quarto
        + PONTOS_ARTILHEIRO * acerto_artilheiro
    )
    return {
        "pontos_final": float(pontos),
        "acerto_campeao": acerto_campeao,
        "acerto_vice": acerto_vice,
        "acerto_terceiro": acerto_terceiro,
        "acerto_quarto": acerto_quarto,
        "acerto_artilheiro": acerto_artilheiro,
    }


def grupo_do_brasil(jogos_gabarito: pd.DataFrame) -> str | None:
    """Identifica o grupo onde o Brasil joga (para o 4º critério de desempate)."""
    brasil = jogos_gabarito[
        (jogos_gabarito["casa"] == "Brasil") | (jogos_gabarito["fora"] == "Brasil")
    ]
    if brasil.empty:
        return None
    return brasil["grupo"].iloc[0]


def montar_ranking(
    avaliado: pd.DataFrame,
    participantes: pd.DataFrame,
    resultado_final: dict,
    grupo_brasil: str | None,
) -> pd.DataFrame:
    """Agrega pontos de jogo + previsões finais e ordena pelos critérios do bolão.

    Usa a lista de `participantes` como espinha: todos aparecem no ranking mesmo que
    ainda não haja palpites de jogo extraídos para eles.
    """
    por_participante = dict(tuple(avaliado.groupby("participante"))) if len(avaliado) else {}

    linhas = []
    for _, p in participantes.iterrows():
        nome = p["nome"]
        final = pontuar_final(p, resultado_final)
        grupo_df = por_participante.get(nome)
        if grupo_df is None:
            pontos_jogo = pe = ven = emp = 0
            pontos_grupo_brasil = 0.0
        else:
            pontos_jogo = grupo_df["pontos"].sum()
            pe = int((grupo_df["tipo"] == "placar_exato").sum())
            ven = int((grupo_df["tipo"] == "vencedor").sum())
            emp = int((grupo_df["tipo"] == "empate").sum())
            pontos_grupo_brasil = (
                grupo_df.loc[grupo_df["grupo"] == grupo_brasil, "pontos"].sum()
                if grupo_brasil
                else 0.0
            )
        linhas.append(
            {
                "participante": nome,
                "pontos": pontos_jogo + final["pontos_final"],
                "pontos_jogo": pontos_jogo,
                "pontos_final": final["pontos_final"],
                "pe": pe,
                "ven": ven,
                "emp": emp,
                "acerto_campeao": final["acerto_campeao"],
                "acerto_artilheiro": final["acerto_artilheiro"],
                "pts_grupo_brasil": pontos_grupo_brasil,
            }
        )
    ranking = pd.DataFrame(linhas)

    # Critério determinístico final: ordem alfabética (sem acento) em caso de empate total
    ranking["nome_ordem"] = (
        ranking["participante"]
        .str.normalize("NFKD")
        .str.encode("ascii", "ignore")
        .str.decode("ascii")
        .str.lower()
    )
    ranking = ranking.sort_values(
        by=[
            "pontos",
            "pe",
            "acerto_campeao",
            "acerto_artilheiro",
            "pts_grupo_brasil",
            "nome_ordem",
        ],
        ascending=[False, False, False, False, False, True],
    ).drop(columns="nome_ordem")
    ranking.insert(0, "posicao", range(1, len(ranking) + 1))
    return ranking.reset_index(drop=True)


def pontuar_extras(palpite: pd.Series, resultado: dict) -> dict:
    """Pontua os 4 palpites de pódio do mata-mata (campeão/vice/3º/4º)."""
    acerto_campeao = _mesma_selecao(palpite.get("campeao"), resultado.get("campeao"))
    acerto_vice = _mesma_selecao(palpite.get("vice_campeao"), resultado.get("vice"))
    acerto_terceiro = _mesma_selecao(
        palpite.get("terceiro_lugar"), resultado.get("terceiro")
    )
    acerto_quarto = _mesma_selecao(palpite.get("quarto_lugar"), resultado.get("quarto"))

    pontos = (
        PONTOS_MATA_CAMPEAO * acerto_campeao
        + PONTOS_MATA_VICE * acerto_vice
        + PONTOS_MATA_TERCEIRO * acerto_terceiro
        + PONTOS_MATA_QUARTO * acerto_quarto
    )
    return {
        "pontos_extra": float(pontos),
        "acerto_campeao": acerto_campeao,
        "acerto_vice": acerto_vice,
        "acerto_terceiro": acerto_terceiro,
        "acerto_quarto": acerto_quarto,
    }


def montar_ranking_mata(
    avaliado: pd.DataFrame,
    participantes: pd.DataFrame,
    resultado_final: dict,
) -> pd.DataFrame:
    """Ranking do bolão do mata-mata: pontos por jogo + pontos extra de pódio.

    Usa a lista de `participantes` como espinha (todos aparecem, mesmo sem palpites).
    Desempate: mais placares exatos > acerto do campeão > nome (alfabético).
    """
    por_participante = (
        dict(tuple(avaliado.groupby("participante"))) if len(avaliado) else {}
    )

    linhas = []
    for _, p in participantes.iterrows():
        nome = p["nome"]
        extra = pontuar_extras(p, resultado_final)
        grupo_df = por_participante.get(nome)
        if grupo_df is None:
            pontos_jogo = exatos = parciais = 0
        else:
            pontos_jogo = int(grupo_df["pontos"].sum())
            exatos = int((grupo_df["tipo"] == "exato").sum())
            parciais = int((grupo_df["tipo"] == "parcial").sum())
        linhas.append(
            {
                "participante": nome,
                "pontos": pontos_jogo + extra["pontos_extra"],
                "pontos_jogo": pontos_jogo,
                "pontos_extra": extra["pontos_extra"],
                "exatos": exatos,
                "parciais": parciais,
                "acerto_campeao": extra["acerto_campeao"],
            }
        )
    ranking = pd.DataFrame(linhas)
    if ranking.empty:
        return ranking

    ranking["nome_ordem"] = (
        ranking["participante"]
        .str.normalize("NFKD")
        .str.encode("ascii", "ignore")
        .str.decode("ascii")
        .str.lower()
    )
    ranking = ranking.sort_values(
        by=["pontos", "exatos", "acerto_campeao", "nome_ordem"],
        ascending=[False, False, False, True],
    ).drop(columns="nome_ordem")
    ranking.insert(0, "posicao", range(1, len(ranking) + 1))
    return ranking.reset_index(drop=True)

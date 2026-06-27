"""Bolão Copa 2026 — ranking em tempo quase real (palpites + API football-data.org)."""

from pathlib import Path

import pandas as pd
import requests
import streamlit as st

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:  # pacote ausente ou com build do frontend quebrada
    st_autorefresh = None

import bolao
import dados_copa
from dados_copa import STATUS_AO_VIVO, STATUS_COM_PLACAR, _normalizar, bandeira_html


def _html(conteudo: str) -> None:
    """Renderiza HTML achatado em uma linha — indentação viraria bloco de código."""
    st.markdown(
        "".join(linha.strip() for linha in conteudo.splitlines()),
        unsafe_allow_html=True,
    )


VALOR_POR_PARTICIPANTE = 30
VALOR_POR_PARTICIPANTE_MATA = 25
PERC_PREMIOS = {1: 0.70, 2: 0.20, 3: 0.10}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo+Black&family=Inter:wght@400;600;800&display=swap');

.stApp {
    background: radial-gradient(ellipse at top, #0c2b1a 0%, #07140d 55%, #050a07 100%);
}
h1, h2, h3 { font-family: 'Archivo Black', sans-serif !important; }

.banner {
    text-align: center; padding: 28px 10px 20px;
    background: linear-gradient(135deg, rgba(14,60,34,.95), rgba(8,30,18,.95));
    border: 1px solid rgba(212,175,55,.45); border-radius: 18px; margin-bottom: 18px;
}
.banner .titulo {
    font-family: 'Archivo Black', sans-serif; font-size: 2.3rem; letter-spacing: 2px;
    background: linear-gradient(90deg, #f5d34c, #d4af37, #f8e58c);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.banner .subtitulo { color: #9fd8b4; font-family: 'Inter', sans-serif;
    font-weight: 600; letter-spacing: 4px; font-size: .85rem; margin-top: 4px; }

.podio { display: flex; gap: 14px; justify-content: center; flex-wrap: wrap; margin: 8px 0 18px; }
.podio-card {
    flex: 1 1 200px; max-width: 270px; text-align: center; padding: 18px 12px 14px;
    border-radius: 16px; font-family: 'Inter', sans-serif;
    background: linear-gradient(160deg, rgba(255,255,255,.07), rgba(255,255,255,.02));
    border: 1px solid rgba(255,255,255,.12);
}
.podio-card.ouro { border-color: #d4af37; box-shadow: 0 0 24px rgba(212,175,55,.25);
    background: linear-gradient(160deg, rgba(212,175,55,.16), rgba(212,175,55,.03)); }
.podio-card.prata { border-color: #b8bcc4; }
.podio-card.bronze { border-color: #b07c4f; }
.podio-card .medalha { font-size: 2.2rem; }
.podio-card .nome { font-weight: 800; font-size: 1.05rem; color: #fff; margin-top: 2px; }
.podio-card .pts { font-family: 'Archivo Black', sans-serif; font-size: 1.7rem; color: #f5d34c; }
.podio-card .premio { color: #9fd8b4; font-weight: 600; font-size: .85rem; }

.dia-titulo { font-family: 'Inter', sans-serif; font-weight: 800; color: #9fd8b4;
    letter-spacing: 2px; font-size: .9rem; margin: 18px 0 8px; text-transform: uppercase; }
.jogos-grid { display: flex; flex-wrap: wrap; gap: 12px; }
.jogo-card {
    flex: 1 1 300px; max-width: 420px; padding: 14px 16px; border-radius: 14px;
    font-family: 'Inter', sans-serif;
    background: linear-gradient(160deg, rgba(255,255,255,.06), rgba(255,255,255,.02));
    border: 1px solid rgba(255,255,255,.10);
}
.jogo-card.aovivo { border-color: #ff5252; box-shadow: 0 0 16px rgba(255,82,82,.25); }
.jogo-card .topo { display: flex; justify-content: space-between; font-size: .72rem;
    color: #8fae9c; font-weight: 600; letter-spacing: 1px; margin-bottom: 8px; }
.jogo-card .linha { display: flex; align-items: center; justify-content: space-between; }
.jogo-card .time { flex: 1; color: #fff; font-weight: 600; font-size: .95rem; }
.jogo-card .time.fora { text-align: right; }
.jogo-card .placar { font-family: 'Archivo Black', sans-serif; font-size: 1.5rem;
    color: #f5d34c; padding: 0 14px; white-space: nowrap; }
.badge { padding: 2px 8px; border-radius: 999px; font-size: .68rem; font-weight: 800; }
.badge.live { background: #ff5252; color: #fff; animation: pulsar 1.2s infinite; }
.badge.fim { background: rgba(159,216,180,.18); color: #9fd8b4; }
.badge.agendado { background: rgba(255,255,255,.10); color: #cdd6d0; }
@keyframes pulsar { 0%,100% { opacity: 1; } 50% { opacity: .45; } }

.final-grid { display: flex; flex-wrap: wrap; gap: 12px; margin: 8px 0 4px; }
.final-card { flex: 1 1 150px; padding: 14px; border-radius: 14px; font-family: 'Inter', sans-serif;
    background: linear-gradient(160deg, rgba(255,255,255,.06), rgba(255,255,255,.02));
    border: 1px solid rgba(255,255,255,.10); }
.final-card.ok { border-color: #4caf78; box-shadow: 0 0 14px rgba(76,175,120,.22); }
.final-card .rotulo { color: #8fae9c; font-size: .72rem; font-weight: 700;
    letter-spacing: 1px; text-transform: uppercase; }
.final-card .palpite { color: #fff; font-weight: 800; font-size: 1.05rem; margin-top: 4px; }
.final-card .ganho { color: #f5d34c; font-weight: 700; font-size: .8rem; margin-top: 2px; }

/* Tabela de ranking */
.rank-tabela { width: 100%; border-collapse: collapse; font-family: 'Inter', sans-serif; margin-top: 6px; }
.rank-tabela th { text-align: left; color: #9fd8b4; font-size: .7rem; text-transform: uppercase;
    letter-spacing: 1px; padding: 8px 10px; border-bottom: 1px solid rgba(255,255,255,.14); }
.rank-tabela th.num, .rank-tabela td.num { text-align: center; }
.rank-tabela td { padding: 9px 10px; border-bottom: 1px solid rgba(255,255,255,.06); color: #e8efe9; font-size: .92rem; }
.rank-tabela tr:hover td { background: rgba(255,255,255,.04); }
.rank-pos { font-family: 'Archivo Black', sans-serif; color: #9fd8b4; text-align: center; width: 46px; }
.rank-nome { font-weight: 700; color: #fff; }
.rank-premio { color: #9fd8b4; font-weight: 600; font-size: .75rem; }
.rank-total { font-family: 'Archivo Black', sans-serif; color: #f5d34c; font-size: 1.15rem; text-align: center; }
.rank-tabela tr.ouro td { background: rgba(212,175,55,.12); }
.rank-tabela tr.prata td { background: rgba(184,188,196,.10); }
.rank-tabela tr.bronze td { background: rgba(176,124,79,.12); }

/* Cards de classificação dos grupos */
.grp-wrap { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 6px; }
.grp-card { flex: 1 1 290px; max-width: 360px; padding: 12px 14px; border-radius: 14px;
    font-family: 'Inter', sans-serif;
    background: linear-gradient(160deg, rgba(255,255,255,.06), rgba(255,255,255,.02));
    border: 1px solid rgba(255,255,255,.10); }
.grp-card .gh { margin: 0 0 8px; color: #f5d34c; font-family: 'Archivo Black', sans-serif;
    font-size: .95rem; letter-spacing: 1px; }
.grp-row { display: flex; align-items: center; gap: 8px; padding: 5px 6px; border-radius: 8px;
    font-size: .9rem; color: #e8efe9; }
.grp-row.q { background: rgba(76,175,120,.14); }
.grp-row .gpos { width: 16px; color: #8fae9c; font-weight: 700; text-align: center; }
.grp-row .gtime { flex: 1; color: #fff; }
.grp-row .gpts { font-weight: 800; color: #f5d34c; width: 26px; text-align: right; }
.grp-row .gjsg { color: #8fae9c; font-size: .76rem; width: 86px; text-align: right; }
.grp-leg { color: #8fae9c; font-size: .74rem; margin: 4px 0 14px; }

/* Tabela de palpites do participante */
.pg-tabela { width: 100%; border-collapse: collapse; font-family: 'Inter', sans-serif; margin-top: 6px; }
.pg-tabela th { text-align: left; color: #9fd8b4; font-size: .68rem; text-transform: uppercase;
    letter-spacing: 1px; padding: 7px 9px; border-bottom: 1px solid rgba(255,255,255,.14); }
.pg-tabela th.c, .pg-tabela td.c { text-align: center; }
.pg-tabela td { padding: 8px 9px; border-bottom: 1px solid rgba(255,255,255,.06); color: #e8efe9; font-size: .9rem; }
.pg-tabela tr:hover td { background: rgba(255,255,255,.04); }
.pg-data { color: #8fae9c; font-size: .78rem; white-space: nowrap; }
.pg-jogo { color: #fff; }
.pg-pal { font-weight: 700; color: #cdd6d0; }
.pg-real { font-weight: 800; color: #f5d34c; }
.pg-pts { font-family: 'Archivo Black', sans-serif; color: #f5d34c; text-align: center; }
.pg-badge { padding: 2px 8px; border-radius: 999px; font-size: .7rem; font-weight: 800; white-space: nowrap; }
.pg-badge.exato { background: rgba(76,175,120,.22); color: #7fe0a6; }
.pg-badge.venc { background: rgba(159,216,180,.16); color: #9fd8b4; }
.pg-badge.emp { background: rgba(212,175,55,.18); color: #f5d34c; }
.pg-badge.errou { background: rgba(255,82,82,.16); color: #ff8a8a; }
.pg-badge.pend { background: rgba(255,255,255,.08); color: #cdd6d0; }
.pg-resumo { display: flex; flex-wrap: wrap; gap: 10px; margin: 10px 0 2px; }
.pg-chip { padding: 6px 12px; border-radius: 999px; font-family: 'Inter', sans-serif; font-size: .82rem;
    background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.10); color: #e8efe9; }
.pg-chip b { color: #f5d34c; }
</style>
"""


def render_banner():
    _html(
        """
        <div class="banner">
            <div class="titulo">🏆 BOLÃO COPA 2026</div>
            <div class="subtitulo">COPA DO MUNDO 2026 · PALPITES + PREVISÕES FINAIS</div>
        </div>
        """
    )


def carregar_resultados_reais(gabarito: pd.DataFrame) -> tuple[pd.DataFrame, str | None]:
    """Combina o gabarito de jogos com os placares reais da API.

    Sem chave/API fora do ar, devolve o gabarito com tudo agendado e um aviso.
    """
    base = gabarito.copy()
    base[["gols_casa", "gols_fora"]] = None
    base["status"] = "SCHEDULED"
    base["minuto"] = None
    base["data_utc"] = None

    chave = dados_copa.obter_api_key()
    if not chave:
        return base, (
            "Sem chave da API football-data.org configurada — os placares reais não "
            "serão carregados. Crie `.streamlit/secrets.toml` com `FOOTBALL_DATA_API_KEY`."
        )

    try:
        api = dados_copa.obter_jogos(chave)
    except requests.RequestException as exc:
        return base, f"Falha ao buscar resultados na API ({exc}). Exibindo só os palpites."

    if api.empty:
        return base, "A API ainda não retornou jogos da fase de grupos."

    # A ordem casa/fora do formulário pode não bater com a oficial da API; por isso
    # casamos por par de seleções (sem ordem) e reorientamos o placar para o gabarito.
    por_par = {}
    for _, j in api.iterrows():
        chave = frozenset({_normalizar(j["casa"]), _normalizar(j["fora"])})
        por_par[chave] = j

    def _real(linha):
        j = por_par.get(frozenset({_normalizar(linha["casa"]), _normalizar(linha["fora"])}))
        if j is None:
            return pd.Series({"gols_casa": None, "gols_fora": None,
                              "status": "SCHEDULED", "minuto": None, "data_utc": None})
        mesma_ordem = _normalizar(linha["casa"]) == _normalizar(j["casa"])
        gc, gf = (j["gols_casa"], j["gols_fora"]) if mesma_ordem else (j["gols_fora"], j["gols_casa"])
        return pd.Series({"gols_casa": gc, "gols_fora": gf, "status": j["status"],
                          "minuto": j["minuto"], "data_utc": j.get("data_utc")})

    base[["gols_casa", "gols_fora", "status", "minuto", "data_utc"]] = base.apply(_real, axis=1)
    return base, None


def carregar_resultado_final() -> dict:
    """Resultado final real (campeão/vice/3º/4º/artilheiro), ou tudo None sem API."""
    vazio = {"campeao": None, "vice": None, "terceiro": None, "quarto": None, "artilheiro": None}
    chave = dados_copa.obter_api_key()
    if not chave:
        return vazio
    try:
        return dados_copa.obter_resultado_final(chave)
    except requests.RequestException:
        return vazio


def render_podio(ranking: pd.DataFrame, premios: dict):
    classes = ["ouro", "prata", "bronze"]
    medalhas = ["🥇", "🥈", "🥉"]
    cards = []
    for i in range(min(3, len(ranking))):
        r = ranking.iloc[i]
        cards.append(
            f"""
            <div class="podio-card {classes[i]}">
                <div class="medalha">{medalhas[i]}</div>
                <div class="nome">{r['participante']}</div>
                <div class="pts">{r['pontos']:g} pts</div>
                <div class="premio">prêmio R$ {premios[i + 1]:g}</div>
            </div>
            """
        )
    _html(f'<div class="podio">{"".join(cards)}</div>')


def render_ranking(ranking: pd.DataFrame, premios: dict):
    render_podio(ranking, premios)

    medalhas = {1: "🥇", 2: "🥈", 3: "🥉"}
    classes = {1: "ouro", 2: "prata", 3: "bronze"}
    linhas = []
    for _, r in ranking.iterrows():
        pos = int(r["posicao"])
        cls = classes.get(pos, "")
        marca = medalhas.get(pos, str(pos))
        premio = (
            f'<div class="rank-premio">R$ {premios[pos]:g}</div>' if pos in premios else ""
        )
        linhas.append(
            f"""
            <tr class="{cls}">
                <td class="rank-pos">{marca}</td>
                <td><span class="rank-nome">{r['participante']}</span>{premio}</td>
                <td class="rank-total">{r['pontos']:g}</td>
                <td class="num">{r['pontos_jogo']:g}</td>
                <td class="num">{r['pontos_final']:g}</td>
                <td class="num">{int(r['pe'])}</td>
                <td class="num">{int(r['ven'])}</td>
                <td class="num">{int(r['emp'])}</td>
            </tr>
            """
        )
    _html(
        '<table class="rank-tabela">'
        '<tr><th class="num">#</th><th>Participante</th><th class="num">Pontos</th>'
        '<th class="num">Jogos</th><th class="num">Finais</th>'
        '<th class="num">🎯 Exato</th><th class="num">✅ Venc.</th><th class="num">🤝 Emp.</th></tr>'
        + "".join(linhas)
        + "</table>"
    )


def render_jogos(jogos: pd.DataFrame):
    col_grupo, col_situacao = st.columns(2)
    grupos = ["Todos"] + sorted(jogos["grupo"].dropna().unique())
    filtro_grupo = col_grupo.selectbox("Grupo", grupos)
    filtro_situacao = col_situacao.selectbox(
        "Situação", ["Todos", "Ao vivo", "Encerrados", "Agendados"]
    )

    filtrado = jogos
    if filtro_grupo != "Todos":
        filtrado = filtrado[filtrado["grupo"] == filtro_grupo]
    if filtro_situacao == "Ao vivo":
        filtrado = filtrado[filtrado["status"].isin(STATUS_AO_VIVO)]
    elif filtro_situacao == "Encerrados":
        filtrado = filtrado[filtrado["status"] == "FINISHED"]
    elif filtro_situacao == "Agendados":
        filtrado = filtrado[~filtrado["status"].isin(STATUS_COM_PLACAR)]

    if filtrado.empty:
        st.info("Nenhum jogo com esse filtro.")
        return

    # Ordena cronologicamente pela data real (UTC→Brasília); jogos sem data vão ao fim.
    filtrado = filtrado.copy()
    filtrado["dt_br"] = (
        pd.to_datetime(filtrado["data_utc"], utc=True, errors="coerce")
        - pd.Timedelta(hours=3)
    )
    filtrado = filtrado.sort_values("dt_br", na_position="last")

    if filtrado["dt_br"].isna().all():
        # Sem datas da API (ex.: sem chave) — mostra por grupo.
        for grupo, do_grupo in filtrado.groupby("grupo"):
            _html(f'<div class="dia-titulo">📍 {grupo}</div>')
            cards = [_card_jogo(j) for _, j in do_grupo.iterrows()]
            _html(f'<div class="jogos-grid">{"".join(cards)}</div>')
        return

    st.caption("Jogos em ordem cronológica · horário de Brasília.")
    dias_pt = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
    for dia, do_dia in filtrado.groupby(filtrado["dt_br"].dt.date, dropna=False):
        if pd.isna(dia):
            titulo = "Data a confirmar"
        else:
            titulo = f"{dias_pt[dia.weekday()]}, {dia.strftime('%d/%m/%Y')}"
        _html(f'<div class="dia-titulo">📅 {titulo}</div>')
        cards = [_card_jogo(j) for _, j in do_dia.iterrows()]
        _html(f'<div class="jogos-grid">{"".join(cards)}</div>')


def _card_jogo(jogo: pd.Series) -> str:
    status = jogo.get("status", "SCHEDULED")
    ao_vivo = status in STATUS_AO_VIVO
    dt = jogo.get("dt_br")
    hora_txt = dt.strftime("%H:%M") if pd.notna(dt) else ""
    if ao_vivo:
        minuto = f" {jogo['minuto']}'" if pd.notna(jogo.get("minuto")) else ""
        badge = f'<span class="badge live">AO VIVO{minuto}</span>'
    elif status == "FINISHED":
        badge = '<span class="badge fim">ENCERRADO</span>'
    else:
        badge = f'<span class="badge agendado">⏰ {hora_txt or "agendado"}</span>'

    if pd.notna(jogo.get("gols_casa")) and pd.notna(jogo.get("gols_fora")):
        placar = f"{int(jogo['gols_casa'])} × {int(jogo['gols_fora'])}"
    else:
        placar = "×"

    info = jogo.get("grupo") or jogo.get("fase") or ""
    if hora_txt:
        info = f"{info} · 🕒 {hora_txt}" if info else f"🕒 {hora_txt}"
    return f"""
    <div class="jogo-card{' aovivo' if ao_vivo else ''}">
        <div class="topo"><span>{info}</span><span>{badge}</span></div>
        <div class="linha">
            <span class="time">{bandeira_html(jogo['casa'])} {jogo['casa']}</span>
            <span class="placar">{placar}</span>
            <span class="time fora">{jogo['fora']} {bandeira_html(jogo['fora'])}</span>
        </div>
    </div>
    """


def render_grupos():
    chave = dados_copa.obter_api_key()
    if not chave:
        st.info("Configure a chave da API para ver a classificação real dos grupos.")
        return
    try:
        classificacao = dados_copa.obter_classificacao(chave)
    except requests.RequestException as exc:
        st.warning(f"Falha ao buscar a classificação ({exc}).")
        return
    if classificacao.empty:
        st.info("A API ainda não retornou a classificação dos grupos.")
        return

    st.caption("As duas primeiras seleções de cada grupo (destacadas) avançam.")
    cards = []
    for grupo in sorted(classificacao["grupo"].unique()):
        tabela = classificacao[classificacao["grupo"] == grupo].sort_values("posicao")
        linhas = []
        for _, t in tabela.iterrows():
            pos = int(t["posicao"]) if pd.notna(t["posicao"]) else 0
            q = " q" if pos and pos <= 2 else ""
            linhas.append(
                f'<div class="grp-row{q}"><span class="gpos">{pos}</span>'
                f'<span class="gtime">{bandeira_html(t["time"])} {t["time"]}</span>'
                f'<span class="gpts">{int(t["pontos"]) if pd.notna(t["pontos"]) else 0}</span>'
                f'<span class="gjsg">J{int(t["jogos"]) if pd.notna(t["jogos"]) else 0} · '
                f'SG {int(t["saldo"]) if pd.notna(t["saldo"]) else 0}</span></div>'
            )
        cards.append(
            f'<div class="grp-card"><div class="gh">{grupo}</div>{"".join(linhas)}</div>'
        )
    _html(f'<div class="grp-wrap">{"".join(cards)}</div>')


_ROTULOS_FINAIS = [
    ("campeao", "Campeão", "campeao", bolao.PONTOS_CAMPEAO),
    ("vice_campeao", "Vice-campeão", "vice", bolao.PONTOS_VICE),
    ("terceiro_lugar", "3º lugar", "terceiro", bolao.PONTOS_TERCEIRO),
    ("quarto_lugar", "4º lugar", "quarto", bolao.PONTOS_QUARTO),
    ("artilheiro", "Artilheiro", "artilheiro", bolao.PONTOS_ARTILHEIRO),
]


def render_previsoes_finais(palpite: pd.Series, resultado: dict):
    detalhe = bolao.pontuar_final(palpite, resultado)
    acertos = {
        "campeao": detalhe["acerto_campeao"], "vice": detalhe["acerto_vice"],
        "terceiro": detalhe["acerto_terceiro"], "quarto": detalhe["acerto_quarto"],
        "artilheiro": detalhe["acerto_artilheiro"],
    }
    cards = []
    for col_csv, rotulo, chave_res, pts in _ROTULOS_FINAIS:
        valor = palpite.get(col_csv) or "—"
        acertou = acertos[chave_res]
        bandeira = bandeira_html(valor) if chave_res != "artilheiro" else ""
        ganho = f'<div class="ganho">+{pts} pts ✓</div>' if acertou else ""
        cards.append(
            f"""
            <div class="final-card{' ok' if acertou else ''}">
                <div class="rotulo">{rotulo}</div>
                <div class="palpite">{bandeira} {valor}</div>
                {ganho}
            </div>
            """
        )
    _html(f'<div class="final-grid">{"".join(cards)}</div>')
    st.caption(f"Pontos das previsões finais: **{detalhe['pontos_final']:g}**")


def render_participante(
    avaliado: pd.DataFrame, ranking: pd.DataFrame, participantes: pd.DataFrame, resultado: dict
):
    nomes = list(participantes["nome"])
    nome = st.selectbox("Participante", nomes)
    posicao = ranking.loc[ranking["participante"] == nome]

    if not posicao.empty:
        r = posicao.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Posição", f"{int(r['posicao'])}º de {len(ranking)}")
        c2.metric("Total", f"{r['pontos']:g}")
        c3.metric("Pontos de jogo", f"{r['pontos_jogo']:g}")
        c4.metric("Placares exatos", int(r["pe"]))

    palpite_final = participantes.loc[participantes["nome"] == nome]
    if not palpite_final.empty:
        st.markdown("#### 🎯 Previsões finais")
        render_previsoes_finais(palpite_final.iloc[0], resultado)

    st.markdown("#### ⚽ Palpites por jogo")
    dados = avaliado[avaliado["participante"] == nome]
    if dados.empty:
        st.info("Palpites de jogo deste participante ainda não foram carregados.")
        return

    tabela = dados.copy()
    if "data_utc" in tabela.columns:
        tabela["dt_br"] = pd.to_datetime(tabela["data_utc"], utc=True, errors="coerce") - pd.Timedelta(hours=3)
    else:
        tabela["dt_br"] = pd.NaT
    tabela = tabela.sort_values(["dt_br", "grupo"], na_position="last")

    tipos = {
        "placar_exato": ("exato", "🎯 Exato"), "vencedor": ("venc", "✅ Vencedor"),
        "empate": ("emp", "🤝 Empate"), "errou": ("errou", "❌ Errou"),
        "pendente": ("pend", "⏳ Aguardando"),
    }
    linhas = []
    for _, j in tabela.iterrows():
        dt = j["dt_br"]
        data_txt = dt.strftime("%d/%m %H:%M") if pd.notna(dt) else "—"
        pal = (
            f"{j['palpite_casa']:.0f} × {j['palpite_fora']:.0f}"
            if pd.notna(j["palpite_casa"]) and pd.notna(j["palpite_fora"]) else "—"
        )
        real = (
            f"{j['gols_casa']:.0f} × {j['gols_fora']:.0f}"
            if pd.notna(j["gols_casa"]) and pd.notna(j["gols_fora"]) else "—"
        )
        cls, rotulo = tipos.get(j["tipo"], ("pend", "—"))
        jogo = (
            f"{bandeira_html(j['casa'])} {j['casa']} "
            f"<span style='color:#8fae9c'>×</span> {j['fora']} {bandeira_html(j['fora'])}"
        )
        linhas.append(
            f'<tr><td class="pg-data">{data_txt}</td>'
            f'<td class="pg-jogo">{jogo}</td>'
            f'<td class="c pg-pal">{pal}</td>'
            f'<td class="c pg-real">{real}</td>'
            f'<td class="c"><span class="pg-badge {cls}">{rotulo}</span></td>'
            f'<td class="pg-pts">{j["pontos"]:g}</td></tr>'
        )
    _html(
        '<table class="pg-tabela">'
        '<tr><th>Data</th><th>Jogo</th><th class="c">Palpite</th><th class="c">Real</th>'
        '<th class="c">Acerto</th><th class="c">Pts</th></tr>'
        + "".join(linhas)
        + "</table>"
    )


def render_regras():
    caminho = Path(__file__).parent / "regras_pontuacao.md"
    if caminho.exists():
        st.markdown(caminho.read_text(encoding="utf-8"))
    else:
        st.info("Arquivo de regras não encontrado.")


# ───────────────────────────── Mata-mata ─────────────────────────────

def _alinhar_gabarito_api(gabarito: pd.DataFrame, api: pd.DataFrame) -> pd.DataFrame:
    """Atribui a cada jogo numerado do gabarito o placar real da API.

    Casa o gabarito com a API por fase: dentro de cada fase, ordena o gabarito por
    número do jogo e a API por data, e pareia posicionalmente. Quando o gabarito já
    traz as seleções (32-avos), tenta casar pelo par de times antes do posicional.
    """
    api = api.copy()
    cols_reais = ["casa", "fora", "gols_casa", "gols_fora", "status", "data_utc", "minuto"]
    linhas = []
    for _, g in gabarito.sort_values("jogo").iterrows():
        fase = g.get("fase")
        candidatos = api[api["fase"] == fase] if "fase" in api.columns else api.iloc[0:0]

        escolhido = None
        casa_g, fora_g = g.get("casa"), g.get("fora")
        if casa_g and fora_g and not candidatos.empty:
            alvo = frozenset({_normalizar(str(casa_g)), _normalizar(str(fora_g))})
            for idx, j in candidatos.iterrows():
                if frozenset({_normalizar(j["casa"]), _normalizar(j["fora"])}) == alvo:
                    escolhido = idx
                    break
        if escolhido is None and not candidatos.empty:
            ordenados = candidatos.sort_values("data_utc", na_position="last")
            disponiveis = [i for i in ordenados.index if i in api.index]
            if disponiveis:
                escolhido = disponiveis[0]

        linha = g.to_dict()
        if escolhido is not None:
            j = api.loc[escolhido]
            for col in cols_reais:
                # Mantém casa/fora do gabarito quando ele já as define.
                if col in ("casa", "fora") and g.get(col):
                    continue
                linha[col] = j.get(col)
            api = api.drop(index=escolhido)  # cada jogo da API é consumido uma vez
        else:
            for col in cols_reais:
                linha.setdefault(col, None)
        linhas.append(linha)
    return pd.DataFrame(linhas)


def carregar_mata_reais(gabarito: pd.DataFrame) -> tuple[pd.DataFrame, str | None]:
    """Jogos do mata-mata com placar real da API (fim da prorrogação).

    Com gabarito preenchido, devolve uma linha por jogo numerado (alinhado à API).
    Sem gabarito, devolve os jogos crus da API (jogo = NaN), só para exibição.
    """
    chave = dados_copa.obter_api_key()
    if not chave:
        return gabarito.copy(), (
            "Sem chave da API football-data.org — os jogos do mata-mata não serão "
            "carregados. Configure `FOOTBALL_DATA_API_KEY`."
        )
    try:
        api = dados_copa.obter_jogos_mata(chave)
    except requests.RequestException as exc:
        return gabarito.copy(), f"Falha ao buscar o mata-mata na API ({exc})."

    if api.empty:
        return gabarito.copy(), "A API ainda não liberou os jogos do mata-mata."
    if gabarito.empty:
        return api, None
    return _alinhar_gabarito_api(gabarito, api), None


def render_ranking_mata(ranking: pd.DataFrame, premios: dict):
    if ranking.empty:
        st.info("Aguardando os palpites da galera para montar o ranking do mata-mata.")
        return
    render_podio(ranking, premios)

    medalhas = {1: "🥇", 2: "🥈", 3: "🥉"}
    classes = {1: "ouro", 2: "prata", 3: "bronze"}
    linhas = []
    for _, r in ranking.iterrows():
        pos = int(r["posicao"])
        cls = classes.get(pos, "")
        marca = medalhas.get(pos, str(pos))
        premio = (
            f'<div class="rank-premio">R$ {premios[pos]:g}</div>' if pos in premios else ""
        )
        linhas.append(
            f"""
            <tr class="{cls}">
                <td class="rank-pos">{marca}</td>
                <td><span class="rank-nome">{r['participante']}</span>{premio}</td>
                <td class="rank-total">{r['pontos']:g}</td>
                <td class="num">{r['pontos_jogo']:g}</td>
                <td class="num">{r['pontos_extra']:g}</td>
                <td class="num">{int(r['exatos'])}</td>
                <td class="num">{int(r['parciais'])}</td>
            </tr>
            """
        )
    _html(
        '<table class="rank-tabela">'
        '<tr><th class="num">#</th><th>Participante</th><th class="num">Pontos</th>'
        '<th class="num">Jogos</th><th class="num">Pódio</th>'
        '<th class="num">🎯 Exato</th><th class="num">➕ Parcial</th></tr>'
        + "".join(linhas)
        + "</table>"
    )


def render_jogos_mata(jogos: pd.DataFrame):
    if jogos.empty or "casa" not in jogos.columns:
        st.info("A API ainda não liberou os confrontos do mata-mata.")
        return

    jogos = jogos.copy()
    jogos["dt_br"] = (
        pd.to_datetime(jogos.get("data_utc"), utc=True, errors="coerce")
        - pd.Timedelta(hours=3)
    )
    if "ordem_fase" not in jogos.columns:
        jogos["ordem_fase"] = 99
    jogos = jogos.sort_values(["ordem_fase", "dt_br"], na_position="last")

    st.caption("Confrontos do mata-mata · placar considera o fim da prorrogação.")
    for fase, do_fase in jogos.groupby("fase", sort=False):
        _html(f'<div class="dia-titulo">🥊 {fase}</div>')
        cards = [_card_jogo(j) for _, j in do_fase.iterrows()]
        _html(f'<div class="jogos-grid">{"".join(cards)}</div>')


_ROTULOS_PODIO_MATA = [
    ("campeao", "Campeã", "campeao", bolao.PONTOS_MATA_CAMPEAO),
    ("vice_campeao", "Vice-campeã", "vice", bolao.PONTOS_MATA_VICE),
    ("terceiro_lugar", "3º lugar", "terceiro", bolao.PONTOS_MATA_TERCEIRO),
    ("quarto_lugar", "4º lugar", "quarto", bolao.PONTOS_MATA_QUARTO),
]


def render_podio_mata(palpite: pd.Series, resultado: dict):
    detalhe = bolao.pontuar_extras(palpite, resultado)
    acertos = {
        "campeao": detalhe["acerto_campeao"], "vice": detalhe["acerto_vice"],
        "terceiro": detalhe["acerto_terceiro"], "quarto": detalhe["acerto_quarto"],
    }
    cards = []
    for col_csv, rotulo, chave_res, pts in _ROTULOS_PODIO_MATA:
        valor = palpite.get(col_csv) or "—"
        acertou = acertos[chave_res]
        ganho = f'<div class="ganho">+{pts} pts ✓</div>' if acertou else ""
        cards.append(
            f"""
            <div class="final-card{' ok' if acertou else ''}">
                <div class="rotulo">{rotulo}</div>
                <div class="palpite">{bandeira_html(valor)} {valor}</div>
                {ganho}
            </div>
            """
        )
    _html(f'<div class="final-grid">{"".join(cards)}</div>')
    st.caption(f"Pontos de pódio: **{detalhe['pontos_extra']:g}**")


def render_participante_mata(
    avaliado: pd.DataFrame, ranking: pd.DataFrame, participantes: pd.DataFrame, resultado: dict
):
    if participantes.empty:
        st.info("Aguardando a lista de participantes do mata-mata.")
        return

    nomes = list(participantes["nome"])
    nome = st.selectbox("Participante", nomes, key="part_mata")
    posicao = ranking.loc[ranking["participante"] == nome] if not ranking.empty else ranking

    if not posicao.empty:
        r = posicao.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Posição", f"{int(r['posicao'])}º de {len(ranking)}")
        c2.metric("Total", f"{r['pontos']:g}")
        c3.metric("Pontos de jogo", f"{r['pontos_jogo']:g}")
        c4.metric("Placares exatos", int(r["exatos"]))

    palpite_podio = participantes.loc[participantes["nome"] == nome]
    if not palpite_podio.empty:
        st.markdown("#### 🏆 Palpites de pódio")
        render_podio_mata(palpite_podio.iloc[0], resultado)

    st.markdown("#### ⚔️ Palpites por jogo")
    dados = avaliado[avaliado["participante"] == nome] if len(avaliado) else avaliado
    if dados.empty:
        st.info("Palpites de jogo deste participante ainda não foram carregados.")
        return

    tabela = dados.copy().sort_values("jogo", na_position="last")
    linhas = []
    for _, j in tabela.iterrows():
        num = f"#{int(j['jogo'])}" if pd.notna(j.get("jogo")) else "—"
        fase = j.get("fase") or ""
        casa, fora = j.get("casa"), j.get("fora")
        if casa and fora and pd.notna(casa) and pd.notna(fora):
            jogo = (
                f"{bandeira_html(casa)} {casa} "
                f"<span style='color:#8fae9c'>×</span> {fora} {bandeira_html(fora)}"
            )
        else:
            jogo = "<span style='color:#8fae9c'>a definir</span>"
        pal = (
            f"{j['palpite_casa']:.0f} × {j['palpite_fora']:.0f}"
            if pd.notna(j["palpite_casa"]) and pd.notna(j["palpite_fora"]) else "—"
        )
        real = (
            f"{j['gols_casa']:.0f} × {j['gols_fora']:.0f}"
            if pd.notna(j.get("gols_casa")) and pd.notna(j.get("gols_fora")) else "—"
        )
        tipo = j.get("tipo", "pendente")
        if tipo == "exato":
            cls, rotulo = "exato", "🎯 3 pts"
        elif tipo == "parcial":
            cls, rotulo = "emp", f"➕ {int(j['pontos'])} pts"
        elif tipo == "errou":
            cls, rotulo = "errou", "❌ 0 pts"
        else:
            cls, rotulo = "pend", "⏳ Aguardando"
        linhas.append(
            f'<tr><td class="pg-data">{num} · {fase}</td>'
            f'<td class="pg-jogo">{jogo}</td>'
            f'<td class="c pg-pal">{pal}</td>'
            f'<td class="c pg-real">{real}</td>'
            f'<td class="c"><span class="pg-badge {cls}">{rotulo}</span></td>'
            f'<td class="pg-pts">{j["pontos"]:g}</td></tr>'
        )
    _html(
        '<table class="pg-tabela">'
        '<tr><th>Jogo</th><th>Confronto</th><th class="c">Palpite</th><th class="c">Real</th>'
        '<th class="c">Acerto</th><th class="c">Pts</th></tr>'
        + "".join(linhas)
        + "</table>"
    )


def render_mata_regras():
    caminho = Path(__file__).parent / "regras_pontuacao_mata.md"
    if caminho.exists():
        with st.expander("📜 Regras do bolão do mata-mata"):
            st.markdown(caminho.read_text(encoding="utf-8"))


def main():
    st.set_page_config(page_title="Bolão Copa 2026", page_icon="🏆", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    render_banner()

    if st_autorefresh is not None:
        st_autorefresh(interval=dados_copa.TTL_SEGUNDOS * 1000, key="atualizacao")
    else:
        # Fallback sem dependência: recarrega a página sozinho a cada TTL segundos.
        st.components.v1.html(
            f"<script>setTimeout(() => window.parent.location.reload(), "
            f"{dados_copa.TTL_SEGUNDOS * 1000});</script>",
            height=0,
        )

    participantes = bolao.carregar_participantes()
    premio_total = VALOR_POR_PARTICIPANTE * len(participantes)
    premios = {pos: round(premio_total * perc) for pos, perc in PERC_PREMIOS.items()}

    with st.sidebar:
        st.header("⚙️ Painel")
        if st.button("🔄 Atualizar agora", width="stretch"):
            st.cache_data.clear()
            st.rerun()
        st.caption(
            f"Os placares se atualizam sozinhos a cada {dados_copa.TTL_SEGUNDOS // 60} "
            "minutos (limite da API gratuita)."
        )
        st.divider()
        st.caption(
            "**Fase de grupos** — placar exato 10 · vencedor 5 · empate 7 · "
            "campeão 30 · vice 20 · artilheiro 20 · 3º 10 · 4º 10.\n\n"
            "**Desempate:** placares exatos → campeão → artilheiro → grupo do Brasil.\n\n"
            f"**Premiação (R$ {premio_total}):** 1º R$ {premios[1]} · "
            f"2º R$ {premios[2]} · 3º R$ {premios[3]}."
        )
        st.divider()
        st.caption(
            "**🥊 Mata-mata** — por jogo (máx. 3): vencedor/empate +1 · gols do time A "
            "+1 · gols do time B +1 (vale o fim da prorrogação, sem pênaltis).\n\n"
            "**Pódio:** campeã 10 · vice 6 · 3º 4 · 4º 2.\n\n"
            f"**Premiação:** R$ {VALOR_POR_PARTICIPANTE_MATA}/pessoa, dividida 70/20/10."
        )

    gabarito = bolao.carregar_jogos_gabarito()
    palpites = bolao.carregar_palpites()
    jogos, aviso = carregar_resultados_reais(gabarito)
    if aviso:
        st.warning(aviso)

    resultado_final = carregar_resultado_final()
    avaliado = bolao.avaliar_palpites(palpites, jogos) if len(palpites) else palpites.assign(
        gols_casa=None, gols_fora=None, status=None, pontos=0.0, tipo="pendente"
    )
    grupo_brasil = bolao.grupo_do_brasil(gabarito)
    ranking = bolao.montar_ranking(avaliado, participantes, resultado_final, grupo_brasil)

    ao_vivo = int(jogos["status"].isin(STATUS_AO_VIVO).sum())
    encerrados = int((jogos["status"] == "FINISHED").sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Participantes", len(participantes))
    c2.metric("Jogos encerrados", f"{encerrados} / {len(jogos)}")
    c3.metric("Jogos ao vivo", ao_vivo)
    c4.metric("Prêmio total", f"R$ {premio_total}")
    if ao_vivo:
        st.caption("⚠️ Há jogos em andamento — a pontuação inclui placares parciais.")

    # Dados do bolão do mata-mata (estrutura pronta; preenche quando a planilha chegar).
    try:
        participantes_mata = bolao.carregar_participantes_mata()
        palpites_mata = bolao.carregar_palpites_mata()
        gabarito_mata = bolao.carregar_jogos_mata()
        jogos_mata, aviso_mata = carregar_mata_reais(gabarito_mata)
        avaliado_mata = (
            bolao.avaliar_palpites_mata(palpites_mata, jogos_mata)
            if len(palpites_mata) else palpites_mata
        )
        premio_total_mata = VALOR_POR_PARTICIPANTE_MATA * len(participantes_mata)
        premios_mata = {
            pos: round(premio_total_mata * perc) for pos, perc in PERC_PREMIOS.items()
        }
        ranking_mata = bolao.montar_ranking_mata(
            avaliado_mata, participantes_mata, resultado_final
        )
    except Exception as exc:  # mata-mata não pode derrubar as abas de grupos
        participantes_mata = palpites_mata = gabarito_mata = None
        jogos_mata = pd.DataFrame()
        avaliado_mata = pd.DataFrame()
        ranking_mata = pd.DataFrame()
        aviso_mata = f"Não foi possível carregar os dados do mata-mata ({exc})."

    aba_ranking, aba_jogos, aba_grupos, aba_part, aba_mata, aba_regras = st.tabs(
        ["🏆 Ranking", "⚽ Jogos", "📊 Grupos", "👤 Participante", "🥊 Mata-mata", "📜 Regras"]
    )
    with aba_ranking:
        render_ranking(ranking, premios)
    with aba_jogos:
        render_jogos(jogos)
    with aba_grupos:
        render_grupos()
    with aba_part:
        render_participante(avaliado, ranking, participantes, resultado_final)
    with aba_mata:
        st.markdown("### 🥊 Bolão do Mata-mata")
        if aviso_mata:
            st.warning(aviso_mata)
        if participantes_mata is not None:
            sub_rank, sub_jogos, sub_part = st.tabs(
                ["🏆 Ranking", "⚔️ Jogos", "👤 Participante"]
            )
            with sub_rank:
                render_ranking_mata(ranking_mata, premios_mata)
            with sub_jogos:
                render_jogos_mata(jogos_mata)
            with sub_part:
                render_participante_mata(
                    avaliado_mata, ranking_mata, participantes_mata, resultado_final
                )
        render_mata_regras()
    with aba_regras:
        render_regras()


if __name__ == "__main__":
    main()

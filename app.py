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
                              "status": "SCHEDULED", "minuto": None})
        mesma_ordem = _normalizar(linha["casa"]) == _normalizar(j["casa"])
        gc, gf = (j["gols_casa"], j["gols_fora"]) if mesma_ordem else (j["gols_fora"], j["gols_casa"])
        return pd.Series({"gols_casa": gc, "gols_fora": gf,
                          "status": j["status"], "minuto": j["minuto"]})

    base[["gols_casa", "gols_fora", "status", "minuto"]] = base.apply(_real, axis=1)
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

    for grupo, do_grupo in filtrado.groupby("grupo"):
        _html(f'<div class="dia-titulo">📍 {grupo}</div>')
        cards = [_card_jogo(jogo) for _, jogo in do_grupo.iterrows()]
        _html(f'<div class="jogos-grid">{"".join(cards)}</div>')


def _card_jogo(jogo: pd.Series) -> str:
    status = jogo.get("status", "SCHEDULED")
    ao_vivo = status in STATUS_AO_VIVO
    if ao_vivo:
        minuto = f" {jogo['minuto']}'" if pd.notna(jogo.get("minuto")) else ""
        badge = f'<span class="badge live">AO VIVO{minuto}</span>'
    elif status == "FINISHED":
        badge = '<span class="badge fim">ENCERRADO</span>'
    else:
        badge = '<span class="badge agendado">⏰ agendado</span>'

    if pd.notna(jogo.get("gols_casa")) and pd.notna(jogo.get("gols_fora")):
        placar = f"{int(jogo['gols_casa'])} × {int(jogo['gols_fora'])}"
    else:
        placar = "×"

    return f"""
    <div class="jogo-card{' aovivo' if ao_vivo else ''}">
        <div class="topo"><span>{jogo['grupo'] or ''}</span><span>{badge}</span></div>
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
    tabela["jogo"] = tabela.apply(lambda j: f"{j['casa']} × {j['fora']}", axis=1)
    tabela["palpite"] = tabela.apply(
        lambda j: f"{j['palpite_casa']:.0f} × {j['palpite_fora']:.0f}"
        if pd.notna(j["palpite_casa"]) and pd.notna(j["palpite_fora"]) else "—",
        axis=1,
    )
    tabela["resultado"] = tabela.apply(
        lambda j: f"{j['gols_casa']:.0f} × {j['gols_fora']:.0f}"
        if pd.notna(j["gols_casa"]) and pd.notna(j["gols_fora"]) else "—",
        axis=1,
    )
    rotulos = {
        "placar_exato": "🎯 Placar exato", "vencedor": "✅ Vencedor",
        "empate": "🤝 Empate", "errou": "❌ Errou", "pendente": "⏳ Aguardando",
    }
    tabela["acerto"] = tabela["tipo"].map(rotulos)
    tabela["pontos"] = tabela["pontos"].map(lambda v: f"{v:g}")

    st.dataframe(
        tabela[["grupo", "jogo", "palpite", "resultado", "acerto", "pontos"]],
        width="stretch",
        hide_index=True,
        height=42 * len(tabela) + 40,
        column_config={
            "grupo": "Grupo", "jogo": "Jogo", "palpite": "Palpite",
            "resultado": "Resultado", "acerto": "Acerto", "pontos": "Pontos",
        },
    )


def render_regras():
    caminho = Path(__file__).parent / "regras_pontuacao.md"
    if caminho.exists():
        st.markdown(caminho.read_text(encoding="utf-8"))
    else:
        st.info("Arquivo de regras não encontrado.")


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
            "**Pontuação:** placar exato 10 · vencedor 5 · empate 7 · "
            "campeão 30 · vice 20 · artilheiro 20 · 3º 10 · 4º 10.\n\n"
            "**Desempate:** placares exatos → campeão → artilheiro → grupo do Brasil.\n\n"
            f"**Premiação (R$ {premio_total}):** 1º R$ {premios[1]} · "
            f"2º R$ {premios[2]} · 3º R$ {premios[3]}."
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

    aba_ranking, aba_jogos, aba_grupos, aba_part, aba_regras = st.tabs(
        ["🏆 Ranking", "⚽ Jogos", "📊 Grupos", "👤 Participante", "📜 Regras"]
    )
    with aba_ranking:
        render_ranking(ranking, premios)
    with aba_jogos:
        render_jogos(jogos)
    with aba_grupos:
        render_grupos()
    with aba_part:
        render_participante(avaliado, ranking, participantes, resultado_final)
    with aba_regras:
        render_regras()


if __name__ == "__main__":
    main()

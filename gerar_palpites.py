"""Gera palpites.csv a partir dos placares extraídos das fotos dos formulários.

Cada formulário tem os mesmos 72 jogos, na mesma ordem de jogos.csv. Aqui guardamos,
por ficha, a lista dos 72 placares (palpite_casa, palpite_fora) lidos da foto — assim
não é preciso redigitar os nomes das seleções (vêm de jogos.csv). Use None para um
dígito ilegível (palpite fica pendente).

Rodar:  python gerar_palpites.py
"""

import csv
from pathlib import Path

PASTA = Path(__file__).parent

# ficha (como em participantes.csv) -> 72 placares na ordem de jogos.csv
PALPITES_POR_FICHA: dict[str, list[tuple[int | None, int | None]]] = {
    # Ficha 01 — "Assinatura ilegivel (Ficha 01)"  (foto: ...17.46.58 (1).jpeg)
    "01": [
        # Grupo A
        (2, 0), (0, 1), (2, 0), (2, 1), (0, 1), (1, 1),
        # Grupo B
        (1, 1), (0, 2), (2, 1), (2, 1), (2, 0), (1, 1),
        # Grupo C
        (2, 1), (0, 2), (1, 2), (4, 0), (3, 0), (2, 2),
        # Grupo D
        (0, 1), (2, 0), (0, 1), (0, 2), (1, 0), (0, 0),
        # Grupo E
        (4, 0), (2, 1), (2, 2), (3, 0), (0, 3), (0, 3),
        # Grupo F
        (1, 0), (1, 0), (2, 0), (0, 2), (1, 1), (0, 0),
        # Grupo G
        (1, 2), (2, 0), (4, 0), (0, 1), (2, 1), (0, 3),
        # Grupo H
        (3, 0), (1, 0), (2, 0), (2, 0), (1, 0), (1, 2),
        # Grupo I
        (0, 1), (0, 2), (2, 0), (1, 2), (2, 0), (1, 2),
        # Grupo J
        (2, 1), (2, 1), (4, 1), (0, 1), (1, 1), (0, 2),
        # Grupo L
        (2, 0), (0, 1), (3, 1), (1, 0), (1, 2), (1, 2),
        # Grupo M
        (1, 1), (1, 0), (3, 0), (0, 2), (2, 1), (0, 2),
    ],
}


def main() -> None:
    participantes = {}
    with open(PASTA / "participantes.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            participantes[row["ficha"]] = row["nome"]

    jogos = []
    with open(PASTA / "jogos.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            jogos.append(row)

    linhas = []
    for ficha, placares in PALPITES_POR_FICHA.items():
        nome = participantes.get(ficha, f"Ficha {ficha}")
        if len(placares) != len(jogos):
            raise SystemExit(
                f"Ficha {ficha}: {len(placares)} placares, mas jogos.csv tem {len(jogos)}."
            )
        for jogo, (pc, pf) in zip(jogos, placares):
            linhas.append(
                {
                    "ficha": ficha,
                    "participante": nome,
                    "grupo": jogo["grupo"],
                    "casa": jogo["casa"],
                    "fora": jogo["fora"],
                    "palpite_casa": "" if pc is None else pc,
                    "palpite_fora": "" if pf is None else pf,
                }
            )

    with open(PASTA / "palpites.csv", "w", newline="", encoding="utf-8") as f:
        campos = ["ficha", "participante", "grupo", "casa", "fora", "palpite_casa", "palpite_fora"]
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(linhas)

    print(f"palpites.csv gerado: {len(linhas)} linhas, {len(PALPITES_POR_FICHA)} ficha(s).")


if __name__ == "__main__":
    main()

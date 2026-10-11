"""Checagens do teste ponta a ponta (chamado por run_e2e.sh)."""
import sys
from pathlib import Path

import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[2]

cfg = yaml.safe_load((RAIZ / "tests/e2e/e2e.yaml").read_text())
saida = RAIZ / cfg["saida"]
rel = saida / "report"
n_taxas, n_reps = len(cfg["carga"]["taxas"]), cfg["carga"]["repeticoes"]
maior_taxa = max(cfg["carga"]["taxas"])
falhas = []


def checar(condicao, mensagem):
    if not condicao:
        falhas.append(mensagem)


resumo = pd.read_csv(rel / "resumo.csv")
checar(len(resumo) == 2 * n_taxas, f"resumo.csv: esperado {2 * n_taxas} linhas, há {len(resumo)}")
for png in ["vazao", "latencia_p95", "cpu", "memoria", "erros"]:
    checar((rel / f"{png}.png").exists(), f"falta {png}.png")
for sufixo in ["plot.html", "vmstat.txt"]:
    n = len(list(saida.glob(f"*/r*_rep*.{sufixo}")))
    checar(n == 2 * n_taxas * n_reps, f"esperado {2 * n_taxas * n_reps} arquivos .{sufixo}, há {n}")
checar(resumo["cpu_pct_media"].notna().all(), "CPU ausente no resumo")
checar((resumo["mem_usada_mb_media"] > 0).all(), "memória usada deveria ser > 0")
checar(len((rel / "tabela.md").read_text().strip().splitlines()) == 2 + 2 * n_taxas, "tabela.md com linhas faltando")

topo = resumo[resumo["taxa"] == maior_taxa].set_index("cenario")["vazao_media"]
checar(topo["c2-2nucleos"] > topo["c1-1nucleo"],
       f"a {maior_taxa} req/s, 2 núcleos deveria atender mais que 1 núcleo: {topo.round(0).to_dict()}")
for cenario, vazao in topo.items():
    checar(vazao < 0.9 * maior_taxa, f"{cenario}: vazão {vazao:.0f} a {maior_taxa} req/s deveria saturar (< 90%)")

if falhas:
    print("E2E FALHOU:\n  " + "\n  ".join(falhas))
    sys.exit(1)
print(f"E2E OK — vazão a {maior_taxa} req/s: {topo.round(0).to_dict()}")

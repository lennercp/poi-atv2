"""Gráficos comparativos: 1 vCPU / 1 GB vs 1 vCPU / 2 GB."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1] / "results"
SAIDA = RAIZ / "report" / "cenarios-1-2"
SAIDA.mkdir(parents=True, exist_ok=True)

CENARIOS = {
    "1cpu-1ram": ("1 vCPU / 1 GB", "#2a78d6"),
    "1cpu-2ram": ("1 vCPU / 2 GB", "#eb6834"),
}
INK, INK2, GRID, SURF = "#1f1f1e", "#5f5e58", "#e6e5e0", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2,
    "ytick.color": INK2, "text.color": INK, "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.titleweight": "bold", "axes.titlesize": 13, "axes.titlelocation": "left",
})

resumo = pd.read_csv(RAIZ / "report" / "resumo.csv")
resumo = resumo[resumo.cenario.isin(CENARIOS)].copy()


def swap_max_mb(cenario, taxa):
    linhas = (RAIZ / cenario / f"r{taxa}_rep1.vmstat.txt").read_text().splitlines()
    swpd = [int(l.split()[2]) for l in linhas if l.split() and l.split()[0].isdigit()]
    return max(swpd) / 1024


resumo["swap_mb"] = [swap_max_mb(c, t) for c, t in zip(resumo.cenario, resumo.taxa)]
resumo["cpu_util"] = resumo.us_media + resumo.sy_media
resumo["sucesso_pct"] = resumo.sucesso_media * 100
resumo["swap_io_mbs"] = (resumo.swap_in_kib_media + resumo.swap_out_kib_media) / 1024
mem_total = {"1cpu-1ram": 971, "1cpu-2ram": 1978}
resumo["mem_pct"] = [m / mem_total[c] * 100 for c, m in zip(resumo.cenario, resumo.mem_usada_mb_media)]

TAXAS = sorted(resumo.taxa.unique())
X = range(len(TAXAS))


def grafico(arquivo, titulo, coluna, ylabel, log=False, ideal=False, ylim=None, rotulos=None, casas=1):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if ideal:
        ax.plot(X, TAXAS, color=INK2, lw=1.2, ls="--", label="Ideal (vazão = taxa)")
    for cen, (nome, cor) in CENARIOS.items():
        d = resumo[resumo.cenario == cen].sort_values("taxa")
        ax.plot(X, d[coluna], color=cor, lw=2, marker="o", ms=7,
                markeredgecolor=SURF, markeredgewidth=2, label=nome)
        for i in (rotulos or []):
            v = d[coluna].iloc[i]
            ax.annotate(f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", "."),
                        (i, v), textcoords="offset points", xytext=(6, 6), fontsize=9, color=INK2)
    ax.set_xticks(list(X), [str(t) for t in TAXAS])
    ax.set_xlabel("Taxa alvo (req/s)")
    ax.set_ylabel(ylabel)
    ax.set_title(titulo)
    if log:
        ax.set_yscale("log")
        ax.axhline(10000, color=INK2, lw=1, ls=":")
        ax.text(len(TAXAS) - 1, 10000 * 1.12, "timeout (10 s)", ha="right", fontsize=9, color=INK2)
    if ylim:
        ax.set_ylim(*ylim)
    ax.legend(frameon=False, loc="center right" if log else "best")
    fig.tight_layout()
    fig.savefig(SAIDA / arquivo, dpi=150)
    plt.close(fig)


grafico("vazao.png", "Vazão efetiva", "vazao_media", "Requisições com sucesso / s",
        ideal=True, ylim=(0, 25), rotulos=[2])
grafico("sucesso.png", "Taxa de sucesso", "sucesso_pct", "Sucesso (%)", ylim=(-3, 105), rotulos=[2, 3])
grafico("latencia_p50.png", "Latência mediana (p50)", "lat_p50_ms_media",
        "p50 (ms, escala log)", log=True, rotulos=[2], casas=0)
grafico("latencia_p95.png", "Latência p95", "lat_p95_ms_media",
        "p95 (ms, escala log)", log=True)
grafico("cpu.png", "CPU processando (us + sy)", "cpu_util", "CPU (%)", ylim=(0, 105))
grafico("iowait.png", "CPU esperando disco (iowait)", "wa_media", "iowait (%)", ylim=(0, 50))
grafico("memoria.png", "Memória usada da VM", "mem_pct", "% da RAM total", ylim=(0, 100))
grafico("swap.png", "Swap usado (pico)", "swap_mb", "Swap (MB)")

print(resumo[["cenario", "taxa", "vazao_media", "sucesso_pct", "lat_p50_ms_media", "cpu_pct_media",
              "wa_media", "mem_pct", "swap_mb", "swap_io_mbs"]].round(1).to_string())

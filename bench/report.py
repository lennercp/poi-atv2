"""Consolida os resultados de todos os cenários em resumo.csv, tabela.md e gráficos."""
import json
import re
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FixedLocator, LogFormatter, NullLocator, ScalarFormatter  # noqa: E402

import vm  # noqa: E402

ARQ_EXECUCAO = re.compile(r"r(\d+)_rep(\d+)\.json")
NS_PARA_MS = 1e-6
METRICAS_VM = ["cpu_pct", "us", "sy", "wa", "st", "mem_usada_mb", "bi", "bo"]

# Paleta categórica validada, em ordem fixa: a cor (e o marcador) acompanha o cenário em todos os gráficos.
CORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
MARCADORES = ["o", "s", "^", "D", "v", "P", "X", "*"]
TINTA, TINTA_SEC, EIXO, GRADE, REFERENCIA = "#0b0b0b", "#52514e", "#c3c2b7", "#e1e0d9", "#898781"

plt.rcParams.update({
    "figure.figsize": (7, 4.2), "font.size": 10,
    "axes.edgecolor": EIXO, "axes.labelcolor": TINTA_SEC, "axes.titlecolor": TINTA, "axes.titlesize": 12,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRADE, "grid.linewidth": 0.6,
    "xtick.color": TINTA_SEC, "ytick.color": TINTA_SEC, "legend.frameon": False,
})


def carregar_execucoes(saida):
    """Uma linha por execução (cenário, taxa, repetição) e o meta.json de cada cenário."""
    linhas, metas = [], {}
    for pasta in sorted(p for p in Path(saida).iterdir() if p.is_dir() and p.name != "report"):
        meta = json.loads((pasta / "meta.json").read_text())
        metas[pasta.name] = meta
        for arq in sorted(pasta.glob("r*_rep*.json")):
            m = ARQ_EXECUCAO.fullmatch(arq.name)
            if not m:
                continue
            v = json.loads(arq.read_text())
            lat = v["latencies"]
            linha = {
                "cenario": pasta.name, "taxa": int(m.group(1)), "rep": int(m.group(2)),
                "taxa_real": v["rate"],
                "requisicoes": v["requests"],
                "vazao": v["throughput"],
                "lat_media_ms": lat["mean"] * NS_PARA_MS,
                "lat_p50_ms": lat["50th"] * NS_PARA_MS,
                "lat_p90_ms": lat["90th"] * NS_PARA_MS,
                "lat_p95_ms": lat["95th"] * NS_PARA_MS,
                "lat_p99_ms": lat["99th"] * NS_PARA_MS,
                "lat_max_ms": lat["max"] * NS_PARA_MS,
                "sucesso": v["success"],
                "erros_pct": (1 - v["success"]) * 100,
            }
            # contagem por código HTTP (0 = sem resposta: timeout, conexão recusada...)
            linha.update({f"http_{codigo}": n for codigo, n in v["status_codes"].items()})
            vmstat = pasta / f"{arq.stem}.vmstat.txt"
            if vmstat.exists():
                amostras = pd.DataFrame(vm.parse(vmstat.read_text(), meta["mem_total_mb"]))
                linha.update(amostras[METRICAS_VM].mean().to_dict())
                linha["swap_in_kib"] = amostras["si"].sum()
                linha["swap_out_kib"] = amostras["so"].sum()
            jvm = pasta / f"{arq.stem}.jvm.csv"
            if jvm.exists():
                amostras = pd.read_csv(jvm)
                linha["heap_mb"] = amostras["heap_mb"].mean()  # amostras vazias (leitura falhou) ficam de fora
                linha["nonheap_mb"] = amostras["nonheap_mb"].mean()
            linhas.append(linha)
    execucoes = pd.DataFrame(linhas)
    codigos = [c for c in execucoes.columns if c.startswith("http_")]
    execucoes[codigos] = execucoes[codigos].fillna(0)  # código ausente numa execução = 0 ocorrências
    return execucoes, metas


def agregar(execucoes):
    """Média e desvio padrão das repetições de cada ponto (cenário, taxa)."""
    grupos = execucoes.drop(columns="rep").groupby(["cenario", "taxa"])
    resumo = grupos.agg(["mean", "std"])
    resumo.columns = [f"{m}_{'media' if e == 'mean' else 'dp'}" for m, e in resumo.columns]
    dp = [c for c in resumo.columns if c.endswith("_dp")]
    resumo[dp] = resumo[dp].fillna(0)  # uma repetição só: sem desvio
    resumo["repeticoes"] = grupos.size()
    return resumo.reset_index()


def _fmt(linha, coluna, escala=1, casas=1):
    media = linha.get(f"{coluna}_media")
    if media is None or pd.isna(media):
        return "—"
    return f"{media * escala:.{casas}f} ± {linha[f'{coluna}_dp'] * escala:.{casas}f}"


def escrever_tabela(resumo, arquivo):
    linhas = [
        "| Cenário | Taxa (req/s) | Vazão (req/s) | p50 (ms) | p90 (ms) | p95 (ms) | p99 (ms) | Sucesso (%) "
        "| CPU (%) | I/O wait (%) | Escrita no disco (KiB/s) | Memória (MB) | Heap (MB) | Fora do heap (MB) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, l in resumo.iterrows():
        linhas.append(f"| {l['cenario']} | {l['taxa']} | {_fmt(l, 'vazao')} | {_fmt(l, 'lat_p50_ms')} | "
                      f"{_fmt(l, 'lat_p90_ms')} | {_fmt(l, 'lat_p95_ms')} | {_fmt(l, 'lat_p99_ms')} | "
                      f"{_fmt(l, 'sucesso', 100)} | {_fmt(l, 'cpu_pct', casas=0)} | {_fmt(l, 'wa', casas=0)} | "
                      f"{_fmt(l, 'bo', casas=0)} | {_fmt(l, 'mem_usada_mb', casas=0)} | "
                      f"{_fmt(l, 'heap_mb', casas=0)} | {_fmt(l, 'nonheap_mb', casas=0)} |")
    Path(arquivo).write_text("\n".join(linhas) + "\n")


def _figura(titulo, rotulo_y, taxas):
    """Eixo X em escala log com marcas exatamente nas taxas testadas."""
    fig, ax = plt.subplots()
    ax.set_title(titulo, loc="left")
    ax.set_xlabel("Demanda (req/s enviadas)")
    ax.set_ylabel(rotulo_y)
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(FixedLocator(taxas))
    ax.xaxis.set_major_formatter(ScalarFormatter())
    ax.xaxis.set_minor_locator(NullLocator())
    return fig, ax


def _series(ax, resumo, coluna, cores):
    for cenario, df in resumo.groupby("cenario"):
        if f"{coluna}_media" not in df or df[f"{coluna}_media"].isna().all():
            continue
        df = df.sort_values("taxa")
        i = cores[cenario]
        ax.errorbar(df["taxa"], df[f"{coluna}_media"], yerr=df[f"{coluna}_dp"], label=cenario,
                    color=CORES[i], marker=MARCADORES[i], markersize=6, linewidth=2, capsize=3)


def _salvar(fig, ax, arquivo):
    ax.legend()
    fig.savefig(arquivo, dpi=150, bbox_inches="tight")
    plt.close(fig)


def desenhar_graficos(resumo, metas, destino):
    cenarios = sorted(resumo["cenario"].unique())
    if len(cenarios) > len(CORES):
        raise SystemExit(f"no máximo {len(CORES)} cenários por relatório")
    cores = {c: i for i, c in enumerate(cenarios)}
    taxas = sorted(resumo["taxa"].unique())

    fig, ax = _figura("Vazão real × demanda", "Vazão (req/s atendidas)", taxas)
    # symlog: log como o eixo X, mas mostra vazão 0 (cenário que colapsou por completo)
    ax.set_yscale("symlog", linthresh=min(taxas), linscale=0.2)  # 0..menor taxa linear e estreito; resto log
    ax.yaxis.set_major_locator(FixedLocator([0] + taxas))  # mesma escala da demanda: compara direto com o eixo X
    ax.yaxis.set_major_formatter(ScalarFormatter())
    ax.yaxis.set_minor_locator(NullLocator())
    ax.plot(taxas, taxas, linestyle="--", linewidth=1, color=REFERENCIA, label="ideal (vazão = demanda)")
    _series(ax, resumo, "vazao", cores)
    ax.set_ylim(bottom=0)  # depois das séries: antes, congelaria o autoescala do topo
    _salvar(fig, ax, destino / "vazao.png")

    fig, ax = _figura("Latência p95 × demanda", "Latência p95 (ms, escala log)", taxas)
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(ScalarFormatter())
    # menos de ~2 décadas visíveis: rotula as marcas menores em número comum, não em 2×10²
    ax.yaxis.set_minor_formatter(LogFormatter(labelOnlyBase=False))
    _series(ax, resumo, "lat_p95_ms", cores)
    _salvar(fig, ax, destino / "latencia_p95.png")

    if "cpu_pct_media" in resumo and resumo["cpu_pct_media"].notna().any():
        fig, ax = _figura("CPU da VM × demanda", "CPU da VM (%)", taxas)
        ax.set_ylim(0, 105)
        _series(ax, resumo, "cpu_pct", cores)
        _salvar(fig, ax, destino / "cpu.png")

        fig, ax = _figura("Memória usada na VM × demanda", "Memória usada (MB)", taxas)
        _series(ax, resumo, "mem_usada_mb", cores)
        for cenario in cenarios:
            if "mem_total_mb" in metas[cenario]:
                ax.axhline(metas[cenario]["mem_total_mb"], linestyle="--", linewidth=1, color=CORES[cores[cenario]])
        ax.plot([], [], linestyle="--", linewidth=1, color=REFERENCIA, label="RAM provisionada (cor do cenário)")
        ax.set_ylim(bottom=0)
        _salvar(fig, ax, destino / "memoria.png")

        fig, ax = _figura("Espera por I/O × demanda", "CPU parada esperando I/O (%)", taxas)
        _series(ax, resumo, "wa", cores)
        ax.set_ylim(bottom=0)
        _salvar(fig, ax, destino / "io_wait.png")

        fig, ax = _figura("Escrita no disco × demanda", "Escrita no disco (KiB/s)", taxas)
        _series(ax, resumo, "bo", cores)
        ax.set_ylim(bottom=0)
        _salvar(fig, ax, destino / "disco_escrita.png")

    fig, ax = _figura("Taxa de erro × demanda", "Erros (% das requisições)", taxas)
    _series(ax, resumo, "erros_pct", cores)
    ax.set_ylim(bottom=0)
    _salvar(fig, ax, destino / "erros.png")

    if "heap_mb_media" in resumo and resumo["heap_mb_media"].notna().any():
        desenhar_memoria_detalhada(resumo, cenarios, destino / "memoria_detalhada.png")


def desenhar_memoria_detalhada(resumo, cenarios, arquivo):
    """Um painel por cenário: barras empilhadas heap + fora do heap (JVM) e a memória usada da VM (vmstat)."""
    colunas = min(3, len(cenarios))
    linhas = -(-len(cenarios) // colunas)
    fig, eixos = plt.subplots(linhas, colunas, figsize=(4.2 * colunas, 3.4 * linhas), sharey=True, squeeze=False)
    for ax, cenario in zip(eixos.flat, cenarios):
        df = resumo[resumo["cenario"] == cenario].sort_values("taxa")
        x = range(len(df))
        fora = df["nonheap_mb_media"].fillna(0)
        ax.bar(x, fora, width=0.6, color=EIXO, label="fora do heap (JVM)")
        ax.bar(x, df["heap_mb_media"].fillna(0), width=0.6, bottom=fora, color=CORES[0], label="heap (JVM)")
        if "mem_usada_mb_media" in df:
            ax.plot(x, df["mem_usada_mb_media"], color=TINTA, marker="o", markersize=4, linewidth=1.5,
                    label="memória usada da VM")
        ax.set_title(cenario, loc="left")
        ax.set_xticks(list(x), [str(t) for t in df["taxa"]])
        ax.set_axisbelow(True)
        ax.grid(axis="x", visible=False)
    for ax in eixos.flat[len(cenarios):]:
        ax.set_visible(False)
    for ax in eixos[:, 0]:
        ax.set_ylabel("Memória (MB)")
    for ax in eixos[-1, :]:
        ax.set_xlabel("Demanda (req/s enviadas)")
    fig.suptitle("Memória da JVM (heap e fora do heap) × memória usada da VM", x=0.01, ha="left")
    handles, rotulos = eixos.flat[0].get_legend_handles_labels()
    fig.legend(handles, rotulos, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout()
    fig.savefig(arquivo, dpi=150, bbox_inches="tight")
    plt.close(fig)


def gerar(cfg):
    saida = Path(cfg["saida"])
    execucoes, metas = carregar_execucoes(saida)
    if execucoes.empty:
        raise SystemExit(f"nenhuma execução encontrada em {saida}/")
    destino = saida / "report"
    destino.mkdir(exist_ok=True)
    resumo = agregar(execucoes)
    resumo.to_csv(destino / "resumo.csv", index=False)
    escrever_tabela(resumo, destino / "tabela.md")
    desenhar_graficos(resumo, metas, destino)
    print(f"relatório gerado em {destino}/")

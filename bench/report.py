"""Consolida os resultados de todos os cenários em resumo.csv, tabela.md, conclusoes.txt e gráficos."""
import json
import re
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FixedLocator, NullLocator, ScalarFormatter  # noqa: E402

import vm  # noqa: E402

ARQ_EXECUCAO = re.compile(r"r(\d+)_rep(\d+)\.json")
NS_PARA_MS = 1e-6
METRICAS_VM = ["cpu_pct", "us", "sy", "wa", "st", "mem_usada_mb"]

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


def capacidade(resumo, qualidade):
    """Por cenário: `capacidade` = última taxa dentro do critério antes da primeira violação
    (None se a primeira já viola); `degradacao` = primeira taxa que viola (None se nenhuma)."""
    resultado = {}
    for cenario, df in resumo.groupby("cenario"):
        df = df.sort_values("taxa").reset_index(drop=True)
        ok = (df["lat_p95_ms_media"] <= qualidade["p95_max_ms"]) & (df["sucesso_media"] >= qualidade["sucesso_min"])
        n = len(df) if ok.all() else int((~ok).idxmax())
        resultado[cenario] = {
            "capacidade": df.iloc[n - 1] if n > 0 else None,
            "degradacao": df.iloc[n] if n < len(df) else None,
        }
    return resultado


def _fmt(linha, coluna, escala=1, casas=1):
    media = linha.get(f"{coluna}_media")
    if media is None or pd.isna(media):
        return "—"
    return f"{media * escala:.{casas}f} ± {linha[f'{coluna}_dp'] * escala:.{casas}f}"


def escrever_tabela(resumo, arquivo):
    linhas = [
        "| Cenário | Taxa (req/s) | Vazão (req/s) | p95 (ms) | Sucesso (%) | CPU (%) | Memória (MB) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, l in resumo.iterrows():
        linhas.append(f"| {l['cenario']} | {l['taxa']} | {_fmt(l, 'vazao')} | {_fmt(l, 'lat_p95_ms')} | "
                      f"{_fmt(l, 'sucesso', 100)} | {_fmt(l, 'cpu_pct', casas=0)} | {_fmt(l, 'mem_usada_mb', casas=0)} |")
    Path(arquivo).write_text("\n".join(linhas) + "\n")


def escrever_conclusoes(caps, qualidade, arquivo):
    linhas = [
        f"Critério de qualidade: p95 ≤ {qualidade['p95_max_ms']} ms e sucesso ≥ {qualidade['sucesso_min'] * 100:g}%.",
        "Capacidade = maior taxa testada dentro do critério antes da primeira violação "
        "(limitada à granularidade das taxas testadas).",
        "",
    ]
    for cenario, c in caps.items():
        cap, deg = c["capacidade"], c["degradacao"]
        if cap is None:
            linhas.append(f"{cenario}: nenhuma taxa testada atende ao critério.")
        else:
            linhas.append(f"{cenario}: capacidade = {cap['taxa']} req/s (vazão = {cap['vazao_media']:.1f} req/s, "
                          f"p95 = {cap['lat_p95_ms_media']:.1f} ms, sucesso = {cap['sucesso_media'] * 100:.1f}%).")
        if deg is None:
            linhas.append(f"  Não degradou até a maior taxa testada ({cap['taxa']} req/s).")
        else:
            cpu = deg.get("cpu_pct_media")
            cpu = f", CPU = {cpu:.0f}%" if cpu is not None and pd.notna(cpu) else ""
            linhas.append(f"  Degrada a partir de {deg['taxa']} req/s: vazão = {deg['vazao_media']:.1f} req/s, "
                          f"p95 = {deg['lat_p95_ms_media']:.1f} ms, sucesso = {deg['sucesso_media'] * 100:.1f}%{cpu}.")
    base = next(iter(caps))
    cap_base = caps[base]["capacidade"]
    if cap_base is not None and len(caps) > 1:
        linhas.append("")
        for cenario, c in caps.items():
            if cenario != base and c["capacidade"] is not None:
                linhas.append(f"{cenario} suporta {c['capacidade']['taxa'] / cap_base['taxa']:.2f}× "
                              f"a capacidade de {base}.")
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


def desenhar_graficos(resumo, metas, caps, qualidade, destino):
    cenarios = sorted(resumo["cenario"].unique())
    if len(cenarios) > len(CORES):
        raise SystemExit(f"no máximo {len(CORES)} cenários por relatório")
    cores = {c: i for i, c in enumerate(cenarios)}
    taxas = sorted(resumo["taxa"].unique())
    p95_max = qualidade["p95_max_ms"]

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
    ax.axhline(p95_max, linestyle="--", linewidth=1, color=REFERENCIA, label=f"limite p95 ({p95_max} ms)")
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

    fig, ax = _figura("Taxa de erro × demanda", "Erros (% das requisições)", taxas)
    _series(ax, resumo, "erros_pct", cores)
    ax.set_ylim(bottom=0)
    _salvar(fig, ax, destino / "erros.png")

    fig, ax = plt.subplots()
    ax.set_title(f"Capacidade por cenário (p95 ≤ {p95_max} ms, sucesso ≥ {qualidade['sucesso_min'] * 100:g}%)",
                 loc="left")
    valores = [int(caps[c]["capacidade"]["taxa"]) if caps[c]["capacidade"] is not None else 0 for c in cenarios]
    barras = ax.bar(cenarios, valores, width=0.6, color=[CORES[cores[c]] for c in cenarios])
    ax.bar_label(barras, labels=[f"{v} req/s" for v in valores], color=TINTA_SEC, padding=3)
    ax.set_ylabel("Maior taxa dentro do critério (req/s)")
    ax.set_ylim(0, max(max(valores), 1) * 1.15)  # espaço para os rótulos acima das barras
    ax.set_axisbelow(True)
    ax.grid(axis="x", visible=False)
    fig.savefig(destino / "capacidade.png", dpi=150, bbox_inches="tight")
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
    caps = capacidade(resumo, cfg["qualidade"])
    escrever_conclusoes(caps, cfg["qualidade"], destino / "conclusoes.txt")
    desenhar_graficos(resumo, metas, caps, cfg["qualidade"], destino)
    print(f"relatório gerado em {destino}/")

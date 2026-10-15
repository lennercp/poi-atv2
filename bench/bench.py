"""Harness de teste de carga da Atividade 2.

  python bench/bench.py run    --cenario 1cpu-1ram [--config experimento-memory-bound.yaml] [--no-vm-metrics]
  python bench/bench.py report                    [--config experimento-memory-bound.yaml]
"""
import argparse
import base64
import json
import math
import mimetypes
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

import report
import vm


def parse_duracao(texto):
    """Converte uma duração no formato do vegeta ('500ms', '30s', '1m') em segundos."""
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(ms|s|m)", str(texto).strip())
    if not m:
        raise ValueError(f"duração inválida: {texto!r} (use, por exemplo, 30s, 500ms ou 1m)")
    return float(m.group(1)) * {"ms": 0.001, "s": 1, "m": 60}[m.group(2)]


def carregar_config(caminho):
    with open(caminho) as f:
        cfg = yaml.safe_load(f)
    carga = cfg["carga"]
    for chave in ("duracao", "aquecimento", "timeout", "pausa"):
        parse_duracao(carga[chave])
    # No vegeta, rate=0 e duration=0 significam "infinito": o teste nunca terminaria.
    if not carga["taxas"] or any(t <= 0 for t in carga["taxas"]):
        raise ValueError("carga.taxas precisa ter apenas valores > 0")
    if parse_duracao(carga["duracao"]) <= 0:
        raise ValueError("carga.duracao precisa ser > 0")
    return cfg


def corpo_multipart(multipart):
    """Monta um corpo multipart/form-data a partir de `campos` (texto) e `arquivos` (caminhos)."""
    fronteira = "----bench-fronteira"
    partes = []
    for nome, valor in (multipart.get("campos") or {}).items():
        partes.append(f'--{fronteira}\r\nContent-Disposition: form-data; name="{nome}"\r\n\r\n{valor}\r\n'.encode())
    for nome, caminho in (multipart.get("arquivos") or {}).items():
        tipo = mimetypes.guess_type(caminho)[0] or "application/octet-stream"
        partes.append(f'--{fronteira}\r\nContent-Disposition: form-data; name="{nome}"; '
                      f'filename="{Path(caminho).name}"\r\nContent-Type: {tipo}\r\n\r\n'.encode()
                      + Path(caminho).read_bytes() + b"\r\n")
    partes.append(f"--{fronteira}--\r\n".encode())
    return b"".join(partes), f"multipart/form-data; boundary={fronteira}"


def escrever_alvo(alvo, arquivo):
    """Grava o alvo no formato de alvos JSON do vegeta (-format=json)."""
    target = {"method": alvo.get("method", "GET"), "url": alvo["url"]}
    if sum(alvo.get(k) is not None for k in ("body", "body_arquivo", "multipart")) > 1:
        raise ValueError("alvo: use só um de body, body_arquivo ou multipart")
    if alvo.get("body") is not None:
        target["body"] = base64.b64encode(str(alvo["body"]).encode()).decode()
        target["header"] = {"Content-Type": ["application/json"]}
    if alvo.get("body_arquivo") is not None:
        target["body"] = base64.b64encode(Path(alvo["body_arquivo"]).read_bytes()).decode()
        target["header"] = {"Content-Type": ["application/json"]}
    if alvo.get("multipart") is not None:
        corpo, tipo = corpo_multipart(alvo["multipart"])
        target["body"] = base64.b64encode(corpo).decode()
        target["header"] = {"Content-Type": [tipo]}
    Path(arquivo).write_text(json.dumps(target) + "\n")


def atacar(alvo, taxa, duracao, timeout, saida):
    """Roda `vegeta attack` em taxa constante e grava os resultados binários em `saida`."""
    subprocess.run(
        ["vegeta", "attack", "-format=json", f"-targets={alvo}", f"-rate={taxa}",
         f"-duration={duracao}", f"-timeout={timeout}", f"-output={saida}"],
        check=True,
    )


def gerar_relatorios(pasta, nome):
    """Gera o JSON de estatísticas a partir do .bin de uma execução."""
    binario = pasta / f"{nome}.bin"
    estatisticas = pasta / f"{nome}.json"
    subprocess.run(["vegeta", "report", "-type=json", f"-output={estatisticas}", str(binario)], check=True)
    return json.loads(estatisticas.read_text())


def cmd_run(args):
    cfg = carregar_config(args.config)
    carga = cfg["carga"]
    destino = None if args.no_vm_metrics else vm.destino(cfg["vm"])
    meta = {"cenario": args.cenario, "inicio": datetime.now().isoformat(timespec="seconds"), "config": cfg}
    if destino:
        meta.update(vm.info(destino))  # antes de criar a pasta: SSH falhando não deixa cenário sem meta.json

    pasta = Path(cfg["saida"]) / args.cenario
    pasta.mkdir(parents=True, exist_ok=True)
    alvo = pasta / "alvo.json"
    escrever_alvo(cfg["alvo"], alvo)
    (pasta / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))

    aquecimento = parse_duracao(carga["aquecimento"])
    pausa = parse_duracao(carga["pausa"])
    amostras = math.ceil(parse_duracao(carga["duracao"]))
    for taxa in sorted(carga["taxas"]):
        for rep in range(1, carga["repeticoes"] + 1):
            nome = f"r{taxa}_rep{rep}"
            if aquecimento > 0:
                atacar(alvo, taxa, carga["aquecimento"], carga["timeout"], os.devnull)
            coletor = vm.Coletor(destino, amostras) if destino else None
            jvm = vm.ColetorJvm(cfg["prometheus"]) if cfg.get("prometheus") else None
            try:
                atacar(alvo, taxa, carga["duracao"], carga["timeout"], pasta / f"{nome}.bin")
                if jvm:
                    (pasta / f"{nome}.jvm.csv").write_text(jvm.parar())
                if coletor:
                    (pasta / f"{nome}.vmstat.txt").write_text(coletor.esperar())
            finally:
                if coletor:
                    coletor.parar()  # Ctrl+C: não deixa vmstat/ssh órfão
                if jvm:
                    jvm.parar()
            r = gerar_relatorios(pasta, nome)
            print(f"[{args.cenario}] {taxa:>5} req/s  rep {rep}/{carga['repeticoes']}  "
                  f"p95 = {r['latencies']['95th'] / 1e6:8.1f} ms  sucesso = {r['success'] * 100:5.1f}%",
                  flush=True)
            time.sleep(pausa)


def cmd_report(args):
    report.gerar(carregar_config(args.config))


def main():
    ap = argparse.ArgumentParser(description="Harness de teste de carga (vegeta + vmstat).")
    sub = ap.add_subparsers(dest="comando", required=True)

    p_run = sub.add_parser("run", help="executa todas as taxas × repetições de um cenário")
    p_run.add_argument("--cenario", required=True, help="rótulo do cenário, ex.: 1cpu-1ram")
    p_run.add_argument("--config", default="experimento-memory-bound.yaml")
    p_run.add_argument("--no-vm-metrics", action="store_true", help="não coleta CPU/memória da VM")
    p_run.set_defaults(func=cmd_run)

    p_rep = sub.add_parser("report", help="consolida todos os cenários em CSV, tabela, conclusões e gráficos")
    p_rep.add_argument("--config", default="experimento-memory-bound.yaml")
    p_rep.set_defaults(func=cmd_report)

    args = ap.parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\ninterrompido", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()

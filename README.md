# Atividade 2 — Harness de teste de carga

Roda testes de stress com o [vegeta](https://github.com/tsenart/vegeta) (carga aberta, taxa constante) contra
uma aplicação HTTP, coleta CPU/memória de dentro da VM com `vmstat`, heap/fora do heap da JVM pelo `/actuator/prometheus` da app
(campo `prometheus` do yaml, opcional) e gera CSV, tabela e gráficos
para o relatório.

## Pré-requisitos (host, Ubuntu)

```bash
# vegeta: binário oficial (não existe no apt) — baixa e instala em /usr/local/bin
curl -sL https://github.com/tsenart/vegeta/releases/download/v12.13.0/vegeta_12.13.0_linux_amd64.tar.gz | sudo tar -xz -C /usr/local/bin vegeta
vegeta -version

# Python 3 do sistema + ambiente virtual
sudo apt install python3-venv
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Uso

Edite `experimento.yaml` (URL da app, taxas, duração, repetições). Para cada cenário:

1. Desligue a VM, ajuste CPU/RAM/"Restrição de execução" no VirtualBox, ligue e suba a app.
2. Rode:
   ```bash
   .venv/bin/python bench/bench.py run --cenario c1
   ```
   O `meta.json` do cenário registra o `nproc` e a memória que a VM realmente tinha.

No final:

```bash
.venv/bin/python bench/bench.py report
```

Saída em `results/report/`: `resumo.csv`, `tabela.md` e os gráficos `vazao.png`,
`latencia_p95.png`, `cpu.png`, `memoria.png`, `io_wait.png`, `disco_escrita.png`, `erros.png` e `memoria_detalhada.png` (um painel por cenário: heap + fora do heap empilhados e a
memória usada da VM). Cada execução também tem um
`results/<cenario>/r<taxa>_rep<n>.plot.html` (latência ao longo do tempo, gerado pelo `vegeta plot`).
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
`latencia_p95.png`, `cpu.png`, `memoria.png`, `erros.png` e `memoria_detalhada.png` (um painel por cenário: heap + fora do heap empilhados e a
memória usada da VM). Cada execução também tem um
`results/<cenario>/r<taxa>_rep<n>.plot.html` (latência ao longo do tempo, gerado pelo `vegeta plot`).

### Variações

- **Rodada exploratória** (para escolher as taxas): copie para `explorar.yaml` com `saida: results-explorar` e
  `duracao: 10s`, e passe `--config explorar.yaml` no `run` e no `report`.
- **Sem aquecimento**: `sem-aquecimento.yaml` com `aquecimento: 0s` e `saida: results-sem-aquecimento`; reinicie a
  app antes de rodar. O efeito aparece no `plot.html` da primeira execução e em p99/max.
- **Apps locais (fora da VM)**: aponte `alvo.url` para a app local e use `--no-vm-metrics`, ou `vm.ssh: local`
  para medir a CPU/memória da própria máquina.

## Teste do harness

```bash
bash tests/e2e/run_e2e.sh
```

Sobe um servidor falso que gasta CPU, limitado a 1 e depois a 2 núcleos, roda os dois "cenários" e confere se o
de 2 núcleos atende mais requisições na taxa mais alta.

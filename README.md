# Teste de Carga em 3 aplicações

Roda testes de stress com o [vegeta](https://github.com/tsenart/vegeta) (carga aberta, taxa constante) contra
uma aplicação HTTP, coleta CPU/memória de dentro da VM com `vmstat`, heap/fora do heap da JVM pelo `/actuator/prometheus` da app
(campo `prometheus` do yaml, opcional) e gera CSV, tabela e gráficos
para o relatório.

## Aplicações

Três apps Spring Boot em `apps/`, cada uma forçando um recurso diferente da VM:

| App | O que faz | Requisição do teste | Porta (host → VM) |
|---|---|---|---|
| `cpu-bound` | conta os primos até `limit` | `GET /api/primes?limit=200000` | 8083 → 82 |
| `memory-bound` | converte uma imagem para tons de cinza | `POST /api/imagens/processar` (`img1000.jpg`, 1000×1000) | 8081 → 80 |
| `io-bound` | grava cada requisição num arquivo novo no disco (com DSYNC) | `POST /files` (`body256k.json`, 256 KB) | 8082 → 81 |

Cada app tem seu `experimento-<app>.yaml` e seus resultados em `results-<app>/`.

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

Escolha o yaml da app (URL, taxas, duração, repetições); o padrão do `--config` é o
`experimento-memory-bound.yaml`. Para cada cenário:

1. Desligue a VM, ajuste CPU/RAM/"Restrição de execução" no VirtualBox, ligue e suba a app.
2. Rode:
   ```bash
   .venv/bin/python bench/bench.py run --cenario 1cpu-1ram --config experimento-cpu-bound.yaml
   ```
   O `meta.json` do cenário registra o `nproc` e a memória que a VM realmente tinha.

No final:

```bash
.venv/bin/python bench/bench.py report --config experimento-cpu-bound.yaml
```

Saída em `results-<app>/report/`: `resumo.csv`, `tabela.md` e os gráficos `vazao.png`,
`latencia_p95.png`, `cpu.png`, `memoria.png`, `io_wait.png`, `disco_escrita.png` e `erros.png`.
Quando o yaml tem `prometheus` (só a memory-bound), sai também o `memoria_detalhada.png` (um painel
por cenário: heap + fora do heap empilhados e a memória usada da VM).

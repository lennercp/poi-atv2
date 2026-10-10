# cpu-bound

Aplicação web (somente backend) com perfil **CPU-bound**, em Java 17 + Spring Boot. Cada requisição conta
os números primos de 2 até `limit` por **divisão por tentativa**, em uma única thread, sem I/O, banco de dados
ou serviços externos. O custo cresce com `limit` (≈ `limit^1.5`), então o trabalho por requisição é
controlado só pelo parâmetro.

Este projeto é independente do resto do repositório (não usa `bench/` nem `tests/`).

## Estrutura

```
cpu-bound/
├── pom.xml, mvnw                  build (Maven Wrapper: só precisa de JDK 17+)
├── src/main/java/poi/cpubound/    CpuBoundApplication, PrimeController, PrimeService
├── src/main/resources/application.properties
├── src/test/java/poi/cpubound/    testes automatizados (JUnit + MockMvc)
├── config/
│   ├── scenarios.env              provisionamento da VM (vCPUs, RAM) — registro dos cenários
│   ├── app.env                    configuração da aplicação (porta, limites, threads, JVM)
│   └── load.env                   carga de teste (limit, usuários, duração, repetições)
├── load/primes.js                 teste de carga k6
└── scripts/
    ├── run-app.sh                 sobe a aplicação com config/app.env (na VM)
    ├── monitor.sh                 coleta CPU/RAM por segundo (na VM)
    └── run-load.sh                executa todos os níveis de carga de um cenário (no hospedeiro)
```

## Compilar, testar e executar

```bash
cd cpu-bound
./mvnw package            # compila, roda os testes e gera target/cpu-bound.jar
./mvnw test               # só os testes
scripts/run-app.sh        # sobe a aplicação (porta 8080 por padrão)
```

## API

| Método | Rota | Resposta |
|---|---|---|
| GET | `/health` | `200 {"status":"UP"}` |
| GET | `/api/primes?limit=N` | `200 {"limit":1000000,"primeCount":78498,"computeTimeMs":48.03}` |

- `computeTimeMs`: tempo **interno** do cálculo, medido no servidor com `System.nanoTime()`. Não inclui rede,
  fila do Tomcat, serialização nem espera por CPU antes do início do cálculo.
- `limit` ausente, não inteiro, menor que `PRIMES_MIN_LIMIT` ou maior que `PRIMES_MAX_LIMIT` → `400 {"error": "..."}`.

Tempos de referência (máquina de desenvolvimento, 1 requisição): `limit=100000` ≈ 5 ms,
`limit=1000000` ≈ 48 ms, `limit=10000000` ≈ 1,2 s. Na VM os valores serão maiores.

## Configuração

Os três grupos de configuração são separados e nenhum exige alterar o código-fonte.

### 1. Provisionamento da VM — `config/scenarios.env`

```
A_VCPUS=1; A_RAM_MB=1024
B_VCPUS=1; B_RAM_MB=2048
C_VCPUS=2; C_RAM_MB=2048
D_VCPUS=2; D_RAM_MB=4096
```

CPU e RAM da VM são definidas **no VirtualBox** (VM desligada → Configurações → Sistema), seguindo o roteiro
da disciplina. Este arquivo só registra qual cenário está sendo executado; `run-load.sh` copia os valores para
`results/<cenário>/meta.txt`. Para criar ou ajustar cenários, edite/adicione linhas `<NOME>_VCPUS` e `<NOME>_RAM_MB`.

### 2. Aplicação — `config/app.env`

| Variável | Padrão | Efeito |
|---|---|---|
| `SERVER_PORT` | 8080 | porta HTTP |
| `PRIMES_MIN_LIMIT` / `PRIMES_MAX_LIMIT` | 2 / 10000000 | faixa aceita para `limit` |
| `TOMCAT_MAX_THREADS` | 200 | máximo de requisições processadas ao mesmo tempo |
| `JAVA_OPTS` | vazio | flags da JVM (ex.: `-Xmx512m`) |

Essas variáveis **não** alteram os recursos da VM. Elas também podem ser passadas direto na linha de comando
(`SERVER_PORT=9090 java -jar target/cpu-bound.jar`).

**Threads do servidor.** Cada requisição ocupa uma thread do Tomcat durante todo o cálculo, e o cálculo não
é paralelizado. Com N vCPUs, no máximo N requisições calculam ao mesmo tempo; as demais threads disputam a CPU
(time-slicing), e acima de `TOMCAT_MAX_THREADS` as requisições esperam na fila de conexões. Mantenha o valor
padrão e registre no relatório se mudar.

**Memória.** Sem `-Xmx`, o heap máximo da JVM é 1/4 da RAM da VM, então mudar a RAM da VM também muda o heap.
A aplicação usa pouca memória (≈ 250 MB de RSS), por isso RAM deve afetar pouco o desempenho — isso é um
resultado esperado do perfil CPU-bound.

### 3. Carga de teste — `config/load.env`

| Variável | Padrão | Significado |
|---|---|---|
| `TARGET_URL` | `http://localhost:8080` | URL da app vista pelo gerador de carga |
| `LIMITS` | `"100000 1000000"` | trabalho por requisição |
| `VUS_LEVELS` | `"1 2 4 8 16 32"` | usuários simultâneos (níveis de demanda) |
| `REPETITIONS` | 3 | repetições de cada combinação |
| `DURATION_SECONDS` | 60 | duração de cada execução |
| `WARMUP_SECONDS` | 15 | aquecimento da JVM (descartado) antes de cada `limit` |
| `COOLDOWN_SECONDS` | 10 | pausa entre execuções |
| `REQUEST_TIMEOUT` | 30s | acima disso a requisição conta como timeout |
| `VM_SSH`, `VM_APP_DIR` | vazio | acesso SSH à VM para coletar CPU/RAM |

O k6 usa modelo **fechado**: cada usuário virtual envia uma nova requisição assim que recebe a resposta. A taxa
de envio é consequência da capacidade do servidor, então a vazão medida mostra onde ela satura. Para usar outro
perfil de carga sem editar o padrão: `LOAD_ENV=config/outro.env scripts/run-load.sh A`.

## Deploy na VM

Dentro da VM (Ubuntu 22.04 do roteiro):

```bash
sudo apt install openjdk-17-jdk git
git clone <repositório> ~/poi-atv2
cd ~/poi-atv2/cpu-bound
./mvnw package
scripts/run-app.sh
```

No VirtualBox, crie o redirecionamento de portas (NAT) da porta do hospedeiro para `SERVER_PORT` do convidado,
como no roteiro, e ajuste `TARGET_URL` em `config/load.env`. Para coleta automática de CPU/RAM, redirecione
também a porta 22 (ex.: hospedeiro 2222) e configure login por chave:

```bash
ssh-copy-id -p 2222 <usuario>@localhost
# config/load.env: VM_SSH="-p 2222 <usuario>@localhost"   VM_APP_DIR="~/poi-atv2/cpu-bound"
```

## Executar os experimentos

No hospedeiro, com o [k6](https://grafana.com/docs/k6/latest/set-up/install-k6/) instalado:

1. Desligue a VM, ajuste vCPUs/RAM do cenário no VirtualBox, ligue a VM e suba a app (`scripts/run-app.sh`).
2. Rode: `scripts/run-load.sh A` (use o nome do cenário configurado).
3. Repita para B, C, D.

Teste manual de uma única configuração, sem script:

```bash
k6 run -e TARGET_URL=http://localhost:8080 -e LIMIT=1000000 -e VUS=8 -e DURATION=60s load/primes.js
```

### Saída

`results/<cenário>/`:

- `runs.csv` — uma linha por execução (formato abaixo);
- `<run>.k6.csv` — linha bruta do k6;
- `<run>.monitor.csv` — CPU/RAM por segundo na VM (se `VM_SSH` estiver configurado). A primeira linha registra
  `nproc` e a RAM total que a VM realmente tinha;
- `meta.txt` — cenário, vCPUs/RAM declarados e a configuração de carga usada.

| Coluna | Métrica |
|---|---|
| `requests`, `rps` | total de requisições e **throughput** (req/s) |
| `avg_ms`, `med_ms`, `p95_ms`, `max_ms` | **tempo de resposta medido pelo cliente** (média, mediana, p95, máximo) |
| `errors` | requisições com falha (status ≠ 2xx/3xx ou erro de rede, inclui timeouts) |
| `timeouts` | requisições que excederam `REQUEST_TIMEOUT` |
| `compute_avg_ms`, `compute_med_ms`, `compute_p95_ms` | **tempo interno do cálculo** (`computeTimeMs` da API) |
| `cpu_avg_pct` | utilização média de CPU da VM (100 − idle do `vmstat`) |
| `mem_used_avg_mb` | memória média usada na VM (`free`) |
| `java_rss_max_mb` | pico de memória residente do processo Java |

A diferença entre `avg_ms` e `compute_avg_ms` é o tempo gasto fora do cálculo: rede, fila do servidor e, sob
contenção, espera por CPU. Quando a demanda passa do número de vCPUs, `compute_avg_ms` também cresce, pois as
threads dividem os núcleos durante o cálculo.

Sem `VM_SSH`, colete CPU/RAM manualmente rodando `scripts/monitor.sh <segundos> > arquivo.csv` dentro da VM
durante a execução (ou acompanhe com `htop`).

## Limitações

- `cpu_avg_pct` é a CPU da VM inteira (inclui SO), não só da aplicação.
- O monitor amostra a cada 1 s e começa junto com o k6 via SSH; pode haver deslocamento de ~1 s.
- O k6 deve rodar no hospedeiro, não na VM, para não competir pela CPU da aplicação.
- A primeira requisição após subir a app é mais lenta (JIT); por isso há o aquecimento.

# cpu-bound

Aplicação CPU-bound em Java 17 com Spring Boot. O endpoint `/api/primes` conta quantos números primos existem
de 2 até `limit` usando divisão por tentativa (testa os divisores até a raiz de cada número). Não usa banco de
dados nem nenhum serviço externo, só CPU.

## Como rodar

Precisa do JDK 17 ou mais novo. O Maven é baixado pelo `./mvnw`.

```bash
./mvnw package
scripts/run-app.sh
```

O `./mvnw package` também roda os testes. Para rodar só os testes: `./mvnw test`.

## Endpoints

```
GET /health                  -> {"status":"UP"}
GET /api/primes?limit=1000000 -> {"limit":1000000,"primeCount":78498,"computeTimeMs":48.0}
```

`computeTimeMs` é o tempo do cálculo medido dentro da aplicação. O tempo de resposta medido pelo k6 é maior,
porque inclui rede e o tempo que a requisição espera no servidor.

Se `limit` estiver faltando, não for inteiro ou estiver fora do intervalo configurado, a resposta é 400.

## Configuração

Os arquivos ficam em `config/`:

- `app.env`: porta, limite mínimo e máximo do `limit`, número máximo de threads do Tomcat e opções da JVM.
- `load.env`: parâmetros do teste de carga (valores de `limit`, usuários simultâneos, duração, repetições).
- `scenarios.env`: cenários de vCPU e RAM usados nos experimentos.

CPU e RAM da VM são configuradas no VirtualBox, não na aplicação. Os cenários planejados:

| Cenário | vCPUs | RAM |
|---|---|---|
| A | 1 | 1 GB |
| B | 1 | 2 GB |
| C | 2 | 2 GB |
| D | 2 | 4 GB |

Cada requisição usa uma thread do Tomcat durante todo o cálculo, e o cálculo não é paralelizado. Com 1 vCPU,
várias requisições ao mesmo tempo dividem o mesmo núcleo. Usamos o padrão de 200 threads do Spring Boot.

## Experimentos

O teste de carga usa o [k6](https://grafana.com/docs/k6/latest/set-up/install-k6/), que deve rodar fora da VM
para não disputar CPU com a aplicação.

Para cada cenário:

1. Configurar vCPUs e RAM no VirtualBox e ligar a VM.
2. Na VM, subir a aplicação com `scripts/run-app.sh`.
3. Na VM, em outro terminal, coletar CPU e memória: `scripts/monitor.sh > monitor_A.csv`.
4. Fora da VM, rodar `scripts/run-load.sh A`.
5. Quando terminar, parar o monitor com Ctrl+C.

O `run-load.sh` roda todas as combinações de `LIMITS` e `VUS` do `load.env` e salva uma linha por execução em
`results/A.csv`, com requisições por segundo, tempo de resposta (média, mediana, p95, máximo), erros,
timeouts e tempo de cálculo da API. As colunas `inicio` e `fim` servem para cruzar com o `monitor_A.csv`, que
registra a cada segundo a CPU usada, a memória usada da VM e a memória do processo Java.

Para rodar um teste só:

```bash
k6 run -e URL=http://localhost:8080 -e LIMIT=1000000 -e VUS=8 -e DURATION=60s load/primes.js
```

"""Métricas de dentro da VM: nproc/memória total, amostras do vmstat (via SSH ou local)
e heap/fora do heap da JVM (via /actuator/prometheus da app)."""
import subprocess
import threading
import time
import urllib.request


def destino(cfg_vm):
    """Prefixo de comando para executar algo na VM; o comando vai como um único argumento.

    `ssh: local` executa na própria máquina (teste ponta a ponta e apps rodando localmente).
    BatchMode=yes faz o ssh falhar em vez de ficar esperando senha.
    ControlMaster reaproveita uma única conexão: abrir uma sessão nova (handshake, PAM, sessão do
    systemd) satura uma VM de 1 CPU por ~1 s bem no início da medição e infla o p95.
    """
    if cfg_vm["ssh"] == "local":
        return ["sh", "-c"]
    return ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
            "-o", "ControlMaster=auto", "-o", "ControlPath=~/.ssh/bench-%C", "-o", "ControlPersist=10m",
            "-p", str(cfg_vm["porta"]), cfg_vm["ssh"]]


def info(destino):
    """Número de CPUs e memória total (MiB) vistos de dentro da VM."""
    # stdin=DEVNULL: o ssh não lê o terminal (senão para com SIGTTIN se o run estiver em segundo plano)
    saida = subprocess.run(destino + ["nproc; grep MemTotal /proc/meminfo"], stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, text=True, check=True).stdout.split()
    # ex.: ['2', 'MemTotal:', '2030000', 'kB']
    return {"nproc": int(saida[0]), "mem_total_mb": round(int(saida[2]) / 1024)}


class Coletor:
    """Roda `vmstat 1` na VM durante uma medição de `amostras` segundos.

    A contagem fixa (+1 pela linha de média desde o boot) faz o vmstat terminar sozinho,
    então a saída chega inteira mesmo com stdout bufferizado.
    """

    def __init__(self, destino, amostras):
        self.proc = subprocess.Popen(destino + [f"vmstat -n 1 {amostras + 1}"],
                                     stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True)

    def esperar(self, timeout=30):
        saida, _ = self.proc.communicate(timeout=timeout)
        if self.proc.returncode != 0:
            raise RuntimeError(f"vmstat terminou com código {self.proc.returncode}")
        return saida

    def parar(self):
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()


class ColetorJvm:
    """Lê `jvm_memory_used_bytes` do endpoint Prometheus da app a cada segundo, numa thread.

    O endpoint passa pela mesma porta da carga: com a app saturada a leitura pode falhar ou
    estourar o timeout; a amostra fica vazia e a coleta segue.
    """

    def __init__(self, url):
        self.url = url
        self.linhas = ["segundo,heap_mb,nonheap_mb"]
        self._parar = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        inicio = time.monotonic()
        while not self._parar.is_set():
            t = time.monotonic() - inicio
            try:
                with urllib.request.urlopen(self.url, timeout=1) as r:
                    areas = parse_jvm(r.read().decode())
                self.linhas.append(f"{t:.1f},{areas['heap']:.1f},{areas['nonheap']:.1f}")
            except Exception:
                self.linhas.append(f"{t:.1f},,")
            self._parar.wait(max(0.0, 1 - (time.monotonic() - inicio - t)))

    def parar(self):
        self._parar.set()
        self._thread.join()
        return "\n".join(self.linhas) + "\n"


def parse_jvm(texto):
    """Soma `jvm_memory_used_bytes` por área (heap / nonheap), em MiB."""
    areas = {"heap": 0.0, "nonheap": 0.0}
    for linha in texto.splitlines():
        if linha.startswith("jvm_memory_used_bytes{"):
            for area in areas:
                if f'area="{area}"' in linha:
                    areas[area] += float(linha.rsplit(" ", 1)[1]) / 2**20
    return areas


def parse(texto, mem_total_mb):
    """Converte a saída do `vmstat -n` (memória em KiB) em amostras. Colunas pelo cabeçalho
    (versões diferentes do vmstat têm colunas diferentes, ex.: `gu`)."""
    linhas = [l.split() for l in texto.strip().splitlines()]
    i = next(i for i, l in enumerate(linhas) if l[:2] == ["r", "b"])
    cabecalho = linhas[i]
    amostras = []
    for valores in linhas[i + 2:]:  # linhas[i + 1] é a média desde o boot
        d = dict(zip(cabecalho, map(int, valores)))
        amostras.append({
            "cpu_pct": 100 - d["id"],
            "us": d["us"], "sy": d["sy"], "wa": d["wa"], "st": d.get("st", 0),
            "mem_usada_mb": mem_total_mb - (d["free"] + d["buff"] + d["cache"]) / 1024,
            "si": d["si"], "so": d["so"],  # KiB/s
        })
    return amostras

import http from 'k6/http';
import { check } from 'k6';
import { Counter, Trend } from 'k6/metrics';

const url = __ENV.URL || 'http://localhost:8080';
const limit = __ENV.LIMIT || '100000';

// tempo de cálculo informado pela API (computeTimeMs)
const calculo = new Trend('calculo_ms', true);
const timeouts = new Counter('timeouts');

export const options = {
  vus: Number(__ENV.VUS || 1),
  duration: __ENV.DURATION || '30s',
  summaryTrendStats: ['avg', 'med', 'p(95)', 'max'],
};

export default function () {
  const res = http.get(`${url}/api/primes?limit=${limit}`, { timeout: __ENV.TIMEOUT || '30s' });
  if (res.error_code === 1050) {
    timeouts.add(1);
  }
  if (check(res, { 'status 200': (r) => r.status === 200 })) {
    calculo.add(res.json('computeTimeMs'));
  }
}

// imprime o resumo do teste em uma linha CSV
export function handleSummary(data) {
  const m = data.metrics;
  const v = (nome, campo) => (m[nome] ? m[nome].values[campo] : 0);
  const linha = [
    v('http_reqs', 'count'),
    v('http_reqs', 'rate').toFixed(2),
    v('http_req_duration', 'avg').toFixed(2),
    v('http_req_duration', 'med').toFixed(2),
    v('http_req_duration', 'p(95)').toFixed(2),
    v('http_req_duration', 'max').toFixed(2),
    v('http_req_failed', 'passes'),
    v('timeouts', 'count'),
    v('calculo_ms', 'avg').toFixed(2),
    v('calculo_ms', 'p(95)').toFixed(2),
  ];
  return { stdout: linha.join(',') + '\n' };
}

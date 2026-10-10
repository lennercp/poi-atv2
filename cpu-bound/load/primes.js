// k6 load test for GET /api/primes (closed model: VUS users, each waits for its response).
// All parameters come from environment variables (see config/load.env and scripts/run-load.sh).
import http from 'k6/http';
import { check } from 'k6';
import { Counter, Trend } from 'k6/metrics';

const TARGET_URL = __ENV.TARGET_URL || 'http://localhost:8080';
const LIMIT = __ENV.LIMIT || '100000';
const REQUEST_TIMEOUT = __ENV.REQUEST_TIMEOUT || '30s';

// Server-side calculation time reported by the API (computeTimeMs).
// Compare with http_req_duration, the full response time measured by the client.
const computeTime = new Trend('compute_time_ms', true);
const timeouts = new Counter('timeouts');

export const options = {
  vus: Number(__ENV.VUS || 1),
  duration: __ENV.DURATION || '30s',
  summaryTrendStats: ['avg', 'med', 'p(95)', 'max'],
};

export default function () {
  const res = http.get(`${TARGET_URL}/api/primes?limit=${LIMIT}`, { timeout: REQUEST_TIMEOUT });
  if (res.error_code === 1050) {
    timeouts.add(1);
  }
  if (check(res, { 'status is 200': (r) => r.status === 200 })) {
    computeTime.add(res.json('computeTimeMs'));
  }
}

// Writes one CSV line (columns listed in scripts/run-load.sh) to the file in OUT.
export function handleSummary(data) {
  const m = data.metrics;
  const v = (name, key) => (m[name] ? m[name].values[key] : 0);
  const f = (x) => Number(x).toFixed(2);
  const line = [
    __ENV.SCENARIO, LIMIT, options.vus, __ENV.REP,
    v('http_reqs', 'count'), f(v('http_reqs', 'rate')),
    f(v('http_req_duration', 'avg')), f(v('http_req_duration', 'med')),
    f(v('http_req_duration', 'p(95)')), f(v('http_req_duration', 'max')),
    v('http_req_failed', 'passes'), v('timeouts', 'count'),
    f(v('compute_time_ms', 'avg')), f(v('compute_time_ms', 'med')), f(v('compute_time_ms', 'p(95)')),
  ].join(',');
  const result = { stdout: `${line}\n` };
  if (__ENV.OUT) {
    result[__ENV.OUT] = line;
  }
  return result;
}

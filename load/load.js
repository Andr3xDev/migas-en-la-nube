import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL;
const ENVIRONMENT = __ENV.ENVIRONMENT;
const SCENARIO = __ENV.SCENARIO;
const RESULTS_DIR = __ENV.RESULTS_DIR || "load-results";

// Traffic model from docs/hld.md section 2: Saturday peak is about 300 visits per hour.
const PEAK_VISITS_PER_MINUTE = 300 / 60;
const PEAK_MULTIPLIER = 3;
// A visit = 4 static requests (home, stylesheet, nav script, product page) plus 6 API calls, as the
// HLD assumes: catalog, 4 product details, catalog again (back to the list).
const STATIC_REQUESTS_PER_VISIT = 4;
const PRODUCTS_VIEWED_PER_VISIT = 4;
const API_CALLS_PER_VISIT = PRODUCTS_VIEWED_PER_VISIT + 2;
const REQUESTS_PER_VISIT = STATIC_REQUESTS_PER_VISIT + API_CALLS_PER_VISIT;

const ORDERS_PER_MINUTE = 6;
const ORDERS_DURATION = "3m";
const REALISTIC_DURATION = "5m";
const SHOP_UTC_OFFSET_HOURS = -5;
const PICKUP_DAYS_AHEAD = 2;
const PICKUP_HOUR = "10:00:00-05:00";
const LOAD_ORDER_CUSTOMER = "k6 load test";
const LOAD_ORDER_PHONE = "3001234567";

const WARMUP_DURATION = "30s";
// Cold start can add seconds to the first requests, so thresholds only cover the measured scenarios.
const MEASURED_SCENARIOS = ["visits", "orders"];

const visitScenarios = {
  realistic: {
    executor: "constant-arrival-rate",
    rate: PEAK_VISITS_PER_MINUTE,
    timeUnit: "1m",
    duration: REALISTIC_DURATION,
    preAllocatedVUs: 2,
    maxVUs: 10,
  },
  peak3x: {
    executor: "constant-arrival-rate",
    rate: PEAK_VISITS_PER_MINUTE * PEAK_MULTIPLIER,
    timeUnit: "1m",
    duration: REALISTIC_DURATION,
    preAllocatedVUs: 5,
    maxVUs: 20,
  },
  // Visits per second: up to 40/s, about 480 times the Saturday peak.
  stress: {
    executor: "ramping-arrival-rate",
    startRate: 1,
    timeUnit: "1s",
    // Too few preallocated VUs made k6 drop iterations at ramp steps while it allocated more.
    preAllocatedVUs: 100,
    maxVUs: 200,
    stages: [
      { target: 5, duration: "30s" },
      { target: 5, duration: "1m" },
      { target: 20, duration: "1m" },
      { target: 20, duration: "1m" },
      { target: 40, duration: "1m" },
      { target: 40, duration: "30s" },
    ],
  },
};

function buildScenarios() {
  const warmup = {
    executor: "per-vu-iterations",
    vus: 1,
    iterations: 5,
    maxDuration: WARMUP_DURATION,
    exec: "warmUp",
  };
  if (SCENARIO === "orders") {
    return {
      warmup,
      orders: {
        executor: "constant-arrival-rate",
        rate: ORDERS_PER_MINUTE,
        timeUnit: "1m",
        duration: ORDERS_DURATION,
        preAllocatedVUs: 2,
        maxVUs: 10,
        startTime: WARMUP_DURATION,
        exec: "createOrder",
      },
    };
  }
  const visits = visitScenarios[SCENARIO];
  if (!visits) {
    throw new Error(`Unknown SCENARIO "${SCENARIO}"`);
  }
  return { warmup, visits: { ...visits, startTime: WARMUP_DURATION, exec: "visit" } };
}

function buildThresholds(scenarios) {
  const thresholds = {};
  for (const name of MEASURED_SCENARIOS.filter((measured) => measured in scenarios)) {
    // Registers the sub-metric so the summary can print the request count of the scenario.
    thresholds[`http_reqs{scenario:${name}}`] = ["count>=0"];
    thresholds[`http_req_failed{scenario:${name}}`] = ["rate<0.01"];
    thresholds[`http_req_duration{scenario:${name}}`] = ["p(95)<1000"];
    // Dropped iterations mean the target rate was not reached, so the run must not pass.
    thresholds[`dropped_iterations{scenario:${name}}`] = ["count==0"];
  }
  return thresholds;
}

if (!BASE_URL || !ENVIRONMENT) {
  throw new Error("BASE_URL and ENVIRONMENT are required");
}
if (SCENARIO === "orders" && ENVIRONMENT !== "dev") {
  throw new Error("The orders scenario writes data and runs only on dev");
}

const scenarios = buildScenarios();

export const options = {
  scenarios,
  thresholds: buildThresholds(scenarios),
  // Without this the exported summary has no p(95) for every sub-metric.
  summaryTrendStats: ["avg", "med", "p(90)", "p(95)", "max"],
};

function pickupTime() {
  const shopNow = new Date(Date.now() + SHOP_UTC_OFFSET_HOURS * 60 * 60 * 1000);
  shopNow.setUTCDate(shopNow.getUTCDate() + PICKUP_DAYS_AHEAD);
  // Two days ahead clears the longest prep time (24 h) and stays inside the 30-day horizon.
  return `${shopNow.toISOString().slice(0, 10)}T${PICKUP_HOUR}`;
}

export function setup() {
  const response = http.get(`${BASE_URL}/api/products`, { tags: { scenario: "setup" } });
  if (response.status !== 200) {
    throw new Error(`GET /api/products returned ${response.status}`);
  }
  const products = response.json().filter((product) => product.variants.length > 0);
  if (products.length === 0) {
    throw new Error("The catalog has no product with variants");
  }
  const first = products[0];
  return {
    productIds: products.map((product) => product.id),
    orderItem: { productId: first.id, variantName: first.variants[0].name, quantity: 1 },
  };
}

export function warmUp() {
  http.get(`${BASE_URL}/api/health`);
  http.get(`${BASE_URL}/api/products`);
  sleep(1);
}

export function visit(data) {
  const firstIndex = Math.floor(Math.random() * data.productIds.length);
  // With fewer products than PRODUCTS_VIEWED_PER_VISIT the ids wrap around and repeat.
  const viewedIds = Array.from(
    { length: PRODUCTS_VIEWED_PER_VISIT },
    (_, offset) => data.productIds[(firstIndex + offset) % data.productIds.length]
  );
  const responses = http.batch([
    ["GET", `${BASE_URL}/`],
    ["GET", `${BASE_URL}/css/styles.css`],
    ["GET", `${BASE_URL}/js/nav.js`],
    ["GET", `${BASE_URL}/api/products`],
    ["GET", `${BASE_URL}/product.html?id=${viewedIds[0]}`],
  ]);
  for (const productId of viewedIds) {
    responses.push(http.get(`${BASE_URL}/api/products/${productId}`));
  }
  responses.push(http.get(`${BASE_URL}/api/products`));
  check(responses, {
    [`all ${REQUESTS_PER_VISIT} requests return 200`]: (all) =>
      all.length === REQUESTS_PER_VISIT && all.every((response) => response.status === 200),
  });
}

export function createOrder(data) {
  const body = JSON.stringify({
    customerName: LOAD_ORDER_CUSTOMER,
    phone: LOAD_ORDER_PHONE,
    pickupTime: pickupTime(),
    items: [data.orderItem],
  });
  const response = http.post(`${BASE_URL}/api/orders`, body, {
    headers: { "Content-Type": "application/json" },
  });
  check(response, {
    "order created (201)": (r) => r.status === 201,
    "order has a code": (r) => {
      if (r.status !== 201) return false;
      try {
        return typeof r.json("code") === "string";
      } catch (error) {
        return false;
      }
    },
  });
}

function metricValues(data, name) {
  return data.metrics[name] ? data.metrics[name].values : undefined;
}

function textSummary(data) {
  const lines = [`Scenario: ${SCENARIO} on ${ENVIRONMENT} (${BASE_URL})`, ""];
  for (const name of MEASURED_SCENARIOS) {
    const duration = metricValues(data, `http_req_duration{scenario:${name}}`);
    const failed = metricValues(data, `http_req_failed{scenario:${name}}`);
    const counted = metricValues(data, `http_reqs{scenario:${name}}`);
    if (!duration || !failed) continue;
    lines.push(
      `Requests (${name}): ${counted ? counted.count : "n/d"}`,
      `Latency ms: avg ${duration.avg.toFixed(0)}, p90 ${duration["p(90)"].toFixed(0)}, ` +
        `p95 ${duration["p(95)"].toFixed(0)}, max ${duration.max.toFixed(0)}`,
      `Failed requests: ${(failed.rate * 100).toFixed(2)} %`,
      ""
    );
  }
  const iterations = metricValues(data, "iterations");
  const requests = metricValues(data, "http_reqs");
  lines.push(
    `Iterations (all scenarios): ${iterations ? iterations.count : 0}`,
    `Average request rate (all scenarios): ${requests ? requests.rate.toFixed(2) : 0} req/s`,
    "Thresholds:"
  );
  for (const [name, metric] of Object.entries(data.metrics)) {
    for (const [threshold, passed] of Object.entries(metric.thresholds || {})) {
      lines.push(`- ${passed.ok ? "PASS" : "FAIL"} ${name} ${threshold}`);
    }
  }
  return lines.join("\n") + "\n";
}

export function handleSummary(data) {
  const text = textSummary(data);
  return {
    stdout: text,
    [`${RESULTS_DIR}/summary.txt`]: text,
    [`${RESULTS_DIR}/summary.json`]: JSON.stringify(data, null, 2),
  };
}

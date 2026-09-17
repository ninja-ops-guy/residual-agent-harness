// RESIDUAL: recover immutable WebVM disk chunks from transient Pages/CDN failures.
// This is intentionally narrow: provider calls, arbitrary resources, non-GETs,
// cross-origin requests, and non-5xx HTTP responses are never retried here.
const RESIDUAL_DIAGNOSTIC_PROTOCOL = "residual.diagnostic.v1";

function residualPublishDiagnostic(event_type, context, options = {}) {
  try {
    const message = {
      protocol: RESIDUAL_DIAGNOSTIC_PROTOCOL,
      event_type,
      context,
      severity: options.severity || "warn",
      failure_class: options.failure_class || null,
      recoverable: options.recoverable === true,
    };
    Promise.resolve(self.clients?.matchAll?.({type: "window", includeUncontrolled: true}) || [])
      .then(clients => { for (const client of clients) client.postMessage(message); })
      .catch(() => {});
  } catch (_) {}
}

function residualIsImmutableDiskChunk(request) {
  try {
    const url = new URL(request.url);
    return request.method === "GET" &&
      url.origin === self.location.origin &&
      /\/residual-demo-[0-9a-f]{64}\.ext2\.c[0-9a-f]+\.txt$/.test(url.pathname);
  } catch (_) {
    return false;
  }
}

function residualDiskRetryDelay(attempt) {
  const milliseconds = attempt === 1 ? 200 : 800;
  return new Promise(resolve => setTimeout(resolve, milliseconds));
}

async function residualFetchWithRetry(request) {
  const retryable = residualIsImmutableDiskChunk(request);
  const attempts = retryable ? 3 : 1;
  let lastError = null;
  for (let attempt = 1; attempt <= attempts; attempt++) {
    try {
      const response = await fetch(retryable ? request.clone() : request);
      if (retryable && response.status >= 500 && response.status <= 599) {
        if (attempt < attempts) {
          residualPublishDiagnostic("serviceworker.disk_chunk_retry", {attempt, max_attempts: attempts, http_status: response.status}, {recoverable: true});
          console.warn(`RESIDUAL disk chunk fetch ${response.status}; retry ${attempt}/${attempts - 1}`, request.url);
          await residualDiskRetryDelay(attempt);
          continue;
        }
        residualPublishDiagnostic("serviceworker.disk_chunk_retry_exhausted", {attempt, max_attempts: attempts, http_status: response.status}, {severity: "error", failure_class: "NetworkFailure"});
      }
      return response;
    } catch (error) {
      lastError = error;
      if (!retryable || attempt >= attempts) {
        if (retryable) residualPublishDiagnostic("serviceworker.disk_chunk_retry_exhausted", {attempt, max_attempts: attempts}, {severity: "error", failure_class: "NetworkFailure"});
        throw error;
      }
      residualPublishDiagnostic("serviceworker.disk_chunk_network_retry", {attempt, max_attempts: attempts}, {recoverable: true, failure_class: "NetworkFailure"});
      console.warn(`RESIDUAL disk chunk network failure; retry ${attempt}/${attempts - 1}`, request.url, error);
      await residualDiskRetryDelay(attempt);
    }
  }
  throw lastError || new Error("RESIDUAL disk chunk retry exhausted");
}

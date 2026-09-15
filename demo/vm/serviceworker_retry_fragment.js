// RESIDUAL: recover immutable WebVM disk chunks from transient Pages/CDN failures.
// This is intentionally narrow: provider calls, arbitrary resources, non-GETs,
// cross-origin requests, and non-5xx HTTP responses are never retried here.
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
      if (retryable && attempt < attempts && response.status >= 500 && response.status <= 599) {
        console.warn(`RESIDUAL disk chunk fetch ${response.status}; retry ${attempt}/${attempts - 1}`, request.url);
        await residualDiskRetryDelay(attempt);
        continue;
      }
      return response;
    } catch (error) {
      lastError = error;
      if (!retryable || attempt >= attempts) throw error;
      console.warn(`RESIDUAL disk chunk network failure; retry ${attempt}/${attempts - 1}`, request.url, error);
      await residualDiskRetryDelay(attempt);
    }
  }
  throw lastError || new Error("RESIDUAL disk chunk retry exhausted");
}

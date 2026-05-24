## Circuit Breaker Pattern

The circuit breaker is named after the physical electrical breaker in your home — when too much current flows, it trips and cuts the connection to prevent damage. The software version does the same: when a downstream service is failing too often, it stops trying and fails fast instead of piling on.

Here's an interactive simulator of the three states and how they transition:Try hitting "Failed call" a few times to trip the breaker, then watch the reset timer count down to half-open.


---

## The three states in detail

**Closed** is the normal operating state. Every request passes through. The breaker silently tracks failures in a sliding window (count-based or time-based). If failures stay below the threshold, nothing changes.

**Open** is the tripped state. The breaker stops forwarding calls entirely and returns an error immediately — no network hop, no timeout wait. This is the key insight: you're protecting both the caller (which gets a fast response instead of a hung thread) and the downstream service (which gets breathing room to recover instead of an avalanche of retries).

**Half-open** is the probe state. After a configured timeout, the breaker lets a single request through. If it succeeds, the circuit closes and normal traffic resumes. If it fails, the breaker trips open again and restarts the timer.

---

## Key configuration knobs

```
Failure threshold     — how many failures before tripping (e.g. 5 failures)
Failure rate          — alternatively, what % failure rate triggers trip (e.g. 50%)
Sliding window        — count-based (last N calls) vs time-based (last N seconds)
Reset timeout         — how long to stay open before probing (e.g. 30s)
Half-open probe count — how many test calls to allow before fully closing
```

Libraries like Resilience4j (Java), Polly (.NET), and `pybreaker` (Python) expose all of these. Most service meshes (Istio, Linkerd) implement it transparently at the sidecar level.

---

## Real-world scenarios where this applies

**Payment gateway calls.** If Stripe or Razorpay starts returning 5xx errors, you don't want every checkout attempt to hang for 30 seconds waiting on a timeout. A circuit breaker trips open after a few failures, returns "payment service temporarily unavailable" instantly, and retries quietly after 30 seconds. Users get a clear error fast rather than a spinning loader.

**Inventory service in an e-commerce platform.** When the inventory service degrades (say, during a flash sale), the order service wraps that call in a circuit breaker. In open state it falls back to a cached inventory estimate or allows the order with an oversell buffer, rather than refusing orders entirely.

**Third-party enrichment APIs.** A background job that enriches user data by calling external APIs (weather, geocoding, credit scoring) can wrap each API in a separate circuit breaker. One API going down doesn't block enrichment jobs for others.

**Database connection pools.** If a replica DB becomes overloaded, a circuit breaker on the read path fails fast and routes reads to the primary (or returns stale cache data), preventing thread exhaustion on the application side.

**Inter-microservice calls at the API gateway.** The gateway wraps each downstream service with a breaker. If the Recommendations service is unhealthy, the gateway returns an empty recommendations list rather than failing the entire page load.

---

## What circuit breakers don't do

They don't replace retries — they complement them. The usual stack is: retry with exponential backoff for transient blips, circuit breaker for sustained failures. They also don't handle cascading failures on their own; for that you need bulkheads (thread pool isolation) to ensure one failing dependency can't exhaust all threads and bring down unrelated calls. Hystrix coined the term "bulkhead" for this; Resilience4j's `BulkHead` module is the modern equivalent.

#################################################################################################################################################################

The **Circuit Breaker pattern** is a resilience pattern used in distributed systems to prevent cascading failures when a dependent service is slow, failing, or unavailable.

---

# 🧠 Intuition (Interview-friendly)

Think of it like an **electrical circuit breaker**:

* When everything is fine → current flows (requests go through)
* When failures increase → breaker trips (stop calling service)
* After some time → system retries cautiously

---

# ⚙️ States of Circuit Breaker

### 1. ✅ Closed (Normal)

* Requests flow normally
* Failures are monitored
* If failures exceed threshold → move to **Open**

---

### 2. ❌ Open (Fail Fast)

* Calls are **not sent** to the downstream service
* Immediate failure response (fallback or cached response)
* After timeout → move to **Half-Open**

---

### 3. ⚠️ Half-Open (Trial Mode)

* Allows **limited requests**
* If success → back to Closed
* If failure → back to Open

---

# 🔥 Why do we need it?

Without circuit breaker:

* Thread pool exhaustion
* Increased latency
* Cascading failures across microservices

With circuit breaker:

* Fast failure
* System stability
* Controlled recovery

---

# 🏗️ Where I Used It (Strong Interview Answer)

You can present something like this 👇

> "In our credit decisioning microservices architecture, we integrated multiple external systems like credit bureaus and risk scoring services. These were unreliable at times, causing latency spikes and failures.
>
> To prevent cascading failures, we implemented a circuit breaker using Polly in our .NET services.
>
> For example, when calling the external credit bureau API:
>
> * If failures exceeded 5 requests within 30 seconds, the circuit would open
> * During open state, we avoided external calls and returned fallback responses (cached bureau data or default risk score)
> * After a cooldown of 1 minute, the system moved to half-open to test recovery
>
> This significantly reduced thread blocking, improved response time under failure conditions, and ensured our system remained responsive."

---

# 💻 .NET Implementation (Polly)

### Install

```bash
dotnet add package Polly
```

---

### Basic Circuit Breaker

```csharp
using Polly;
using Polly.CircuitBreaker;

var circuitBreaker = Policy
    .Handle<HttpRequestException>()
    .CircuitBreakerAsync(
        exceptionsAllowedBeforeBreaking: 5,
        durationOfBreak: TimeSpan.FromSeconds(30),
        onBreak: (ex, breakDelay) =>
        {
            Console.WriteLine($"Circuit opened for {breakDelay.TotalSeconds}s");
        },
        onReset: () =>
        {
            Console.WriteLine("Circuit closed");
        },
        onHalfOpen: () =>
        {
            Console.WriteLine("Circuit half-open, testing...");
        }
    );
```

---

### Usage with HttpClient

```csharp
public async Task<string> GetCreditScoreAsync()
{
    return await circuitBreaker.ExecuteAsync(async () =>
    {
        var response = await _httpClient.GetAsync("https://credit-bureau/api/score");

        response.EnsureSuccessStatusCode();

        return await response.Content.ReadAsStringAsync();
    });
}
```

---

# 🧩 Production-Grade Enhancements

In real systems, circuit breaker is **never used alone**:

### Combine with:

#### 1. Retry

```csharp
Policy.WrapAsync(retryPolicy, circuitBreakerPolicy);
```

#### 2. Timeout

* Prevent long waits

#### 3. Bulkhead Isolation

* Limit concurrent calls to external service

#### 4. Fallback

```csharp
Policy<string>
    .Handle<Exception>()
    .FallbackAsync("DEFAULT_SCORE");
```

---

# 🏗️ Real Architecture Placement

```
API Gateway / Service
        |
   Circuit Breaker
        |
 External Service (Credit Bureau / Payment / KYC)
```

---

# ⚠️ Trade-offs (Interview Gold)

### Pros

* Prevents cascading failures
* Improves system stability
* Reduces latency during outages

### Cons

* Temporary denial even after recovery
* Requires tuning thresholds carefully
* Adds complexity

---

# 💡 Key Interview Punchline

> "Circuit breaker is about failing fast and protecting the system, not fixing the failure. It ensures resilience by isolating unstable dependencies."


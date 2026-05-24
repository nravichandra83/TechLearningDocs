## Question:
Give me a real production incident walkthrough for the perfromance assessment for Latency observed in API.

## Answer:
Alright—let’s walk through a **realistic production incident** the way a senior engineer / architect would handle it. I’ll keep it grounded in .NET + microservices since that’s your space.

---

# 🚨 Incident: “API is slow, CPU is low”

### 🧾 Context

* .NET Core Web API (Order Service)
* Uses:

  * SQL Server
  * External Payment API
  * Redis cache
* Hosted in Kubernetes
* Traffic spike during sale

---

# ⏱️ Step 0: Alert triggers

From Application Insights:

* 🚨 Response time: **200ms → 8 seconds**
* ❗ Failure rate: normal (no errors)
* 📉 CPU: **~20% (low)**
* 📈 Requests/sec: normal

👉 First instinct:

> “System is not failing… it's waiting”

---

# 🧠 Step 1: Classify using your matrix

| CPU | Memory | Behavior     |
| --- | ------ | ------------ |
| low | normal | high latency |

👉 Bucket:
**Thread starvation / blocking / dependency wait**

---

# 🔍 Step 2: Check dependencies (quick win)

From App Insights:

* SQL duration → normal ✅
* Redis → normal ✅
* External Payment API → **not called yet (later step)**

👉 So issue is **inside API before dependencies**

---

# 📊 Step 3: Check ThreadPool health

Using dotnet-counters:

```bash
dotnet-counters monitor System.Runtime -p <pid>
```

### Observations:

* `threadpool-thread-count` → increasing slowly 📈
* `threadpool-queue-length` → growing ⚠️
* `completed-items-count` → flat

👉 🔥 Bingo:

> Requests are queued → threads not available

---

# 🧪 Step 4: Take memory dump during slowness

Using dotnet-dump:

```bash
dotnet-dump collect -p <pid>
```

---

# 🔬 Step 5: Analyze dump

```bash
dotnet-dump analyze dump.dmp
clrstack -all
```

---

## 👀 What we found

Many threads stuck here:

```csharp
System.Threading.Tasks.Task`1.GetResultCore()
System.Threading.Tasks.Task`1.get_Result()
MyApp.Services.PaymentService.ProcessPayment()
```

---

### 🔥 That’s suspicious:

We search code:

```csharp
public async Task<OrderResult> PlaceOrder(Order order)
{
    var paymentResult = _paymentService.ProcessPayment(order).Result; // ❌
    ...
}
```

---

# 💣 Root Cause

### ❗ Hidden sync-over-async

* `.Result` blocks thread
* Under load:

  * Threads get blocked
  * ThreadPool slowly adds threads
  * Requests queue up

👉 Classic **ThreadPool starvation**

---

# 🧠 Why CPU stayed LOW?

Because:

* Threads were **waiting**, not executing
* No heavy computation

---

# 🛠 Step 6: Fix

### ✅ Fix code

```csharp
public async Task<OrderResult> PlaceOrder(Order order)
{
    var paymentResult = await _paymentService.ProcessPayment(order); // ✅
}
```

---

### ✅ Also audited entire codebase for:

* `.Result`
* `.Wait()`
* `GetAwaiter().GetResult()`

---

# 📈 Step 7: Post-fix metrics

After deployment:

* Response time: **8s → 250ms** ✅
* ThreadPool queue: **0** ✅
* CPU: slight increase (healthy) ✅

---

# 🧠 But here’s the twist (real-world depth)

You might think:

> “Okay problem solved”

But in **real production**, we found **another layer**

---

# 🔁 Secondary Issue (often happens)

Even after fix:

* Latency spikes still occasionally

---

## 🔍 Investigation

Tracing showed:

* Payment API calls sometimes slow (2–3 sec)

---

## 💣 Root cause #2

* No timeout
* No retry policy
* No circuit breaker

---

## 🛠 Fix #2

Using Polly:

```csharp
.AddPolicyHandler(Policy.TimeoutAsync<HttpResponseMessage>(2))
.AddPolicyHandler(Policy.Handle<HttpRequestException>()
    .WaitAndRetryAsync(3, retry => TimeSpan.FromMilliseconds(200)));
```

---

# 🧠 Final Architecture Fix

We improved system:

### ✅ Before

* Sync-over-async
* No resilience

### ✅ After

* Fully async
* Resilient HTTP calls
* Timeouts + retries + fallback

---

# 📌 Key Learnings (this is what interviewers love)

### 1. Async alone ≠ safe

> Hidden blocking kills scalability

---

### 2. CPU low ≠ healthy

> Could mean threads are waiting

---

### 3. Always confirm with data

* Counters
* Dumps
* Traces

---

### 4. Production issues are layered

> Fix one → uncover next

---

# 🧭 How YOU should narrate this in interview

Structure like this:

> “We had a production incident where latency increased but CPU was low.
> We suspected thread starvation, confirmed via thread pool counters and dump analysis.
> Found sync-over-async (`.Result`) causing blocked threads.
> Fixed by making code fully async.
> Then identified dependency slowness and added resilience patterns.”

---

# 🚀 If you want next level

I can simulate:

* A **deadlock incident walkthrough**
* A **memory leak investigation**
* A **high CPU debugging case**
* Or give you **mock interview questions based on this**

Just tell me 👍
---

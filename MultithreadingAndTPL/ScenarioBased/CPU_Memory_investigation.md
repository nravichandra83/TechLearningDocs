## Question
Stimulate the below each with code example then how to access at real time (like memory dumpts etc) and analyze the issue. Give me pointers to look at and then analyze it further. Also talk about confirming the issue and fixing it along with testing strategy.
A deadlock incident walkthrough
A memory leak investigation
A high CPU debugging case

## Answer
---
Perfect—this is **architect-level debugging practice**. I’ll simulate each scenario like a **real production incident lab**:

For each:

1. 💣 Repro code (how issue happens)
2. 🔍 What you see in production
3. 🛠 How to capture (dump, counters, etc.)
4. 🧪 How to analyze
5. ✅ How to confirm root cause
6. 🔧 Fix
7. 🧪 Testing strategy

---

# 💀 1. DEADLOCK INCIDENT WALKTHROUGH

---

## 💣 Repro Code (classic async deadlock)

```csharp
public class DeadlockService
{
    public string GetData()
    {
        return GetDataAsync().Result; // ❌ blocking
    }

    public async Task<string> GetDataAsync()
    {
        await Task.Delay(1000);
        return "Done";
    }
}
```

Or worse (lock deadlock):

```csharp
lock (_lock1)
{
    lock (_lock2)
    {
        // thread 1
    }
}

// thread 2
lock (_lock2)
{
    lock (_lock1)
    {
    }
}
```

---

## 🔍 Production Symptoms

* CPU: LOW
* Requests: STUCK (never completes)
* Thread count: stable
* No errors ❗

---

## 🛠 Capture in Production

### Take dump:

```bash
dotnet-dump collect -p <pid>
```

---

## 🧪 Analyze

```bash
dotnet-dump analyze dump.dmp
threads
clrstack -all
```

---

## 👀 What to look for

* Threads waiting on each other:

```
Thread A waiting for lock held by Thread B  
Thread B waiting for lock held by Thread A
```

* Or:

```
Task.Wait()
GetResult()
```

---

## 🧠 Key Insight

> Deadlock = circular wait
> Threads are permanently blocked

---

## ✅ Confirm

* Same threads stuck across multiple dumps
* No progress over time
* No CPU usage

---

## 🔧 Fix

* Remove `.Result` / `.Wait()`
* Use async end-to-end
* Avoid nested locks
* Use lock ordering

---

## 🧪 Testing Strategy

* Use stress test (parallel requests)
* Add timeout detection
* Use tools like:

  * Parallel.For simulation
* Add logging around locks

---

# 🧠 2. MEMORY LEAK INVESTIGATION

---

## 💣 Repro Code

```csharp
public static List<byte[]> cache = new();

public void Leak()
{
    cache.Add(new byte[10_000_000]); // 10MB leak
}
```

Or event leak:

```csharp
public class Leaky
{
    public static event Action OnSomething;

    public void Subscribe()
    {
        OnSomething += () => Console.WriteLine("Leak");
    }
}
```

---

## 🔍 Production Symptoms

* Memory keeps increasing 📈
* CPU: normal or slightly high
* Eventually:

  * OOM crash
  * GC pauses increase

---

## 🛠 Capture

```bash
dotnet-dump collect -p <pid>
```

---

## 🧪 Analyze

```bash
dotnet-dump analyze dump.dmp
```

### Commands:

```bash
dumpheap -stat
```

👉 Shows object types consuming memory

---

### Drill deeper:

```bash
dumpheap -type System.Byte[]
```

```bash
gcroot <object-address>
```

---

## 👀 What to look for

* Large objects (`byte[]`, `string`)
* Objects not getting collected
* Roots holding references:

  * static fields
  * caches
  * events

---

## 🧠 Key Insight

> Leak = object is still referenced, so GC cannot collect

---

## ✅ Confirm

* Multiple dumps → same objects retained
* Memory keeps growing
* GC runs but memory not freed

---

## 🔧 Fix

* Remove static references
* Use weak references if needed
* Limit cache size (LRU)
* Unsubscribe events

---

## 🧪 Testing Strategy

* Long-running load test
* Monitor memory trend
* Use:

  * dotnet-counters (GC heap size)
* Validate memory stabilizes

---

# 🔥 3. HIGH CPU DEBUGGING CASE

---

## 💣 Repro Code

```csharp
public void HighCpu()
{
    while (true) // ❌ tight loop
    {
    }
}
```

Or inefficient logic:

```csharp
public void BadAlgorithm()
{
    var list = Enumerable.Range(1, 1_000_000).ToList();

    foreach (var item in list)
    {
        list.Contains(item); // O(n²)
    }
}
```

---

## 🔍 Production Symptoms

* CPU: 90–100% 🔥
* Requests slow
* Threads in RUNNING state

---

## 🛠 Capture

### Option 1: counters

```bash
dotnet-counters monitor System.Runtime -p <pid>
```

---

### Option 2: trace

```bash
dotnet-trace collect -p <pid>
```

---

## 🧪 Analyze

Open trace in PerfView or similar

---

## 👀 What to look for

* Methods consuming most CPU
* Hot paths:

  * loops
  * serialization
  * LINQ
  * regex

---

## 🧠 Key Insight

> CPU issue = threads are actively executing inefficient work

---

## ✅ Confirm

* Same method dominating CPU samples
* Repro locally with same input

---

## 🔧 Fix

* Optimize algorithm (O(n²) → O(n))
* Add caching
* Reduce unnecessary loops
* Use async if I/O bound

---

## 🧪 Testing Strategy

* Benchmark before/after
* Use load testing
* Measure:

  * CPU %
  * response time

---

# 🧭 FINAL: HOW TO THINK LIKE AN ARCHITECT

---

## 🧠 Pattern Recognition Table

| Symptom           | Root Cause          |
| ----------------- | ------------------- |
| CPU low + stuck   | deadlock / blocking |
| Memory increasing | leak                |
| CPU high          | inefficient code    |

---

## 🔁 Universal Debug Flow

1. Observe metrics (CPU, memory, latency)
2. Classify problem type3. Capture evidence (dump / trace)
4. Analyze (threads / heap / CPU)
5. Confirm with data
6. Fix
7. Validate with load test

---

# 🚀 If you want next level (highly recommended)

I can simulate a **full interview round** where:

* I give you symptoms
* You debug step-by-step
* I challenge your assumptions like a real interviewer

Or I can give:

* **Cheat sheet for dotnet-dump commands**
* **Real dump file walkthrough (deep)**

Just tell me 👍

--- 
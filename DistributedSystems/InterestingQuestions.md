# Advanced Distributed Systems & Architecture Interview Topics

---

# 1. Distributed Transactions & Consistency Models

At enterprise scale, **ACID transactions across microservices** don't work. Architects must design for **eventual consistency**.

---

## 1.1 How do you manage distributed transactions across microservices without distributed locks (2PC)?

### Expected Answer

Discuss the **Saga Pattern** and compare:

### Orchestration-Based Saga

- Central workflow manager controls the sequence.
- Services remain unaware of each other.
- Easier monitoring and debugging.
- Explicit workflow state.
- Examples:
  - Temporal
  - Camunda
  - Zeebe
  - Azure Durable Functions

**Pros**

- Easier to understand
- Centralized retry logic
- Easier compensation
- Better visibility

**Cons**

- Orchestrator becomes critical infrastructure.
- Must be highly available.
- Possible bottleneck if poorly designed.

---

### Choreography-Based Saga

Each service reacts to events and publishes the next event.

```
Order Created
      ↓
Inventory Reserved
      ↓
Payment Completed
      ↓
Shipping Initiated
```

**Pros**

- Fully decentralized
- Highly scalable
- Loosely coupled

**Cons**

- Harder to visualize workflow
- Circular dependencies may emerge
- Difficult debugging
- Event storms possible

---

### Compensating Transactions

Instead of rollback:

```
Reserve Inventory
↓
Payment Failed
↓
Release Inventory
```

Every completed step has an opposite compensating action.

---

## 1.2 How do you guarantee Idempotency in a high-throughput event consumer where retries can deliver duplicate events?

### Expected Answer

Move beyond database unique constraints.

Techniques include:

### 1. Idempotency Keys

```
EventId = GUID

If EventId exists
    Ignore
Else
    Process
```

---

### 2. Redis Deduplication

```
SET Event123 Processed TTL=24hrs

Exists?
    Ignore
```

Benefits:

- Fast
- Distributed
- Auto cleanup using TTL

---

### 3. Database Deduplication Table

```
ProcessedEvents

EventId
ProcessedTime
```

Useful for permanent deduplication.

---

### 4. State Machine Validation

Example:

```
Current Order State

Delivered

Incoming Event

Shipped
```

Ignore because state already advanced.

---

### 5. Outbox Pattern

Producer writes:

- Business Data
- Outbox Event

Inside one local transaction.

Separate worker publishes to Kafka.

Guarantees exactly-once publishing from the producer.

---

## 1.3 How do you handle Read-Your-Own-Writes consistency in CQRS?

### Problem

```
Write DB updated

↓

Read DB still catching up

↓

User refreshes

↓

Old data shown
```

### Strategies

#### Route Reads to Primary

Immediately after write:

```
User

↓

Primary DB

↓

Replica later
```

---

#### Version-Based Reads

Client stores:

```
Version = 105
```

Read model waits until projection reaches:

```
>=105
```

---

#### Poll Read Model

```
Retry every

100 ms

until timeout
```

---

#### Sticky Sessions

Temporarily pin user to primary database.

---

# 2. Advanced Architectural Patterns (CQRS & Event Sourcing)

---

## 2.1 When would you choose Event Sourcing over CRUD?

### Benefits

- Complete audit history
- Time-travel debugging
- Replay events
- Temporal analytics
- Event replay after bugs
- Natural event-driven integration

---

### Hidden Costs

#### Schema Evolution

Events must remain readable for years.

Old versions cannot simply disappear.

---

#### Snapshotting

Without snapshots:

```
1 million events

↓

Replay on startup
```

Very slow.

Instead:

```
Snapshot

↓

Replay last 500 events
```

---

#### Eventual Consistency

Read model updates asynchronously.

Users may temporarily see stale data.

---

## 2.2 How do you reduce CQRS lag between write and read models?

### Improve Projection Performance

- Parallel consumers
- Kafka partitioning
- Batch writes

---

### Handle Poison Messages

```
Projection fails

↓

DLQ

↓

Continue processing
```

---

### UI Strategies

- Loading indicators
- Optimistic updates
- Refresh notifications
- Retry polling

---

# 3. Scalability, Partitioning & Ordering

---

## 3.1 How do you maintain ordering while scaling Kafka?

### Reality

Global ordering requires:

```
1 Topic

↓

1 Partition
```

Which limits throughput.

---

### Better Strategy

Partition by Aggregate Root

Example:

```
CustomerId

or

OrderId
```

Ordering becomes:

- Per customer
- Per order

instead of global.

---

### Alternative

Logical sequence numbers.

Consumers reorder temporarily before processing.

---

## 3.2 How do you handle Hot Partitions?

Example:

One celebrity generates:

```
500K events/sec
```

All routed to one partition.

---

### Solutions

#### Salted Keys

Instead of:

```
Customer123
```

Use:

```
Customer123-A

Customer123-B

Customer123-C
```

Distributes load.

---

#### Dynamic Partitioning

Increase partitions during spikes.

---

#### Caching

Producer buffers repetitive updates.

---

#### Rate Limiting

Prevent single producer from overwhelming Kafka.

---

## 3.3 What is Backpressure?

Producer generates faster than consumer processes.

```
Producer

1000/sec

↓

Consumer

100/sec
```

Queue grows forever.

---

### Kafka

Consumers pull data.

Natural backpressure.

---

### HTTP/Webhooks

Need:

- Rate limiting
- Circuit breakers
- Retry queues
- Buffer overflow strategies

Overflow strategies:

- Drop messages
- Spill to disk
- Slow producer

---

# 4. Enterprise Governance, Schema Evolution & Operations

---

## 4.1 How do you manage breaking schema changes?

### Schema Registry

Examples:

- Confluent Schema Registry
- Azure Schema Registry

Compatibility modes:

- Backward
- Forward
- Full

---

### Consumer-Driven Contracts

Consumers define expectations.

Producer validates before deployment.

---

### CloudEvents

Standard envelope containing:

- Event Id
- Event Type
- Source
- Correlation Id
- Timestamp
- Trace Context

---

## 4.2 How do you build Multi-Region Active-Active Architecture?

Challenges:

- Replication lag
- Split brain
- Conflicting updates

---

### Conflict Resolution

#### Last Write Wins (LWW)

Simple but may lose data.

---

#### Vector Clocks

Track causality between updates.

---

#### CRDTs (Conflict-Free Replicated Data Types)

Allow conflict-free merging across regions.

Useful for:

- Counters
- Sets
- Collaborative systems

---

## 4.3 Disaster Recovery (DR)

Goals:

### RPO

Maximum acceptable data loss.

### RTO

Maximum acceptable downtime.

---

### Kafka DR

MirrorMaker 2

```
Primary Cluster

↓

Mirror

↓

Secondary Cluster
```

---

### Additional Strategies

- Replicate consumer offsets
- Backup state stores
- Automated failover
- Offset translation after recovery

---

# 5. Observability & Debugging Distributed Systems

---

## 5.1 How do you trace transactions across asynchronous microservices?

Use:

- OpenTelemetry
- W3C Trace Context

Propagate:

```
traceparent

correlationId

causationId
```

inside every event.

---

### Log Correlation

Centralized platforms:

- ELK
- Grafana
- Datadog
- Azure Monitor

Can reconstruct:

```
API

↓

Kafka

↓

Inventory

↓

Payment

↓

Shipping

↓

Notification
```

using the same trace.

---

## 5.2 How do you design an effective Dead Letter Queue (DLQ) strategy?

Avoid simply storing failed events.

---

### Robust DLQ Pipeline

```
Failure

↓

Retry

↓

Exponential Backoff

↓

Jitter

↓

DLQ

↓

Alert

↓

Engineer Review

↓

Replay
```

---

### Best Practices

#### Alerting

Trigger alerts when DLQ exceeds thresholds.

---

#### Retry Policies

Use:

- Exponential backoff
- Random jitter

to avoid retry storms.

---

#### Poison Pill Detection

Identify permanently failing messages.

Prevent infinite retry loops.

---

#### Replay Tooling

Provide internal tools to:

- Inspect failed messages
- Edit payloads (if safe)
- Replay events
- Audit replay history

Safely reprocess events after fixes.

---

# Key Takeaways

Senior architects should demonstrate expertise in:

- Distributed Transactions & Saga Patterns
- Eventual Consistency
- CQRS & Event Sourcing
- Kafka Partitioning & Ordering
- Idempotency Patterns
- Hot Partition Mitigation
- Backpressure Handling
- Schema Evolution & Governance
- Multi-Region Active-Active Design
- Disaster Recovery (RPO/RTO)
- OpenTelemetry & Distributed Tracing
- Dead Letter Queue Design & Automated Remediation
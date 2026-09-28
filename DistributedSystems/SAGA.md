This is one of the **most important system design topics** for senior engineers, architects, and principal engineers.

Most interviewers don't ask **"What is Saga?"**
Instead they ask:

> "How would you maintain consistency across multiple microservices when one step fails?"

If you can explain Saga clearly, you'll stand out.

---

# The Problem Saga Solves

Let's first understand **why Saga exists**.

Imagine an e-commerce website.

Customer clicks

> Buy Now

The following things happen:

```
Place Order
      |
      V
Reserve Inventory
      |
      V
Process Payment
      |
      V
Book Shipment
      |
      V
Send Email
```

Looks simple.

But these are **5 different microservices**.

```
Order Service
Inventory Service
Payment Service
Shipping Service
Notification Service
```

Each service has **its own database.**

```
Order DB
Inventory DB
Payment DB
Shipping DB
Notification DB
```

Microservices **never share one database**.

---

## Traditional Transaction

In a monolith we simply write

```
BEGIN TRANSACTION

Insert Order

Decrease Inventory

Charge Payment

Commit
```

If anything fails

```
ROLLBACK
```

Everything returns to previous state.

Simple.

---

# Why doesn't this work in Microservices?

Because every service owns its database.

```
Order DB
Inventory DB
Payment DB
```

You cannot start one SQL transaction across all databases.

This is called

**Distributed Transaction**

Historically solved using

```
2 Phase Commit (2PC)
```

---

# Why not use 2PC?

Suppose

```
Coordinator

Order

Inventory

Payment
```

Coordinator asks

```
Can you commit?
```

Everyone replies

```
YES
```

Coordinator says

```
Commit
```

But suddenly

Payment service crashes.

Now

```
Order committed

Inventory committed

Payment not committed
```

Now coordinator waits.

Locks remain.

Other transactions cannot proceed.

Huge scalability problem.

---

Large companies almost never use 2PC.

Instead they use

**Eventual Consistency**

---

# Eventual Consistency

Instead of

> Everything succeeds together

We say

> Every service eventually reaches the correct state.

That is where Saga comes in.

---

# What is Saga?

A Saga is simply

> A sequence of local transactions.

Each service performs

1. its own database transaction
2. publishes an event

Example

```
Order Created

↓

Inventory Reserved

↓

Payment Completed

↓

Shipment Created
```

Every service commits independently.

If something fails

Instead of rollback

we execute

**Compensating Transactions**

---

Think of it like

```
Undo
```

rather than

```
Rollback
```

---

# Analogy — Planning a Wedding

Imagine planning a wedding.

You

Book Hall

↓

Book Catering

↓

Book Photographer

↓

Book Music

Each booking is confirmed separately.

If the photographer cancels

Can you rollback hall booking?

No.

Instead

You manually

Cancel Hall

Cancel Catering

Refund Music

These are

**Compensating actions**

Exactly Saga.

---

# Another Analogy — Trip Booking

Suppose you book

```
Flight

Hotel

Taxi
```

Everything succeeds except

Hotel unavailable.

Can airline rollback automatically?

No.

Instead

```
Cancel Flight

Cancel Taxi
```

This is compensation.

---

# Saga Flow

```
Create Order

↓

Reserve Inventory

↓

Take Payment

↓

Create Shipment
```

Now suppose payment fails.

Instead of SQL rollback

Saga executes

```
Release Inventory

Cancel Order
```

Notice

Inventory was actually committed.

Now another transaction undoes it.

---

# What is a Compensating Transaction?

Normal transaction

```
Reserve Inventory
```

Compensation

```
Release Inventory
```

Normal

```
Debit Wallet
```

Compensation

```
Credit Wallet
```

Normal

```
Book Seat
```

Compensation

```
Cancel Seat
```

Not all operations are perfectly reversible (for example, sending an email), so compensation must be designed carefully.

---

# Two Ways to Implement Saga

There are two major approaches.

```
Saga

├── Choreography

└── Orchestration
```

These are the approaches interviewers usually compare.

---

# 1. Choreography

Nobody is in charge.

Every service listens to events.

Imagine a group dance.

Nobody says

```
Now move.
```

Everyone already knows what to do.

Exactly choreography.

---

Example

```
Order Service
```

publishes

```
OrderCreated
```

Inventory listens.

```
Inventory Reserved
```

Inventory publishes

```
InventoryReserved
```

Payment listens.

```
PaymentCompleted
```

Payment publishes

```
PaymentSucceeded
```

Shipping listens.

Entire flow

```
Order

↓

Inventory

↓

Payment

↓

Shipping
```

No central controller.

---

## Diagram

```text
               OrderCreated
Order ------------------------>

                 Inventory
                     |
                     | InventoryReserved
                     V
                 Payment
                     |
                     | PaymentSucceeded
                     V
                 Shipping
```

Every service only knows

> Which event should I consume?

---

### Advantages

Very loosely coupled.

Easy to add new subscribers.

For example

```
Analytics Service
```

can simply subscribe.

No existing service changes.

Great scalability.

---

### Disadvantages

Flow becomes hard to follow.

Imagine 30 services.

```
OrderCreated

↓

InventoryReserved

↓

PaymentDone

↓

CouponApplied

↓

LoyaltyUpdated

↓

FraudChecked

↓

InvoiceGenerated
```

Who started this?

Where are we?

Hard to answer.

Debugging becomes difficult.

---

## Failure Scenario

Payment fails.

Payment emits

```
PaymentFailed
```

Inventory listens.

```
ReleaseInventory
```

Order listens.

```
CancelOrder
```

Again

No central coordinator.

---

# 2. Orchestration

Now imagine a conductor leading an orchestra.

```
Violin

Piano

Drums
```

They don't coordinate with each other.

The conductor tells each one when to play.

That's orchestration.

---

Instead of services talking directly,

everything talks to

```
Saga Orchestrator
```

---

Flow

```
Customer

↓

Orchestrator

↓

Order Service

↓

Inventory Service

↓

Payment

↓

Shipping
```

The orchestrator says

```
Create Order
```

Order replies

```
Done
```

Then

```
Reserve Inventory
```

Inventory replies

```
Done
```

Then

```
Take Payment
```

Payment replies

```
Failed
```

Now orchestrator decides

```
Release Inventory

↓

Cancel Order
```

---

## Diagram

```text
          +----------------------+
          |   Saga Orchestrator  |
          +----------------------+
             |        |       |
             V        V       V
          Order   Inventory Payment
             ^        ^       ^
             |        |       |
          Result   Result   Result
```

The orchestrator knows the complete workflow.

---

# Example Flow

```
1 Create Order

↓

2 Reserve Inventory

↓

3 Process Payment

↓

4 Ship Product
```

Suppose payment fails.

Orchestrator executes

```
Release Inventory

↓

Cancel Order
```

Everything is coordinated centrally.

---

# Advantages

Easy to visualize the business process.

Simple debugging.

Single place for retries.

Simple timeout handling.

Good for long business workflows.

---

# Disadvantages

The orchestrator becomes critical infrastructure. If it is unavailable, new saga executions may pause until it recovers, so it must be made highly available.

Slightly tighter coupling because the orchestrator understands the workflow.

---

# Comparison

| Feature                   | Choreography                | Orchestration                           |
| ------------------------- | --------------------------- | --------------------------------------- |
| Central controller        | ❌ No                        | ✅ Yes                                   |
| Communication             | Events between services     | Commands from orchestrator              |
| Coupling                  | Loose                       | Moderate                                |
| Scalability               | Excellent                   | Excellent (with HA orchestrator)        |
| Debugging                 | Difficult                   | Easy                                    |
| Workflow visibility       | Poor                        | Excellent                               |
| Easy to add new listeners | Yes                         | Sometimes requires orchestrator changes |
| Best for                  | Simple event-driven systems | Complex business workflows              |

---

# When Should You Use Which?

### Use Choreography when

* Few services participate.
* Business flow is simple.
* Services should remain highly independent.
* New event consumers are added frequently.
* Analytics, notifications, auditing, and projections are common examples.

Example:

```
UserRegistered

↓

Email

↓

Analytics

↓

CRM

↓

Marketing
```

No service needs to know about the others.

---

### Use Orchestration when

* Many services participate.
* Complex business rules exist.
* You need retries, timeouts, or human approval steps.
* You want a single place to observe progress.

Example:

```
Loan Approval

↓

Credit Check

↓

Fraud Check

↓

Risk Engine

↓

Manager Approval

↓

Disbursement
```

This is much easier with an orchestrator.

---

# Interview Answer (2-Minute Version)

> "In microservices, we can't rely on distributed ACID transactions because each service owns its own database, and protocols like 2PC don't scale well due to locking and coordinator failures. Instead, we use the Saga pattern, where each service executes a local transaction and, if a later step fails, compensating transactions undo the previously completed business actions. Sagas can be implemented using choreography, where services communicate through events without a central controller, or orchestration, where a dedicated orchestrator coordinates the workflow and triggers compensation when needed. I generally prefer choreography for simple event-driven processes and orchestration for complex business workflows because it provides better visibility, centralized retry logic, and easier debugging."

---

# Real-World Usage

| Company / System              | Common Approach      | Reason                                                                       |
| ----------------------------- | -------------------- | ---------------------------------------------------------------------------- |
| Amazon order processing       | Mostly orchestration | Complex order lifecycle, refunds, returns, inventory management              |
| Uber ride lifecycle           | Orchestration        | Driver assignment, payment, cancellations, notifications                     |
| Food delivery (Swiggy/Zomato) | Hybrid               | Order workflow is orchestrated; analytics and notifications are event-driven |
| Banking/payment workflows     | Orchestration        | Strict business process, compensation, auditability                          |
| User registration ecosystems  | Choreography         | Independent consumers like email, analytics, CRM, and marketing              |

In practice, many organizations combine both patterns: an **orchestrator** manages the core business transaction, while services also publish **domain events** that other independent consumers (analytics, search indexing, notifications, auditing) subscribe to. This hybrid approach provides strong control over critical workflows while preserving the flexibility of event-driven architecture.

**Human-in-the-loop (HITL)** in Agentic AI means the agent can autonomously perform a workflow, but **pauses at a predefined decision point where a human must review, approve, reject, or provide additional information before the workflow continues.**

For a refund workflow, for example:

```text
Customer requests refund
        ↓
Agent validates order
        ↓
Agent checks refund policy
        ↓
Agent calculates refund
        ↓
     ┌──────────────┐
     │ Human review │  ← HITL
     └──────────────┘
        ↓
   Supervisor approves
        ↓
Agent calls Payment API
        ↓
Refund completed
        ↓
Customer notified
```

## 1. What exactly happens in LangGraph?

This is where LangGraph is particularly useful.

You can model the workflow as:

```text
START
  ↓
validate_request
  ↓
check_policy
  ↓
calculate_refund
  ↓
human_approval
  ↓
process_refund
  ↓
notify_customer
  ↓
END
```

The important part is that **`human_approval` isn't just a normal function that waits**.

The graph can **interrupt execution**, persist the current state/checkpoint, and resume later using the same workflow/thread.

Conceptually:

```python
def refund_workflow(state):

    state = validate_request(state)
    state = check_policy(state)
    state = calculate_refund(state)

    # Pause here
    interrupt({
        "type": "refund_approval",
        "refund_amount": state["refund_amount"],
        "reason": state["reason"]
    })

    state = process_refund(state)
    state = notify_customer(state)

    return state
```

The key idea for an interview is:

> **LangGraph separates workflow state from workflow execution. When an interrupt occurs, the current graph state is checkpointed against a thread/run identifier. The graph can later resume from that checkpoint with human input.**

So you don't need to keep a Python process sitting there waiting for the supervisor.

---

# 2. How does LangGraph "preserve the task"?

This is one of the most important concepts to understand.

Imagine:

```text
Thread ID: REFUND-12345
```

The graph has reached:

```text
calculate_refund
       ↓
      HITL
```

The persisted state might look conceptually like:

```json
{
  "thread_id": "REFUND-12345",
  "order_id": "ORD-9821",
  "customer_id": "C123",
  "refund_amount": 2500,
  "currency": "INR",
  "reason": "Damaged product",
  "policy_result": "Eligible",
  "risk_score": 0.08,
  "approval_required": true,
  "status": "WAITING_FOR_APPROVAL",
  "current_step": "human_approval"
}
```

The important thing is that **the state is durable**.

The application can therefore return:

```text
HTTP 202 Accepted

Refund request submitted.
Waiting for supervisor approval.
Reference: REFUND-12345
```

The server doesn't need to hold an HTTP request open for 30 minutes.

Later:

```text
Supervisor clicks APPROVE
          ↓
Backend receives approval
          ↓
Find thread REFUND-12345
          ↓
Resume LangGraph
          ↓
process_refund()
          ↓
notify_customer()
```

---

# 3. Customer and supervisor should see different things

This is an important production architecture distinction.

You generally **shouldn't expose the LangGraph state directly to the customer**.

Instead, create an **application-level workflow/task model**.

For example:

```text
                    LangGraph
                       │
                       │ state/checkpoint
                       ↓
              Workflow/Task Store
                       │
             ┌─────────┴─────────┐
             ↓                   ↓
       Customer UI         Supervisor UI
```

Your application database could have:

### `RefundRequest`

| Field | Example |
|---|---|
| RefundId | REFUND-12345 |
| OrderId | ORD-9821 |
| CustomerId | C123 |
| Amount | ₹2,500 |
| Status | Pending Approval |
| CurrentStage | Supervisor Review |
| AssignedTo | Supervisor-42 |
| CreatedAt | ... |
| UpdatedAt | ... |
| LangGraphThreadId | REFUND-12345 |
| ApprovalRequired | true |

This gives your UI a clean business representation.

---

# 4. What does the customer see?

The customer doesn't need to know:

> "LangGraph is currently suspended at node `human_approval`."

Instead show something like:

### Refund status

```text
Refund #REFUND-12345

Order: ORD-9821
Refund amount: ₹2,500

✓ Refund request received
✓ Order and eligibility verified
✓ Refund amount calculated
● Waiting for approval
○ Refund being processed
○ Refund completed

Current status:
Waiting for supervisor approval

We'll notify you once the approval is completed.
```

This is a **business-friendly projection of the agent's state**.

You could also show:

```text
Refund requested
      ↓
Eligibility verified
      ↓
Supervisor approval
      ↓
Payment processing
      ↓
Refund completed
```

---

# 5. What does the supervisor see?

The supervisor needs much more information.

For example:

### Refund Approval Dashboard

```text
┌───────────────────────────────────────────────┐
│ Refund Approval                               │
├───────────────────────────────────────────────┤
│ Refund ID     REFUND-12345                    │
│ Order         ORD-9821                        │
│ Customer      John Doe                        │
│ Amount        ₹2,500                          │
│ Reason        Product damaged                 │
│                                               │
│ Agent Assessment                              │
│ ────────────────────────────────────────────  │
│ Policy        Eligible                        │
│ Order age     12 days                         │
│ Risk score    Low                             │
│ Evidence      ✓ Customer uploaded photos      │
│                                               │
│ Agent recommendation                          │
│ ────────────────────────────────────────────  │
│ Recommend APPROVE                             │
│                                               │
│ [ APPROVE ]       [ REJECT ]                  │
│                                               │
│ Comments: [____________________________]      │
└───────────────────────────────────────────────┘
```

The supervisor isn't really interacting with "LangGraph."

They're interacting with **your business application**.

The application translates:

```text
LangGraph state
      ↓
Business workflow state
      ↓
Supervisor UI
```

---

# 6. What happens when supervisor clicks Approve?

This is the interesting part.

Suppose:

```text
REFUND-12345
```

is currently suspended.

Supervisor clicks:

```text
APPROVE
```

Your backend might receive:

```http
POST /refunds/REFUND-12345/approval
```

with:

```json
{
  "decision": "APPROVED",
  "approvedBy": "SUPERVISOR-42",
  "comments": "Verified damaged product"
}
```

Your backend then:

```text
Find RefundRequest
        ↓
Find LangGraph Thread ID
        ↓
Load checkpoint
        ↓
Inject human decision
        ↓
Resume graph
```

The graph continues:

```text
human_approval
       ↓
process_refund
       ↓
payment_gateway
       ↓
update_refund_status
       ↓
notify_customer
       ↓
END
```

---

# 7. What if supervisor rejects?

Exactly the same mechanism.

```text
human_approval
       ↓
REJECT
       ↓
update status = REJECTED
       ↓
generate customer explanation
       ↓
notify customer
       ↓
END
```

Or the supervisor could request additional information:

```text
                    ┌── APPROVE ──→ Process refund
                    │
Human approval ─────┼── REJECT ───→ Close request
                    │
                    └── MORE INFO → Customer
```

That's where agentic workflows become very powerful.

---

# 8. HITL isn't necessarily just "approval"

There are several patterns.

### Approval

```text
Agent → Human → Continue
```

Example:

> "Approve refund of ₹25,000?"

### Review/edit

```text
Agent → Human modifies proposed action → Continue
```

Example:

Agent proposes:

```text
Refund = ₹10,000
```

Supervisor changes it:

```text
Refund = ₹7,500
```

Then:

```text
Continue with ₹7,500
```

### Request information

```text
Agent → Human → Provide information → Continue
```

Example:

> "Customer identity cannot be verified. Please provide verification."

### Reject/terminate

```text
Agent → Human → Reject → End workflow
```

---

# 9. The architecture I'd recommend in an interview

For a production-grade refund system, I would describe it like this:

```text
                    Customer
                       │
                       ↓
                ┌──────────────┐
                │ API Gateway  │
                └──────┬───────┘
                       ↓
                Refund Service
                       │
                       ↓
                ┌──────────────┐
                │  LangGraph   │
                │    Agent     │
                └──────┬───────┘
                       │
            ┌──────────┴──────────┐
            ↓                     ↓
       Check Policy          Payment APIs
            │
            ↓
       HITL required
            │
            ↓
     Persist checkpoint
            │
            ↓
     Workflow DB / Store
            │
            ├──────────────→ Customer UI
            │
            └──────────────→ Supervisor UI
                                  │
                              APPROVE
                                  │
                                  ↓
                         Resume LangGraph
                                  │
                                  ↓
                           Process Refund
```

I'd actually add an **event/message broker** for production:

```text
Supervisor
    │
    ↓
Approval API
    │
    ↓
Approval Event
    │
    ↓
Queue / Kafka / Service Bus
    │
    ↓
Agent Worker
    │
    ↓
Resume LangGraph
```

This makes the system resilient if the agent worker is temporarily unavailable.

---

# 10. One very important distinction for interviews

Don't say:

> "LangGraph keeps the agent running until the human responds."

That's not the best mental model.

Say:

> **"LangGraph persists the graph state at the interruption point. The execution can stop, and when the human decision arrives, the application resumes the graph using the persisted checkpoint and workflow/thread identifier."**

That's a much stronger answer.

And then add:

> **"For a customer-facing application, I would not expose raw LangGraph state. I would maintain a business-level workflow/status model and project the agent state into customer and supervisor-specific views."**

That last sentence demonstrates **production architecture thinking**, rather than just LangGraph knowledge.

### The key mental model

```text
             AGENT
               │
               ↓
        ┌─────────────┐
        │ Agent State │
        └──────┬──────┘
               │
          HITL interrupt
               │
               ↓
       ┌────────────────┐
       │ Durable State  │
       │ + Checkpoint   │
       └───────┬────────┘
               │
       Human decision
               │
               ↓
        Resume execution
               │
               ↓
         Next node/tool
```

**Agent state is the technical mechanism; the workflow/status database and UI are the customer-facing representation.**

For your interview, this connects directly to **LangGraph state + checkpointing + interrupt/resume + durable execution + HITL + event-driven architecture**.
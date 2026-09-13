# Mwalimu AI

**An Intelligent Learning Companion for Kenyan Secondary Schools**

Mwalimu AI is an AI-supported learning platform designed to help secondary school students identify learning weaknesses, receive targeted support, practise concepts, and generate actionable learning data for teachers.

The MVP focuses on **Form 2 Biology** and is built around one core principle:

> **Student weakness → Diagnosis → AI learning → Assessment → Learning data → Teacher insight → Intervention**

Mwalimu AI supports **SDG 4 — Quality Education** by exploring how artificial intelligence and learning analytics can provide more personalized learning support while helping teachers identify where students need intervention.

---

## Project Status

**Version:** 0.1
**Stage:** MVP / Competition Prototype
**Primary Subject:** Form 2 Biology
**Primary SDG:** SDG 4 — Quality Education

The current objective is to build and validate a functional end-to-end prototype.

The MVP is intentionally narrow. Features that do not strengthen the core learning and teacher-intervention loop are considered secondary.

---

## The Problem

In a typical classroom, students do not understand every concept at the same pace.

A teacher may know the overall performance of a class through tests and assignments, but it can be difficult to continuously determine:

* which concepts individual students are struggling with;
* which misconceptions repeatedly appear;
* whether a student improved after receiving additional support;
* which topics are becoming class-wide learning gaps; and
* where teacher intervention would have the greatest impact.

At the same time, simply giving students access to a general-purpose AI chatbot does not automatically create measurable learning.

Mwalimu AI addresses this by connecting AI-assisted learning with structured assessment and learning analytics.

---

## Core Product Loop

The system is built around three connected loops.

### Student Loop

```text
Login
  ↓
Select Biology Topic
  ↓
Diagnostic Assessment
  ↓
Identify Weakness
  ↓
Learn with AI
  ↓
Practice
  ↓
Receive Feedback
  ↓
Complete Learning Session
```

### System Loop

```text
Student Activity
  ↓
Learning Events
  ↓
Structured Learning Data
  ↓
Analytics
  ↓
Teacher Insight
```

### Teacher Loop

```text
Login
  ↓
Select Class
  ↓
View Learning Data
  ↓
Identify Weak Topics
  ↓
Read AI Summary
  ↓
Receive Intervention Recommendation
```

Together, these implement the broader principle:

> **Teach → Measure → Understand → Intervene**

---

## MVP Features

### Student

Students will be able to:

* authenticate securely;
* access assigned Form 2 Biology content;
* select a topic;
* complete diagnostic questions;
* receive identified learning weaknesses;
* interact with an AI tutor;
* practise targeted questions;
* receive feedback;
* complete assessments; and
* view basic learning progress.

### Teacher

Teachers will be able to:

* authenticate securely;
* access authorized classes;
* view class learning analytics;
* identify weak topics and concepts;
* inspect authorized student learning activity;
* view structured AI-generated summaries; and
* receive suggested teaching interventions.

### Platform

The platform will:

* record structured learning events;
* calculate learning metrics;
* connect diagnostic and assessment performance;
* aggregate class-level learning patterns;
* provide structured analytics to the teacher AI layer; and
* maintain separation between deterministic assessment logic and generative AI assistance.

---

## AI Design Principles

Mwalimu AI uses artificial intelligence as a **learning-support and interpretation layer**, not as the sole authority over student performance.

Objective assessment should use structured questions and deterministic scoring wherever practical.

The AI tutor may:

* explain concepts;
* adapt explanations;
* provide examples;
* respond to student questions;
* guide students through difficult concepts; and
* support targeted practice.

The teacher AI may:

* interpret structured learning analytics;
* summarize learning patterns;
* identify notable weaknesses; and
* suggest possible interventions.

AI-generated output must not fabricate student performance or analytics.

Where objective answers can be evaluated deterministically, the application should not rely solely on an LLM to determine whether an answer is correct.

---

## Learning Event Model

Learning activity should produce structured events that can later be analyzed.

Examples include:

```text
diagnostic_started
diagnostic_answered
diagnostic_completed

tutor_session_started
tutor_interaction
tutor_session_completed

practice_answered

assessment_started
assessment_answered
assessment_completed
```

Events should contain enough structured information to answer useful educational questions such as:

* Which topic is weakest?
* Which concepts produce the most incorrect answers?
* Did performance improve after tutoring?
* Which students may require teacher intervention?
* Which learning gaps occur across the class?

The objective is not simply to record clicks.

The objective is to create **meaningful learning evidence**.

---

## Content Strategy

The initial content scope is:

**Kenyan Secondary School — Form 2 Biology**

Assessment content should be curated and reviewed rather than generated freely during assessment.

Structured content may include:

* topics;
* concepts;
* explanations;
* diagnostic questions;
* practice questions;
* assessment questions;
* correct answers; and
* explanations for answers.

Generative AI can support conversational learning around this structured content, but curated academic content remains the foundation of the MVP.

---

## Privacy and Student Data

Mwalimu AI follows a minimum-necessary-data approach.

For the MVP:

* use student identifiers where practical;
* avoid unnecessary personal information;
* do not collect addresses, photographs, or phone numbers unless genuinely required;
* restrict teachers to authorized student/class data;
* prevent cross-student data exposure;
* use synthetic or approved demonstration data for competition demonstrations; and
* establish appropriate consent procedures before collecting real data from minors.

Any real-world validation involving students must document:

* what data is collected;
* why it is collected;
* who can access it;
* how it is stored;
* how it is used; and
* how it can be deleted.

---

## Security

The MVP should implement reasonable security controls from the beginning, including:

* password hashing;
* authenticated sessions;
* role-based access control;
* school/class authorization;
* server-side validation;
* environment-based secret management;
* appropriate application logging; and
* protection against unauthorized access to student information.

API keys and production secrets must never be committed to the repository.

---

## Technology Stack

The initial architecture uses:

| Layer      | Technology                       |
| ---------- | -------------------------------- |
| Backend    | Python / FastAPI                 |
| Database   | PostgreSQL                       |
| ORM        | SQLAlchemy                       |
| Frontend   | Jinja2 / HTML / CSS / JavaScript |
| AI         | External LLM API                 |
| Deployment | Docker where practical           |

The architecture should maintain clear separation between:

```text
Presentation
Routes / API
Business Logic
Database Models
AI Services
Analytics
Configuration
Tests
```

The MVP should remain simple enough to build, understand, test, and demonstrate within the available development period.

---

## Planned Project Structure

The exact structure will be created incrementally during implementation.

```text
mwalimu-ai/
│
├── PROJECT_CONSTITUTION.md
├── README.md
├── .gitignore
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
│
├── app/
│   ├── core/
│   ├── models/
│   ├── routes/
│   ├── schemas/
│   ├── services/
│   ├── analytics/
│   ├── templates/
│   └── static/
│
├── tests/
│
└── scripts/
```

This structure may evolve during implementation, but changes should remain consistent with `PROJECT_CONSTITUTION.md`.

---

## Validation and Technology Readiness

A working local application alone does not demonstrate a high Technology Readiness Level.

Validation evidence should distinguish clearly between:

* implemented functionality;
* developer testing;
* controlled demonstrations;
* user testing;
* classroom or school validation; and
* production deployment.

Claims about Technology Readiness Level must be supported by documented evidence.

The project should not claim **TRL 6 or higher** solely because the software runs successfully in a local or hosted environment.

---

## Development Plan

### Day 1 — Foundation

Build the technical foundation:

* project constitution;
* README;
* project structure;
* configuration;
* database;
* authentication;
* core models;
* seed data;
* student dashboard; and
* teacher dashboard foundation.

### Day 2 — Intelligence

Implement the core learning system:

* diagnostic assessment;
* AI tutor;
* targeted practice;
* assessment engine;
* learning-event tracking;
* analytics;
* teacher learning-gap views; and
* AI-generated teacher insights.

### Day 3 — Validation and Deployment

Prepare the system for demonstration:

* end-to-end testing;
* UI polish;
* demonstration data;
* deployment;
* logging and error handling;
* validation activities;
* documentation;
* competition evidence; and
* final demonstration preparation.

---

## MVP Success Criteria

The MVP is successful when the following complete flow works reliably:

```text
Student logs in
        ↓
Selects a Biology topic
        ↓
Completes diagnostic assessment
        ↓
System identifies weakness
        ↓
Student learns with AI
        ↓
Student practises
        ↓
Student completes assessment
        ↓
Learning events are recorded
        ↓
Analytics identify learning patterns
        ↓
Teacher sees the learning gap
        ↓
AI provides a grounded intervention recommendation
```

Everything else is secondary to making this loop work correctly.

---

## Development Rule

When time or complexity forces a choice:

> **Cut features before cutting the core loop.**

Or, more simply:

> **Core loop first. Features second.**

---

## Project Governance

`PROJECT_CONSTITUTION.md` is the primary guardrail for development decisions.

Before adding a significant feature, ask:

1. Does it strengthen the core learning loop?
2. Does it generate or improve meaningful learning evidence?
3. Does it help the student learn or the teacher intervene?
4. Can it be implemented without compromising privacy or security?
5. Can its effectiveness be demonstrated honestly within the MVP?

If the answer is no, the feature should normally be postponed until after the MVP.

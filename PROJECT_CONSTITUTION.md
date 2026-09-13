# PROJECT CONSTITUTION

## Project
**Name:** Mwalimu AI  
**Working Title:** Mwalimu AI — An Intelligent Learning Companion for Kenyan Secondary Schools  
**Version:** 0.1  
**Status:** MVP / Competition Prototype  
**Primary Subject:** Form 2 Biology  
**Primary SDG:** SDG 4 — Quality Education

---

## 1. Vision

Mwalimu AI helps teachers understand where students are struggling and helps students receive personalized support before learning gaps become persistent.

The product is built around:

> **Teach → Measure → Understand → Intervene**

Mwalimu AI is not intended to replace teachers. It is intended to give teachers better evidence about student learning and give students an intelligent, supportive learning companion.

---

## 2. Problem Statement

In a secondary-school classroom, one teacher may be responsible for many students with different levels of understanding.

A teacher may know that a class performed poorly on a topic, but it can be difficult to quickly determine:
- which students are struggling;
- which concepts are causing difficulty;
- what misconceptions are common;
- which students need additional support; and
- what intervention should happen next.

Students may also know that they are "weak" in a topic without knowing exactly what they do not understand.

Mwalimu AI closes this gap by connecting:
1. student self-identified learning needs;
2. AI-guided learning;
3. structured assessment;
4. learning-event data;
5. class-level analytics; and
6. actionable teacher recommendations.

---

## 3. Core Product Promise

A student can say:

> "I struggle with Cell Division."

Mwalimu AI should help answer:

> "What exactly are you struggling with?"

The system diagnoses the student's understanding, provides appropriate support, assesses progress, and records useful learning events.

The teacher can then see evidence such as:

> "17 of 25 students in Form 2 East are currently struggling with Cell Division. The dominant difficulty is sequencing the stages of mitosis. A visual recap followed by a short formative assessment is recommended."

The numbers above are illustrative only. The system must never fabricate student performance data.

---

## 4. Target Users

### Students
Secondary-school students who need:
- personalized explanations;
- practice questions;
- formative assessment;
- feedback;
- hints;
- progress tracking; and
- help identifying weak areas.

### Teachers
Teachers who need:
- class-level learning analytics;
- topic mastery information;
- identification of common learning gaps;
- authorized student-level learning activity;
- AI-generated summaries; and
- recommended instructional interventions.

### School
The initial prototype is designed around a school/class context. Multi-school enterprise functionality is not part of the initial MVP.

---

## 5. MVP Scope

### Subject
**Form 2 Biology**

### Student Experience
A student can:
1. log in;
2. access their assigned school/class;
3. view Biology topics;
4. identify topics they feel weak in;
5. begin a diagnostic assessment;
6. interact with an AI tutor;
7. receive explanations and hints;
8. answer practice questions;
9. receive feedback;
10. complete a learning session; and
11. view basic progress.

### Teacher Experience
A teacher can:
1. log in;
2. view their assigned class;
3. see student learning activity;
4. see topic-level performance;
5. identify common learning gaps;
6. view authorized individual student progress;
7. receive an AI-generated class summary; and
8. receive recommended interventions.

### Intelligence Loop

**Student identifies weakness → Diagnostic → AI support → Practice → Assessment → Learning events → Analytics → Teacher insight → Intervention recommendation**

This loop is more important than having a large number of features.

---

## 6. Non-Goals

The MVP will NOT attempt to:
- replace teachers;
- replace the official school curriculum;
- provide autonomous high-stakes grading;
- make disciplinary decisions about students;
- make admissions or promotion decisions;
- diagnose medical or psychological conditions;
- collect unnecessary personal information;
- build a full learning-management system;
- support every Kenyan subject;
- support every school from day one;
- build a complex mobile application before the web MVP works;
- claim production readiness without evidence; or
- claim a TRL level that has not been demonstrated.

---

## 7. Product Principles

### 1 — Teacher First, Not Teacher Replacement
The system strengthens teacher decision-making rather than removing the teacher from the learning process.

### 2 — Evidence Over Guesswork
Teacher insights must be derived from recorded learning events and assessment results. Self-reported weakness is useful, but is not proof of lack of mastery.

### 3 — AI Should Explain, Not Merely Answer
The tutor should encourage understanding through explanations, questions, hints, examples, and feedback rather than simply giving answers.

### 4 — Assessment Must Be Meaningful
Assessment should measure understanding. Questions should be linked to topics, concepts, skills, difficulty levels, and expected answers where practical.

### 5 — The Data Loop Is the Product
Mwalimu AI is not simply a chatbot. Its core value comes from transforming individual student interactions into useful, aggregated learning intelligence for teachers.

### 6 — Simple Before Complex
A reliable small system is more valuable than a large unfinished system. Prioritize the end-to-end learning loop over feature quantity.

### 7 — Mobile and Low-Bandwidth Friendly
The system should be designed with Kenyan school environments in mind and remain usable on ordinary phones and modest internet connections wherever practical.

### 8 — Local Relevance
Examples, explanations, and learning experiences should be appropriate for Kenyan secondary-school learners and the intended curriculum.

### 9 — Responsible AI
Clearly distinguish between verified/structured educational content, generated AI explanations, measured student performance, and AI-generated recommendations.

### 10 — Honest Validation
Never invent students, test results, school adoption, user numbers, performance improvements, validation studies, or TRL evidence. Demo data must be clearly identified as synthetic/demo data.

---

## 8. AI Requirements

### Tutor
The AI tutor should:
- explain Biology concepts at an appropriate level;
- adapt explanations to apparent understanding;
- ask guiding questions;
- provide hints;
- give examples;
- encourage active learning;
- avoid unnecessary jargon;
- acknowledge uncertainty when appropriate; and
- avoid confidently presenting unsupported information.

### Assessment
Assessment should primarily rely on structured questions and deterministic scoring where practical. An LLM should not be the sole authority for objective-question scoring.

For open-ended answers, use an explicit rubric or clearly defined evaluation approach.

### Teacher Insights
The teacher-insight AI should receive structured analytics rather than unrestricted access to raw student conversations.

The system should first calculate facts such as:
- active students;
- attempts;
- correct/incorrect answers;
- topic performance;
- recent performance;
- common question errors; and
- diagnostic results.

The AI may then turn those structured facts into a readable summary and intervention recommendation.

### No Fabricated Analytics
If insufficient data exists, the system must say so. It must never invent a percentage, student count, misconception, or trend.

---

## 9. Learning Event Model

The system should record meaningful learning events.

Initial event types:
- `TOPIC_SELECTED`
- `DIAGNOSTIC_STARTED`
- `QUESTION_ATTEMPTED`
- `QUESTION_CORRECT`
- `QUESTION_WRONG`
- `HINT_REQUESTED`
- `EXPLANATION_REQUESTED`
- `SESSION_COMPLETED`
- `TOPIC_MASTERED`

Events should be associated with appropriate context such as:
- student;
- topic;
- session;
- timestamp;
- event type;
- question;
- score;
- difficulty; and
- confidence where available.

The event system is the foundation for future analytics.

---

## 10. Learning Analytics Principles

### Student Level
Answer:
- What topics has the student studied?
- Which topics appear weak?
- What has the student improved?
- What should the student work on next?

### Class Level
Answer:
- Which topics have the largest learning gaps?
- What percentage of students appear to be struggling?
- What concepts produce the most incorrect responses?
- Which intervention should the teacher prioritize?

### Intervention Level
Transform analytics into practical teacher actions:

**Learning gap → Likely concept → Recommended teaching action → Follow-up assessment**

---

## 11. Privacy and Student Safety

Because the system is intended for schoolchildren:
- collect the minimum personal information necessary;
- use student IDs instead of unnecessary identifying information;
- avoid collecting phone numbers, addresses, photographs, or other unnecessary data in the prototype;
- restrict teacher access to authorized classes/students;
- do not expose one student's private learning information to another student;
- use synthetic/demo data for competition demonstrations unless appropriate authorization exists for real student data;
- apply appropriate school, parent/guardian, and ethical consent procedures before testing with minors where required; and
- document how data is stored, used, and deleted.

The competition prototype must prioritize privacy by design.

---

## 12. Security Principles

The application should include:
- password hashing;
- authenticated sessions;
- role-based authorization;
- school/class-level access control;
- environment variables for secrets;
- no API keys committed to source control;
- server-side validation;
- basic audit/logging capability; and
- secure production configuration before public deployment.

Security should be proportional to the MVP but must not be ignored.

---

## 13. Architecture Principles

Initial technology:
- **Python**
- **FastAPI**
- **PostgreSQL**
- **SQLAlchemy**
- **Jinja2 / HTML / CSS / JavaScript**
- an external LLM/API provider for AI functionality
- Docker for reproducible deployment where practical

Keep these concerns separate:
1. presentation;
2. routes/API;
3. business logic;
4. database models;
5. AI services;
6. analytics;
7. configuration; and
8. tests.

The implementation should remain simple enough to build and debug rapidly.

---

## 14. Curriculum and Content Principles

Biology content must be:
- appropriate for the intended Form 2 level;
- organized by topic;
- based on reliable educational sources;
- reviewed before being used as core assessment content; and
- separated from generated conversational content.

The system should not rely on an LLM to invent the entire curriculum.

A curated question/content bank will provide the foundation for reliable assessment.

---

## 15. Competition Alignment

Mwalimu AI is primarily designed for the **AI for Education** track.

It also has potential alignment with **AI for Less Developed Countries** through:
- mobile-first access;
- low-bandwidth design;
- infrastructure-conscious architecture;
- localized educational content;
- teacher-support tooling; and
- potential future local-language/voice capabilities.

Primary SDG:

**SDG 4 — Quality Education**

Potential secondary alignment:
- **SDG 9 — Industry, Innovation and Infrastructure**
- **SDG 10 — Reduced Inequalities**

The project must only claim competition requirements that are actually satisfied.

---

## 16. Technology Readiness and Validation

We will not claim TRL 6+ merely because the application works locally.

Credible readiness evidence may include:
- functioning deployed prototype;
- realistic end-to-end usage;
- structured testing;
- usability feedback;
- teacher feedback;
- student feedback where appropriately authorized;
- performance/error testing;
- documented fixes;
- repeatable demonstrations; and
- evidence that the system works in a realistic educational environment.

All validation results must be documented honestly.

---

## 17. Definition of MVP Success

### Student
**Login → Select Biology topic → Diagnose weakness → Learn with AI → Practice → Receive feedback → Complete session**

### Teacher
**Login → Select class → View learning data → Identify weak topic → Read AI summary → Receive intervention recommendation**

### System
**Student activity → Learning events → Analytics → Teacher insight**

If this entire chain works reliably, the MVP has achieved its primary objective.

---

## 18. Three-Day Execution Rule

### Day 1 — Foundation
- project initialization;
- constitution;
- README;
- repository structure;
- configuration;
- database;
- authentication;
- school/class/student/teacher models;
- Biology topic/question seed data;
- basic student and teacher dashboards.

### Day 2 — Intelligence
- AI tutor;
- diagnostics;
- practice;
- assessment;
- learning events;
- analytics;
- teacher learning-gap dashboard;
- AI-generated teacher insights.

### Day 3 — Validation and Deployment
- end-to-end testing;
- UI polish;
- realistic demo data;
- deployment;
- logging/error handling;
- validation;
- documentation;
- competition evidence;
- final demonstration flow.

### Scope Rule
If time becomes limited, cut features before cutting the core loop.

**Core loop first. Features second.**

---

## 19. Definition of Done

A feature is not complete because its code exists.

A feature is complete when:
- it works end-to-end;
- invalid input is handled;
- authorization is respected;
- it does not expose unnecessary data;
- the important path has been tested;
- the UI communicates its purpose clearly; and
- it contributes to the core product loop.

---

## 20. What We Will Not Compromise

We will not compromise on:
1. honesty of competition claims;
2. student privacy;
3. teacher authority;
4. data integrity;
5. assessment reliability;
6. basic security; and
7. end-to-end functionality.

---

## 21. Product North Star

> **Can Mwalimu AI help a teacher move from "My class is struggling" to "I know exactly what they are struggling with and what I should do next"?**

If a feature does not help answer that question, it is probably not a priority for the MVP.

---

## 22. Working Motto

> **Don't build another chatbot. Build a learning intelligence loop.**

---

## 23. Version Control

This constitution is the project's governing document for the initial MVP.

Changes are allowed when they:
- improve the project's ability to solve the core problem;
- do not violate safety/privacy principles;
- do not introduce unnecessary scope; and
- are documented when significant.

**Current version:** 0.1
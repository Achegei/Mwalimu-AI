
# Mwalimu AI Architecture Constitution

**Version:** 1.0
**Status:** LOCKED
**Effective Date:** 19 September 2026

---

# 1. Purpose

This constitution defines the authoritative domain architecture,
ownership rules, tenant boundaries, curriculum-resource rules,
teaching relationships, and authorization principles for Mwalimu AI.

All future implementation must conform to this constitution.

This document describes architectural rules rather than individual
implementation details.

A material architectural change must not be introduced silently.
It must be documented as a new architectural decision that explicitly
supersedes the affected rule.

---

# 2. SaaS Tenant Model

Mwalimu AI is a multi-tenant education SaaS platform.

The primary tenant is a School.

The hierarchy is:

Mwalimu AI Platform
    |
    +-- School A
    |
    +-- School B
    |
    +-- School C

Data belonging to one school must never become accessible to another
school unless a future explicitly authorized platform feature provides
such access.

Tenant isolation must be enforced by the backend.

Frontend filtering is never considered a security boundary.

---

# 3. Platform Roles

Mwalimu AI has four principal user roles:

1. Super Admin
2. School Admin
3. Teacher
4. Student

Each role has different authority.

---

# 4. Super Admin

The Super Admin operates at the SaaS platform level.

The Super Admin is not an ordinary school user.

Responsibilities include:

- create schools;
- activate or suspend schools;
- manage tenant lifecycle;
- create or provision the initial School Admin;
- view platform-level tenant information;
- manage platform configuration;
- manage SaaS operational controls;
- perform authorized platform support operations.

A Super Admin must not be constrained to one school.

Ordinary school users must never receive Super Admin privileges.

The Super Admin interface shall eventually live under a dedicated
platform area such as:

    /super-admin/

Super Admin functionality must remain separate from normal school
administration.

---

# 5. School Admin

A School Admin belongs to one school.

The School Admin manages the institutional structure of that school.

Responsibilities include:

- create and manage teachers;
- create and manage students;
- create and manage classrooms;
- manage student enrollment;
- assign teachers to subjects and classrooms;
- manage school-wide curriculum resources;
- manage approved textbooks and common reference material;
- manage other institution-wide academic configuration.

A School Admin is not the normal owner of teacher-created instructional
material.

---

# 6. Teacher

A Teacher belongs to one school.

A teacher may teach:

- multiple subjects;
- multiple form levels;
- multiple classrooms;
- the same subject across multiple form levels;
- the same subject across multiple classrooms;
- different subjects in different classrooms.

Example:

Teacher Kamau may teach:

    Biology -> Form 1 East
    Biology -> Form 2 East
    Biology -> Form 3 East
    Chemistry -> Form 2 East

Another teacher may independently teach:

    Biology -> Form 4 East

Therefore, a teacher must NOT have a single subject_id or single
classroom_id as the representation of what they teach.

---

# 7. Teaching Assignment

The authoritative relationship between teachers, subjects, and classes
shall be represented by a Teaching Assignment.

Conceptually:

    TeachingAssignment
        school_id
        teacher_id
        subject_id
        classroom_id
        is_active

A Teaching Assignment answers:

    "Which teacher teaches which subject to which class?"

This relationship is the authorization foundation for teacher academic
operations.

A teacher may have many Teaching Assignments.

A subject may have many teachers.

A classroom may have many teachers.

A teacher may teach the same subject in many classrooms.

---

# 8. Classroom Model

A classroom represents an actual school class or stream.

Examples:

    Form 1 East
    Form 1 West
    Form 2 East
    Form 3 North

A classroom contains a form level.

A classroom must NOT be treated as belonging academically to only one
teacher.

A classroom can have multiple teachers through Teaching Assignments.

Example:

Form 2 East
    Biology     -> Teacher A
    Chemistry   -> Teacher A
    Mathematics -> Teacher B
    English     -> Teacher C
    Geography   -> Teacher D

TeachingAssignment is therefore the authoritative relationship for
subject teaching.

---

# 9. Subjects

Subjects belong to a school.

Examples:

    Biology
    Chemistry
    Mathematics
    English
    Geography

Subject access for teachers is derived from Teaching Assignments.

A teacher must not gain access to a subject merely because the subject
exists in their school.

---

# 10. Curriculum Topics

Topics belong to subjects and form levels.

Example:

Biology
    Form 2
        Transport in Plants and Animals
        Respiration
        Excretion

Topics provide curriculum structure for:

- diagnostics;
- tutoring;
- practice;
- document retrieval;
- progress analysis.

---

# 11. Two-Tier Document Architecture

Mwalimu AI shall support two distinct document scopes:

1. COMMON SCHOOL CURRICULUM MATERIAL
2. TEACHING-ASSIGNMENT MATERIAL

These scopes must not be confused.

---

# 12. Common School Curriculum Material

Common material belongs to the school curriculum rather than an
individual teacher.

Its normal scope is:

    School
        + Subject
        + Form Level
        + optional Topic

Examples include:

- approved curriculum or syllabus;
- approved textbooks;
- school-approved reference books;
- official curriculum resources;
- common school revision resources;
- official examination resources where appropriate.

Example:

    School A
        Biology
            Form 2
                Approved Biology Textbook

The textbook is uploaded once.

It must NOT need to be uploaded separately for:

    Form 2 East
    Form 2 West
    Form 2 North

All authorized Form 2 Biology teaching contexts may use the common
resource.

---

# 13. Ownership of Common Material

School Admin controls institution-wide common curriculum material.

The School Admin may:

- upload;
- approve;
- replace;
- archive;
- reactivate;
- manage metadata.

Teachers must not independently replace the school's canonical approved
textbook or curriculum for all classes.

A future workflow may allow teachers to submit resources for school
approval, but submission does not automatically make the material
school-wide.

---

# 14. Teacher/Class-Specific Material

Teacher-created or class-specific resources belong to a Teaching
Assignment.

Scope:

    School
        + Teacher
        + Subject
        + Classroom

Examples:

- teacher notes;
- lesson summaries;
- worksheets;
- teacher-created revision material;
- class revision papers;
- supplementary explanations;
- classroom-specific resources.

Example:

    Teacher Kamau
        Biology
            Form 2 East
                Teacher Notes
                Revision Worksheet
                Topic Summary

These resources must not automatically become resources for another
teacher's class.

---

# 15. Teacher Document Authorization

A teacher may manage class-specific academic material only when an
active Teaching Assignment authorizes that teacher for the relevant:

    school
    subject
    classroom

Authorization must be enforced server-side.

For example:

If Teacher Kamau has:

    Biology -> Form 1 East
    Biology -> Form 2 East
    Biology -> Form 3 East

then Kamau may manage class-specific Biology material for those
assignments.

Kamau must NOT be able to manage:

    Biology -> Form 4 East

unless an active Teaching Assignment exists.

Manipulating HTML, JavaScript, request payloads, IDs, or API calls must
not bypass this rule.

---

# 16. Document Scope

Documents should support an explicit scope.

Conceptually:

    COMMON
    TEACHING_ASSIGNMENT

A common document does not require a Teaching Assignment.

A teaching-assignment document must reference the Teaching Assignment
that owns it.

Conceptually:

    Document
        school_id
        subject_id
        form_level
        topic_id optional

        scope

        teaching_assignment_id optional

        uploaded_by_id
        document_type
        title
        processing_status
        ...

Rules:

If:

    scope == COMMON

then:

    teaching_assignment_id must be NULL

If:

    scope == TEACHING_ASSIGNMENT

then:

    teaching_assignment_id must be present

and must belong to the same:

    school
    subject
    form/class context

---

# 17. Examination and Revision Material

Document type alone must not determine ownership.

For example, not every examination paper is teacher-specific.

An official examination or school-wide past paper may be common
material.

A teacher-created revision test may be Teaching Assignment material.

Therefore:

    document_type != authorization_scope

The intended audience and ownership determine scope.

---

# 18. Document Lifecycle

Curriculum resources change over time.

Documents therefore require lifecycle management.

The system must support at minimum:

- active;
- archived/replaced;
- processing;
- processing failure.

Historical documents should normally be archived rather than destroyed
immediately.

Replacing curriculum material must not silently corrupt historical
records.

---

# 19. Curriculum Changes

When a school changes an approved textbook:

    Biology
        Form 2
            Old Textbook -> archived
            New Textbook -> active

the change should occur once at the common curriculum level.

All relevant teaching contexts should subsequently retrieve the active
common resource.

Teacher-specific notes remain independent unless explicitly changed.

---

# 20. AI Tutor Retrieval

Mwalimu AI must build tutoring context from authorized sources only.

For a student interaction, retrieval should conceptually combine:

    A. COMMON CURRICULUM CONTEXT

        School
        + Subject
        + Form Level
        + optional Topic

    AND

    B. CLASS-SPECIFIC CONTEXT

        Teaching Assignment
        + Subject
        + Classroom
        + optional Topic

The resulting authorized material may then be supplied to the AI tutor.

---

# 21. Retrieval Isolation

Document retrieval must enforce boundaries before relevance ranking.

At minimum, retrieval must respect:

- school;
- subject;
- form level;
- topic where applicable;
- document status;
- document activity/lifecycle;
- document scope;
- Teaching Assignment where applicable.

A relevance score must never override authorization.

Security filtering happens before relevance ranking.

---

# 22. Student Context

A student belongs to a school.

Students are enrolled in classrooms through the enrollment system.

The student's classroom, subject, and relevant Teaching Assignment
determine which teacher-specific resources may participate in tutoring.

A student must never receive another school's documents.

A student should not receive another classroom's private
teacher-specific material merely because the subject and form level
match.

---

# 23. Tenant Isolation

Every tenant-sensitive operation must enforce school ownership on the
backend.

This includes:

- users;
- classrooms;
- enrollments;
- subjects;
- topics;
- teaching assignments;
- assessments;
- documents;
- document chunks;
- AI retrieval;
- teacher analytics;
- student progress.

IDs supplied by the browser are never trusted as proof of ownership.

---

# 24. Authorization Principle

Authorization must be based on server-side relationships.

The frontend may improve usability by hiding unauthorized choices, but
frontend controls are not security controls.

The backend must independently validate every protected operation.

---

# 25. Role Separation

The system shall preserve these boundaries:

SUPER ADMIN

    manages SaaS tenants

SCHOOL ADMIN

    manages the institution and common curriculum

TEACHER

    manages teaching activities and material within assigned teaching
    contexts

STUDENT

    learns within authorized enrollment and curriculum contexts

Roles must not be expanded merely for implementation convenience.

---

# 26. Document Upload Responsibility

Common curriculum resources:

    primarily School Admin responsibility

Teaching Assignment resources:

    Teacher responsibility

This distinction must be reflected in both:

- API authorization;
- user interface.

The Admin dashboard must not become the permanent interface for
teacher-owned resources.

---

# 27. Existing Admin Document UI

The currently implemented Admin document functionality may be used as
an implementation stepping stone.

It must not be interpreted as the final ownership architecture.

As implementation progresses:

- common-resource management remains with School Admin;
- teaching-assignment resource management moves to Teacher workflows.

---

# 28. Security Invariants

The following are non-negotiable:

1. No cross-school data leakage.
2. No teacher access outside active Teaching Assignments.
3. No student access to unauthorized classroom-specific resources.
4. No frontend-only authorization.
5. No retrieval before tenant and curriculum authorization.
6. No Super Admin authority granted to ordinary tenant administrators.
7. No document scope inferred solely from user-controlled request data.
8. No silent replacement of historical curriculum resources.

---

# 29. Testing Requirements

Architectural authorization rules must have automated tests.

Tests must include:

- tenant isolation;
- teacher assignment isolation;
- subject isolation;
- classroom isolation;
- form-level isolation;
- document-scope isolation;
- common-resource retrieval;
- teacher-resource retrieval;
- unauthorized teacher upload attempts;
- unauthorized student retrieval;
- cross-school attacks;
- invalid foreign IDs;
- archived resource exclusion.

Passing UI tests alone is insufficient.

---

# 30. Database Integrity

Where practical, important architectural invariants should be protected
by both:

1. application validation; and
2. database constraints.

The application must not depend exclusively on browser behavior to
preserve relational integrity.

---

# 31. Implementation Order

The architecture shall be introduced incrementally.

Phase 1:
    Teaching Assignment foundation

Phase 2:
    School Admin Teaching Assignment management

Phase 3:
    Document scope model

Phase 4:
    Teacher document management

Phase 5:
    Scope-aware AI retrieval

Phase 6:
    Complete School Admin institutional management

Phase 7:
    SaaS Super Admin tenant management

Each phase must preserve passing tests before proceeding.

---

# 32. Backward Compatibility

Existing working functionality must not be casually destroyed while
introducing this architecture.

Where an existing model conflicts with this constitution, migration
must be deliberate and tested.

For example, an existing Classroom.teacher_id may temporarily remain
during migration but must not become the authoritative source for
subject teaching assignments.

TeachingAssignment becomes the authoritative academic relationship.

---

# 33. Change Control

This constitution is LOCKED at Version 1.0.

Implementation details may evolve without changing the constitution
when they preserve these rules.

A material architectural change requires an Architecture Decision
Record (ADR).

Examples include:

- changing the tenant model;
- changing TeachingAssignment semantics;
- changing document ownership;
- changing curriculum scope;
- changing role authority;
- changing tenant-isolation rules.

An accepted architectural decision must not be silently rewritten.

A later decision that reverses an earlier architectural decision must
explicitly supersede it.

---

# 34. Architectural Decision Records

Future significant decisions shall be stored under:

    docs/adr/

Suggested naming:

    0001-teaching-assignment-model.md
    0002-two-tier-document-scope.md
    0003-super-admin-tenant-model.md

Each ADR should record:

- Status
- Context
- Decision
- Rationale
- Consequences
- Security implications
- Migration implications
- Tests enforcing the decision

---

# 35. Definition of Done

An architectural phase is not complete merely because the UI works.

A phase is complete only when:

- database model is correct;
- migration succeeds;
- backend authorization exists;
- tenant isolation exists;
- API behavior is tested;
- relevant UI works;
- regression tests pass;
- git diff check passes;
- architecture remains consistent with this constitution.

---

# 36. Governing Principle

Mwalimu AI shall model the real academic relationship:

    School
        |
        +-- Curriculum
        |
        +-- Classroom
        |
        +-- Subject
        |
        +-- Teacher
              |
              +-- Teaching Assignment
                       |
                       +-- Subject
                       +-- Classroom

and shall distinguish:

    institutional curriculum knowledge

from:

    teacher/class instructional knowledge.

AI tutoring shall use both only when the requesting student's school,
curriculum, classroom, and teaching context authorize them.

---

END OF CONSTITUTION

Status: LOCKED
Version: 1.0
Effective: 19 September 2026
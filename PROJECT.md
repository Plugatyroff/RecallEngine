# Project Brief: Recall Engine

## 1. Project Overview

We are building **Recall Engine**, a mobile-first, adaptive spaced-repetition application designed to help users retain knowledge across multiple subjects over long periods.

The application combines three ideas:

1. **Anki-style flashcards** for active recall and spaced repetition.
2. **Obsidian-style knowledge organization** with hierarchical topics and interconnected cards.
3. **An adaptive notification and scheduling system** that proactively selects material for review based on forgetting, difficulty, importance, and review history.

The central idea is that users should not have to manually decide what to revise every day. The application should intelligently resurface previously learned material, especially during the critical first hours after learning.

The initial application is intended for a single user, but its architecture should support future expansion.

## 2. Core Functionality

### A. Hierarchical Knowledge Organization

Users can create an unlimited hierarchy of subjects and subtopics.

Example:

- Mathematics
  - Linear Algebra
    - Matrices
      - Matrix Operations
      - Determinants
      - Inverse Matrices
    - Vector Spaces
    - Linear Transformations
  - Calculus
    - Limits
    - Derivatives
    - Integrals
- Hungarian
  - Vocabulary
  - Grammar
  - Etymology
- Electronics
  - Microcontrollers
  - Digital Electronics

Each topic can contain flashcards, notes, and nested subtopics.

Avoid creating separate database tables for each subject. Use a unified hierarchical data model.

### B. Flashcard System

Each flashcard should support:

- Front: question, prompt, or problem.
- Back: answer, explanation, or solution.
- Rich text and mathematical notation (LaTeX).
- Images and other media in future versions.
- Tags and content classifications.
- Links to other cards.
- Review history and scheduling metadata.

Cards should support different learning purposes:

- Definitions and fundamental concepts.
- Theorems and mathematical statements.
- Proofs and conceptual explanations.
- Practical exercises and applications.
- Vocabulary, translations, and example sentences.

A theorem may have separate cards testing its statement, proof, interpretation, and application.

### C. Linked Knowledge

Cards should be interconnected, similar to hyperlinks in Wikipedia or Obsidian.

Examples:

- Clicking a mathematical concept opens its explanation.
- Clicking a Hungarian word opens its definition and etymology.
- Related vocabulary can link to words sharing the same root.
- A theorem can link to its prerequisites, corollaries, and applications.

Support explicit relationships between cards, potentially including relationship types such as `related_to`, `prerequisite_of`, `example_of`, and `derived_from`.

A full graphical knowledge visualization is not necessary for the MVP.

### D. Adaptive Spaced Repetition

This is the application's most important feature.

Unlike a conventional flashcard workflow focused primarily on daily reviews, Recall Engine should support **ultra-short initial review intervals measured in hours**.

An initial experimental schedule might be:

- First exposure: immediately upon learning.
- First review: approximately 2 hours later.
- Second review: approximately 6 hours after the first review.
- Third review: approximately 12 hours later.
- Subsequent reviews: 1 day, 3 days, 7 days, etc.

These are initial configurable hypotheses, not scientifically established optimal intervals.

The scheduler should account for:

- Time since the last successful review.
- Retrieval success or failure.
- Estimated difficulty.
- Importance of the knowledge.
- Number of previous reviews.
- Whether the material is new or established.
- Dependencies between concepts.
- User-defined learning priorities.

A failed review should generally shorten the next interval.

A successful review should generally increase it.

The scheduling algorithm must be modular, configurable, and independently testable so that more advanced algorithms, potentially including FSRS, can be evaluated later.

**Important:** Creating a card does not necessarily mean the user has successfully learned it. The system should distinguish between card creation, first exposure, and successful retrieval.

### E. Intelligent Review Sessions

The application should proactively assemble review sessions containing cards from multiple subjects.

Example afternoon session:

- 5 linear algebra theorem cards.
- 8 Hungarian vocabulary cards.
- 3 electronics concept cards.

The selection algorithm should balance:

- Cards currently due for review.
- Weak or frequently forgotten material.
- Foundational concepts.
- Diversity across subjects.
- User priorities.
- Available review time.

The goal is to prevent entire subjects from being neglected as users progress to new material.

### F. Notifications

The user should be able to configure notification times, initially perhaps twice daily.

Notifications should summarize the selected review material and allow users to enter the corresponding session.

The system should eventually support time-sensitive early reviews without overwhelming the user with excessive notifications.

Android notifications are a major product feature, but can be implemented after the basic review workflow.

### G. Learning Progression

The application should distinguish between memorization, conceptual understanding, and practical application.

For example, learning a mathematical theorem might involve:

1. Remembering its statement.
2. Understanding its assumptions.
3. Reconstructing its proof.
4. Recognizing when to apply it.
5. Solving problems using it.

As knowledge becomes established, review frequency should decrease, allowing users to focus on higher-level concepts.

The system should not require users to repeatedly reconstruct every elementary proof once those concepts have become reliable tools.

## 3. Technical Stack

| Layer                     | Technology                          |
| ------------------------- | ----------------------------------- |
| Frontend                  | React Native + Expo                 |
| Language                  | TypeScript                          |
| Backend                   | Python                              |
| API framework             | FastAPI                             |
| Database                  | Microsoft SQL Server (Express)      |
| Database driver           | pyodbc + ODBC Driver 18             |
| ORM                       | SQLAlchemy                          |
| Database migrations       | Alembic                             |
| API communication         | REST / JSON over HTTPS              |
| Backend testing           | pytest                              |
| Frontend testing          | Jest + React Native Testing Library |
| Version control           | Git + GitHub                        |
| Development environment   | Windows + VS Code                   |
| AI development assistance | Claude Code + OpenAI Codex          |

Use Expo to simplify Android development and testing.

The frontend should eventually be accessible from both Android and a laptop. Evaluate Expo's web support before deciding whether a separate web frontend is necessary.

The database and backend should initially run locally for development, with a straightforward path toward cloud deployment.

For local development, the database runs on a local SQL Server Express instance using Windows authentication, so no database password is stored in the project. Only the backend connects to the database; the frontend never does.

SQL Server was chosen over PostgreSQL because it is already installed and familiar to the developer. SQLAlchemy keeps most code database-agnostic, so this choice can be revisited. SQL Server-specific constraints to design around:

- A self-referencing foreign key (such as `Topic.parent_id`) cannot use `ON DELETE CASCADE`; deleting topics must be handled in the service layer.
- Store timestamps as `DATETIME2` in UTC.

For cloud hosting, we can evaluate Azure SQL Database for the managed database and a separate Python hosting provider for FastAPI.

Cloud deployment and authentication should not be prerequisites for the first working prototype.

## 4. Architecture

The application should follow this general architecture:

**React Native / Expo frontend**
↓
**FastAPI REST API**
↓
**Python application services**
↓
**SQLAlchemy**
↓
**SQL Server database**

Keep the following concerns separated:

- UI and navigation.
- API communication.
- Business logic.
- Spaced-repetition scheduling.
- Database persistence.
- Notification scheduling.

Frontend components should not directly access the database.

Database operations should be encapsulated in a repository or service layer so that implementation details can change without requiring major changes elsewhere.

### Initial Database Entities

Consider the following entities:

- `Topic`: hierarchical organization with a self-referencing parent ID.
- `Card`: flashcard content and metadata.
- `CardLink`: relationships between cards.
- `Review`: individual review attempts and results.
- `ReviewState`: current scheduling state for each card.
- `Tag`: optional categorization.
- `CardTag`: many-to-many card/tag relationships.

The database should support efficient retrieval of due cards, topic filtering, and linked-card navigation.

Do not introduce unnecessary tables or abstractions without a clear use case.

## 5. Proposed Project Structure

```text
recall-engine/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── features/
│   ├── services/
│   └── types/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── repositories/
│   │   └── core/
│   ├── migrations/
│   └── tests/
│
├── docs/
│   ├── architecture.md
│   ├── database-design.md
│   ├── scheduling-algorithm.md
│   └── roadmap.md
│
├── README.md
├── PROJECT.md
├── AGENTS.md
├── CLAUDE.md
└── .gitignore
```

This is a proposed structure, not a requirement to create every directory immediately.

## 6. Development Strategy

Build incrementally, prioritizing a functional application over unnecessary architectural complexity.

### Phase 1 — Minimum Working Prototype

- Initialize the Expo frontend.
- Initialize the FastAPI backend.
- Configure the SQL Server database.
- Create the initial database models.
- Implement topic creation and retrieval.
- Implement flashcard creation and retrieval.
- Display flashcards in the Android application.
- Allow users to reveal answers.
- Record review results.
- Implement a basic configurable scheduler.

**Success criterion:** A user can create a card, review it, and see when it is next scheduled.

### Phase 2 — Core Learning Experience

- Nested topic navigation.
- Linked cards.
- Improved review scheduling.
- Multi-subject review sessions.
- Review history and statistics.
- Mathematical notation and rich text.

### Phase 3 — Proactive Learning

- Android notifications.
- Configurable review windows.
- Intelligent subject balancing.
- Review priority calculations.
- Improved scheduling based on user performance.

### Phase 4 — Cloud and Multi-Device

- Cloud-hosted database.
- Cloud-hosted backend.
- Authentication.
- Synchronization between Android and laptop.
- Reliable handling of connectivity interruptions.

### Phase 5 — AI Assistance

- Generate draft cards from user notes.
- Extract important concepts from learning material.
- Suggest links between related cards.
- Generate practice questions.
- Suggest prerequisite concepts.
- Assist with explanations and examples.

AI-generated educational content must be reviewable and editable before being added to the user's knowledge base.

## 7. GitHub Portfolio Requirements

This is also a professional portfolio project.

The repository should demonstrate:

- Clear architecture.
- Readable and maintainable code.
- Thoughtful database design.
- Meaningful automated tests.
- Reproducible development setup.
- Well-documented engineering decisions.
- Incremental Git history.
- Screenshots and video demonstrations.
- Clear distinction between implemented and planned features.

The README should explain the product within 30 seconds.

Use small, descriptive commits and focused pull requests.

Do not commit credentials, personal learning data, or environment secrets.

## 8. Instructions for Claude Code

Act as a senior software engineer and technical mentor.

The developer is learning software engineering and wants to understand the system rather than blindly accept generated code.

Follow these principles:

1. Prefer simple, maintainable solutions.
2. Do not overengineer for hypothetical future users.
3. Work in small, testable increments.
4. Explain important architectural decisions.
5. Before significant implementation, propose a plan.
6. Ask for approval before major architectural changes.
7. Write tests for critical business logic.
8. Avoid unnecessary dependencies.
9. Keep frontend, backend, and persistence responsibilities separate.
10. Never claim functionality has been tested unless tests were actually executed.
11. Explain how implemented features work, including the path from frontend to backend to database.
12. Keep the repository suitable for public GitHub presentation.

## 9. First Task

**Do not generate the entire application immediately.**

First:

1. Review this specification.
2. Identify ambiguities and potential architectural problems.
3. Propose the smallest practical MVP.
4. Recommend the initial database schema.
5. Explain the local development workflow for Windows and Android.
6. Propose a step-by-step implementation plan with independently testable milestones.

Prioritize a working flashcard creation and review workflow.

Wait for approval before implementing the initial project structure.

---

**Long-term vision:** Recall Engine should become a personal knowledge-retention system that helps users continuously revisit, connect, and apply everything they learn without requiring them to manually organize their daily revision schedule.

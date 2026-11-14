
# Code Quality and Project Structure Guidelines

## 1. General Coding Standards

- Write clean, readable, maintainable, and production-quality code.
- Use meaningful variable, function, class, and file names.
- Add Python type hints and appropriate docstrings.
- Follow consistent formatting and naming conventions.
- Avoid duplicated code and unnecessary complexity.
- Do not write unnecessarily large functions or classes.
- Keep dependencies minimal.
- Avoid hardcoded configuration values.

## 2. Project Structure and Modularity

- Maintain a clear separation of responsibilities.
- Keep frontend and backend code independent.
- Organize code into logical modules and packages.
- Follow separation of concerns.
- Keep business logic separate from API routes.
- Keep API communication separate from frontend components.
- Use reusable components and utility functions.
- Use service and repository layers where appropriate.
- Avoid putting the entire application logic into a single file.
- Do not create abstractions unless they provide meaningful value.

## 3. Backend Code Quality

- Follow Python best practices and PEP 8.
- Keep FastAPI route handlers thin.
- Place business logic in service modules.
- Use Pydantic models for request and response validation.
- Use dependency injection where appropriate.
- Centralize configuration and exception handling.
- Use structured logging.
- Handle errors gracefully.
- Avoid global mutable state.
- Write reusable and testable functions.

## 4. Frontend Code Quality

- Use functional React components.
- Use TypeScript interfaces and types.
- Keep components small and focused.
- Separate UI rendering from business logic.
- Keep API calls in dedicated service modules.
- Use custom hooks for reusable stateful logic.
- Maintain consistent component and folder naming.
- Reuse common UI components.
- Avoid unnecessary prop drilling and duplicated state.
- Keep styling consistent and responsive.


## 5. Documentation

- Add comments only where they clarify non-obvious logic.
- Document complex functions and architectural decisions.
- Keep documentation updated when implementation changes.
- Maintain clear setup and execution instructions.

## 6. Development Discipline

- Inspect existing code before modifying it.
- Follow the established project structure.
- Avoid unnecessary changes to unrelated modules.
- Do not introduce placeholder implementations for completed features.
- Run relevant tests after making changes.
- Fix errors instead of ignoring them.
- Do not claim that tests or builds pass unless they have actually been executed.

---
name: PR Review Checklist
description: A pre-PR checklist based on historical maintainer remarks (Daksh and others) to ensure quality and scope compliance before opening any pull request. Trigger this skill before committing or creating a PR.
---

# PR Review Checklist

Before creating a Pull Request or completing a major feature, you **MUST** review the codebase against these maintainer requirements:

### 1. Preserve UX & Callbacks
- Do NOT break existing frontend callbacks (e.g., `onSelect`, `onViewDetails`, `onMarkerReady`) when refactoring or wrapping components. Ensure props are correctly drilled down so that user interactions like clicking markers and opening sidebars remain functional.

### 2. Code Cleanliness (Whitespace)
- Run `git diff --check` to identify and remove any trailing whitespaces or formatting artifacts introduced by your changes. Clean commits are required.

### 3. React StrictMode Integrity
- NEVER disable or remove `<React.StrictMode>` to hide bugs or lifecycle issues. If a library (like mapping or clustering) crashes under StrictMode, fix the underlying reference instability (e.g., using `useMemo` for stable object references).

### 4. Strict PR Scoping
- Keep the PR scoped strictly to its primary purpose. Do not sneak unrelated map behavior tweaks (like changing `minZoom`, `defaultCenter`, or unrelated styling) into a feature PR unless explicitly requested.

### 5. Efficient API Usage
- Do not introduce unused API calls. If a component fetches data (like `fetchDataGapsSummary`), ensure it actually consumes and renders that data. Remove dead state and unused imports.

### 6. Map Clustering
- Ensure clustering algorithms do not group distant coastal communities together, causing their centroids to fall in the ocean. Use appropriate thresholds (e.g., `maxClusterRadius={40}`) to keep clusters localized on land masses.

### 7. Frontend-Only Isolation
- For issues categorized as frontend performance or rendering improvements (like map clustering), do NOT modify backend databases, formula logic, or seed CSV files (e.g., coordinate adjustments). Keep the PR strictly focused on the frontend layers.

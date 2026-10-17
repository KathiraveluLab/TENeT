# Frontend engineering boundaries

Keep frontend changes small, behavior-preserving, and easy to review.

## Ownership boundaries

- `src/api` owns HTTP calls and the frontend contracts for backend responses. Components should not call endpoints directly.
- `src/hooks` owns reusable state, data-loading, and orchestration logic. Hooks should not own presentation.
- `src/components/ui` owns shared visual primitives; feature folders own feature composition and feature-specific styling.
- `src/types` owns shared domain types that span more than one feature. Keep local-only props and types beside their consumer.

## Change rules

- Maintain one shared design system in `src/components/ui`. Extend or migrate the existing primitives instead of creating a parallel set.
- Do not present inferred, partial, modeled, or unavailable data as an observed metric. Labels and supporting text must state the source or limitation clearly enough to avoid misleading users.
- When a shared primitive exists, use it instead of introducing raw styling for the same UI role. Dynamic values that cannot be represented by an existing class or token may remain inline.
- Every new abstraction must replace and delete or migrate the old code in the same change. Do not layer a second path over an obsolete one.

## Quality gates

- `npm run typecheck` checks the strict TypeScript project without emitting files.
- `npm run test` runs the Vitest unit and component tests once.
- `npm run build` creates the production Vite bundle.
- `npm run validate` runs typecheck, tests, and build in sequence.
- End-to-end coverage is available separately through `npm run e2e` because it requires a browser and an application/API environment.

ESLint and Prettier are not currently installed. No lint or format-check script is declared until those tools and an agreed configuration are added; a script that only aliases typechecking would be misleading.

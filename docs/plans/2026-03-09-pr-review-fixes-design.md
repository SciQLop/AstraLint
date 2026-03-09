# PR Review Fixes — Design

Addresses review feedback on PR #10 (feat/jinja2-message-templates).

## 1. Generalize path captures to all assertions

`BaseAssertion.evaluate()` switches from `resolve_path()` to `resolve_path_with_captures()`. Captured values merge into the Jinja2 context via `build_context(**extra)`, making `{{ var }}` available in any assertion's `message`.

`single_assertion()` gains a `captures: dict[str, str]` parameter (default `{}`). `CompareToAssertion` is unchanged (manages its own resolution).

## 2. Named regex groups in `parse_captures`

Replace positional index tracking with `(?P<name>pattern)` named groups. Extract via `match.group(name)` instead of `match.group(idx + 1)`.

Benefits:
- Duplicate capture names detected by Python's `re` engine automatically
- Nested capturing groups in custom patterns don't break indexing
- Simpler return type: just a list of capture names, no index map

## 3. Combinator `message` support

Add `message: str = Field(default="")` to `BaseAssertionGroup`.

In each combinator's `evaluate()`:
- If `self.message` is set: render as Jinja2 template with `{"valid": bool}` and relevant context (e.g. child result counts), use as result message
- If not set: use current hardcoded fallback (e.g. "Expected exactly 1 to pass in 'one_of', but 2 passed")

Optional override — backward-compatible, no behavior change for rules without `message`.

## 4. Error wrapping on template rendering

Wrap `render_message()` in try/except for `TemplateSyntaxError` and `UndefinedError`. On failure, return `"[template error: {error}] template: {template}"` instead of crashing the lint run.

## 5. Small fixes

- **`missing_keys` ordering**: pass `sorted(missing_keys)` instead of raw `frozenset` to template context
- **Doc examples**: use `{{ var }}` (Jinja2) in `message` fields, keep `{var}` for `path`/`other_path` captures
- **YAML rules**: verify `any_of` message fields in ISTP rules use correct Jinja2 syntax (they now work with section 3)

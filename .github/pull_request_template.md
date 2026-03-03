## Summary

Describe what changed and why.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Connector update
- [ ] Typology update
- [ ] Documentation only
- [ ] Refactor / maintenance

## Verification

List commands and outcomes.

```bash
uv run --extra test pytest -q
```

If frontend changed:

```bash
cd web
npm run lint
npm run build
```

## Data and Security Review

- [ ] No secrets/tokens/personal data were committed
- [ ] LGPD safeguards remain intact (no raw CPF persistence)
- [ ] Any new env vars are documented in `.env.example` and `README.md`

## Checklist

- [ ] Tests added/updated for behavior changes
- [ ] Docs updated (README/CONTRIBUTING/ARCHITECTURE) when relevant
- [ ] Backward compatibility considered for API/schema changes
- [ ] Related issues linked

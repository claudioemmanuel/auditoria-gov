# Dual-mode adapter layer.
# In monorepo mode (CORE_SERVICE_URL not set): delegates directly to shared.repo.
# In split mode (CORE_SERVICE_URL set): delegates to CoreClient (HTTP gateway).
# Post-split: the monorepo fallback branch is deleted entirely from this package.

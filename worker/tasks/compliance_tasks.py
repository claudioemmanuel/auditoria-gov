"""Weekly source compliance audit task.

Validates all connector base URLs against the domain guard, checks
exception review dates, probes API health, and updates the
coverage_registry with compliance status.
"""

from datetime import date, datetime, timedelta, timezone

import httpx
from celery import shared_task
from sqlalchemy import select

from shared.connectors import ConnectorRegistry
from shared.connectors.domain_guard import (
    DOMAIN_EXCEPTIONS,
    DomainNotAllowedError,
    validate_domain,
)
from shared.db_sync import SyncSession
from shared.logging import log
from shared.models.orm import CoverageRegistry

# Base URLs per connector (matches http_client.py factories)
_CONNECTOR_URLS: dict[str, str] = {
    "portal_transparencia": "https://api.portaldatransparencia.gov.br/api-de-dados",
    "compras_gov": "https://compras.dados.gov.br",
    "comprasnet_contratos": "https://compras.dados.gov.br",
    "pncp": "https://pncp.gov.br/api/consulta/v1",
    "transferegov": "https://api.transferegov.gestao.gov.br",
    "camara": "https://dadosabertos.camara.leg.br/api/v2",
    "senado": "https://legis.senado.leg.br/dadosabertos",
    "tse": "https://dadosabertos.tse.jus.br",
    "receita_cnpj": "https://dados.rfb.gov.br",
    "orcamento_bim": "https://www.gov.br",
    "querido_diario": "https://api.queridodiario.ok.org.br",
}


@shared_task(name="worker.tasks.compliance_tasks.check_source_compliance")
def check_source_compliance() -> dict:
    """Weekly compliance audit for all data sources.

    Steps:
    1. Validate all connector base URLs against domain guard
    2. Check DOMAIN_EXCEPTIONS review dates (warn if <30 days to expiry)
    3. HTTP HEAD probe to confirm APIs responding
    4. Update coverage_registry.compliance_status and last_compliance_check_at
    5. Log structured events for violations
    """
    log.info("check_source_compliance.start")

    now = datetime.now(timezone.utc)
    today = date.today()
    violations: list[dict] = []
    warnings: list[dict] = []
    checked = 0

    # Step 1 & 2: Validate domains and check exception expiry
    for connector_name in ConnectorRegistry:
        base_url = _CONNECTOR_URLS.get(connector_name, "")
        if not base_url:
            warnings.append({
                "connector": connector_name,
                "issue": "no_base_url_configured",
            })
            continue

        try:
            validate_domain(base_url)
        except DomainNotAllowedError as exc:
            violations.append({
                "connector": connector_name,
                "url": base_url,
                "issue": "domain_not_allowed",
                "detail": str(exc),
            })

    # Check exception review dates
    for domain, exc in DOMAIN_EXCEPTIONS.items():
        days_until_review = (exc.review_by - today).days
        if days_until_review < 0:
            violations.append({
                "domain": domain,
                "issue": "exception_expired",
                "review_by": exc.review_by.isoformat(),
                "days_overdue": abs(days_until_review),
            })
        elif days_until_review < 30:
            warnings.append({
                "domain": domain,
                "issue": "exception_expiring_soon",
                "review_by": exc.review_by.isoformat(),
                "days_remaining": days_until_review,
            })

    # Step 3: HTTP HEAD probes
    probe_results: dict[str, bool] = {}
    with httpx.Client(timeout=httpx.Timeout(10.0)) as client:
        for connector_name, url in _CONNECTOR_URLS.items():
            try:
                resp = client.head(url, follow_redirects=True)
                probe_results[connector_name] = resp.status_code < 500
            except (httpx.HTTPError, httpx.TimeoutException):
                probe_results[connector_name] = False
                warnings.append({
                    "connector": connector_name,
                    "issue": "api_unreachable",
                    "url": url,
                })

    # Step 4: Update coverage_registry
    violation_connectors = {v["connector"] for v in violations if "connector" in v}

    with SyncSession() as session:
        for name, cls in ConnectorRegistry.items():
            connector = cls()
            for job in connector.list_jobs():
                stmt = select(CoverageRegistry).where(
                    CoverageRegistry.connector == name,
                    CoverageRegistry.job == job.name,
                )
                cov = session.execute(stmt).scalar_one_or_none()
                if cov is None:
                    continue

                if name in violation_connectors:
                    cov.compliance_status = "violation"
                elif not probe_results.get(name, True):
                    cov.compliance_status = "warning"
                else:
                    cov.compliance_status = "ok"
                cov.last_compliance_check_at = now
                checked += 1

        session.commit()

    # Step 5: Log structured events
    for v in violations:
        log.warning("compliance.violation", **v)
    for w in warnings:
        log.info("compliance.warning", **w)

    log.info(
        "check_source_compliance.done",
        checked=checked,
        violations=len(violations),
        warnings=len(warnings),
    )
    return {
        "status": "completed",
        "checked": checked,
        "violations": len(violations),
        "warnings": len(warnings),
    }

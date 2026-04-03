"""Tests for source veracity scoring model."""

from shared.connectors import ConnectorRegistry
from shared.connectors.veracity import (
    SOURCE_VERACITY_REGISTRY,
    SourceVeracityProfile,
    DomainTier,
)


class TestCompositeScore:
    def test_composite_score_formula(self):
        profile = SourceVeracityProfile(
            government_domain=1.0,
            legal_authority=1.0,
            public_availability=1.0,
            official_api_documented=1.0,
            metadata_traceability=1.0,
            domain_tier=DomainTier.GOVERNMENT,
        )
        assert profile.composite_score == 1.0

    def test_composite_score_weighted(self):
        profile = SourceVeracityProfile(
            government_domain=0.5,
            legal_authority=0.5,
            public_availability=0.5,
            official_api_documented=0.5,
            metadata_traceability=0.5,
            domain_tier=DomainTier.GOVERNMENT,
        )
        assert profile.composite_score == 0.5

    def test_composite_score_mixed(self):
        profile = SourceVeracityProfile(
            government_domain=1.0,  # 0.40
            legal_authority=0.8,    # 0.20
            public_availability=0.6,  # 0.09
            official_api_documented=0.4,  # 0.04
            metadata_traceability=0.2,  # 0.02
            domain_tier=DomainTier.GOVERNMENT,
        )
        expected = 1.0 * 0.40 + 0.8 * 0.25 + 0.6 * 0.15 + 0.4 * 0.10 + 0.2 * 0.10
        assert profile.composite_score == round(expected, 4)


class TestLabels:
    def test_label_official(self):
        profile = SourceVeracityProfile(
            government_domain=1.0, legal_authority=1.0,
            public_availability=1.0, official_api_documented=1.0,
            metadata_traceability=0.75, domain_tier=DomainTier.GOVERNMENT,
        )
        assert profile.composite_score >= 0.95
        assert profile.veracity_label == "official"

    def test_label_high(self):
        profile = SourceVeracityProfile(
            government_domain=1.0, legal_authority=0.8,
            public_availability=0.8, official_api_documented=0.7,
            metadata_traceability=0.7, domain_tier=DomainTier.GOVERNMENT,
        )
        score = profile.composite_score
        assert 0.85 <= score < 0.95
        assert profile.veracity_label == "high"

    def test_label_acceptable(self):
        profile = SourceVeracityProfile(
            government_domain=0.5, legal_authority=0.8,
            public_availability=1.0, official_api_documented=0.9,
            metadata_traceability=0.8, domain_tier=DomainTier.EXCEPTION,
        )
        score = profile.composite_score
        assert 0.70 <= score < 0.85
        assert profile.veracity_label == "acceptable"

    def test_label_low(self):
        profile = SourceVeracityProfile(
            government_domain=0.0, legal_authority=0.3,
            public_availability=0.5, official_api_documented=0.2,
            metadata_traceability=0.2, domain_tier=DomainTier.EXCEPTION,
        )
        assert profile.composite_score < 0.70
        assert profile.veracity_label == "low"


class TestRegistryCoverage:
    def test_all_connectors_have_profiles(self):
        """Every connector:job in the ConnectorRegistry must have a veracity profile."""
        missing = []
        for name, cls in ConnectorRegistry.items():
            connector = cls()
            for job in connector.list_jobs():
                key = f"{name}:{job.name}"
                if key not in SOURCE_VERACITY_REGISTRY:
                    missing.append(key)
        assert missing == [], f"Missing veracity profiles: {missing}"

    def test_government_sources_above_90(self):
        """All government-domain sources should score >= 0.90."""
        for key, profile in SOURCE_VERACITY_REGISTRY.items():
            if profile.domain_tier == DomainTier.GOVERNMENT:
                assert profile.composite_score >= 0.90, (
                    f"{key} scored {profile.composite_score}, expected >= 0.90"
                )

    def test_querido_diario_below_85(self):
        profile = SOURCE_VERACITY_REGISTRY["querido_diario:qd_gazettes"]
        assert profile.composite_score < 0.85
        assert profile.domain_tier == DomainTier.EXCEPTION

    def test_senado_ceaps_is_official_after_codante_removal(self):
        profile = SOURCE_VERACITY_REGISTRY["senado:senado_ceaps"]
        assert profile.domain_tier == DomainTier.GOVERNMENT
        assert profile.composite_score >= 0.90

    def test_registry_count_matches_connector_jobs(self):
        total_jobs = 0
        for cls in ConnectorRegistry.values():
            connector = cls()
            total_jobs += len(connector.list_jobs())
        assert len(SOURCE_VERACITY_REGISTRY) == total_jobs

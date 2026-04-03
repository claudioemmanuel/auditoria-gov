# FAQ

## Is OpenWatch a commercial product?

No. It is an open-source public-interest project.

## Does the platform "prove" corruption?

No. It surfaces deterministic risk signals and evidence for investigation.

## Is AI used for scoring?

No. Detection and scoring are deterministic. Optional LLM usage is explanatory only.

## Can I run it locally?

Yes. The repository includes Docker Compose and setup instructions.

## Which data sources need credentials?

Portal da Transparencia jobs require a token. Most other sources are public.

## Where should I propose a new data connector?

Open an issue with the `new_connector` template.

## Can I search for entities by name?

Yes. `GET /public/entity/search?q=<text>&type=company|person&limit=20` performs fuzzy search using PostgreSQL pg_trgm. It supports accent-folded queries (e.g. `"joao"` matches `"João"`). Person results are LGPD-scoped to public-servant entities only.

## Can I find the connection between two entities?

Yes. `GET /public/graph/path?from=<entity_id>&to=<entity_id>&max_hops=5` returns the shortest path as an ordered list of nodes and edges, each labeled with `event_type`, `typology_ids`, and temporal bounds (`first_seen`, `last_seen`). Returns 404 when no path exists within `max_hops`.

## How does entity resolution affect signals?

After an ER merge, `entity.cluster_id` links formerly separate entities. The platform's query layer uses `resolve_entity_ids_with_clusters()` to expand any entity ID to its full cluster — so signals filed against a pre-merge UUID are correctly surfaced when querying the post-merge canonical entity.

---

## Conformidade Legal

## Isso é legal? Vocês podem expor isso publicamente?

Sim. A plataforma opera exclusivamente sobre dados de **transparência ativa obrigatória** — dados que os órgãos públicos são legalmente obrigados a publicar pela Lei de Acesso à Informação (Lei 12.527/2011, art. 8º) e pelo Decreto 7.724/2012. A Constituição Federal (art. 5º, XXXIII e art. 37, caput) garante o direito de qualquer cidadão acessar e analisar essas informações. Consulte [docs/COMPLIANCE.md](../docs/COMPLIANCE.md) para o respaldo legal completo.

## Como vocês tratam dados pessoais (LGPD)?

O tratamento tem base legal no art. 7º, VI da LGPD (exercício regular de direitos) e opera sobre dados publicados por obrigação legal. CPFs são **imediatamente anonimizados** via hash SHA-256 + salt configurado por variável de ambiente (`CPF_HASH_SALT`). O valor original do CPF nunca é armazenado. Dados hasheados são considerados dados anonimizados conforme o art. 12 da LGPD e, portanto, não são dados pessoais para fins da lei.

## Um servidor público pode me processar por usar essa plataforma?

A análise de dados de transparência ativa é exercício de direito constitucional garantido pelo art. 5º, XXXIII e XXXIV da CF/88, além do art. 74, §1º que assegura a qualquer cidadão legitimidade para denunciar irregularidades ao TCU. O STF, no RE 652.777, fixou a legitimidade da publicação de remuneração de servidores. A plataforma produz sinais investigáveis, não acusações. Para situações jurídicas específicas, consulte um advogado.

## Quem pode usar os dados desta plataforma?

Qualquer pessoa — a plataforma é pública, gratuita e de código aberto. É destinada a cidadãos, jornalistas, advogados, pesquisadores, auditores e órgãos de controle (CGU, TCU, MPF). Os dados analisados são públicos por determinação legal e não há restrição de uso para fins de controle social.

## Como faço para contestar um sinal que me afeta?

1. Consulte `GET /signal/{id}/provenance` para ver **todos os dados brutos** que geraram o sinal
2. Verifique a lógica da tipologia em `/methodology` e na documentação/código disponibilizados pela implantação ou repositório correspondente
3. Use `POST /public/contestation` para registrar uma impugnação formal com justificativa
4. Se houver erro de dados na fonte original (Portal da Transparência, PNCP etc.), reporte diretamente ao órgão responsável pela fonte

Lembre-se: sinais são hipóteses estatísticas para triagem, não acusações. A contestação é um mecanismo de correção técnica da plataforma.

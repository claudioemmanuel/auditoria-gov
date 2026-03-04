# FAQ

## Is AuditorIA Gov a commercial product?

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
2. Verifique a lógica da tipologia em `/methodology` — o código-fonte é aberto (AGPL-3.0)
3. Use `GET /contestation` para registrar uma impugnação formal com justificativa
4. Se houver erro de dados na fonte original (Portal da Transparência, PNCP etc.), reporte diretamente ao órgão responsável pela fonte

Lembre-se: sinais são hipóteses estatísticas para triagem, não acusações. A contestação é um mecanismo de correção técnica da plataforma.

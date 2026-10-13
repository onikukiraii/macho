from features.review._pure import build_review_prompt, to_findings
from features.review.types import FindingOutput, Severity


class TestBuildReviewPrompt:
    def test_契約書本文が入る(self) -> None:
        prompt = build_review_prompt("第1条 本契約は…", ["解除条項の有無"])

        assert "第1条 本契約は…" in prompt

    def test_観点は箇条書きになる(self) -> None:
        prompt = build_review_prompt("本文", ["解除条項の有無", "損害賠償の上限"])

        assert "- 解除条項の有無\n- 損害賠償の上限" in prompt

    def test_観点が1つでも箇条書きの記号が付く(self) -> None:
        assert "- 解除条項の有無" in build_review_prompt("本文", ["解除条項の有無"])


class TestToFindings:
    def test_LLM_出力をドメイン型に移す(self) -> None:
        outputs = [
            FindingOutput(severity=Severity.high, comment="解除条項がありません", quote="第5条"),
            FindingOutput(severity=Severity.low, comment="表記ゆれ", quote="第7条"),
        ]

        findings = to_findings(outputs)

        assert [finding.severity for finding in findings] == [Severity.high, Severity.low]
        assert findings[0].comment == "解除条項がありません"

    def test_空の出力は空のリスト(self) -> None:
        assert to_findings([]) == []

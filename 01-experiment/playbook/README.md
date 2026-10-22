# 실험 플레이북

> A/B 테스트와 인과추론을 실무에서 쓰면서 정리한 **판단 기준** 모음. 문서마다 "언제 쓰나 → 판단 기준 → 핵심 패턴 → 안티패턴" 순서로 쓰고, 식은 코드와 테스트로 검증한다.

## 구조

```
playbook/
├── docs/
│   ├── index.md              ← 질문으로 찾기 (이 질문이면 이 문서)
│   ├── decision-tree.md      ← 상황별 방법 고르기 (무작위 가능? → 유저 단위? → …)
│   ├── methods/              ← 방법론 문서. 모두 같은 4단 구조
│   │   ├── _template.md      ← 새 문서는 여기서 시작
│   │   ├── power-and-sample-size.md
│   │   └── z-vs-t.md
│   ├── forms/                ← 실험 설계서, 결과 보고서 양식
│   ├── roadmap.md            ← 다음에 쓸 문서와 순서
│   └── assets/               ← 그림 (스크립트로 다시 생성 가능)
├── src/playbook/             ← 문서의 식을 옮긴 함수 (표본 크기, 검정력, MDE, 다중 비교)
├── tests/                    ← 문서 예시값과 statsmodels 결과를 함께 맞추는 테스트
├── scripts/
│   ├── make_power_figures.py ← 그림 생성
│   └── validate_docs.py      ← 머리말, 섹션 순서, 링크 검사 (저장소 CI에서 실행)
```

## 빠른 시작

```bash
pip install -r ../../requirements.txt
python -m pytest tests -q          # 계산 검증
python scripts/validate_docs.py    # 문서 형식 검사
```

```python
# src/ 를 경로에 넣은 상태에서
from playbook import sample_size_per_group, mde_given_n

sample_size_per_group(p0=0.10, mde=0.01)   # 그룹당 14,749명
mde_given_n(p0=0.10, n_per_group=5_000)    # 5천 명으로 잡을 수 있는 최소 차이
```

## 지금 있는 문서

| 문서 | 답하는 질문 |
|---|---|
| [검정력과 표본 크기](docs/methods/power-and-sample-size.md) | 몇 명, 며칠? p > 0.05면 효과가 없는 건가? |
| [z 검정과 t 검정](docs/methods/z-vs-t.md) | 두 그룹 비교에 z와 t 중 무엇을? 표본이 크면 차이가 있나? |
| [방법 고르기](docs/decision-tree.md) | 무작위 배정이 안 되면 무엇을 쓰나? |
| [실험 설계서](docs/forms/experiment-design.md), [결과 보고서](docs/forms/results-report.md) | 실험 전에 무엇을 고정하고, 결과를 어떻게 보고하나? |

다음 문서 순서는 [로드맵](docs/roadmap.md)에 있다.

## 이렇게 만든 이유

- **안티패턴을 따로 둔다.** 방법을 아는 것보다 틀리는 지점을 아는 게 실무에서 더 쓸모 있다. 실무에서 직접 겪은 실수를 회사 정보 없이 일반화해 적는다.
- **문서의 숫자는 테스트가 지킨다.** 문서 예시값(그룹당 약 1만 4,750명 등)을 `tests/`가 같이 확인해서, 식을 고치면 문서와 코드가 함께 맞는지 드러난다.
- **형식은 CI가 지킨다.** 새 문서가 4단 구조나 머리말을 빼먹으면 저장소 검사가 실패한다.
- **모든 수치는 가상 시나리오다.** 실제 서비스 데이터는 쓰지 않는다.

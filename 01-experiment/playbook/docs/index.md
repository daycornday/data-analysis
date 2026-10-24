---
title: 실험 플레이북
category: 길잡이
question: 이 플레이북으로 무엇에 답할 수 있나?
related: []
status: active
updated: 2026-10-24
---

# 실험 플레이북

A/B 테스트와 인과추론을 실무에서 쓰면서 정리한 판단 기준 모음이다. 문서마다 **언제 쓰나 → 판단 기준 → 핵심 패턴 → 안티패턴** 순서로 쓴다. 안티패턴에는 실무에서 직접 겪은 실수를 회사 정보 없이 일반화해 적는다.

## 질문으로 찾기

| 이런 질문이 생기면 | 읽을 문서 |
|---|---|
| 어떤 방법을 써야 할지 모르겠다 | [방법 고르기](decision-tree.md) |
| 실험을 몇 명에게, 며칠 돌려야 하나? | [검정력과 표본 크기](methods/power-and-sample-size.md) |
| p값이 0.08이 나왔다. 효과가 없는 건가? | [검정력과 표본 크기](methods/power-and-sample-size.md) 안티패턴 2 |
| z 검정과 t 검정 중 무엇을 쓰나? | [z 검정과 t 검정](methods/z-vs-t.md) |
| 그룹이 셋이다. 어떻게 비교하나? | [다중 비교 보정](methods/multiple-comparisons.md) |
| 2차 지표를 스무 개 봤는데 하나가 유의하다 | [다중 비교 보정](methods/multiple-comparisons.md) 안티패턴 1 |
| 대조군이 이겼다. 어떻게 해석하나? | 작성 예정 |
| 한 유저가 여러 번 행동하는데 건수로 검정해도 되나? | 작성 예정 (delta method) |
| 무작위 배정을 못 하는데 효과를 재야 한다 | [방법 고르기](decision-tree.md) |

## 실험할 때 쓰는 양식

- [실험 설계서](forms/experiment-design.md): 실험 전에 고정할 것
- [결과 보고서](forms/results-report.md): 결과가 양성이든 음성이든 같은 틀로

## 코드

문서의 식은 `src/playbook/`에 함수로 있고, `tests/`에서 문서의 예시 계산과 statsmodels 결과를 함께 맞춰 본다.

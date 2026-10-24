# Data Analysis

분석하면서 생긴 질문을 직접 재현해 보고 기록해 두는 저장소입니다. 방법을 아는 데서 끝내지 않고, 정답을 알고 있는 데이터에서 그 방법이 실제로 맞는 답을 내는지 확인하는 데 초점을 두고 있습니다.

- 다루는 것: 실험 설계, 인과추론, 유저 분석, 마케팅 측정, 데이터 품질
- 데이터: 공개 데이터 또는 정답을 심어 둔 가상 데이터 (회사 데이터는 쓰지 않음)
- 폴더마다 결과와 함께 전제한 가정, 한계를 같이 적어 둠
- playbook은 2주에 한 편씩 추가 중이고, 변경 내역은 맨 아래 업데이트 기록에 남김

## 폴더

### [01. 실험](01-experiment/)
| 폴더 | 내용 |
|---|---|
| [playbook](01-experiment/playbook/) | 실험할 때 매번 다시 찾아보게 되는 판단 기준 노트 (2주에 한 편) |

### [02. 인과추론](02-causal-inference/)
| 폴더 | 내용 |
|---|---|
| [did-psm](02-causal-inference/did-psm/) | 실험이 안 될 때 효과 추정. 논문 공개 데이터로 재계산 |

### [03. 유저 분석](03-user-analysis/)
| 폴더 | 내용 |
|---|---|
| [markov-growth](03-user-analysis/markov-growth/) | 어느 상태 전이를 고쳐야 활성 유저가 가장 많이 느는지 |
| [segmentation](03-user-analysis/segmentation/) | 합이 1인 사용 비중으로 군집 나눌 때의 함정 (CLR + GMM) |
| [aha-moment](03-user-analysis/aha-moment/) | "N번 쓰면 남는다"의 N 고르기 (aha-ratio 대신 MCC) |

### [04. 마케팅 측정](04-marketing/)
| 폴더 | 내용 |
|---|---|
| [incrementality](04-marketing/incrementality/) | 기여와 증분의 차이, 홀드아웃, 지역 실험, MMM 비교 |

### [05. 데이터 품질](05-data-quality/)
| 폴더 | 내용 |
|---|---|
| [metric-mart](05-data-quality/metric-mart/) | 원본 로그에서 지표 테이블까지 SQL 레이어와 데이터 테스트 |
| [validation](05-data-quality/validation/) | "검증했다"를 단계로 나누고 흔한 버그를 검사로 잡기 |

### [06. 일하는 방식](06-workflow/)
| 폴더 | 내용 |
|---|---|
| [claude-code](06-workflow/claude-code/) | 반복 업무를 Claude Code 스킬, 훅으로 자동화한 구성 |

### [notes](notes/)
짧은 메모 (트래킹 유실, 예약 실행, SQL grain 체크리스트)

## 업데이트 기록

<!-- 새 기록은 표 맨 위에 추가 -->
| 날짜 | 내용 |
|---|---|
| 2026-10-24 | playbook: 다중 비교 보정 |
| 2026-10-22 | 주제별 폴더로 재구성, 문서 정리 |
| 2026-10-20 | playbook 2편 (검정력과 표본 크기, z 검정과 t 검정), 프로젝트 정리 시작 |

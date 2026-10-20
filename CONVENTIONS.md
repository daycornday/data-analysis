# 폴더 작성 규칙

이 저장소는 폴더 하나가 프로젝트 하나다. 모든 폴더가 같은 모양을 지킨다.

## 폴더 구조

```
<folder>/
├── README.md          # 아래 README 양식
├── run.py             # 이 폴더의 모든 숫자와 그림을 처음부터 재현한다 (2분 이내)
├── src/<pkg>/         # 계산 함수 (run.py와 tests가 import)
├── tests/             # pytest. 핵심 함수마다 1개 이상, 알려진 정답을 되찾는지 확인
├── data/              # 합성 데이터 생성 코드가 만든 파일 또는 작은 공개 데이터 사본 (출처, 라이선스를 README에)
└── outputs/           # run.py가 만드는 그림(png)과 결과 표(csv/md)
```

- 패키지 이름은 폴더 이름의 하이픈을 밑줄로 바꾼 것 (`growth-markov` → `growth_markov`)
- `tests/conftest.py`에서 `src`를 sys.path에 넣는다. 루트에서 `python -m pytest <folder>/tests`가 돌아야 한다
- run.py는 폴더 안에서 `python run.py`로 실행. 경로는 `Path(__file__).parent` 기준

## 환경

- Python 3.8 (f-string의 `=` 디버그, `match`, `list[int]` 타입 표기 금지)
- 쓸 수 있는 라이브러리: numpy, pandas, scipy, statsmodels, scikit-learn, matplotlib, sqlite3(표준). 그 밖은 쓰지 않는다
- 난수는 항상 시드 고정. 같은 시드면 README의 숫자가 그대로 나와야 한다
- matplotlib 한글: `plt.rcParams["font.family"] = "Malgun Gothic"`, `axes.unicode_minus = False`. 그림 제목과 축은 한국어

## README 양식 (순서 고정)

```markdown
# 제목

> 한 줄 요약: 이 프로젝트가 답하는 질문과 결론 한 문장

## 질문
실무에서 이 질문이 왜 생기는지 2~3줄

## 결론
숫자가 들어간 결과 3~5줄 (run.py가 실제로 낸 값만)

## 방법
단계별 설명. 식은 코드 블록이나 $$ 블록

## 결과
그림(outputs/)과 표, 해석

## 한계와 다음 단계
이 분석이 말해 주지 않는 것

## 실행
pip install -r ../requirements.txt
python run.py
python -m pytest tests

## 더 읽을 것
교재, 논문, 공개 기술 블로그 링크
```

## 금지

- 회사 이름, 사내 수치, 동료 이름, 사내 테이블명. 금지어: 미리디, 미리캔버스, 비즈하우스, 캐치테이블, 더에스엠씨, 유효채택, 서브큐, 요고, 토스, 카카오
- 가운뎃점 문자(U+00B7). 나열은 쉼표나 줄바꿈으로
- 실제로 실행하지 않은 숫자
- 설명할 수 없는 복잡한 코드. 함수는 짧게, 이름은 의미 그대로

## 문체

- 존댓말이 아니라 문서체(~다). 짧은 문장, 결론 먼저
- "혁신적", "강력한", "완벽한" 같은 홍보 문구 금지
- 이모지 금지

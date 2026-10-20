"""SQL 파일을 레이어 순서대로 실행한다 (dbt run을 아주 작게 흉내 낸 것)."""
import sqlite3
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"
LAYERS = ["01_staging", "02_marts", "03_metrics"]

# 같은 레이어 안에서 먼저 만들어야 하는 모델 (dim_users를 fct가 참조한다)
MART_ORDER = ["dim_users", "dim_date", "fct_orders", "fct_events"]


def connect(path=":memory:"):
    return sqlite3.connect(str(path))


def load_raw(conn, raw):
    """원본 DataFrame을 모두 TEXT 컬럼으로 적재한다. 원본은 타입을 믿지 않는다."""
    for name, df in raw.items():
        df.astype(object).to_sql(name, conn, if_exists="replace", index=False,
                                 dtype={c: "TEXT" for c in df.columns})


def sql_files(sql_dir=SQL_DIR):
    """실행 순서대로 정렬한 SQL 파일 목록."""
    files = []
    for layer in LAYERS:
        layer_files = sorted((Path(sql_dir) / layer).glob("*.sql"))
        if layer == "02_marts":
            layer_files.sort(key=lambda p: MART_ORDER.index(p.stem))
        files.extend(layer_files)
    return files


def run_model(conn, name, sql_dir=SQL_DIR):
    """모델 하나만 다시 만든다. 테스트에서 일부러 깨뜨린 뒤 재실행할 때 쓴다."""
    path = next(p for p in sql_files(sql_dir) if p.stem == name)
    conn.executescript(path.read_text(encoding="utf-8"))


def build(conn, sql_dir=SQL_DIR):
    """모든 모델을 순서대로 만든다. 만든 모델 이름 목록을 돌려준다."""
    built = []
    for path in sql_files(sql_dir):
        conn.executescript(path.read_text(encoding="utf-8"))
        built.append(path.stem)
    return built


def grain_of(path):
    """SQL 맨 위 주석 한 줄에서 grain 설명을 꺼낸다."""
    first = Path(path).read_text(encoding="utf-8").splitlines()[0]
    return first.split("grain:", 1)[1].strip() if "grain:" in first else ""

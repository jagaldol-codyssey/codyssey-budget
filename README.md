# 용돈 기입장

Python 표준 라이브러리만 사용하는 콘솔 가계부입니다. 거래 추가·수정·삭제, 조건 검색, 월별 요약, 카테고리·예산 관리, CSV 가져오기·내보내기를 지원합니다.

## 실행

Python 3.10 이상에서 저장소 폴더를 열고 실행합니다. 패키지 설치는 필요 없습니다.

```sh
python3 -m budget_app --help
python3 -m budget_app category add
python3 -m budget_app add
python3 -m budget_app list
```

첫 실행에 `data/`와 CSV 3개를 만듭니다. 비어 있는 저장 파일에는 헤더를 만듭니다. 카테고리가 없으면 거래를 추가할 수 없으므로 `category add`에서 `food`처럼 이름을 먼저 등록합니다.

`add`는 날짜 → 타입(`income`/`expense`) → 카테고리 → 양수 정수 금액 → 메모 → 태그 순으로 입력합니다. 메모·태그는 엔터로 생략할 수 있습니다. 태그는 쉼표로 구분합니다.

저장 폴더를 바꾸려면 **명령 앞에** `--data-dir`을 붙입니다. 이후 같은 폴더를 지정하면 저장된 내역을 이어서 사용합니다.

```sh
python3 -m budget_app --data-dir ./data/demo category add
python3 -m budget_app --data-dir ./data/demo add
```

## 주요 명령

아래 명령 앞에 `python3 -m budget_app`을 붙입니다. 모든 명령과 하위 명령에서 `--help`를 사용할 수 있습니다. `<id>`는 추가 후 출력되거나 목록에 표시된 거래 id로 바꿉니다.

| 명령 | 동작 |
| --- | --- |
| `add` | 대화형 거래 추가 |
| `list --limit 5` | 최신 거래 5건 조회, 기본 10건 |
| `search --from 2024-01-01 --to 2024-01-31 --category food --type expense --q 점심 --tag meal` | 모든 조건을 동시에 만족하는 거래 조회 |
| `update --id <id> --amount 18000 --memo 저녁` | 지정한 필드만 수정 |
| `delete --id <id>` | 해당 거래 삭제 |
| `summary --month 2024-01 --top 3` | 수입·지출·잔액, 지출 TOP 3, 예산 조회 |
| `budget set --month 2024-01 --amount 10000` | 월 예산 설정·변경 |
| `category add` / `category list` / `category remove` | 추가·삭제는 이름을 대화형으로 입력 |
| `export --out ./data/export.csv --month 2024-01` | 해당 월의 거래를 CSV로 저장 |
| `export --out ./data/export.csv --from 2024-01-01 --to 2024-01-31` | 해당 기간의 거래를 CSV로 저장 |
| `import --from ./data/export.csv` | CSV 전체 검증 후 새로운 거래로 추가 |

- 최신순은 **거래 날짜 내림차순**입니다. 같은 날짜에는 나중에 추가한 거래가 먼저 나옵니다. 검색 기간은 양 끝 날짜를 포함하고, 메모는 부분 일치, 태그는 정확히 일치하는 값으로 찾습니다.
- 수정은 **옵션 방식**입니다. `--date`, `--type`, `--category`, `--amount`, `--memo`, `--tags`를 지원하며 `--memo ""`, `--tags ""`로 내용을 비울 수 있습니다. id는 유지됩니다.
- 사용 중인 카테고리는 삭제할 수 없습니다. 예산 사용률은 해당 월의 총지출 ÷ 예산이며, 예산을 넘으면 경고합니다.
- export에는 월 또는 시작·종료 날짜가 필요합니다. 둘 다 지정하면 교집합을 내보냅니다. 기존 출력 파일은 덮어쓰지만 저장용 CSV 3개는 덮어쓸 수 없습니다.
- 잘못된 입력·파일 오류는 원인과 힌트를 표시하고 종료 코드 `1`로 끝납니다. 정상 종료는 `0`입니다.

## 저장 형식과 CSV 교환

모든 파일은 **UTF-8, 헤더 포함 CSV**입니다. `data/`는 Git에 포함하지 않습니다.

| 파일 | 컬럼 |
| --- | --- |
| `data/transactions.csv` | `id,date,type,category,amount,memo,tags` |
| `data/categories.csv` | `category` |
| `data/budgets.csv` | `month,amount` |

import/export에서는 id를 제외한 아래 스키마를 사용합니다. 앞의 네 컬럼은 필수이며, import에서 `memo`, `tags` 컬럼은 생략할 수 있습니다. 쉼표·줄바꿈·따옴표는 표준 `csv` 모듈이 처리합니다.

```csv
date,type,category,amount,memo,tags
2024-01-15,expense,food,15000,점심,"meal,office"
```

import는 등록된 카테고리만 허용합니다. 잘못된 행이 하나라도 있으면 **아무 거래도 반영하지 않고 중단**하므로 수정 후 다시 가져오면 됩니다. 성공한 파일을 다시 가져오면 새 id로 중복 추가됩니다. id는 UUID로 생성합니다.

## 코드를 읽는 순서

`__main__.py → cli.main() → service 함수 → Store` 순서로 실행됩니다.

| 파일 | 맡은 일 |
| --- | --- |
| [models.py](budget_app/models.py) | `Transaction` dataclass, 날짜·타입·금액 검증, CSV 행 변환 |
| [storage.py](budget_app/storage.py) | `Store`가 CSV 3개의 생성·읽기·쓰기를 담당 |
| [service.py](budget_app/service.py) | 거래·카테고리 규칙, 검색·요약, import/export |
| [cli.py](budget_app/cli.py) | 명령 옵션, `input()`·출력, `handle_errors` 데코레이터 |

평가에서 설명할 핵심은 다음과 같습니다.

- **제너레이터:** `read_csv → Store.transactions → search`가 `yield`로 한 건씩 전달합니다. 목록은 `islice`로 필요한 건수까지만 읽습니다. 파일을 저장할 때 정렬하므로 조회에서 전체 목록을 만들 필요가 없습니다.
- **수정·삭제:** 기존 거래 전체를 읽고 입력 검증·id 확인을 마친 뒤 재작성합니다. 잘못된 입력이나 읽기 오류가 원본을 지우지 않게 처리합니다. 쓰기 중 디스크 오류·강제 종료까지 복구하는 구조는 아니며, 동시 실행을 통한 수정은 지원하지 않습니다.
- **데코레이터:** `@handle_errors`가 CLI 전체의 예상 가능한 오류를 공통 처리합니다. 기능마다 같은 예외 출력 코드를 반복하지 않습니다.
- **타입 힌트:** `amount: int`, `Iterator[Transaction]`처럼 계산 대상과 전달하는 값의 형태를 보여 줍니다. 힌트 자체가 입력을 검사하지는 않으며 `from_row()`가 문자열 금액을 검증·변환합니다.
- **CSV 선택:** 거래가 평평한 필드 구조이고 import/export도 CSV라서 같은 모듈을 재사용합니다. JSONL은 중첩 자료·배열 표현이 편하지만, 여기서는 CSV의 헤더와 행으로 충분합니다.
- **10만 건일 때:** 목록은 필요한 행까지만 읽고 검색·요약은 전체를 순회합니다. 쓰기는 전체를 메모리에 담아 정렬·재작성하므로 병목입니다. 더 커지면 날짜·카테고리 인덱스를 둔 SQLite 같은 저장소로 바꾸는 방향을 설명할 수 있습니다.

## 동료평가 확인

1. `category add`로 `food`를 등록하고 `add`에 `2024-01-15`, `expense`, `food`, `15000`, `점심`, `meal`을 입력합니다.
2. `list`를 다시 실행해 저장된 id를 확인하고, 위 표의 `search` 명령으로 같은 거래를 찾습니다.
3. 월 예산을 `10000`으로 설정하고 `summary`에서 총지출 `15000`, 잔액 `-15000`, 사용률 `150.0%`, 초과 경고를 확인합니다.
4. `update`로 금액을 바꾼 뒤 export/import를 실행해 처리 건수와 파일을 확인합니다. `category remove`에서 `food` 삭제가 차단되는지 확인합니다.
5. `delete`로 거래를 지우고 같은 id를 다시 삭제해 오류 메시지를 확인합니다. 바로 `echo $?`를 실행하면 `1`이 나옵니다.

[미션](MISSION.md)과 [평가표](EVALUATION.md)의 필수 기능·오류 조건은 임시 폴더를 사용하는 통합 테스트로도 확인할 수 있습니다. 테스트는 명령마다 새 프로세스를 실행하므로 재실행 후 데이터 유지도 검증합니다.

```sh
python3 -m unittest discover -s tests -v
```

# 동료평가 실행 가이드

Python 3.10 이상, macOS/Linux의 bash 또는 zsh에서 저장소 폴더를 열고 실행한다. 아래 순서대로 한 번씩 실행하면 예상 결과와 일치한다.

## 1. 초기 데이터 준비

```sh
python3 scripts/seed_demo.py
```

실행할 때마다 기본 `data/` 폴더의 기존 내용 전체를 삭제하고 초기 데이터를 다시 넣는다. 평가를 처음부터 다시 시작할 때도 같은 명령을 실행하면 된다.

생성 파일: `transactions.csv`, `categories.csv`, `budgets.csv`, `import-ok.csv`, `import-invalid.csv`.
평가용 거래는 명령을 그대로 복사할 수 있도록 고정 id `demo-001`부터 `demo-007`을 사용한다. 실제 `add`와 `import`는 UUID를 생성한다. 데이터는 Git에서 제외되는 `data/` 안에 저장된다.

| 초기 상태 | 값 |
| --- | --- |
| 전체 거래 | 7건: 9월 1건, 10월 5건, 11월 1건 |
| 10월 수입 / 지출 / 잔액 | 300000 / 74500 / 225500원 |
| 10월 지출 순위 | rent 50000, food 20000, transport 4500원 |
| 10월 예산 / 사용률 | 70000원 / 106.4%, 초과 경고 |

## 2. 도움말·목록·검색

```sh
python3 -m budget_app --help
python3 -m budget_app search --help
python3 -m budget_app list
python3 -m budget_app list --limit 2
```

모든 명령에서 `--help`를 사용할 수 있다. 목록은 날짜 최신순이며, 2건 제한 시 `demo-007`, `demo-006` 순으로 나온다.

```sh
python3 -m budget_app search --from 2026-10-01 --to 2026-10-31
python3 -m budget_app search --category food --type expense --q 점심 --tag office
python3 -m budget_app search --from 2026-10-20 --to 2026-10-20
python3 -m budget_app search --tag 없는태그
```

순서대로 10월 거래 5건, `demo-006` 1건, `demo-006` 1건, `데이터 없음`이 나온다. 날짜 경계 포함, 조건의 AND 결합, 메모 부분 일치와 태그 정확 일치를 확인한다.

## 3. 월별 요약·예산

```sh
python3 -m budget_app summary --month 2026-10 --top 2
python3 -m budget_app summary --month 2026-12
python3 -m budget_app budget set --month 2026-10 --amount 74500
python3 -m budget_app summary --month 2026-10
python3 -m budget_app budget set --month 2026-10 --amount 100000
python3 -m budget_app summary --month 2026-10
```

첫 요약은 위 초기 상태와 같고 TOP 2에는 rent와 food만 나온다. 12월은 `데이터 없음`이다. 예산 변경 후 사용률은 각각 `100.0%`, `74.5%`이며 둘 다 초과 경고가 없다. 별도 명령으로 다시 조회해 예산 영구 저장도 확인한다.

## 4. 카테고리 추가·조회·삭제

```sh
python3 -m budget_app category add
```

카테고리명에 `hobby`를 입력한다.

```sh
python3 -m budget_app category list
python3 -m budget_app category remove
```

목록에 hobby가 있는지 확인하고, 삭제 이름으로 `hobby`를 입력한다. 이후 다음 명령에서는 `food`를 입력한다.

```sh
python3 -m budget_app category remove
python3 -m budget_app category list
```

food는 사용 중이라 삭제가 거절된다. 목록에는 food가 남고 hobby는 없어야 한다.

## 5. 거래 추가·수정·삭제

```sh
python3 -m budget_app add
```

아래 값을 질문 순서대로 입력한다. 10월 집계에 영향을 주지 않도록 11월 거래로 추가한다.

```text
2026-11-02
expense
food
9000
평가용 점심
meal,test
```

생성된 id가 출력되고 최신 목록에 추가된다. 수정·삭제는 초기 데이터의 고정 id로 실행한다.

```sh
python3 -m budget_app list --limit 2
python3 -m budget_app update --id demo-007 --amount 7000 --memo "수정한 간식" --tags ""
python3 -m budget_app search --from 2026-11-01 --to 2026-11-01
python3 -m budget_app delete --id demo-007
python3 -m budget_app search --from 2026-11-01 --to 2026-11-01
python3 -m budget_app delete --id demo-007
```

수정 후 id는 유지되고 금액은 7000원, 메모는 `수정한 간식`, 태그는 빈 값이다. 삭제 후 검색은 `데이터 없음`이며, 같은 id 재삭제는 없는 데이터 오류가 나온다.

## 6. CSV 내보내기·가져오기

```sh
python3 -m budget_app export --month 2026-10 --out "data/export-month.csv"
python3 -m budget_app export --from 2026-10-15 --to 2026-10-20 --out "data/export-range.csv"
cat "data/export-month.csv"
python3 -m budget_app import --from "data/import-ok.csv"
python3 -m budget_app summary --month 2026-10
```

내보내기는 각각 5건, 3건이다. 헤더는 `date,type,category,amount,memo,tags`이며 id는 제외된다. 정상 가져오기는 `imported=2`이고, 이후 10월 지출은 79500원, 잔액은 220500원, 사용률은 `79.5%`다. 같은 CSV를 다시 가져오면 중복 추가되므로 한 번만 실행한다.

잘못된 CSV는 두 번째 거래의 금액이 음수다. 정상인 첫 거래까지 포함해 아무것도 반영되지 않는지 확인한다.

```sh
python3 -m budget_app import --from "data/import-invalid.csv"
python3 -m budget_app summary --month 2026-10
```

가져오기는 `레코드 2` 오류가 나온다. 이후 요약의 지출 79500원, 잔액 220500원이 그대로인지 확인한다.

## 7. 오류 처리·자동 테스트

아래 오류 명령은 각각 원인과 해결 힌트를 출력한다.

```sh
python3 -m budget_app list --limit 0
python3 -m budget_app update --id demo-006 --amount -1
python3 -m budget_app import --from "data/missing.csv"
python3 -m budget_app export --out "data/no-filter.csv"
python3 -m unittest discover -s tests -v
```

자동 테스트는 별도 임시 폴더를 사용하므로 평가용 데이터를 바꾸지 않는다. 현재 16개 테스트가 기능·오류 처리·데이터 유지·스트리밍 동작을 검증한다.

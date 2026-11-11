import csv                                   # CSV(쉼표로 나뉜 표) 파일을 읽는 파이썬 기본 도구예요
from pathlib import Path                     # 파일 위치(경로)를 쉽게 다루는 도구예요

# 이 파일(data.py)이 있는 D21-flask 폴더 안 → data 폴더 → classes.csv
# (폴더 안에 있어야 이 폴더만 서버에 올려도 CSV가 같이 가요)
CSV_PATH = Path(__file__).parent / "data" / "classes.csv"


def to_number(text):                         # 글자를 숫자로 바꿔 주는 도우미예요
    text = text.strip()                      # 앞뒤 빈 공간을 지워요
    if text == "":                           # 빈칸이면
        return None                          # 0이 아니라 "값 없음(None)"으로 돌려줘요
    return float(text)                       # 글자가 있으면 숫자로 바꿔요 (예: "25000.0" → 25000.0)


def load_classes():                          # CSV를 읽어서 클래스 목록(리스트)을 만들어 주는 함수예요
    classes = []                             # 클래스를 하나씩 담을 빈 바구니예요
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:   # 파일을 열어요 (utf-8-sig: 한글 + 맨 앞 숨은 글자 처리)
        for row in csv.DictReader(f):        # 한 줄씩 꺼내요. row["정가"]처럼 칸 이름으로 값을 꺼낼 수 있어요
            price = to_number(row["정가"])     # 정가 (빈칸이면 None)
            discount = to_number(row["할인가"])  # 할인가 (빈칸이면 None)
            rating = to_number(row["평점"])    # 평점 (빈칸이면 None)

            if price is not None:            # 정가가 있으면
                price = int(price)           # 25000.0 → 25000 처럼 소수점을 떼요
            if discount is not None:         # 할인가가 있으면
                discount = int(discount)     # 마찬가지로 소수점을 떼요

            if discount is not None:         # 할인가가 있으면
                sale_price = discount        # 판매가 = 할인가
            else:                            # 할인가가 없으면
                sale_price = price           # 판매가 = 정가 (정가도 없으면 None 그대로)

            on_sale = (                      # 할인 중인지 알아봐요 (참/거짓)
                discount is not None         # 할인가가 있고
                and price is not None        # 정가도 있고
                and discount < price         # 할인가가 정가보다 싸면 → 할인 중!
            )

            classes.append({                 # 정리한 값을 사전(dict)으로 묶어서 바구니에 넣어요
                "id": int(row["id"]),                       # 번호
                "category": row["카테고리"],                 # 카테고리 (예: 공예)
                "region": row["지역"],                       # 지역 (예: 서울 성수)
                "title": row["클래스명"],                    # 클래스 이름
                "price": price,                             # 정가 (없으면 None)
                "sale_price": sale_price,                   # 판매가 (없으면 None)
                "on_sale": on_sale,                         # 할인 중이면 True
                "rating": rating,                           # 평점 (없으면 None)
                "reviews": int(row["리뷰수"] or 0),          # 리뷰 수 (빈칸이면 0개)
            })
    return classes                           # 다 담은 바구니를 돌려줘요


def get_class(class_id):                     # 번호로 클래스 하나를 찾아 주는 함수예요
    for c in load_classes():                 # 클래스를 하나씩 꺼내 보면서
        if c["id"] == class_id:              # 번호가 같으면
            return c                         # 그 클래스를 돌려줘요
    return None                              # 끝까지 못 찾으면 "없음(None)"을 돌려줘요


def get_categories(classes):                 # 카테고리 이름만 중복 없이 뽑는 함수예요
    names = {c["category"] for c in classes} # { } 집합에 넣으면 같은 이름은 한 번만 남아요
    return sorted(names)                     # 가나다순으로 줄 세워 돌려줘요


def filter_and_sort(classes, category="", sort=""):   # 카테고리로 거르고, 정렬하는 함수예요
    result = classes                         # 일단 전부 가져와요

    if category:                             # 카테고리를 골랐으면 (빈 글자가 아니면)
        result = [c for c in result if c["category"] == category]   # 그 카테고리만 남겨요

    if sort == "price":                      # 싼 순 정렬이면
        result = sorted(result, key=lambda c: (
            c["sale_price"] is None,         # 가격 없는 것(True)은 뒤로, 있는 것(False)은 앞으로
            c["sale_price"] or 0,            # 그다음 판매가가 작은 순서로
        ))
    elif sort == "rating":                   # 평점순 정렬이면
        result = sorted(result, key=lambda c: (
            c["rating"] is None,             # 평점 없는 것은 뒤로
            -(c["rating"] or 0),             # 평점이 높은 순서로 (- 를 붙이면 큰 게 앞으로 와요)
            -c["reviews"],                   # 평점이 같으면 리뷰가 많은 순서로
        ))

    return result                            # 거르고 정렬한 결과를 돌려줘요


def get_stats(classes):                      # 통계 숫자들을 계산하는 함수예요
    prices = [c["sale_price"] for c in classes if c["sale_price"] is not None]   # 판매가가 있는 것만 모아요 (빈칸 빼기)
    ratings = [c["rating"] for c in classes if c["rating"] is not None]          # 평점이 있는 것만 모아요 (빈칸 빼기)

    by_category = {}                         # 카테고리별 개수를 적을 빈 공책이에요
    for c in classes:                        # 클래스를 하나씩 보면서
        name = c["category"]                 # 카테고리 이름을 꺼내고
        by_category[name] = by_category.get(name, 0) + 1   # 그 이름 칸의 숫자를 1 올려요 (처음이면 0에서 시작)

    return {
        "total": len(classes),                                           # 전체 개수
        "avg_sale_price": round(sum(prices) / len(prices)) if prices else None,   # 평균 판매가 (원 단위 반올림, 하나도 없으면 null)
        "price_inquiry_count": len(classes) - len(prices),              # 가격 문의 수 = 전체 - 가격 있는 것
        "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,  # 평균 평점 (소수 둘째 자리, 하나도 없으면 null)
        "no_review_count": len(classes) - len(ratings),                 # 리뷰 없음 수 = 전체 - 평점 있는 것
        "by_category": dict(sorted(by_category.items())),               # 카테고리별 개수 (가나다순)
    }


def won(number):                             # 숫자를 "25,000원" 모양으로 바꾸는 도우미예요
    return f"{number:,}원"                    # :, 는 세 자리마다 쉼표를 찍어 줘요

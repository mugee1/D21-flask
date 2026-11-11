import os                                # 컴퓨터의 환경변수(바깥 설정값)를 읽는 파이썬 기본 도구예요
from datetime import timedelta           # "30일" 같은 기간을 나타내는 파이썬 기본 도구예요
from pathlib import Path                 # 파일 위치(경로)를 쉽게 다루는 도구예요
from dotenv import load_dotenv           # .env 파일에 적힌 값을 환경변수로 불러오는 도구예요 (python-dotenv)
from flask import Flask, render_template, request, abort, jsonify, redirect, url_for, flash, session   # + redirect: 다른 주소로 보내기, url_for: 함수 이름으로 주소 만들기, flash: 한 번만 보이는 안내, session: 방문자별 보관함
from data import load_classes, get_class, get_categories, filter_and_sort, get_stats, won   # data.py에서 만든 함수들을 가져와요
from db import init_db, add_review, get_reviews, get_review_stats   # db.py에서 만든 함수들: 표 만들기, 후기 넣기, 후기 꺼내기, 평균 계산

load_dotenv(Path(__file__).parent / ".env")   # 이 폴더의 .env 파일을 읽어서 환경변수로 넣어요 (파일이 없으면 조용히 넘어가요 → 서버에서는 서버 설정값을 써요)

app = Flask(__name__)                    # 내 웹사이트(앱)를 하나 만들어요. 이름은 app이에요
app.add_template_filter(won, "won")      # 템플릿에서 {{ 숫자|won }} 이라고 쓰면 "25,000원"으로 바뀌게 등록해요
app.json.ensure_ascii = False            # JSON에서 한글을 공 같은 암호 대신 "공예" 그대로 보내요
app.json.sort_keys = False               # JSON 칸 순서를 가나다/abc로 섞지 말고 내가 쓴 순서대로 보내요
# 세션·flash는 브라우저 쿠키에 담기는데, 남이 내용을 고치지 못하게 이 비밀 열쇠로 도장(서명)을 찍어요
# 열쇠는 코드에 적지 않고 .env(내 컴퓨터) 또는 서버 환경변수에서만 읽어요 → git에 비밀이 올라가지 않아요
app.secret_key = os.environ.get("SECRET_KEY")   # 환경변수에서 열쇠를 꺼내요 (없으면 None)
if not app.secret_key:                   # 열쇠가 없으면 (.env를 안 만들었거나 서버에 설정을 안 했으면)
    raise RuntimeError(                  # 여기서 바로 멈추고 이유를 알려줘요 (열쇠 없이 켜져서 나중에 엉뚱한 에러가 나는 것보다 나아요)
        "SECRET_KEY가 없어요. .env.example을 복사해 .env를 만들고 SECRET_KEY 값을 채워 주세요."
    )
app.permanent_session_lifetime = timedelta(days=30)   # 찜 목록을 브라우저를 껐다 켜도 30일 동안 기억해요

init_db()                                # 서버가 켜질 때 reviews.db에 후기 표가 없으면 만들어요 (있으면 그대로 둬요)


def get_wishlist():                      # 세션에서 내 찜 목록(클래스 번호 리스트, 예: [3, 1])을 꺼내는 도우미예요
    return session.get("wishlist", [])   # 한 번도 찜한 적 없으면 빈 리스트를 돌려줘요


@app.context_processor                   # 모든 화면(템플릿)에 자동으로 값을 건네주는 장치예요
def inject_wish_count():                 # 메뉴의 "찜 목록 (개수)"는 모든 화면에 있으니 여기서 한 번에 건네요
    return {"wish_count": len(get_wishlist())}   # 템플릿에서 {{ wish_count }}로 써요


@app.route("/")                          # 누군가 주소 / (첫 화면)로 들어오면
def home():                              # 아래 home 함수가 일을 해요
    classes = load_classes()             # CSV에서 클래스 목록을 읽어 와요
    return render_template(              # home.html 화면을 보여줘요
        "home.html",
        total=len(classes),              # 전체 클래스 개수를 total이라는 이름으로 건네줘요
        categories=get_categories(classes),   # 카테고리 이름 목록도 건네줘요 (버튼 만들 때 써요)
        counts={cat: sum(1 for c in classes if c["category"] == cat) for cat in get_categories(classes)},   # 카테고리별 클래스 개수 (뱃지 설명글에 써요)
    )


@app.route("/about")                     # 누군가 주소 /about (소개 페이지)로 들어오면
def about():                             # 아래 about 함수가 일을 해요
    return render_template("about.html") # templates 폴더의 about.html 화면을 보여줘요


@app.route("/hello/<name>")              # 주소 /hello/ 뒤에 쓴 이름을 name이라는 상자에 담아요 (어떤 이름이든 OK)
def hello(name):                         # 이름이 담긴 name 상자를 들고 hello 함수가 일을 해요
    return render_template("hello.html", name=name)  # hello.html 화면에 name 상자를 같이 건네줘요


@app.route("/classes")                   # 누군가 주소 /classes (클래스 목록)로 들어오면
def class_list():                        # 아래 class_list 함수가 일을 해요
    category = request.args.get("category", "")   # 주소의 ?category=공예 에서 "공예"를 꺼내요 (없으면 빈 글자)
    sort = request.args.get("sort", "")           # 주소의 ?sort=price 에서 "price"를 꺼내요 (없으면 빈 글자)
    all_classes = load_classes()                  # CSV에서 전체 클래스를 읽어 와요
    shown = filter_and_sort(all_classes, category, sort)   # 고른 조건대로 거르고 정렬해요
    return render_template(                       # classes.html 화면을 보여줘요
        "classes.html",
        classes=shown,                            # 화면에 보여줄 클래스들
        categories=get_categories(all_classes),   # 고르는 상자에 넣을 카테고리 목록
        category=category,                        # 지금 고른 카테고리 (상자에 선택된 채로 보이게)
        sort=sort,                                # 지금 고른 정렬 (상자에 선택된 채로 보이게)
        wished=set(get_wishlist()),               # 내가 찜한 번호 묶음 → 카드마다 ♡/♥ 중 무엇을 보일지 정해요 (set: "들어 있나?"를 빨리 확인)
    )


@app.route("/class/<int:class_id>", methods=["GET", "POST"])   # 주소 /class/번호 · GET(화면 보기)과 POST(후기 저장) 둘 다 받아요
def class_detail(class_id):              # 번호가 담긴 class_id를 들고 class_detail 함수가 일을 해요
    c = get_class(class_id)              # 그 번호의 클래스를 찾아요
    if c is None:                        # 못 찾았으면 (예: /class/999)
        abort(404)                       # 여기서 멈추고 "404 없음" 에러를 내요 → 아래 not_found가 받아요

    error = None                         # 잘못 입력했을 때 보여줄 안내 문구 (처음엔 없음)
    form = {}                            # 사용자가 적었던 값 (에러가 나도 다시 적지 않게 채워 두려고 써요)

    if request.method == "POST":         # 저장 버튼을 눌러서 POST로 들어왔으면
        form = request.form              # form 칸에 적힌 값들을 통째로 꺼내요
        nickname = form.get("nickname", "").strip()   # 닉네임 칸 (strip: 앞뒤 빈칸 지우기 → 띄어쓰기만 넣으면 빈 글자가 돼요)
        rating = form.get("rating", "")               # 별점 칸 (form 값은 항상 글자로 와요: 5가 아니라 "5")
        content = form.get("content", "").strip()     # 후기 내용 칸

        if not nickname:                 # 닉네임이 비어 있으면
            error = "닉네임을 적어 주세요."
        elif rating not in ["1", "2", "3", "4", "5"]:   # 별점이 1~5 글자가 아니면 (안 골랐거나 이상한 값)
            error = "별점을 1~5 중에서 골라 주세요."
        elif not content:                # 후기 내용이 비어 있으면
            error = "후기 내용을 적어 주세요."
        else:                            # 셋 다 괜찮으면 저장해요
            add_review(class_id, nickname, int(rating), content)   # reviews.db 표에 한 줄 넣어요 (별점은 "5" 글자 → 5 숫자로 바꿔서 · 시각은 DB가 자동으로 적어요)
            flash("후기가 저장됐어요!")    # 다음 화면에서 딱 한 번만 보여줄 안내를 남겨요 (한 번 꺼내 보면 사라져요)
            return redirect(url_for("class_detail", class_id=class_id, _anchor="reviews"))   # 저장 끝 → 같은 주소로 다시 보내요 (302). 새로고침해도 두 번 저장되지 않아요. #reviews: 후기 자리로 스크롤

    reviews = get_reviews(class_id)      # reviews.db에서 이 클래스의 후기만 최신순으로 꺼내요
    stats = get_review_stats(class_id)   # 후기 수와 평균 별점도 계산해요 (예: {"count": 3, "avg": 4.3})
    status = 400 if error else 200       # 잘못 입력했으면 400(요청이 잘못됨), 아니면 200(정상)
    is_wished = class_id in get_wishlist()   # 이 클래스를 이미 찜했는지 (참/거짓) → 버튼 글자를 바꿔요
    return render_template("detail.html", c=c, reviews=reviews, stats=stats, error=error, form=form, is_wished=is_wished), status   # 화면 + 상태코드를 같이 돌려줘요


@app.route("/class/<int:class_id>/wish", methods=["POST"])   # 찜하기/찜 취소 주소 · 값을 바꾸는 일이라 POST만 받아요 (GET으로 오면 Flask가 405를 내요)
def set_wish(class_id):                  # 버튼이 "찜해줘(on)" 또는 "취소해줘(off)"를 정확히 말해 주면 그대로 해요
    if get_class(class_id) is None:      # 없는 클래스 번호면
        abort(404)                       # 404로 멈춰요 (이상한 번호가 찜 목록에 들어가지 않게)

    want = request.form.get("want")      # 버튼의 숨은 칸 want: "on"(찜해줘) 또는 "off"(취소해줘)
    wishlist = get_wishlist()            # 지금 찜 목록을 꺼내요
    without_me = [i for i in wishlist if i != class_id]   # 이 클래스를 뺀 목록 (찜이든 아니든 일단 빼 둬요)
    if want == "on":                     # "찜해줘"면
        wishlist = [class_id] + without_me   # 맨 앞에 붙여요 (이미 찜했어도 한 번만 들어가요 · 최근에 찜한 게 맨 위)
    elif want == "off":                  # "취소해줘"면
        wishlist = without_me            # 뺀 목록 그대로 (이미 취소됐어도 그대로 취소 상태)
    else:                                # on도 off도 아니면 (주소를 직접 조작한 경우 등)
        abort(400)                       # 400(요청이 잘못됨)으로 멈춰요
    # 옛날 화면에서 눌러도 "누른 버튼에 적힌 대로" 돼요 → 찜하기를 눌렀는데 취소되는 일이 없어요

    session["wishlist"] = wishlist       # 바뀐 목록을 세션에 다시 넣어요 (새 리스트로 바꿔 끼워야 Flask가 "바뀌었다"를 알아채요)
    session.permanent = True             # 브라우저를 닫아도 30일 동안 기억하게 해요

    next_page = request.form.get("next")  # 어느 화면에서 눌렀는지 (숨은 칸 next)
    if next_page == "wishlist":          # 찜 목록 화면에서 누른 거라면
        return redirect(url_for("wishlist"))     # 찜 목록으로 돌아가요 (PRG: 302)
    if next_page == "classes":           # 클래스 목록 화면에서 누른 거라면
        return redirect(url_for(         # 목록으로 돌아가요 (PRG: 302)
            "class_list",
            category=request.form.get("category") or None,   # 고른 카테고리 유지 (없으면 주소에서 빼요)
            sort=request.form.get("sort") or None,           # 고른 정렬 유지 (없으면 주소에서 빼요)
            _anchor=f"class-{class_id}", # #class-3: 방금 누른 카드 자리로 스크롤 → 맨 위로 튀지 않아요
        ))                               # url_for로 우리 사이트 주소만 만들어서, 바깥 사이트로 보내질 걱정이 없어요
    return redirect(url_for("class_detail", class_id=class_id))   # 아니면 그 상세 화면으로 돌아가요 (PRG: 302 · 새로고침해도 또 바뀌지 않아요)


@app.route("/wishlist")                  # 주소 /wishlist (내 찜 목록)로 들어오면
def wishlist():                          # 아래 wishlist 함수가 일을 해요 (그냥 보기만 하니 GET)
    by_id = {c["id"]: c for c in load_classes()}   # 전체 클래스를 {번호: 클래스} 사전으로 만들어요 (번호로 바로 찾으려고)
    classes = [by_id[i] for i in get_wishlist() if i in by_id]   # 찜한 번호 순서대로 클래스를 꺼내요 (CSV에서 사라진 번호는 건너뛰어요)
    return render_template("wishlist.html", classes=classes)    # wishlist.html 화면에 찜한 클래스들을 건네줘요


# ---------- 여기부터 JSON 주소(API): 사람 대신 프로그램이 읽어 가는 데이터 ----------

@app.route("/api/classes")               # 주소 /api/classes 로 들어오면
def api_classes():                       # 아래 api_classes 함수가 일을 해요
    category = request.args.get("category", "")   # ?category=공예 에서 "공예"를 꺼내요 (없으면 빈 글자)
    classes = filter_and_sort(load_classes(), category)   # 전체를 읽고, 카테고리를 골랐으면 걸러요
    return jsonify({                     # 사전(dict)을 JSON으로 바꿔서 보내요 (None은 자동으로 null이 돼요)
        "count": len(classes),           # 개수
        "category": category or None,    # 고른 카테고리 (안 골랐으면 null)
        "classes": classes,              # 클래스 목록
    })


@app.route("/api/classes/<int:class_id>")   # 주소 /api/classes/ 뒤의 숫자를 class_id 상자에 담아요
def api_class(class_id):                 # 아래 api_class 함수가 일을 해요
    c = get_class(class_id)              # 그 번호의 클래스를 찾아요
    if c is None:                        # 못 찾았으면
        return jsonify({"error": f"{class_id}번 클래스를 찾을 수 없어요"}), 404   # JSON 에러 메시지 + 진짜 404
    return jsonify(c)                    # 찾았으면 그 클래스 하나를 JSON으로 보내요


@app.route("/api/stats")                 # 주소 /api/stats 로 들어오면
def api_stats():                         # 아래 api_stats 함수가 일을 해요
    return jsonify(get_stats(load_classes()))   # 전체 클래스로 통계를 계산해서 JSON으로 보내요


@app.errorhandler(404)                   # 어디서든 404(없는 페이지) 에러가 나면
def not_found(error):                    # 아래 not_found 함수가 대신 일을 해요
    if request.path.startswith("/api/"): # 주소가 /api/ 로 시작하면 (프로그램이 물어본 거라면)
        return jsonify({"error": "찾는 주소가 없어요"}), 404   # 화면 대신 JSON 에러 + 진짜 404
    return render_template("404.html", error_page=True), 404   # 사람이 보는 주소면 404.html 화면 + 진짜 404 (error_page: 메뉴 진하게 표시 끄기)


@app.after_request                       # 모든 응답이 브라우저로 나가기 직전에 한 번씩 거치는 자리예요
def no_store_html(response):             # 화면(HTML)에 "사진 찍어 두지 마" 쪽지를 붙여요
    if response.mimetype == "text/html": # 화면일 때만 (CSS 같은 static 파일은 그대로 저장해도 돼요 → 빨리 열려요)
        response.headers["Cache-Control"] = "no-store"   # 저장하지 말고 매번 새로 받아 가라 → 뒤로가기 해도 최신 찜 개수가 보여요
    return response                      # 쪽지를 붙인 응답을 그대로 내보내요


@app.errorhandler(500)                   # 코드에서 예상 못 한 에러가 나면 (500 = 서버 쪽 잘못)
def server_error(error):                 # 아래 server_error 함수가 대신 일을 해요 (debug가 켜져 있으면 이 대신 자세한 에러 화면이 나와요)
    app.logger.exception("500 에러가 났어요: %s", request.path)   # 무슨 에러였는지 서버 기록(로그)에 남겨요 → 사용자에겐 안 보이고 나만 봐요
    if request.path.startswith("/api/"): # 프로그램이 물어본 주소면
        return jsonify({"error": "잠시 문제가 생겼어요. 잠시 후 다시 시도해 주세요"}), 500   # JSON 에러 + 진짜 500
    return render_template("500.html", error_page=True), 500   # 사람이 보는 주소면 500.html 화면 + 진짜 500 (에러 내용은 보여주지 않아요)


if __name__ == "__main__":               # 이 파일을 python app.py 로 직접 켰을 때만 (서버의 gunicorn은 이 줄을 실행하지 않아요)
    debug = os.environ.get("FLASK_DEBUG") == "1"   # .env에 FLASK_DEBUG=1이 있을 때만 참 → 내 컴퓨터에서만 debug가 켜져요
    app.run(debug=debug)                 # 서버를 켜요 (debug: 고치면 자동 반영 + 에러 자세히 보기)

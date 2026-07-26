# 무한매수법 자동매매 시스템

키움증권 REST API 기반 TQQQ/SOXL 무한매수법 자동매매 시스템

## 특징

- 일반모드: 별지점 기반 LOC 매수 + 쿼터LOC매도/지정가매도
- 리버스모드: 소진 후 5일선 기반 자동 회복
- 텔레그램 봇: 실시간 주문 내역 확인 및 버튼 주문
- 20분할/40분할 지원
- TQQQ (+15% 목표) / SOXL (+20% 목표)

## 설치

```bash
# 1. 클론
git clone https://github.com/YOUR_USERNAME/kiwoom-infinite-buy.git
cd kiwoom-infinite-buy

# 2. 가상환경
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 3. 의존성
pip install -r requirements.txt

# 4. 설정
cp config.yaml.example config.yaml
# config.yaml에 실제 키 입력

# 5. 실행
python telegram_bot.py   # 텔레그램 봇
# 또는
python main.py --mode cli  # 커맨드라인

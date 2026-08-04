"""
Task 1 — Thu thập văn bản chính sách thương mại điện tử / hỗ trợ khách hàng.

Nguồn: nội dung được trích xuất thực tế (qua WebFetch) từ trang trung tâm trợ giúp
công khai của Shopee Vietnam (help.shopee.vn) vào ngày thu thập ghi trong manifest.
Vì các trang này là SPA (nội dung render bằng JavaScript), nội dung text được lưu lại
ở đây rồi render thành PDF cục bộ bằng fpdf2 — thay vì tải trực tiếp file PDF/DOCX
(Shopee không cung cấp bản PDF tải về công khai cho các trang chính sách này).

Mỗi tài liệu được gắn nhãn `customer_role` (`buyer`/`seller`/`both`) — cần thiết
cho Task 4 (chunking/indexing với metadata_filter) và được ghi cả vào manifest.json
lẫn ngay trong nội dung PDF.
"""

import json
from datetime import date
from pathlib import Path

from fpdf import FPDF

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

# Font Unicode TTF cần thiết để fpdf2 render được tiếng Việt có dấu.
_FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\arial.ttf"),
    Path(r"C:\Windows\Fonts\seguisym.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
]

DOCUMENTS = [
    {
        "filename": "returns-refund-policy-shopee.pdf",
        "title": "Chinh Sach Tra Hang Va Hoan Tien",
        "url": "https://help.shopee.vn/portal/4/article/77251",
        "customer_role": "both",
        "content": """
A. PHAM VI VA DOI TUONG AP DUNG
Chinh sach ap dung cho Nguoi Mua, Nguoi Ban, don vi van chuyen va nhan vien giao
nhan hang hoa tren San Thuong Mai Dien Tu Shopee.

B. DIEU KIEN TRA HANG / HOAN TIEN
Shopee bao ve quyen loi Nguoi Mua bang cach cho phep gui yeu cau tra hang/hoan tien
trong thoi gian bao hanh duoc quy dinh tai Dieu Khoan Dich Vu.

C. CAC TRUONG HOP DUOC TRA HANG / HOAN TIEN
Nguoi Mua co the yeu cau tra hang/hoan tien khi:
- Khong nhan duoc hang, hoac don hang khong day du
- San pham la hang gia, hang nhai
- San pham bi hu hong, mop meo trong qua trinh van chuyen
- Giao sai san pham (mau sac, kich thuoc, chung loai)
- San pham khong dung nhu mo ta cua Nguoi Ban
- San pham het han su dung
- Nguoi Ban dong y cho tra hang du khong thuoc cac ly do tren

Thoi han gui yeu cau: trong vong 15 (muoi lam) ngay ke tu khi don hang duoc giao
thanh cong; rieng san pham tuoi song la 24 gio.

D. TRA HANG DO DOI Y (Change of Mind - COM)
Chi ap dung cho thanh vien hang Vang/Kim Cuong hoac nguoi dang ky ShopeeVIP.
Thanh vien Vang/Kim Cuong: khong gioi han so lan tra hang moi thang.
Thanh vien ShopeeVIP: toi da 15 lan tra hang moi thang.

E. TRACH NHIEM CUA NGUOI BAN
Nguoi Ban phai phan hoi yeu cau hoan tien trong vong 2 ngay theo lich; neu khong
phan hoi, yeu cau duoc mac dinh chap nhan.

F. YEU CAU VE BANG CHUNG
Nguoi Mua bat buoc phai quay video va/hoac chup lai anh San Pham khi nhan hang va
khi dong goi tra hang, lam bang chung cho yeu cau tra hang/hoan tien.

G. TRACH NHIEM PHI VAN CHUYEN
Nguoi Ban thuong chiu phi van chuyen tra hang doi voi san pham loi/giao sai.
Nguoi Mua tu sap xep tra hang (khong thuoc loi Nguoi Ban) se duoc hoan tra mot phan
phi van chuyen. Tien hoan tra ve Vi Shopee, tai khoan ngan hang hoac so du Shopee.

H. GIAI QUYET TRANH CHAP
Khuyen khich Nguoi Mua va Nguoi Ban trao doi truc tiep de giai quyet. Neu khong
thanh cong, tranh chap co the duoc chuyen den co quan chuc nang de xu ly.
""",
    },
    {
        "filename": "payment-methods-shopee.pdf",
        "title": "Cac Phuong Thuc Thanh Toan Tren Shopee",
        "url": "https://help.shopee.vn/portal/4/article/79198",
        "customer_role": "buyer",
        "content": """
Shopee Viet Nam ho tro cac phuong thuc thanh toan sau danh cho Nguoi Mua khi
dat hang tren nen tang:

1. Vi ShopeePay — vi dien tu tich hop san trong ung dung Shopee.
2. The tin dung / ghi no — Visa, Mastercard, JCB, AMEX; gia tri don hang toi
   thieu 10.000 VND.
3. Tra gop qua the tin dung — khong ap dung cho don hang quoc te.
4. Thanh toan QR — qua dich vu ngan hang truc tuyen, ap dung tu 10.000 VND.
5. Ung dung ngan hang — chuyen huong truc tiep sang ung dung ngan hang cua
   Nguoi Mua de xac nhan thanh toan.
6. The noi dia NAPAS ket hop Internet Banking — ap dung tu 10.000 VND.
7. Apple Pay — ap dung cho don hang tu 10.000 VND den 25.000.000 VND.
8. Google Pay — ap dung cho don hang tu 10.000 VND den 120.000.000 VND.
9. Thanh toan khi nhan hang (COD) — tuy thuoc vao tung Shop co ho tro hay khong.
10. SPayLater — mua truoc tra sau, chia thanh 01, 02, 03 hoac 06 ky thanh toan.

Moi phuong thuc co dieu kien ap dung, han muc va huong dan rieng; Nguoi Mua nen
kiem tra Shop va gia tri don hang truoc khi chon phuong thuc thanh toan phu hop.
""",
    },
    {
        "filename": "privacy-policy-shopee.pdf",
        "title": "Chinh Sach Bao Mat Thong Tin",
        "url": "https://help.shopee.vn/portal/4/article/77244",
        "customer_role": "both",
        "content": """
1. GIOI THIEU
Shopee nghiem tuc thuc hien trach nhiem cua minh lien quan den bao mat du lieu.
Chinh sach nay mo ta cach thong tin ca nhan duoc thu thap, su dung va xu ly.

2. THOI DIEM THU THAP DU LIEU
Du lieu duoc thu thap khi nguoi dung dang ky tai khoan, dien mau don, tuong tac
qua dien thoai/email, su dung dich vu dien tu, thuc hien giao dich, gui phan hoi,
hoac tham gia chuong trinh/cuoc thi.

3. LOAI DU LIEU DUOC THU THAP
Bao gom: ho ten, email, ngay sinh, dia chi, so dien thoai, thong tin thanh toan,
thong tin thiet bi, vi tri, tuy chon lien lac va lich su giao dich.

4. DU LIEU BO SUNG
Thiet bi cua nguoi dung gui thong tin nhu dia chi IP, loai trinh duyet va cookie
de giup phan tich cach su dung nen tang.

5. COOKIE
Cookie luu du lieu ve thoi quen su dung thiet bi. Nguoi dung co the tat cookie qua
cai dat trinh duyet, tuy nhien co the lam han che mot so chuc nang.

6. MUC DICH SU DUNG DU LIEU
Du lieu duoc dung de xu ly giao dich, quan ly tai khoan, gui tai lieu tiep thi,
thuc hien nghien cuu, phong chong gian lan va tuan thu quy dinh phap luat.

7. BAO VE DU LIEU
Shopee khong the dam bao an ninh tuyet doi nhung ap dung cac bien phap hop ly de
bao ve du lieu nguoi dung.

8. TIET LO DU LIEU
Thong tin co the duoc chia se voi nha cung cap dich vu, co quan nha nuoc, doi tac
va ben thu ba khi can thiet theo quy dinh phap luat.

9. QUYEN CUA NGUOI DUNG
Nguoi dung co the rut lai su dong y, yeu cau truy cap du lieu, hoac chinh sua
thong tin ca nhan bang cach lien he: dpo.vn@shopee.com
""",
    },
    {
        "filename": "product-listing-regulations-shopee.pdf",
        "title": "Quy Dinh Ve Dang Ban San Pham Tren Shopee",
        "url": "https://help.shopee.vn/portal/4/article/77246",
        "customer_role": "seller",
        "content": """
A. PHAM VI VA DOI TUONG AP DUNG
Doi tuong: tat ca Nguoi Ban tren san TMDT Shopee.
Pham vi: quy dinh ve viec dang ban san pham tren San Shopee.

B. QUY DINH CHUNG
1. Nguyen tac chung: Nguoi Ban phai tuan thu quy dinh cua Luat Thuong Mai (Dieu
   117, 120.4, 121); chung tu cung cap phai la ban scan chung tu goc, khong gia
   mao, chinh sua hay tay xoa.
2. Noi dung cam dang ban: phan dong, chong pha, bai xich ton giao, khieu dam,
   bao luc; thong tin rac, pha roi uy tin dich vu; tuyen truyen su dung chat cam;
   dong vat va che pham tu dong vat quy hiem; vi pham quyen so huu tri tue; san
   pham nam trong danh sach cam/han che cua Shopee.
3. Hanh vi cam: dung thong tin vi pham phap luat hoac thieu tham my; xuc pham uy
   tin, danh du, nhan pham; dung hinh anh/loi noi ca nhan chua duoc dong y; cung
   cap thong tin sai lech; so sanh truc tiep voi san pham cung loai cua to chuc
   khac; quang cao cho doanh nghiep khac; dang ban lap lai (spam); thay doi noi
   dung de gian lan danh gia; dang sai nganh hang; tang gia bat hop ly truoc
   khuyen mai; dinh gia qua cao hoac qua thap so voi mat bang thi truong.

C. HUONG DAN DANG BAN SAN PHAM
1. Hinh anh san pham: anh chup ro, chi tiet tinh trang san pham; it nhat mot
   hinh that do Nguoi Ban tu chup, dien tich san pham chiem toi thieu 40% dien
   tich anh; ngon ngu tren phong nen la tieng Viet; khong chua yeu to ghe ron;
   tuyet doi khong dang hinh anh khoa than, khieu goi.
2. Ten san pham: mo ta dung hang hoa bang tieng Viet co dau; ro nghia, khong
   dung ky tu dac biet, khong viet tat; trung khop voi thong tin tren hinh anh;
   khong dung tu tuc, bao luc, ky thi dan toc; khong chua "hot", "ban chay",
   "giam gia", "mien phi van chuyen" trong ten san pham.
3. Quy dinh rieng theo nganh hang: my pham (ro nguon goc, khong ban hang da qua
   su dung/khong ro nguon goc); thuc pham chuc nang (can Xac Nhan Cong Bo Phu
   Hop An Toan Thuc Pham, ghi ro "san pham nay khong phai la thuoc..."); thoi
   trang/do lot (anh that, khong phan cam); giay dep/phu kien (ro chat lieu,
   kich thuoc); do uong co con (tuan thu Luat Phong chong tac hai ruou bia);
   sach (phai tham gia Shopee Mall, day du giay phep xuat ban/phat hanh); thuoc
   khong ke don (tuan thu Luat Duoc, ghi ro khuyen cao su dung theo huong dan
   bac si/duoc si).
4. Thong tin mo ta: day du, chi tiet, giup Nguoi Mua hieu ro dac diem, cong
   dung, cach dung, luu y; san pham da qua su dung phai ghi ro tinh trang; tu
   ngu trung thuc, khong gay hieu lam; khong chua so dien thoai/thong tin lien
   lac quang cao.
5. Danh muc nganh hang: chon dung nhom danh muc; chon sai co the bi coi la gian
   lan, xu ly theo chinh sach gian lan.
6. Gia san pham: tinh bang VND; phan loai ro theo kich co, mau sac, chat luong;
   nghiem cam tang gia goc bat hop ly truoc khuyen mai; gia bat hop ly co the bi
   xu ly.
7. Phi van chuyen: xac dinh chinh xac khoi luong san pham sau khi dong goi;
   Nguoi Ban chiu trach nhiem tinh chinh xac khoi luong.
8. Chat luong san pham: phai dung nhu mo ta, dat tieu chuan chat luong hien
   hanh; nhieu to cao/danh gia tieu cuc se bi Shopee ap dung bien phap phu hop.

D. QUY DINH VE HAN SU DUNG
1. Danh sach san pham bat buoc co han su dung: duoc pham, hoa chat tay rua/ve
   sinh, my pham, nuoc hoa, ta/bang ve sinh, thuc pham, thuc pham chuc nang va
   cac san pham khac theo Nghi dinh 43/2017/ND-CP.
2. Khi giao di, san pham phai con toi thieu 30% thoi han su dung va toi thieu
   30 ngay tinh tu hien tai; thuc pham con duoi 30 ngay han phai ghi ro trong
   mo ta va Nguoi Ban tu sap xep van chuyen.
3. Qua tang kem cong khai ap dung quy dinh han su dung nhu san pham chinh.

E. XU LY VI PHAM
Tuy muc do vi pham, Shopee co the: xoa/khoa/tam an hien thi san pham; gioi han
hoac khoa tai khoan; yeu cau den bu thiet hai cho Nguoi Mua; can tru tien tu So
Du Tai Khoan Shopee; khoa tinh nang rut tien; cung cap thong tin cho co quan nha
nuoc; khoi kien tai Toa an; va cac bien phap khac theo chinh sach hien hanh. San
pham khong tuan thu quy dinh co the bi khoa/xoa ma khong can thong bao truoc.

Ban cap nhat va cong bo ngay 14/8/2024 (co hieu luc sau 07 ngay).
""",
    },
]


def setup_directory():
    """Tạo thư mục data/landing/legal/ nếu chưa có."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Thư mục đã sẵn sàng: {DATA_DIR}")


def _find_unicode_font() -> Path:
    """Tìm font TTF Unicode để fpdf2 render được tiếng Việt có dấu."""
    for candidate in _FONT_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Không tìm thấy font TTF Unicode (vd. arial.ttf) trên máy. "
        "Cài một font TTF hỗ trợ Unicode và thêm đường dẫn vào _FONT_CANDIDATES."
    )


def render_pdf(doc: dict) -> Path:
    """Render 1 document (dict trong DOCUMENTS) thành file PDF bằng fpdf2."""
    font_path = _find_unicode_font()

    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("Body", "", str(font_path))

    pdf.set_font("Body", size=16)
    pdf.multi_cell(0, 10, doc["title"])

    pdf.set_font("Body", size=9)
    pdf.cell(0, 6, f"Nguon: {doc['url']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Ngay thu thap: {date.today().isoformat()}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0, 6,
        f"Doi tuong ap dung (customer_role): {doc['customer_role']}",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(4)

    pdf.set_font("Body", size=11)
    pdf.multi_cell(0, 7, doc["content"].strip())

    filepath = DATA_DIR / doc["filename"]
    pdf.output(str(filepath))
    print(f"✓ Đã tạo: {filepath.name} ({filepath.stat().st_size:,} bytes)")
    return filepath


def write_manifest():
    """Ghi manifest.json (filename -> title/url/customer_role) để Task 4 dùng khi gắn metadata."""
    manifest = {
        doc["filename"]: {
            "title": doc["title"],
            "url": doc["url"],
            "customer_role": doc["customer_role"],
        }
        for doc in DOCUMENTS
    }
    manifest_path = DATA_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"✓ Manifest: {manifest_path.name}")


def collect_all():
    """Tạo toàn bộ file PDF chính sách + manifest.json trong data/landing/legal/."""
    setup_directory()
    for doc in DOCUMENTS:
        render_pdf(doc)
    write_manifest()
    print(f"\n✓ Hoàn tất: {len(DOCUMENTS)} văn bản pháp lý trong {DATA_DIR}")


if __name__ == "__main__":
    collect_all()

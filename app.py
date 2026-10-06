import streamlit as st
import requests
import json
import pandas as pd
import fitz  # Thư viện PyMuPDF để đọc PDF

st.set_page_config(page_title="Đề online từ file PDF", layout="wide")

# --- HÀM CACHE CHUYỂN PDF THÀNH ẢNH (GIÚP APP CHẠY MƯỢT, KHÔNG LAG) ---
@st.cache_data(show_spinner="Đang xử lý đề thi PDF...")
def convert_pdf_to_images(pdf_bytes, dpi=150):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("png")
        images.append(img_bytes)
    return images

# --- HÀM CHUYỂN FILE EXCEL THÀNH DICTIONARY ĐÁP ÁN ---
def load_excel_key(file):
    try:
        # Đọc file Excel (yêu cầu cài openpyxl)
        df = pd.read_excel(file)
        
        key_dict = {}
        for index, row in df.iterrows():
            cau = str(row['Câu']).strip()
            dap_an = str(row['Đáp án']).strip()
            key_dict[cau] = dap_an
            
        return key_dict
    except Exception as e:
        st.error(f"Lỗi đọc file Excel đáp án: {e}")
        return None

# --- HÀM TÍNH ĐIỂM ---
def tinh_tong_diem(user_ans, key):
    tong_diem = 0.0

    # Chấm Phần I (0.25đ / câu)
    for i in range(1, 13):
        q = f"Câu {i}"
        if user_ans.get(q) == key.get(q):
            tong_diem += 0.25

    # Chấm Phần II (Baram bậc thang: 0.1 - 0.25 - 0.5 - 1.0)
    barchart_p2 = {1: 0.1, 2: 0.25, 3: 0.5, 4: 1.0}
    for i in range(13, 17):
        so_y_dung = 0
        for sub in ['a', 'b', 'c', 'd']:
            q = f"Câu {i}_{sub}"
            if user_ans.get(q) == key.get(q):
                so_y_dung += 1
        tong_diem += barchart_p2.get(so_y_dung, 0.0)

    # Chấm Phần III (0.5đ / câu)
    for i in range(17, 23):
        q = f"Câu {i}"
        val_user = str(user_ans.get(q, '')).strip()
        val_key = str(key.get(q, '')).strip()
        if val_user == val_key and val_user != '':
            tong_diem += 0.5

    return round(tong_diem, 2)


# --- THANH CẤU HÌNH DÀNH CHO GIÁO VIÊN (SIDEBAR) ---
with st.sidebar:
    st.header("⚙️ Quản lý Đề & Đáp án")
    
    # 1. Tải đề thi PDF
    uploaded_pdf = st.file_uploader("1. Tải đề thi PDF lên:", type=["pdf"])
    
    # 2. Tải file đáp án Excel (.xlsx / .xls)
    uploaded_excel = st.file_uploader("2. Tải file đáp án Excel (.xlsx):", type=["xlsx", "xls"])
    
    answer_key_data = {}
    if uploaded_excel is not None:
        answer_key_data = load_excel_key(uploaded_excel)
        if answer_key_data:
            st.success("✅ Đã nạp đáp án từ Excel thành công!")


# --- GIAO DIỆN CHÍNH ---
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyh7-mqwrdLzptQLEj-C_ryc_UwXexPpVl1yAl3rfkRIssjryntt5qhBk6RJdaBtbcc/exec"

st.title("📝 Kiểm tra trực tuyến môn Toán")

# Chia tỷ lệ cột 6-4 để đề thi rộng rãi, dễ nhìn hơn
col_pdf, col_form = st.columns([6, 4])

# --- CỘT TRÁI: HIỂN THỊ FILE PDF (ĐÃ KHẮC PHỤC LỖI CHROME BLOCK) ---
with col_pdf:
    st.subheader("📄 Đề thi")
    if uploaded_pdf is not None:
        try:
            pdf_bytes = uploaded_pdf.getvalue()
            images = convert_pdf_to_images(pdf_bytes)
            
            # Tùy chọn cách xem đề thi
            display_mode = st.radio(
                "Chế độ xem đề thi:", 
                ["Xem tất cả các trang (Cuộn)", "Xem từng trang (Sang trang)"], 
                horizontal=True
            )
            
            st.markdown("---")
            
            if display_mode == "Xem từng trang (Sang trang)":
                page_number = st.slider("Chuyển trang đề thi", min_value=1, max_value=len(images), value=1)
                st.image(images[page_number - 1], use_container_width=True)
            else:
                # Cuộn xem tất cả
                for img in images:
                    st.image(img, use_container_width=True)
                    st.divider()
                    
        except Exception as e:
            st.error(f"Lỗi xử lý file PDF: {e}")
    else:
        st.info("👆 Vui lòng tải file PDF ở thanh bên trái (Sidebar) để hiển thị đề thi!")

# --- CỘT PHẢI: PHIẾU BÀI LÀM ---
with col_form:
    st.subheader("📋 Phiếu trả lời trắc nghiệm")
    
    with st.expander("👤 Thông tin học sinh", expanded=True):
        ho_ten = st.text_input("Họ và tên:")
        lop = st.text_input("Lớp:")
    
    user_answers = {}
    
    # Phần I
    st.markdown("### PHẦN I: Chọn phương án (12 câu)")
    for i in range(1, 13):
        user_answers[f"Câu {i}"] = st.radio(f"Câu {i}:", ["A", "B", "C", "D"], horizontal=True, key=f"p1_c{i}", index=None)
    
    st.markdown("---")
    
    # Phần II
    st.markdown("### PHẦN II: Đúng / Sai (4 câu)")
    for i in range(13, 17):
        st.write(f"**Câu {i}:**")
        for sub in ['a', 'b', 'c', 'd']:
            user_answers[f"Câu {i}_{sub}"] = st.radio(f"Ý {sub}):", ["Đúng", "Sai"], horizontal=True, key=f"p2_c{i}_{sub}", index=None)

    st.markdown("---")
    
    # Phần III
    st.markdown("### PHẦN III: Trả lời ngắn (6 câu)")
    for i in range(17, 23):
        user_answers[f"Câu {i}"] = st.text_input(f"Câu {i}:", key=f"p3_c{i}")

    st.markdown("---")
    
    # NỘP BÀI
    if st.button("🚀 NỘP BÀI THI", type="primary", use_container_width=True):
        if not ho_ten or not lop:
            st.error("Vui lòng nhập đầy đủ Họ tên và Lớp trước khi nộp bài!")
        elif not answer_key_data:
            st.error("Chưa có dữ liệu đáp án! Vui lòng nhờ giáo viên tải file Excel đáp án lên.")
        else:
            # Chấm điểm từ file Excel
            diem_so = tinh_tong_diem(user_answers, answer_key_data)
            
            payload = {
                "ho_ten": ho_ten,
                "lop": lop,
                "tong_diem": diem_so
            }
            
            with st.spinner("Đang chấm điểm và gửi bài làm..."):
                try:
                    response = requests.post(WEBHOOK_URL, data=json.dumps(payload), headers={"Content-Type": "application/json"})
                    if response.status_code == 200:
                        st.success(f"Chúc mừng {ho_ten} (Lớp {lop}) đã nộp bài thành công!")
                        st.metric(label="Tổng điểm của bạn", value=f"{diem_so} / 10.0 điểm")
                        st.balloons()
                    else:
                        st.error("Gửi bài thất bại, vui lòng thử lại!")
                except Exception as e:
                    st.error(f"Lỗi kết nối: {e}")
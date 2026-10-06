import streamlit as st
import base64
import requests
import json
import pandas as pd  # Thêm thư viện pandas để đọc file Excel

st.set_page_config(page_title="Đề online từ file PDF", layout="wide")

# --- HÀM CHUYỂN FILE EXCEL THÀNH DICTIONARY ĐÁP ÁN ---
def load_excel_key(file):
    try:
        # Đọc file Excel
        df = pd.read_excel(file)
        
        # Chuyển 2 cột "Câu" và "Đáp án" thành dạng Dictionary
        # Đảm bảo ép kiểu chuỗi để tránh lỗi so sánh số/chữ
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

col_pdf, col_form = st.columns([3, 2])

# --- CỘT TRÁI: HIỂN THỊ FILE PDF ---
with col_pdf:
    st.subheader("📄 Đề thi (File PDF)")
    if uploaded_pdf is not None:
        base64_pdf = base64.b64encode(uploaded_pdf.read()).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
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
            st.error("Chưa có dữ liệu đáp án! Vui lòng tải file Excel đáp án lên ở thanh bên (Sidebar).")
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
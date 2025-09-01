# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
import io
import time
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- Cài đặt font cho PDF (hỗ trợ tiếng Việt) ---
try:
    pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
    FONT_NAME = 'Arial'
except Exception:
    st.warning("Không thể đăng ký font 'Arial.ttf'. PDF sẽ dùng font mặc định.")
    FONT_NAME = 'Helvetica'


# --- Cài đặt cơ bản của ứng dụng ---
st.set_page_config(layout="wide", page_title="Hệ Thống Quản Lý Vàng")

# --- Hàm hỗ trợ ---
def save_bill(bill_items_data):
    """Lưu dữ liệu các món hàng vào file data.xlsx."""
    try:
        # Tải dữ liệu cũ hoặc tạo DataFrame mới nếu file chưa tồn tại
        if os.path.exists("data.xlsx"):
            df_existing = pd.read_excel("data.xlsx")
        else:
            df_existing = pd.DataFrame(columns=['Ngày', 'Tên Người Bán', 'Số CCCD', 'Địa Chỉ', 'Cân Nặng (gram)', 'Loại Vàng', 'Đơn Giá (VND)', 'Thành Tiền (VND)'])

        df_new_rows = pd.DataFrame(bill_items_data)
        df_updated = pd.concat([df_existing, df_new_rows], ignore_index=True)
        df_updated.to_excel("data.xlsx", index=False)
        st.success("Bảng kê đã được lưu thành công!", icon="✅")
    except Exception as e:
        st.error(f"Đã xảy ra lỗi khi lưu bảng kê: {e}", icon="❌")

def generate_pdf(bill_data):
    """Tạo file PDF từ dữ liệu bảng kê."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A5, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleStyle', alignment=TA_CENTER, fontSize=14, fontName=FONT_NAME + '-Bold'))
    styles.add(ParagraphStyle(name='SubTitleStyle', alignment=TA_CENTER, fontSize=10, fontName=FONT_NAME))
    styles.add(ParagraphStyle(name='NormalStyle', alignment=TA_CENTER, fontSize=10, fontName=FONT_NAME))
    styles.add(ParagraphStyle(name='Heading1Style', fontSize=12, fontName=FONT_NAME + '-Bold'))
    styles.add(ParagraphStyle(name='NormalLeft', fontSize=10, fontName=FONT_NAME))

    story = []
    
    # Tiêu đề và thông tin chung
    story.append(Paragraph("CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM", styles['NormalStyle']))
    story.append(Paragraph("Độc lập - Tự do - Hạnh phúc", styles['NormalStyle']))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Tên đơn vị: Công Ty Trách Nhiệm Hữu Hạn Trang Sức Vàng Anh Đào", styles['NormalLeft']))
    story.append(Paragraph("BẢNG KÊ MUA HÀNG HOÁ, DỊCH VỤ CỦA TỔ CHỨC, CÁ NHÂN KHÔNG KINH DOANH KHÔNG CÓ HOÁ ĐƠN, CHỨNG TỪ", styles['TitleStyle']))
    story.append(Paragraph("(Theo mẫu 01/TNDN)", styles['SubTitleStyle']))
    story.append(Spacer(1, 15))

    # Thông tin người bán
    story.append(Paragraph(f"Tên người bán: {bill_data['Tên Người Bán']}", styles['NormalLeft']))
    story.append(Paragraph(f"Số CCCD: {bill_data['Số CCCD']}", styles['NormalLeft']))
    story.append(Paragraph(f"Địa chỉ: {bill_data['Địa Chỉ']}", styles['NormalLeft']))
    story.append(Paragraph(f"Ngày: {bill_data['Ngày'].strftime('%d/%m/%Y %H:%M:%S')}", styles['NormalLeft']))
    story.append(Spacer(1, 15))

    # Bảng chi tiết
    data_table = [['Cân Nặng (gram)', 'Loại Vàng', 'Đơn Giá (VND)', 'Thành Tiền (VND)']]
    for i in range(len(bill_data['Loại Vàng'])):
        data_table.append([
            f"{bill_data['Cân Nặng (gram)'][i]:,.2f}",
            bill_data['Loại Vàng'][i],
            f"{bill_data['Đơn Giá (VND)'][i]:,.0f}",
            f"{bill_data['Thành Tiền (VND)'][i]:,.0f}"
        ])
    
    # Thêm dòng tổng tiền
    total_amount = sum(bill_data['Thành Tiền (VND)'])
    data_table.append(['', '', 'Tổng Cộng:', f"{total_amount:,.0f} VND"])

    table_style = TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), FONT_NAME + '-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (2, -1), (2, -1), FONT_NAME + '-Bold'),
        ('FONTNAME', (3, -1), (3, -1), FONT_NAME + '-Bold'),
    ])
    
    table = Table(data_table, colWidths=[2.2*cm, 3.5*cm, 3.5*cm, 4.0*cm])
    table.setStyle(table_style)
    story.append(table)
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"Tổng số tiền bằng chữ: {convert_to_vietnamese_words(total_amount)}", styles['NormalLeft']))
    story.append(Spacer(1, 20))

    # Chữ ký (sử dụng bảng để đặt cạnh nhau)
    signatures = [['Chữ ký người bán', 'Chữ ký người mua']]
    sig_table = Table(signatures, colWidths=[7*cm, 7*cm])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 40))

    try:
        doc.build(story)
    except Exception as e:
        st.error(f"Đã xảy ra lỗi khi tạo PDF: {e}")
        return None

    buffer.seek(0)
    return buffer

def convert_to_vietnamese_words(number):
    """Chuyển số thành chữ tiếng Việt."""
    
    # Để đơn giản, chỉ xử lý đến hàng tỷ
    num_str = f"{int(number):,.0f}"
    return f"{num_str.replace(',', '.')} đồng." # Đơn giản hóa, bạn có thể tìm thư viện hoặc viết hàm đầy đủ hơn

# --- Ứng dụng Streamlit ---
st.title("Ứng Dụng Quản Lý Mua Vàng")
st.markdown("---")

# Điều hướng trang bằng session_state
if 'page' not in st.session_state:
    st.session_state.page = "Trang Chủ"
if 'step' not in st.session_state:
    st.session_state.step = 1

if st.session_state.page == "Trang Chủ":
    st.header("Dashboard Tổng Quan")

    col1, _ = st.columns([1, 2])
    with col1:
        if st.button("Tạo Bảng Kê", width='stretch', type="primary"):
            st.session_state.page = "Tạo Bảng Kê"
            st.session_state.step = 1
            st.rerun()

    st.markdown("---")

    # Biểu đồ thống kê lịch sử
    st.subheader("Biểu đồ Thống Kê Lịch Sử")
    if os.path.exists("data.xlsx"):
        df_history = pd.read_excel("data.xlsx")
        df_history['Ngày'] = pd.to_datetime(df_history['Ngày'])
        df_history = df_history.sort_values(by='Ngày')
        
        # Biểu đồ tổng tiền theo ngày
        df_daily_total = df_history.groupby(df_history['Ngày'].dt.date)['Thành Tiền (VND)'].sum().reset_index()
        fig = px.bar(df_daily_total, x='Ngày', y='Thành Tiền (VND)', title='Tổng Tiền Mua Vàng Hàng Ngày', 
                     labels={'Ngày': 'Ngày', 'Thành Tiền (VND)': 'Tổng Tiền (VND)'})
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Lịch Sử Giao Dịch")
        
        # Sắp xếp lại thứ tự cột để dễ nhìn hơn
        desired_order = ['Ngày', 'Tên Người Bán', 'Số CCCD', 'Địa Chỉ', 'Loại Vàng', 'Cân Nặng (gram)', 'Đơn Giá (VND)', 'Thành Tiền (VND)']
        st.dataframe(df_history[desired_order], use_container_width=True)
    else:
        st.info("Chưa có dữ liệu giao dịch nào để hiển thị.")

    # Nút xóa dữ liệu
    st.markdown("---")
    st.subheader("Quản lý dữ liệu")
    col1, _ = st.columns([1, 2])
    with col1:
        if st.button("Xóa Toàn Bộ Dữ Liệu", width='stretch', type="secondary"):
            if os.path.exists("data.xlsx"):
                os.remove("data.xlsx")
            st.success("Đã xóa toàn bộ dữ liệu thành công!", icon="🗑️")
            st.rerun()

elif st.session_state.page == "Tạo Bảng Kê":
    st.header("Tạo Bảng Kê")
    st.markdown("Điền thông tin vào form dưới đây để tạo bảng kê mua vàng.")
    
    if st.session_state.step == 1:
        with st.form("seller_info_form"):
            st.subheader("Thông tin người bán")
            st.session_state.seller_name = st.text_input("Tên người bán", value=st.session_state.get('seller_name', ''))
            st.session_state.seller_id = st.text_input("Số CCCD", value=st.session_state.get('seller_id', ''))
            st.session_state.seller_address = st.text_input("Địa chỉ", value=st.session_state.get('seller_address', ''))

            submitted = st.form_submit_button("Tiếp", type="primary", width='stretch')
            if submitted:
                if not st.session_state.seller_name or not st.session_state.seller_id or not st.session_state.seller_address:
                    st.error("Vui lòng nhập đầy đủ thông tin người bán.")
                else:
                    st.session_state.step = 2
                    st.rerun()
    
    elif st.session_state.step == 2:
        with st.form("bill_items_form"):
            st.subheader("Chi tiết món hàng (Tối đa 5 món)")
            
            if 'num_items' not in st.session_state:
                st.session_state.num_items = 1

            items = []
            total_amount = 0
            # Danh sách để lưu các món hàng đã được "san phẳng"
            items_to_save = []

            for i in range(st.session_state.num_items):
                st.markdown(f"**Món hàng {i+1}**")
                col1, col2 = st.columns(2)
                with col1:
                    weight = st.number_input(f"Cân nặng (gram)", min_value=0.0, format="%.2f", key=f"weight_{i}", value=st.session_state.get(f"weight_{i}", 0.0))
                with col2:
                    gold_type = st.selectbox("Loại vàng", ["Vàng SJC", "Vàng 9999", "Vàng 24K", "Vàng 18K", "Vàng Trắng"], key=f"gold_type_{i}", index=st.session_state.get(f"gold_type_index_{i}", 0))

                # Nhập đơn giá thủ công
                manual_price_thousand = st.number_input(
                    "Nhập đơn giá (nghìn VND)",
                    min_value=0,
                    format="%d",
                    key=f"manual_price_{i}",
                    value=st.session_state.get(f"manual_price_{i}", 0)
                )
                unit_price = manual_price_thousand * 1000

                item_amount = weight * unit_price
                total_amount += item_amount
                
                items.append({
                    'weight': weight,
                    'gold_type': gold_type,
                    'unit_price': unit_price,
                    'amount': item_amount
                })

                # Chuẩn bị dữ liệu cho việc lưu vào Excel
                items_to_save.append({
                    'Ngày': datetime.now(),
                    'Tên Người Bán': st.session_state.seller_name,
                    'Số CCCD': st.session_state.seller_id,
                    'Địa Chỉ': st.session_state.seller_address,
                    'Cân Nặng (gram)': weight,
                    'Loại Vàng': gold_type,
                    'Đơn Giá (VND)': unit_price,
                    'Thành Tiền (VND)': item_amount
                })
                st.markdown("---")

            col_add, col_remove, _ = st.columns([1, 1, 4])
            with col_add:
                if st.session_state.num_items < 5:
                    if st.form_submit_button("Thêm Món Hàng", type="secondary"):
                        st.session_state.num_items += 1
                        st.rerun()
            with col_remove:
                if st.session_state.num_items > 1:
                    if st.form_submit_button("Xóa Món Hàng Cuối", type="secondary"):
                        st.session_state.num_items -= 1
                        st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"<h2 style='text-align: center;'>Tổng Tiền: {total_amount:,.0f} VND</h2>", unsafe_allow_html=True)
            
            col_back, col_submit = st.columns([1, 1])
            with col_back:
                if st.form_submit_button("Quay Lại", type="secondary"):
                    st.session_state.step = 1
                    st.rerun()
            with col_submit:
                submitted = st.form_submit_button("Đã Chuẩn Bị Tiền", type="primary", width='stretch')

        if submitted:
            vietnam_now = datetime.now()
            
            bill_data = {
                'Ngày': vietnam_now,
                'Tên Người Bán': st.session_state.seller_name,
                'Số CCCD': st.session_state.seller_id,
                'Địa Chỉ': st.session_state.seller_address,
                'Cân Nặng (gram)': [item['weight'] for item in items],
                'Loại Vàng': [item['gold_type'] for item in items],
                'Đơn Giá (VND)': [item['unit_price'] for item in items],
                'Thành Tiền (VND)': [item['amount'] for item in items]
            }

            # Lưu vào file Excel
            save_bill(items_to_save)

            # Tạo và cung cấp file PDF để tải xuống
            pdf_file = generate_pdf(bill_data)
            if pdf_file:
                st.download_button(
                    label="Tải Xuống Bảng Kê PDF",
                    data=pdf_file,
                    file_name=f"Bang_ke_{st.session_state.seller_name}_{vietnam_now.strftime('%Y%m%d%H%M%S')}.pdf",
                    mime="application/pdf",
                    width='stretch'
                )
            
            # Reset form sau khi lưu thành công
            for i in range(st.session_state.num_items):
                del st.session_state[f"weight_{i}"]
                del st.session_state[f"gold_type_{i}"]
                del st.session_state[f"manual_price_{i}"]
                
            del st.session_state.seller_name
            del st.session_state.seller_id
            del st.session_state.seller_address
            st.session_state.num_items = 1
            st.session_state.step = 1
    
    st.markdown("---")
    if st.button("Về Trang Chủ", width='stretch'):
        st.session_state.page = "Trang Chủ"
        st.rerun()

# streamlit_pdf_compressor.py
#install -y ghostscript
import ghostscript as gs # i hav ewrite this line
import streamlit as st
import fitz  # PyMuPDF
import os
import time
import io
from PIL import Image
import subprocess

# Ghostscript compression
def compress_pdf_gs(input_pdf, output_pdf, quality='screen'):
    command = [
        "gs",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS=/{quality}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_pdf}",
        input_pdf
    ]
    subprocess.run(command, check=True)

# Image-based compression
def compress_images_in_pdf(doc, compression_type="less"):
    new_pdf = fitz.open()
    jpeg_quality = 85 if compression_type == "less" else 65
    resize_ratio = 1.0 if compression_type == "less" else 0.7

    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        new_page = new_pdf.new_page(width=page.rect.width, height=page.rect.height)
        new_page.show_pdf_page(new_page.rect, doc, page_num)

        for img in page.get_images(full=True):
            try:
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                with Image.open(io.BytesIO(image_bytes)) as image:
                    if image.mode != 'RGB':
                        image = image.convert('RGB')

                    if resize_ratio < 1.0:
                        image = image.resize(
                            (int(image.width * resize_ratio), int(image.height * resize_ratio)),
                            Image.LANCZOS
                        )

                    buffer = io.BytesIO()
                    image.save(buffer, format="JPEG", quality=jpeg_quality)
                    new_page.insert_image(page.rect, stream=buffer.getvalue())

            except Exception as e:
                print(f"Error processing image: {e}")
                continue

    output_file = f"compressed_{compression_type}_{int(time.time())}.pdf"
    new_pdf.save(output_file, deflate=True)
    return output_file

def compress_pdf(input_path, compression_type="less"):
    doc = fitz.open(input_path)
    if compression_type == "extreme":
        output_path = f"compressed_extreme_{int(time.time())}.pdf"
        compress_pdf_gs(input_path, output_path, quality='screen')
    elif compression_type == "less":
        if any(page.get_images(full=True) for page in doc):
            output_path = compress_images_in_pdf(doc, "less")
        else:
            output_path = f"compressed_less_{int(time.time())}.pdf"
            compress_pdf_gs(input_path, output_path, quality='printer')
    else:
        raise ValueError("Invalid compression type")

    return output_path

# Streamlit UI
st.title("📄 PDF Compression Tool")
uploaded_file = st.file_uploader("Upload your PDF", type="pdf")

compression_choice = st.radio(
    "Select compression type:",
    ("less", "extreme")
)

if uploaded_file is not None:
    with open(uploaded_file.name, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.write(f"Uploaded file: {uploaded_file.name}")
    if st.button("🔧 Compress PDF"):
        try:
            start = time.time()
            compressed = compress_pdf(uploaded_file.name, compression_choice)
            duration = time.time() - start

            st.success(f"✅ Compression complete in {duration:.1f} seconds.")
            with open(compressed, "rb") as f:
                st.download_button("📥 Download Compressed PDF", f, file_name=compressed)
        except Exception as e:
            st.error(f"❌ Error during compression: {e}")

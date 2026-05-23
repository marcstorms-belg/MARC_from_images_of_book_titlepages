import streamlit as st
import csv
import io
import time
from datetime import datetime
from google import genai

# ================= STREAMLIT UI SETUP =================
st.set_page_config(page_title="MARC21 Cataloging Automation Tool", layout="wide", page_icon="📚")

st.title("📚 MARC21 Cataloging Automation Tool")

# ℹ️ ADICIONE ESTE BLOCO LOGO ABAIXO DO TÍTULO:
with st.popover("ℹ️ Information / How to Use"):
    st.markdown("""
    With this **MARC21 Cataloging Automation Tool** you can process images of book title pages into MARC records.
    
    ### How to use:
    * **Step 1.** Take images of the title pages of the books you want to catalog.
    * **Step 2.** Insert your Gemini API Key (left corner).
    * **Step 3.** Choose the images you want to upload.
    * **Step 4.** Click on process (it takes about 30 seconds to process each image).
    * **Step 5.** Download the csv-file with the MARC21 records.
    
    ---
    *The tool was created by Marc Storms with the help of Gemini.*
    """)



st.markdown("Upload book title page images to automatically generate complete MARC21 bibliographic records using AI.")

# --- Sidebar Configuration ---
st.sidebar.header("🔑 Configuration")

# 1. API Key Input
user_api_key = st.sidebar.text_input(
    "Enter your Gemini API Key", 
    type="password", 
    help="Get a free or pay-as-you-go key from https://aistudio.google.com/"
)

# Optional adjustments for advanced users
temperature = st.sidebar.slider("Temperature (Lower = more precise)", 0.0, 1.0, 0.1, 0.05)
max_tokens = st.sidebar.number_input("Max Output Tokens", min_value=500, max_value=8000, value=4000)

# Fixed blueprint instructions for the cataloging engine
PROMPT = """You are a professional librarian creating MARC21 bibliographic records.
Instructions:Follow MARC21 bibliographic format
Use correct field tags (100, 245, 260, etc.)
If data is missing, leave the field blank or infer cautiously
Additional requirements:
Field 242 must have the title in the original language.
Field 245 must have the title transcribed into English. 
Include field 041 for the language code
Include field 044 for the country of publishing Entity Code
Include field 500 to mention the different languages
Include field 520 for a concise summary when sufficient information is available
Include field 600 for personal name subjects if relevant persons are clearly identified
Include field 650 for topical subjects based on the content
Insert in field 945: $a l; $b LIVRO; $c 01
Formatting rules:
Maintain consistent field order
Use standard MARC subfield delimiters ($a, $b, etc.)
Do not invent specific data; general subject terms are acceptable if needed
Keep summaries (520) factual and brief
Output only the MARC21 text, no explanations."""

# --- Main App Body ---
# 2. File Upload Interface (Replaces local folder input)
uploaded_files = st.file_uploader(
    "Choose book images to process", 
    type=['jpg', 'jpeg', 'png', 'tiff', 'bmp'], 
    accept_multiple_files=True
)

if not user_api_key:
    st.info("💡 Please enter your Gemini API Key in the sidebar to begin.")
elif uploaded_files:
    st.success(f"📸 Ready to process {len(uploaded_files)} images.")
    
    if st.button("🚀 Start Batch Processing", type="primary"):
        try:
            # Initialize the Gemini client dynamically with the user's key
            client = genai.Client(api_key=user_api_key)
            
            # Setup placeholder memory structures for the CSV data
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow([
                'Original Filename', 'Status', 'MARC Record', 
                'Error Message', 'Timestamp', 'Processing Time (seconds)'
            ])
            
            # Setup layout containers for real-time visual progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_preview = st.container()
            
            success_count = 0
            failure_count = 0
            
            for idx, file in enumerate(uploaded_files, 1):
                filename = file.name
                status_text.markdown(f"**Processing ({idx}/{len(uploaded_files)}):** `{filename}`")
                
                start_time = time.time()
                marc_record = None
                error_msg = ""
                
                try:
                    # Read the file directly from memory bytes
                    image_bytes = file.read()
                    
                    image_part = genai.types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=file.type
                    )
                    
                    # Run the request using the verified prompt first structural order
                    response = client.models.generate_content(
                        model='gemini-2.5-pro', 
                        contents=[PROMPT, image_part],
                        config=genai.types.GenerateContentConfig(
                            temperature=temperature,
                            max_output_tokens=max_tokens,
                        )
                    )
                    
                    marc_record = response.text
                    
                    if not marc_record or len(marc_record.strip()) < 50:
                        raise ValueError(f"Generated record is too short or empty. (Got {len(marc_record) if marc_record else 0} chars)")
                    
                    status = "SUCCESS"
                    success_count += 1
                    error_msg = ""
                    
                except Exception as api_error:
                    status = "FAILED"
                    failure_count += 1
                    marc_record = ""
                    error_msg = str(api_error)
                
                processing_time = round(time.time() - start_time, 2)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Write row data to our dynamic text stream memory buffer
                writer.writerow([filename, status, marc_record, error_msg, timestamp, processing_time])
                
                # Update visual trackers
                progress_bar.progress(idx / len(uploaded_files))
                
                with results_preview:
                    if status == "SUCCESS":
                        with st.expander(f"✅ {filename} ({processing_time}s)"):
                            st.code(marc_record, language="text")
                    else:
                        st.error(f"❌ {filename} failed: {error_msg[:150]}")
            
            status_text.markdown("### 🎉 Processing Complete!")
            
            # Summary Metrics Layout
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Files", len(uploaded_files))
            col2.metric("Successful", success_count, delta_color="normal")
            col3.metric("Failed", failure_count, delta_color="inverse" if failure_count > 0 else "normal")
            
            # 3. Download CSV Button (Replaces hardcoded output folder logic)
            st.markdown("### 💾 Download Results")
            st.download_button(
                label="📥 Download MARC_Records.csv",
                data=csv_buffer.getvalue().encode('utf-8-sig'),
                file_name=f"MARC_Records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="download-csv"
            )
            
        except Exception as startup_error:
            st.error(f"Initialization Failed: Ensure your API Key is active. Details: {startup_error}")

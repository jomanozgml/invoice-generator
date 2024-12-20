from flask import Flask, render_template, request, redirect, url_for, send_file, flash, jsonify
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import logging
from dotenv import load_dotenv

app = Flask(__name__, static_url_path='/static')
load_dotenv()
app.secret_key = os.getenv('FLASK_SECRET_KEY')
app.config['UPLOAD_FOLDER'] = '/uploads'
app.config['OUTPUT_FOLDER'] = '/invoices'

# Ensure upload and output directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Setup logging
logging.basicConfig(filename='app.log', level=logging.INFO)

# Configuration
CONFIG = {
    "company_name": "MOON STAR TAILORS",
    "address": "Solteemode-14, Kathmandu",
    "phone_number": "+977 9813719892 ",
    "email": "info@moonstar.com.np",
    "pan_no": "605813520"
}

class CSVValidationError(Exception):
    pass

def validate_csv_data(df):
    required_columns = ['order_id', 'customer_name', 'email', 'item_name', 'quantity', 'price']
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        raise CSVValidationError(f"Missing columns: {', '.join(missing_cols)}")
    for idx, row in df.iterrows():
        if pd.isnull(row).any():
            raise CSVValidationError(f"Missing data in row {idx + 1}")
        if not isinstance(row['quantity'], (int, float)) or row['quantity'] <= 0:
            raise CSVValidationError(f"Invalid quantity in row {idx + 1}")
        if not isinstance(row['price'], (int, float)) or row['price'] <= 0:
            raise CSVValidationError(f"Invalid price in row {idx + 1}")
        if '@' not in row['email']:
            raise CSVValidationError(f"Invalid email in row {idx + 1}")

def generate_invoice_pdf(df):
    pdf = FPDF()

    for idx, row in df.iterrows():
        pdf.add_page()

        # Set margins
        pdf.set_margins(10, 10, 10)

        # Company Details (Centered)
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, CONFIG["company_name"], ln=True, align="C")
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, CONFIG["address"], ln=True, align="C")
        pdf.cell(0, 5, f"Phone: {CONFIG['phone_number']}", ln=True, align="C")
        pdf.cell(0, 5, f"Email: {CONFIG['email']}", ln=True, align="C")
        pdf.cell(0, 5, f"PAN No.: {CONFIG['pan_no']}", ln=True, align="C")
        pdf.ln(5)

        # Date (Top Right) and Order ID (Top Left)
        pdf.set_font("Arial", "", 10)
        current_date = datetime.now().strftime('%Y-%m-%d')

        # Save position for Order ID
        x_position = pdf.get_x()
        y_position = pdf.get_y()

        # Print date on right
        pdf.cell(0, 5, f"Date: {current_date}", align="R", ln=True)

        # Return to saved position and print Order ID
        if 'order_id' in row:
            pdf.set_xy(x_position, y_position)
            pdf.cell(0, 5, f"Order ID: {row['order_id']}", align="L")
        pdf.ln(10)

        # Customer Details
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 5, "Bill To:", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, f"Name: {row['customer_name']}", ln=True)
        pdf.cell(0, 5, f"Email: {row['email']}", ln=True)
        pdf.ln(10)

        # Items Table Header
        pdf.set_font("Arial", "B", 10)
        pdf.cell(10, 7, "SN", 1, 0, "C")
        pdf.cell(80, 7, "Item", 1, 0, "C")
        pdf.cell(30, 7, "Quantity", 1, 0, "C")
        pdf.cell(35, 7, "Price", 1, 0, "C")
        pdf.cell(35, 7, "Total", 1, 1, "C")

        # Items Table Content
        pdf.set_font("Arial", "", 10)
        total = float(row['quantity']) * float(row['price'])

        pdf.cell(10, 7, "1", 1, 0, "C")
        pdf.cell(80, 7, str(row['item_name']), 1, 0, "L")
        pdf.cell(30, 7, str(row['quantity']), 1, 0, "C")
        pdf.cell(35, 7, f"${row['price']:.2f}", 1, 0, "R")
        pdf.cell(35, 7, f"${total:.2f}", 1, 1, "R")

        # Total Amount
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(155, 7, "Total Amount:", 0, 0, "R")
        pdf.cell(35, 7, f"${total:.2f}", 1, 1, "R")

        # Footer
        pdf.set_y(-31)
        pdf.set_font("Arial", "I", 8)
        pdf.cell(0, 10, "Thank you for your business!", 0, 0, "C")

    output_filename = f"invoices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
    pdf.output(output_path)
    return output_path

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        CONFIG["company_name"] = request.form.get("company_name", CONFIG["company_name"])
        CONFIG["address"] = request.form.get("address", CONFIG["address"])
        CONFIG["phone_number"] = request.form.get("phone_number", CONFIG["phone_number"])
        CONFIG["email"] = request.form.get("email", CONFIG["email"])
        CONFIG["pan_no"] = request.form.get("pan_no", CONFIG["pan_no"])

        if 'csv_file' not in request.files:
            return jsonify({'message': 'No file part'}), 400
        file = request.files['csv_file']
        if file.filename == '':
            return jsonify({'message': 'No selected file'}), 400
        if file and file.filename.endswith('.csv'):
            filename = secure_filename(file.filename)
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(upload_path)
            try:
                df = pd.read_csv(upload_path)
                validate_csv_data(df)
                pdf_path = generate_invoice_pdf(df)
                return jsonify({'message': 'Invoices generated successfully!', 'pdf_path': pdf_path}), 200
            except CSVValidationError as e:
                logging.error(f'CSV validation error: {str(e)}')
                return jsonify({'message': f'CSV validation error: {str(e)}'}), 400
            except Exception as e:
                logging.error(f'Processing error: {str(e)}')
                return jsonify({'message': f'An error occurred: {str(e)}'}), 500
        else:
            return jsonify({'message': 'Invalid file type. Please upload a CSV file.'}), 400
    return render_template('index.html', company=CONFIG)

@app.route('/download')
def download():
    file_path = request.args.get('file')
    if file_path and os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({'message': 'File not found'}), 404

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
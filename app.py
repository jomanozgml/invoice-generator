from flask import Flask, render_template, request, redirect, url_for, send_file, flash, jsonify
import pandas as pd
from fpdf import FPDF
from datetime import datetime
from num2words import num2words
from random import randint
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
    required_columns = [
        'Created at',
        'Order Number',
        'Shipping Name',
        'Shipping Address',
        'Shipping Phone Number',
        'Item Name',
        'Variation',
        'Unit Price',
        'Tracking Code'
    ]

    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        raise CSVValidationError(f"Missing columns: {', '.join(missing_cols)}")

    # Convert 'Unit Price' to float
    df['Unit Price'] = df['Unit Price'].replace('[\$,]', '', regex=True).astype(float)

def generate_invoice_pdf(df):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    for idx, row in df.iterrows():
        pdf.add_page()
        pdf.set_margins(10, 10, 10)

        # Company Details (Centered)
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, CONFIG["company_name"], ln=True, align="C")
        # Increase font size by 2 for other details
        pdf.set_font("Arial", "I", 12)
        pdf.cell(0, 7, CONFIG["address"], ln=True, align="C")
        pdf.cell(0, 7, CONFIG["phone_number"], ln=True, align="C")
        pdf.cell(0, 7, CONFIG["email"], ln=True, align="C")

        # PAN with boxes around digits on the same line
        pdf.ln(5)
        pdf.set_font("Arial", "", 12)
        pan_digits = str(CONFIG["pan_no"])
        pan_label = "PAN : "  # Added space after "PAN :"
        pan_label_width = pdf.get_string_width(pan_label)
        digit_box_width = 7
        total_pan_width = len(pan_digits) * digit_box_width
        total_width = pan_label_width + total_pan_width
        pan_x_start = (pdf.w - total_width) / 2
        pdf.set_x(pan_x_start)
        pdf.cell(pan_label_width, 7, pan_label, ln=0)
        for digit in pan_digits:
            pdf.cell(digit_box_width, 7, digit, border=1, ln=0, align="C")
        pdf.ln(10)

        # Order Number and Date on the same line
        pdf.set_font("Arial", "", 12)
        order_text = f"Order Number: {row['Order Number']}"
        date_text = f"Date: {row['Created at']}"
        pdf.cell(0, 7, order_text, ln=0)
        pdf.cell(0, 7, date_text, ln=1, align='R')
        # Dotted underline under details
        pdf.set_x(pdf.l_margin + pdf.get_string_width("Order Number: "))
        pdf.dashed_line(pdf.get_x(), pdf.get_y(), pdf.get_x() + pdf.get_string_width(str(row['Order Number'])), pdf.get_y())
        pdf.set_x(pdf.w - pdf.r_margin - pdf.get_string_width(date_text) + pdf.get_string_width("Date: "))
        pdf.dashed_line(pdf.get_x(), pdf.get_y(), pdf.get_x() + pdf.get_string_width(str(row['Created at'])), pdf.get_y())

        # Tracking Code and Invoice No. on the same line
        pdf.ln(2)
        tracking_text = f"Tracking Code: {row['Tracking Code']}" if pd.notnull(row['Tracking Code']) else "Tracking Code: N/A"
        invoice_no = datetime.now().strftime('%Y%m%d') + str(randint(100, 999))
        invoice_text = f"Invoice No.: {invoice_no}"
        pdf.cell(0, 7, tracking_text, ln=0)
        pdf.cell(0, 7, invoice_text, ln=1, align='R')
        # Dotted underline under details
        pdf.set_x(pdf.l_margin + pdf.get_string_width("Tracking Code: "))
        pdf.dashed_line(pdf.get_x(), pdf.get_y(), pdf.get_x() + pdf.get_string_width(str(row['Tracking Code'])), pdf.get_y())
        pdf.set_x(pdf.w - pdf.r_margin - pdf.get_string_width(invoice_text) + pdf.get_string_width("Invoice No.: "))
        pdf.dashed_line(pdf.get_x(), pdf.get_y(), pdf.get_x() + pdf.get_string_width(invoice_no), pdf.get_y())

        # Customer's Name with dotted underline
        pdf.ln(4)
        customer_text = f"Customer's Name: {row['Shipping Name']}"
        pdf.cell(0, 7, customer_text, ln=1)
        pdf.set_x(pdf.l_margin + pdf.get_string_width("Customer's Name: "))
        pdf.dashed_line(pdf.get_x(), pdf.get_y(), pdf.get_x() + pdf.get_string_width(row['Shipping Name']), pdf.get_y())

        # Address on left, Contact No. on right, same line
        pdf.ln(2)
        address_text = f"Address: {row['Shipping Address']}"
        contact_text = f"Contact No.: {row['Shipping Phone Number']}"
        pdf.cell(0, 7, address_text, ln=0)
        pdf.cell(0, 7, contact_text, ln=1, align='R')
        # Dotted underline under details
        pdf.set_x(pdf.l_margin + pdf.get_string_width("Address: "))
        pdf.dashed_line(pdf.get_x(), pdf.get_y(), pdf.get_x() + pdf.get_string_width(row['Shipping Address']), pdf.get_y())
        pdf.set_x(pdf.w - pdf.r_margin - pdf.get_string_width(contact_text) + pdf.get_string_width("Contact No.: "))
        pdf.dashed_line(pdf.get_x(), pdf.get_y(), pdf.get_x() + pdf.get_string_width(row['Shipping Phone Number']), pdf.get_y())

        pdf.ln(10)

        # Table Headers
        pdf.set_font("Arial", "B", 12)
        page_width = pdf.w - 2 * pdf.l_margin
        col_widths = {
            'SN': 10,
            'Particulars': page_width - 80,
            'Inventory Code': 35,
            'Amount': 35
        }
        pdf.set_fill_color(211, 211, 211)  # Light gray fill color for borders
        pdf.set_draw_color(169, 169, 169)  # Set border color to gray
        pdf.cell(col_widths['SN'], 10, "SN", 1, 0, "C", fill=True)
        pdf.cell(col_widths['Particulars'], 10, "Particulars", 1, 0, "C", fill=True)
        pdf.cell(col_widths['Inventory Code'], 10, "Inventory Code", 1, 0, "C", fill=True)
        pdf.cell(col_widths['Amount'], 10, "Amount", 1, 1, "C", fill=True)

        # Items Table Content
        pdf.set_font("Arial", "", 12)
        amount = float(row['Unit Price'])
        pdf.cell(col_widths['SN'], 10, "1", 1, 0, "C")
        particulars = row['Item Name']
        if pd.notnull(row['Variation']):
            particulars += f" ({row['Variation']})"
        pdf.cell(col_widths['Particulars'], 10, particulars, 1, 0, "L")
        pdf.cell(col_widths['Inventory Code'], 10, "", 1, 0, "C")
        pdf.cell(col_widths['Amount'], 10, f"NRs. {amount:.2f}", 1, 1, "R")

        # Add empty row before last row
        pdf.cell(col_widths['SN'], 10, "", 1, 0, "C")
        pdf.cell(col_widths['Particulars'], 10, "", 1, 0, "L")
        pdf.cell(col_widths['Inventory Code'], 10, "", 1, 0, "C")
        pdf.cell(col_widths['Amount'], 10, "", 1, 1, "R")

        # Total Amount inside the table
        amount_in_words = num2words(amount, to='cardinal', lang='en_IN').capitalize()
        amount_in_words_text = f"Amount in Words: {amount_in_words} Rupees Only"
        # Last row with 3 columns
        total_col_widths = {
            'Particulars': col_widths['SN'] + col_widths['Particulars'],
            'Inventory Code': col_widths['Inventory Code'],
            'Amount': col_widths['Amount']
        }
        pdf.cell(total_col_widths['Particulars'], 14, amount_in_words_text, 1, 0, "L")
        pdf.cell(total_col_widths['Inventory Code'], 14, "Total Amount", 1, 0, "C")
        pdf.cell(total_col_widths['Amount'], 14, f"NRs. {amount:.2f}", 1, 1, "R")

        # Footer
        pdf.set_y(-30)
        pdf.set_font("Arial", "I", 12)
        pdf.cell(0, 10, "Thank you for your business!", 0, 0, "C")

    output_filename = f"invoices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
    pdf.output(output_path)
    return output_path

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Update company details from form data
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
                df = pd.read_csv(upload_path, sep=';', encoding='utf-8')
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
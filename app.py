from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
from fpdf import FPDF
from datetime import datetime
from num2words import num2words
import os
from werkzeug.utils import secure_filename
import logging
from dotenv import load_dotenv
import warnings

# Suppress specific openpyxl warning
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

app = Flask(__name__, static_url_path='/static')
load_dotenv()
app.secret_key = os.getenv('FLASK_SECRET_KEY')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'invoices'

# Ensure upload and output directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Setup logging
logging.basicConfig(filename='app.log', level=logging.INFO)

# Configuration
CONFIG = {
    "company_name": "MOON STAR TAILORS",
    "address": "Solteemode-14, Kathmandu",
    "phone_number": "+977 9813719892",
    "email": "info@moonstar.com.np",
    "pan_no": "605813520"
}

class CSVValidationError(Exception):
    pass

def validate_csv_data(df):
    required_columns = [
        'orderNumber', 'sellerSku', 'createTime', 'invoiceNumber',
        'customerName', 'trackingCode', 'paidPrice'
    ]

    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        raise CSVValidationError(f"Missing columns: {', '.join(missing_cols)}")

    # Convert 'paidPrice' to float
    df['paidPrice'] = df['paidPrice'].replace('[\$,]', '', regex=True).astype(float)

def generate_invoice_pdf(df):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    grouped = df.groupby('orderNumber')

    for order_number, group in grouped:
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
        pdf.ln(15)

        # Order Number and Date on the same line
        pdf.set_font("Arial", "", 12)
        order_text = f"Order Number: {order_number}"
        date_text = f"Date: {group['createTime'].iloc[0]}"
        pdf.cell(0, 7, order_text, ln=0)
        pdf.cell(0, 7, date_text, ln=1, align='R')
        # Dotted underline under details
        pdf.set_x(pdf.l_margin + pdf.get_string_width("Order Number: "))
        pdf.dashed_line(pdf.get_x(), pdf.get_y(), pdf.get_x() + pdf.get_string_width(str(order_number)), pdf.get_y())
        pdf.set_x(pdf.w - pdf.r_margin - pdf.get_string_width(date_text) + pdf.get_string_width("Date: "))
        pdf.dashed_line(pdf.get_x(), pdf.get_y(), pdf.get_x() + pdf.get_string_width(str(group['createTime'].iloc[0])), pdf.get_y())

        # Tracking Code and Invoice No. on the same line
        pdf.ln(3)
        # Update tracking code and dashed line section
        tracking_text = f"Tracking Code: {group['trackingCode'].iloc[0]}" if pd.notnull(group['trackingCode'].iloc[0]) else "Tracking Code: N/A"
        invoice_text = f"Invoice No.: {group['invoiceNumber'].iloc[0]}"
        pdf.cell(0, 7, tracking_text, ln=0)
        pdf.cell(0, 7, invoice_text, ln=1, align='R')
        # Dotted underline under details
        pdf.set_x(pdf.l_margin + pdf.get_string_width("Tracking Code: "))
        tracking_value = str(group['trackingCode'].iloc[0]) if pd.notnull(group['trackingCode'].iloc[0]) else "N/A"
        pdf.dashed_line(pdf.get_x(), pdf.get_y(), pdf.get_x() + pdf.get_string_width(tracking_value), pdf.get_y())
        pdf.set_x(pdf.w - pdf.r_margin - pdf.get_string_width(invoice_text) + pdf.get_string_width("Invoice No.: "))
        pdf.dashed_line(pdf.get_x(), pdf.get_y(), pdf.get_x() + pdf.get_string_width(str(group['invoiceNumber'].iloc[0])), pdf.get_y())

        # Customer's Name with dotted underline
        pdf.ln(5)
        customer_text = f"Customer's Name: {group['customerName'].iloc[0]}"
        pdf.cell(0, 7, customer_text, ln=1)
        pdf.set_x(pdf.l_margin + pdf.get_string_width("Customer's Name: "))
        pdf.dashed_line(pdf.get_x(), pdf.get_y(), pdf.get_x() + pdf.get_string_width(group['customerName'].iloc[0]), pdf.get_y())

        # Address on left, Contact No. on right, same line
        pdf.ln(3)
        address_text = "Address: Nepal"
        contact_text = "Contact No.: " + " " * 20  # 20 empty spaces
        pdf.set_font("Arial", "", 12)  # Reset font back to normal
        pdf.cell(0, 7, address_text, ln=0)
        pdf.cell(0, 7, contact_text, ln=1, align='R')
        # Dotted underline under details
        pdf.set_x(pdf.l_margin + pdf.get_string_width("Address: "))
        pdf.dashed_line(pdf.get_x(), pdf.get_y(), pdf.get_x() + pdf.get_string_width("Nepal"), pdf.get_y())
        pdf.set_x(pdf.w - pdf.r_margin - pdf.get_string_width(contact_text) + pdf.get_string_width("Contact No.: "))
        pdf.dashed_line(pdf.get_x(), pdf.get_y(), pdf.get_x() + pdf.get_string_width(" " * 20), pdf.get_y())

        pdf.ln(10)

        # Table Headers
        pdf.set_font("Arial", "B", 12)
        page_width = pdf.w - 2 * pdf.l_margin
        col_widths = {
            'SN': 10,
            'Particulars': page_width - 70,
            'Inv Code': 30,
            'Amount': 30
        }
        pdf.set_fill_color(211, 211, 211)  # Light gray fill color for borders
        pdf.set_draw_color(169, 169, 169)  # Set border color to gray
        pdf.cell(col_widths['SN'], 10, "SN", 1, 0, "C", fill=True)
        pdf.cell(col_widths['Particulars'], 10, "Particulars", 1, 0, "C", fill=True)
        pdf.cell(col_widths['Inv Code'], 10, "Inv Code", 1, 0, "C", fill=True)
        pdf.cell(col_widths['Amount'], 10, "Amount", 1, 1, "C", fill=True)

        # Items Table Content
        pdf.set_font("Arial", "", 12)
        total_amount = 0
        # Update amount formatting in table content
        for i, item in enumerate(group.itertuples(), start=1):
            particulars = item.sellerSku
            amount = float(item.paidPrice)
            total_amount += amount
            amount_str = f"NRs. {amount:.2f}"
            pdf.cell(col_widths['SN'], 10, str(i), 1, 0, "C")
            pdf.cell(col_widths['Particulars'], 10, particulars, 1, 0, "L")
            pdf.cell(col_widths['Inv Code'], 10, "", 1, 0, "C")
            pdf.cell(col_widths['Amount'], 10, amount_str, 1, 1, "R")

        # Add empty row before last row
        pdf.cell(col_widths['SN'], 10, "", 1, 0, "C")
        pdf.cell(col_widths['Particulars'], 10, "", 1, 0, "L")
        pdf.cell(col_widths['Inv Code'], 10, "", 1, 0, "C")
        pdf.cell(col_widths['Amount'], 10, "", 1, 1, "R")

        # Total Amount inside the table
        amount_in_words = num2words(total_amount, to='cardinal', lang='en_IN').capitalize()
        amount_in_words_text = f"{amount_in_words} Rupees Only"
        pdf.set_font("Arial", "I", 12)  # Set font to italic
        # Last row with 3 columns
        total_col_widths = {
            'Particulars': col_widths['SN'] + col_widths['Particulars'],
            'Inv Code': col_widths['Inv Code'],
            'Amount': col_widths['Amount']
        }
        pdf.cell(total_col_widths['Particulars'], 14, amount_in_words_text, 1, 0, "L")
        pdf.cell(total_col_widths['Inv Code'], 14, "Total", 1, 0, "C")
        pdf.cell(total_col_widths['Amount'], 14, f"NRs. {total_amount:.2f}", 1, 1, "R")

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
        if file and (file.filename.endswith('.csv') or file.filename.endswith('.xls') or file.filename.endswith('.xlsx')):
            filename = secure_filename(file.filename)
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(upload_path)
            try:
                if file.filename.endswith('.csv'):
                    df = pd.read_csv(upload_path, sep=None, engine='python')
                else:
                    df = pd.read_excel(upload_path)
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
            return jsonify({'message': 'Invalid file type. Please upload a CSV or Excel file.'}), 400
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
    app.run(host='0.0.0.0', port=port, debug=False)
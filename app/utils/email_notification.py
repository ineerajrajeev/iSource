from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

# Simulating notifications
notifications = [
    # {"title": "New Notification", "body": "You have a new message.", "redirect_url": "/"},
    # {"title": "Update Available", "body": "A new update is available for your app."}
]

def send_email(to_email, subject, html_content,attachment=None):
    # Gmail SMTP server details
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587  # Gmail SMTP port

    # Sender's Gmail address and password
    sender_email = 'neerajshetkar@gmail.com' #enter your email
    sender_password = 'sqds cgya rtlq ihxq' #enter code > you can get it at https://myaccount.google.com/apppasswords or search for "app password" in google account > create a new app code > format "wxyz wxyz wxyz wxyz" > enter it here

    # Create a MIME multipart message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject

    if attachment:
        # Attach file
        # part = MIMEBase('application', 'octet-stream')
        # part.set_payload(open(attachment, 'rb').read())
        # encoders.encode_base64(part)
        # part.add_header('Content-Disposition', f'attachment; filename={attachment}')
        # msg.attach(part)

        pdf_part = MIMEApplication(attachment, _subtype='pdf')
        pdf_part.add_header('Content-Disposition', 'attachment', filename='report.pdf')
        msg.attach(pdf_part)


    # Attach HTML content
    msg.attach(MIMEText(html_content, 'html','utf-8'))

    # Connect to Gmail's SMTP server
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()  # Start TLS encryption
    server.login(sender_email, sender_password)  # Login to Gmail

    # Send email
    server.sendmail(sender_email, to_email, msg.as_string())

    # Close SMTP connection
    server.quit()
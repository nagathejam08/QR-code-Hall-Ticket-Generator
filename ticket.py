import csv
import qrcode
import json
from PIL import Image, ImageDraw, ImageFont
import os
import sqlite3
import logging
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from tkinter import Tk, Label, Entry, Button, StringVar, filedialog, messagebox, Toplevel, Listbox

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)''')
    conn.commit()
    conn.close()

# HallTicketGenerator class with improved QR code positioning
class HallTicketGenerator:
    def __init__(self, csv_path, output_dir, college_name="COLLEGE NAME"):
        self.csv_path = csv_path
        self.output_dir = output_dir
        self.college_name = college_name
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        try:
            self.title_font = ImageFont.truetype("arial.ttf", 18)
            self.header_font = ImageFont.truetype("arialbd.ttf", 14)
            self.normal_font = ImageFont.truetype("arial.ttf", 12)
            self.small_font = ImageFont.truetype("arial.ttf", 10)
        except IOError:
            # Provide better fallback for font loading failures
            logging.warning("Could not load specified fonts, using default fonts")
            self.title_font = ImageFont.load_default()
            self.header_font = ImageFont.load_default()
            self.normal_font = ImageFont.load_default()
            self.small_font = ImageFont.load_default()
        
        self.width = 1000
        self.height = 750
        self.table_start_x = 50
        self.table_start_y = 200
        self.table_width = 800  # Reduced width to make room for QR code
        self.row_height = 50
        self.num_rows = 7

        logging.basicConfig(filename=os.path.join(output_dir, 'hall_ticket_generator.log'), 
                            level=logging.INFO, 
                            format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info(f"HallTicketGenerator initialized at {datetime.now()}")

    def read_csv_data(self):
        students = []
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    students.append(row)
            logging.info(f"CSV data read successfully with {len(students)} records")
            return students
        except Exception as e:
            logging.error(f"Error reading CSV file: {e}")
            return []
    
    def generate_qr_code(self, student_data):
        try:
            # Only include necessary data in QR code to reduce size
            qr_data = {
                'name': student_data['Student Name'],
                'roll': student_data['Roll Number'],
                'course': student_data['Course'],
                'semester': student_data['Semester']
            }
            data_json = json.dumps(qr_data)
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=8,
                border=4,
            )
            qr.add_data(data_json)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            logging.info(f"QR code generated successfully for {student_data['Roll Number']}")
            return qr_img
        except Exception as e:
            logging.error(f"Error generating QR code: {e}")
            return None
    
    def draw_line(self, draw, start_pos, end_pos, width=1):
        draw.line([start_pos, end_pos], fill="black", width=width)
    
    def draw_rectangle(self, draw, top_left, bottom_right, outline="black", width=1):
        draw.rectangle([top_left, bottom_right], outline=outline, width=width)
    
    def draw_text(self, draw, position, text, font, fill="black", anchor="lt"):
        draw.text(position, text, font=font, fill=fill, anchor=anchor)
    
    def draw_table(self, draw):
        table_end_x = self.table_start_x + self.table_width
        table_end_y = self.table_start_y + self.row_height * self.num_rows
        self.draw_rectangle(draw, (self.table_start_x, self.table_start_y), 
                           (table_end_x, table_end_y), width=2)
        
        for i in range(1, self.num_rows):
            y = self.table_start_y + i * self.row_height
            self.draw_line(draw, (self.table_start_x, y), 
                          (table_end_x, y), width=1)
        
        sno_width = 50
        subject_width = 200
        date_width = 150
        time_width = 150
        signature_width = 250  # Adjusted to fit within reduced table width
        
        x = self.table_start_x + sno_width
        self.draw_line(draw, (x, self.table_start_y), 
                      (x, table_end_y), width=1)
        
        x += subject_width
        self.draw_line(draw, (x, self.table_start_y), 
                      (x, table_end_y), width=1)
        
        x += date_width
        self.draw_line(draw, (x, self.table_start_y), 
                      (x, table_end_y), width=1)
        
        x += time_width
        self.draw_line(draw, (x, self.table_start_y), 
                      (x, table_end_y), width=1)
        
        header_y = self.table_start_y + self.row_height / 2
        self.draw_text(draw, (self.table_start_x + sno_width / 2, header_y), 
                      "S.No", self.header_font, anchor="mm")
        self.draw_text(draw, (self.table_start_x + sno_width + subject_width / 2, header_y), 
                      "Subject Name", self.header_font, anchor="mm")
        self.draw_text(draw, (self.table_start_x + sno_width + subject_width + date_width / 2, header_y), 
                      "Date", self.header_font, anchor="mm")
        self.draw_text(draw, (self.table_start_x + sno_width + subject_width + date_width + time_width / 2, header_y), 
                      "Time", self.header_font, anchor="mm")
        self.draw_text(draw, (self.table_start_x + sno_width + subject_width + date_width + time_width + signature_width / 2, header_y), 
                      "Invigilator Signature", self.header_font, anchor="mm")
        
        return {
            'sno_width': sno_width,
            'subject_width': subject_width,
            'date_width': date_width,
            'time_width': time_width,
            'signature_width': signature_width
        }
    
    def create_hall_ticket(self, student_data):
        try:
            image = Image.new('RGB', (self.width, self.height), color='white')
            draw = ImageDraw.Draw(image)
            
            self.draw_text(draw, (self.width / 2, 40), self.college_name, 
                          self.title_font, anchor="mm")
            self.draw_text(draw, (self.width / 2, 70), "EXAMINATION HALL TICKET", 
                          self.header_font, anchor="mm")
            
            # Check if required keys exist in student_data
            required_keys = ['Student Name', 'Roll Number', 'Course', 'Semester']
            for key in required_keys:
                if key not in student_data or not student_data[key]:
                    logging.error(f"Missing required data: {key} for student {student_data.get('Roll Number', 'Unknown')}")
                    return None
            
            # Student information section - adjusted to leave space for QR code
            self.draw_text(draw, (60, 110), "Student Name:", self.header_font)
            self.draw_text(draw, (60, 140), "Roll Number:", self.header_font)
            self.draw_text(draw, (60, 170), "Course:", self.header_font)
            self.draw_text(draw, (400, 110), "Semester:", self.header_font)
            
            self.draw_text(draw, (200, 110), student_data['Student Name'], self.normal_font)
            self.draw_text(draw, (200, 140), student_data['Roll Number'], self.normal_font)
            self.draw_text(draw, (200, 170), student_data['Course'], self.normal_font)
            self.draw_text(draw, (480, 110), student_data['Semester'], self.normal_font)
            
            # Draw QR code in proper position before drawing the table
            qr_img = self.generate_qr_code(student_data)
            if qr_img:
                qr_size = 120
                qr_img = qr_img.resize((qr_size, qr_size))
                # Position QR code in top right corner with proper padding
                qr_position = (self.width - qr_size - 60, 50)
                image.paste(qr_img, qr_position)
            
            table_dims = self.draw_table(draw)
            
            for i in range(1, 7):
                subject_key = f"Subject {i}"
                date_key = f"Date {i}"
                time_key = f"Time {i}"
                
                if subject_key in student_data and student_data[subject_key]:
                    row_y = self.table_start_y + (i) * self.row_height + self.row_height / 2
                    self.draw_text(draw, (self.table_start_x + table_dims['sno_width'] / 2, row_y), 
                                  str(i), self.normal_font, anchor="mm")
                    self.draw_text(draw, (self.table_start_x + table_dims['sno_width'] + table_dims['subject_width'] / 2, row_y), 
                                  student_data[subject_key], self.normal_font, anchor="mm")
                    date_text = student_data.get(date_key, "DD/MM/YYYY")
                    self.draw_text(draw, (self.table_start_x + table_dims['sno_width'] + table_dims['subject_width'] + 
                                        table_dims['date_width'] / 2, row_y), 
                                  date_text, self.normal_font, anchor="mm")
                    time_text = student_data.get(time_key, "HH:MM - HH:MM")
                    self.draw_text(draw, (self.table_start_x + table_dims['sno_width'] + table_dims['subject_width'] + 
                                        table_dims['date_width'] + table_dims['time_width'] / 2, row_y), 
                                  time_text, self.normal_font, anchor="mm")
            
            instructions_y = self.table_start_y + self.row_height * self.num_rows + 30
            self.draw_text(draw, (60, instructions_y), "Instructions:", self.header_font)
            
            instructions = [
                "1. Students must bring this hall ticket for every exam.",
                "2. Latecomers will not be allowed to enter the exam hall.",
                "3. Use of electronic gadgets is strictly prohibited.",
                "4. Follow all exam guidelines as instructed by the invigilator."
            ]
            
            for i, instruction in enumerate(instructions):
                self.draw_text(draw, (60, instructions_y + 25 + i * 20), instruction, self.normal_font)
            
            sig_y = instructions_y + 25 + len(instructions) * 20 + 30
            self.draw_text(draw, (60, sig_y), "Principal's Signature:", self.normal_font)
            self.draw_line(draw, (200, sig_y + 10), (350, sig_y + 10))
            self.draw_text(draw, (500, sig_y), "Student's Signature:", self.normal_font)
            self.draw_line(draw, (640, sig_y + 10), (790, sig_y + 10))
            
            filename = f"{student_data['Roll Number']}_hall_ticket.png"
            save_path = os.path.join(self.output_dir, filename)
            image.save(save_path)
            logging.info(f"Hall ticket created for {student_data['Student Name']} ({student_data['Roll Number']})")
            return save_path
        except Exception as e:
            logging.error(f"Error creating hall ticket: {e}")
            return None
    
    def generate_all_hall_tickets(self):
        students = self.read_csv_data()
        if not students:
            logging.error("No student data found or error reading CSV")
            return []
            
        generated_tickets = []
        
        for student in students:
            ticket_path = self.create_hall_ticket(student)
            if ticket_path:
                generated_tickets.append(ticket_path)
        
        logging.info(f"Generated {len(generated_tickets)} hall tickets out of {len(students)} students")
        return generated_tickets

class Application:
    def __init__(self):
        self.root = Tk()
        self.root.title("Hall Ticket Generator")
        self.root.geometry("400x300")
        self.username = StringVar()
        self.password = StringVar()
        self.init_db()
        self.create_widgets()

    def init_db(self):
        init_db()

    def create_widgets(self):
        Label(self.root, text="Hall Ticket Generator", font=("Arial", 16)).pack(pady=10)
        Label(self.root, text="Username").pack(pady=5)
        Entry(self.root, textvariable=self.username).pack(pady=5)
        Label(self.root, text="Password").pack(pady=5)
        Entry(self.root, textvariable=self.password, show="*").pack(pady=5)
        
        # Add button frame for better layout
        button_frame = Label(self.root)
        button_frame.pack(pady=5)
        Button(button_frame, text="Login", command=self.login).pack(side="left", padx=5)
        Button(button_frame, text="Clear", command=self.clear_login_fields).pack(side="left", padx=5)
        Button(button_frame, text="Register", command=self.open_register_form).pack(side="left", padx=5)

    def clear_login_fields(self):
        self.username.set("")
        self.password.set("")

    def open_register_form(self):
        register_win = Toplevel(self.root)
        register_win.title("Register")
        register_win.geometry("300x200")
        
        username = StringVar()
        password = StringVar()
        
        Label(register_win, text="Create Username").pack(pady=5)
        Entry(register_win, textvariable=username).pack(pady=5)
        Label(register_win, text="Create Password").pack(pady=5)
        Entry(register_win, textvariable=password, show="*").pack(pady=5)
        
        # Add button frame with Clear option
        button_frame = Label(register_win)
        button_frame.pack(pady=10)
        Button(button_frame, text="Register", command=lambda: self.register(username, password, register_win)).pack(side="left", padx=5)
        Button(button_frame, text="Clear", command=lambda: self.clear_register_fields(username, password)).pack(side="left", padx=5)

    def clear_register_fields(self, username, password):
        username.set("")
        password.set("")

    def register(self, username, password, window):
        if username.get() and password.get():
            try:
                # Fix: Changed the hash method to 'pbkdf2:sha256' which is supported by werkzeug
                hashed_password = generate_password_hash(password.get())
            
                conn = sqlite3.connect('database.db')
                c = conn.cursor()
                c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username.get(), hashed_password))
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Registration", "User registered successfully!")
                window.destroy()
            except sqlite3.IntegrityError:
                messagebox.showerror("Registration", "Username already exists. Please choose another.")
            except Exception as e:
                messagebox.showerror("Registration Error", f"An error occurred: {str(e)}")
        else:
            messagebox.showerror("Registration", "Please enter both username and password")

    def login(self):
        username = self.username.get()
        password = self.password.get()
        
        if not username or not password:
            messagebox.showerror("Login", "Please enter both username and password")
            return
            
        try:
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = c.fetchone()
            conn.close()
            
            if user and check_password_hash(user[2], password):
                messagebox.showinfo("Login", "Login successful!")
                self.root.withdraw()  # Hide the login window
                self.upload_window()
            else:
                messagebox.showerror("Login", "Invalid username or password")
        except Exception as e:
            messagebox.showerror("Login Error", f"An error occurred: {str(e)}")

    def upload_window(self):
        upload_win = Toplevel(self.root)
        upload_win.title("Hall Ticket Generator")
        upload_win.geometry("500x400")
        upload_win.protocol("WM_DELETE_WINDOW", self.close_application)
        
        Label(upload_win, text="Generate Hall Tickets", font=("Arial", 16)).pack(pady=10)
        
        frame = Label(upload_win)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.college_name_var = StringVar(value="East Point College")
        Label(frame, text="College Name:").pack(anchor="w", pady=5)
        Entry(frame, textvariable=self.college_name_var, width=40).pack(anchor="w", pady=5)
        
        self.output_dir_var = StringVar(value="output")
        Label(frame, text="Output Directory:").pack(anchor="w", pady=5)
        dir_frame = Label(frame)
        dir_frame.pack(fill="x", pady=5)
        Entry(dir_frame, textvariable=self.output_dir_var, width=30).pack(side="left")
        Button(dir_frame, text="Browse", command=self.browse_output_dir).pack(side="left", padx=5)
        
        # Add button frame with Clear option
        button_frame = Label(frame)
        button_frame.pack(pady=10)
        Button(button_frame, text="Upload CSV & Generate Tickets", command=self.upload_csv).pack(side="left", padx=5)
        Button(button_frame, text="Clear Form", command=self.clear_upload_form).pack(side="left", padx=5)
        
        list_frame = Label(upload_win)
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        Label(list_frame, text="Generated Hall Tickets:").pack(anchor="w")
        self.hall_ticket_list = Listbox(list_frame, width=50, height=10)
        self.hall_ticket_list.pack(fill="both", expand=True, pady=5)
        
        # Add button frame for ticket operations
        ticket_button_frame = Label(list_frame)
        ticket_button_frame.pack(pady=5)
        Button(ticket_button_frame, text="Open Selected Ticket", command=self.open_selected_ticket).pack(side="left", padx=5)
        Button(ticket_button_frame, text="Clear All Tickets", command=self.clear_all_tickets).pack(side="left", padx=5)
    
    def browse_output_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir_var.set(directory)
    
    def clear_upload_form(self):
        self.college_name_var.set("East Point College")  # Reset to default
        self.output_dir_var.set("output")  # Reset to default
        self.hall_ticket_list.delete(0, "end")  # Clear the listbox
        messagebox.showinfo("Clear", "Form has been cleared")
    
    def clear_all_tickets(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to delete all generated hall tickets?"):
            output_dir = self.output_dir_var.get()
            if os.path.exists(output_dir):
                try:
                    # Delete only PNG files (hall tickets) in the directory
                    deleted_count = 0
                    for file in os.listdir(output_dir):
                        if file.endswith("_hall_ticket.png"):
                            os.remove(os.path.join(output_dir, file))
                            deleted_count += 1
                    
                    # Clear the listbox
                    self.hall_ticket_list.delete(0, "end")
                    messagebox.showinfo("Success", f"{deleted_count} hall tickets have been deleted")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete tickets: {str(e)}")
            else:
                messagebox.showinfo("Info", "Output directory does not exist")
    
    def open_selected_ticket(self):
        selection = self.hall_ticket_list.curselection()
        if selection:
            ticket_name = self.hall_ticket_list.get(selection[0])
            output_dir = self.output_dir_var.get()
            ticket_path = os.path.join(output_dir, ticket_name)
            
            if os.path.exists(ticket_path):
                try:
                    # Platform independent way to open files
                    import subprocess
                    import sys
                    
                    if sys.platform == 'win32':
                        os.startfile(ticket_path)
                    elif sys.platform == 'darwin':  # macOS
                        subprocess.run(['open', ticket_path], check=True)
                    else:  # Linux
                        subprocess.run(['xdg-open', ticket_path], check=True)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to open file: {str(e)}")
            else:
                messagebox.showerror("Error", "File not found")
    
    def upload_csv(self):
        csv_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not csv_path:
            return
            
        output_dir = self.output_dir_var.get()
        college_name = self.college_name_var.get()
        
        # Clear the listbox
        self.hall_ticket_list.delete(0, "end")
        
        try:
            # Create output directory if it doesn't exist
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            generator = HallTicketGenerator(csv_path, output_dir, college_name)
            tickets = generator.generate_all_hall_tickets()
            
            if tickets:
                for ticket_path in tickets:
                    self.hall_ticket_list.insert("end", os.path.basename(ticket_path))
                
                messagebox.showinfo("Success", f"{len(tickets)} hall tickets generated in {output_dir}")
            else:
                messagebox.showwarning("Warning", "No hall tickets were generated. Check the log file for details.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
    
    def close_application(self):
        self.root.destroy()
    
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = Application()
    app.run()
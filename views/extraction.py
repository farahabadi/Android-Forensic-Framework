import customtkinter
from subprocess import call



class Extraction(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("Extraction")
        self.geometry("600x300")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.textbox = customtkinter.CTkTextbox(master=self, corner_radius=10, font=("FreeSans", 20))

        self.textbox.grid(row=0, column=0, sticky="new")
        self.textbox.insert("0.0", "Please connect your phone to usb cable and enable usb debugging\nAfter that click start button")

        self.button1 = customtkinter.CTkButton(self, text="Start Extraction", command=self.button_callback)
        self.button1.grid(row=1, column=0, padx=20, pady=20, sticky="ew", columnspan=2)

        # self.button2 = customtkinter.CTkButton(self, text="Open Files", command=self.button_callback)
        # self.button2.grid(row=1, column=0, padx=20, pady=20, sticky="ew", columnspan=2)

        
    def button_callback(self):
        rc = call("bash/extract.sh")

import customtkinter
from .extraction import Extraction



class MyCheckboxFrame(customtkinter.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        self.checkbox_1 = customtkinter.CTkCheckBox(self, text="checkbox 1")
        self.checkbox_1.grid(row=2, column=0, padx=20, pady=20, sticky="w")
        self.checkbox_2 = customtkinter.CTkCheckBox(self, text="checkbox 2")
        self.checkbox_2.grid(row=2, column=1, padx=20, pady=20, sticky="e")

    def get(self, number):
        if (number == 1):
            return self.checkbox_1.get()
        elif (number == 2):
            return self.checkbox_2.get()


    

class WelcomePage(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("my app")
        self.geometry("600x300")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure((0,1, 2), weight=1)

        self.checkbox_frame = MyCheckboxFrame(self)
        self.checkbox_frame.grid(row=2, column=0, padx=20, pady=20, sticky="we")

        self.button1 = customtkinter.CTkButton(self, text="Start Extraction", command=self.button_callback)
        self.button1.grid(row=0, column=0, padx=20, pady=20, sticky="ew", columnspan=2)

        self.button2 = customtkinter.CTkButton(self, text="Open Files", command=self.button_callback)
        self.button2.grid(row=1, column=0, padx=20, pady=20, sticky="ew", columnspan=2)

        
    def button_callback(self):
        print("button pressed")
        self.quit()
        self.destroy()
        app = Extraction()
        app.mainloop()
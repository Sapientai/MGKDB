from tkinter import *

class Window(Frame):
    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.master = master
        self.state = {}
        self.init_window()
        
    
    def init_window(self):
        self.master.title("MGKDB")
        self.pack(fill=BOTH, expand=1)

        topTextFrame = Frame(self)
        topTextFrame.pack(fill=X)
        
        topText = Text(topTextFrame, height=2, width=90)
        topText.pack(side=TOP, padx=5, pady=5)
        topText.insert(END, "Enter your database username and password to upload files.\nCheck the box if you are uploading multiple runs.")

        usernameFrame = Frame(self)
        usernameFrame.pack(fill=X)

        usernameLabel = Label(usernameFrame, text="Username: ", width=10)
        usernameLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.username = StringVar()
        usernameEntry = Entry(usernameFrame, textvariable=self.username)
        usernameEntry.pack(fill=X, padx=5, expand=True)
        usernameEntry.focus_set()

        passwordFrame = Frame(self)
        passwordFrame.pack(fill=X)

        passwordLabel = Label(passwordFrame, text="Password: ", width=10)
        passwordLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.password = StringVar()
        passwordEntry = Entry(passwordFrame, textvariable=self.password)
        passwordEntry.pack(fill=X, padx=5, expand=True)

        multirunsFrame = Frame(self)
        multirunsFrame.pack(fill=X)

        self.multiruns = BooleanVar()
        multirunsCheckbox = Checkbutton(multirunsFrame, text="Multiple Runs", variable=self.multiruns, onvalue=True, offvalue=False)
        multirunsCheckbox.pack()

        utilsFrame = Frame(self)
        utilsFrame.pack(fill=X)

        goButton = Button(utilsFrame, text="Go", command=self.go)
        self.master.bind("<Return>", self.go)
        goButton.pack(side=RIGHT, padx=5, pady=5)

        cancelButton = Button(utilsFrame, text="Cancel", command=self.cancel)
        cancelButton.pack(side=RIGHT, padx=5, pady=5)

    def go(self, event=None):
        username = self.username.get()
        password = self.password.get()
        multiruns = self.multiruns.get()
        self.state = {"username": username, "password": password, "multiruns": multiruns}
        self.master.quit()
        
    def cancel(self, event=None):
        exit()


def get_user_info():
    credentials_window = Tk()
    credentials_window.geometry("500x180")
    app = Window(credentials_window)
    credentials_window.mainloop()
    return app.state
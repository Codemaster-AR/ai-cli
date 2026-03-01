from tkinter import *

# Create the main window
root = Tk()
root.title("Calculator")

# Global variable to store the current expression
expression = ""

# Function to update the expression variable
def update_expression(num):
    global expression
    expression += str(num)
    equation.set(expression)

# Function to evaluate the expression
def evaluate():
    global expression
    try:
        result = eval(expression)
        equation.set(result)
        expression = str(result)
    except:
        equation.set("Error")
        expression = ""

# Function to clear the expression
def clear():
    global expression
    expression = ""
    equation.set("")

# Create the entry field for the equation
equation = StringVar()
entry_field = Entry(root, textvariable=equation, width=20)
entry_field.grid(row=0, column=0, columnspan=4)

# Create the number buttons
button_1 = Button(root, text="1", width=5, command=lambda: update_expression(1))
button_1.grid(row=1, column=0)
button_2 = Button(root, text="2", width=5, command=lambda: update_expression(2))
button_2.grid(row=1, column=1)
button_3 = Button(root, text="3", width=5, command=lambda: update_expression(3))
button_3.grid(row=1, column=2)

button_4 = Button(root, text="4", width=5, command=lambda: update_expression(4))
button_4.grid(row=2, column=0)
button_5 = Button(root, text="5", width=5, command=lambda: update_expression(5))
button_5.grid(row=2, column=1)
button_6 = Button(root, text="6", width=5, command=lambda: update_expression(6))
button_6.grid(row=2, column=2)

button_7 = Button(root, text="7", width=5, command=lambda: update_expression(7))
button_7.grid(row=3, column=0)
button_8 = Button(root, text="8", width=5, command=lambda: update_expression(8))
button_8.grid(row=3, column=1)
button_9 = Button(root, text="9", width=5, command=lambda: update_expression(9))
button_9.grid(row=3, column=2)

button_0 = Button(root, text="0", width=5, command=lambda: update_expression(0))
button_0.grid(row=4, column=0)

# Create the operator buttons
button_add = Button(root, text="+", width=5, command=lambda: update_expression("+"))
button_add.grid(row=1, column=3)
button_subtract = Button(root, text="-", width=5, command=lambda: update_expression("-"))
button_subtract.grid(row=2, column=3)
button_multiply = Button(root, text="*", width=5, command=lambda: update_expression("*"))
button_multiply.grid(row=3, column=3)
button_divide = Button(root, text="/", width=5, command=lambda: update_expression("/"))
button_divide.grid(row=4, column=3)

button_equals = Button(root, text="=", width=10, command=evaluate)
button_equals.grid(row=4, column=1, columnspan=2)

button_clear = Button(root, text="Clear", width=20, command=clear)
button_clear.grid(row=5, column=0, columnspan=4)

# Start the main loop
root.mainloop()
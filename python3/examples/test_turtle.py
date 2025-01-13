from turtle import *

pen1 = Turtle()


def drawCircle(pen1, x, y, r):
    """
    draw a circle with radius r and position (x, y)
    """
    pen1.penup()
    pen1.goto(x, y)
    pen1.down()
    pen1.circle(r)
    pen1.seth(0)
    pen1.penup()


drawCircle(pen1, 0, 0, 100)

done()

import pyttsx3

engine=pyttsx3.init()
engine.setProperty('rate',180)

def parler(text):
    engine.say(text)
    engine.runAndWait()


for i in range(11):
    parler(f"5 fois {i} égale à {5*i}")